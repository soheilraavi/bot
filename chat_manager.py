"""
مدیریت چت تک‌پیامی — ویرایش یک پیام به جای ارسال پیام‌های جدید
"""

import logging
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from database import db


async def safe_edit(message: Message, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """ویرایش پیام با fallback"""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception:
        return False


async def show_panel(
    bot: Bot,
    user_id: int,
    chat_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    callback: CallbackQuery = None,
    force_new: bool = False,
) -> int:
    """
    نمایش/ویرایش پیام اصلی منو.
    همیشه سعی می‌کند همان پیام را edit کند.
    """
    menu_id = await db.get_menu_message_id(user_id)

    if callback and callback.message and not force_new:
        if await safe_edit(callback.message, text, reply_markup, parse_mode):
            mid = callback.message.message_id
            await db.set_menu_message_id(user_id, mid)
            await db.track_chat_message(user_id, mid)
            return mid

    if menu_id and not force_new:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=menu_id,
                reply_markup=reply_markup, parse_mode=parse_mode,
            )
            return menu_id
        except Exception:
            pass

    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    await db.set_menu_message_id(user_id, sent.message_id)
    await db.track_chat_message(user_id, sent.message_id)
    return sent.message_id


async def track_message(user_id: int, message_id: int):
    """ثبت پیام برای پاکسازی بعدی"""
    await db.track_chat_message(user_id, message_id)


async def cleanup_chat(bot: Bot, user_id: int):
    """پاک کردن همه پیام‌ها به جز منوی اصلی"""
    menu_id = await db.get_menu_message_id(user_id)
    msg_ids = await db.get_tracked_messages(user_id)
    for mid in msg_ids:
        if mid == menu_id:
            continue
        try:
            await bot.delete_message(user_id, mid)
        except Exception:
            pass
    await db.clear_tracked_messages(user_id, keep=menu_id)
