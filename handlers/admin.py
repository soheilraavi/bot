import asyncio
import os
import math
import shutil
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ITEMS_PER_PAGE, ACCOUNTS_FILE, DB_NAME
from database import db
from states import (AddAccountStates, EditAccountStates, AddPlanStates, EditPlanStates,
                    AddCouponStates, EditCouponStates, AddTutorialStates, EditTutorialStates, AdminStates)
from filters import IsAdmin, IsOwner
from keyboards import (admin_main_kb, admin_order_actions_kb, admin_account_actions_kb,
                       admin_plan_actions_kb, admin_plan_price_kb, admin_plan_days_kb,
                       admin_coupon_actions_kb, admin_coupon_discount_kb, admin_coupon_limit_kb,
                       admin_tutorial_actions_kb, admin_ticket_actions_kb,
                       admin_customer_actions_kb, admin_admin_actions_kb, admin_settings_kb,
                       back_kb, confirm_delete_kb, admin_acc_plan_select_kb, admin_edit_messages_kb)

router = Router()


async def safe_edit(message, text, reply_markup=None, parse_mode=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


# ============ MAIN ============
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ دسترسی ندارید.")
        return
    s = await db.get_stats()
    text = (f"👑 <b>پنل مدیریت</b>\n\n"
            f"👥 کاربران: {s['users']}\n⏳ سفارش: {s['pending']}\n"
            f"🎫 تیکت: {s['open_tickets']}\n📦 آزاد: {s['free']}\n"
            f"⏸ رزرو: {s['pending_acc']}\n💳 کیف پول: {s['wallet_total']:,}\n"
            f"🔓 آنلاک: {s['apple_pending']}")
    await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await db.log("LOGIN", message.from_user.id, "", message.from_user.username)


@router.callback_query(F.data == "admin_back", IsAdmin())
async def admin_back(callback: CallbackQuery):
    s = await db.get_stats()
    text = (f"👑 <b>پنل مدیریت</b>\n\n"
            f"👥 کاربران: {s['users']}\n⏳ سفارش: {s['pending']}\n"
            f"🎫 تیکت: {s['open_tickets']}\n📦 آزاد: {s['free']}\n"
            f"⏸ رزرو: {s['pending_acc']}\n💳 کیف پول: {s['wallet_total']:,}\n"
            f"🔓 آنلاک: {s['apple_pending']}")
    await safe_edit(callback.message, text, admin_main_kb(), "HTML")
    await callback.answer()


# ============ ORDERS ============
@router.callback_query(F.data == "admin_orders", IsAdmin())
async def show_orders_main(callback: CallbackQuery):
    try:
        orders = await db.get_all_orders(limit=20)
        
        text = "📥 <b>سفارش‌ها</b>\n\n"
        kb = InlineKeyboardBuilder()
        
        if not orders:
            text += "❌ سفارشی ثبت نشده."
        else:
            for o in orders:
                order_id = o[0]
                price = o[3]
                status = o[4]
                
                emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "❓")
                text += f"{emoji} #{order_id} | 💰 {price:,}\n"
                kb.button(text=f"{emoji} #{order_id}", callback_data=f"admin_order_view_{order_id}")
            kb.adjust(2)
        
        kb.button(text="🔙 بازگشت", callback_data="admin_back")
        await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    except Exception as e:
        logging.error(f"Error in show_orders_main: {e}")
        await safe_edit(callback.message, f"❌ خطا: {str(e)}", back_kb("admin_back"))
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_view_"), IsAdmin())
async def view_order_detail(callback: CallbackQuery):
    try:
        order_id = int(callback.data.replace("admin_order_view_", ""))
        o = await db.get_order(order_id)
        
        if not o:
            await callback.answer("❌ سفارش یافت نشد", show_alert=True)
            return
        
        user_id = o[1]
        plan_id = o[2]
        price = o[3]
        status = o[4]
        
        user_info = await db.get_user(user_id)
        username = user_info[2] if user_info and user_info[2] else f"ID:{user_id}"
        
        plan_info = await db.get_plan(plan_id)
        plan_name = plan_info[1] if plan_info else "نامشخص"
        
        status_text = {"pending": "⏳ در انتظار", "approved": "✅ تایید شده", "rejected": "❌ رد شده"}.get(status, "❓")
        
        text = (f"📥 <b>سفارش #{order_id}</b>\n\n"
                f"👤 کاربر: @{username}\n"
                f"📦 پلن: {plan_name}\n"
                f"💰 مبلغ: {price:,} تومان\n"
                f"📊 وضعیت: {status_text}")
        
        kb = InlineKeyboardBuilder()
        if status == "pending":
            kb.button(text="✅ تایید و تحویل", callback_data=f"admin_order_approve_{order_id}")
            kb.button(text="❌ رد کردن", callback_data=f"admin_order_reject_{order_id}")
            kb.adjust(2)
        
        kb.button(text="🔙 بازگشت", callback_data="admin_orders")
        kb.adjust(1, 1)
        
        await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    except Exception as e:
        logging.error(f"Error in view_order_detail: {e}")
        await safe_edit(callback.message, f"❌ خطا: {str(e)}", back_kb("admin_orders"))
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_approve_"), IsAdmin())
async def approve_order_callback(callback: CallbackQuery, bot: Bot):
    try:
        order_id = int(callback.data.replace("admin_order_approve_", ""))
        logging.info(f"🔍 [BOT] Approving order #{order_id}")
        
        o = await db.get_order(order_id)
        if not o:
            await callback.answer("❌ سفارش یافت نشد", show_alert=True)
            return
        
        current_status = o[4]
        if current_status == "approved":
            await callback.answer("⚠️ این سفارش قبلاً تایید شده!", show_alert=True)
            return
        
        if current_status == "rejected":
            await callback.answer("⚠️ این سفارش قبلاً رد شده!", show_alert=True)
            return
        
        user_id = o[1]
        plan_id = o[2]
        
        p = await db.get_plan(plan_id)
        if not p:
            await callback.answer("❌ پلن یافت نشد", show_alert=True)
            return
        
        free = await db.get_free_account(plan_id=plan_id)
        acc_id = o[6] if len(o) > 6 else None
        acc_u = acc_p = None

        if acc_id:
            acc = await db.get_account(acc_id)
            if acc and acc[4] == 'pending':
                acc_u, acc_p = acc[1], acc[2]
            else:
                acc_id = None

        if not acc_id:
            if not free:
                free = await db.get_free_account()
            if not free:
                await callback.answer("❌ هیچ اکانت آزادی موجود نیست!", show_alert=True)
                return
            acc_id, acc_u, acc_p = free
        
        success = await db.update_order_status(order_id, "approved", acc_id)
        if not success:
            await callback.answer("⚠️ سفارش قبلاً پردازش شده!", show_alert=True)
            return
        
        await db.sell_account(acc_id, user_id)
        await db.process_referral_bonus(user_id)
        
        try:
            expire_at = (datetime.now() + timedelta(days=p[3])).isoformat()
            await db.update_order_expire(order_id, expire_at)
        except Exception as e:
            logging.error(f"⚠️ Error setting expire: {e}")
        
        try:
            expire_date_str = (datetime.now() + timedelta(days=p[3])).strftime("%Y/%m/%d")
            approval_text = await db.get_message("order_approved")
            if not approval_text:
                approval_text = (
                    "🎉 تبریک! سفارش شما تایید شد.\n\n"
                    "🎯 پلن: {plan}\n"
                    "👤 Username: <code>{username}</code>\n"
                    "🔑 Password: <code>{password}</code>\n\n"
                    "📅 مدت اشتراک: {days} روز\n"
                    "⏰ تاریخ انقضا: {expire_date}\n\n"
                    "✅ اطلاعات بالا رو با دقت ذخیره کنید."
                )
            try:
                msg_text = approval_text.format(
                    plan=p[1], username=acc_u, password=acc_p,
                    days=p[3], expire_date=expire_date_str
                )
            except:
                msg_text = approval_text
            await bot.send_message(user_id, msg_text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"❌ Error sending to user: {e}")
        
        await db.log("APPROVE", callback.from_user.id, f"Order {order_id}", callback.from_user.username)
        
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.answer("✅ تایید و تحویل شد", show_alert=True)
        await show_orders_main(callback)
        
    except Exception as e:
        logging.error(f"❌ CRITICAL in approve_order: {e}", exc_info=True)
        await callback.answer(f"❌ خطا: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("admin_order_reject_"), IsAdmin())
async def reject_order_callback(callback: CallbackQuery, bot: Bot):
    try:
        order_id = int(callback.data.replace("admin_order_reject_", ""))
        o = await db.get_order(order_id)
        
        if not o:
            await callback.answer("❌ سفارش یافت نشد", show_alert=True)
            return
        
        current_status = o[4]
        if current_status == "approved":
            await callback.answer("⚠️ این سفارش قبلاً تایید شده!", show_alert=True)
            return
        
        if current_status == "rejected":
            await callback.answer("⚠️ این سفارش قبلاً رد شده!", show_alert=True)
            return
        
        user_id = o[1]
        
        success = await db.update_order_status(order_id, "rejected")
        if not success:
            await callback.answer("⚠️ سفارش قبلاً پردازش شده!", show_alert=True)
            return

        await db.release_pending_account(order_id)
        try:
            await bot.send_message(user_id, "❌ سفارش شما رد شد.")
        except:
            pass
        
        await db.log("REJECT", callback.from_user.id, f"Order {order_id}", callback.from_user.username)
        
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.answer("❌ رد شد", show_alert=True)
        await show_orders_main(callback)
    except Exception as e:
        logging.error(f"Error in reject_order: {e}")
        await callback.answer(f"❌ خطا: {str(e)}", show_alert=True)


# ============ SEND MESSAGE TO USER ============
@router.callback_query(F.data == "admin_send_msg", IsAdmin())
async def start_send_message(callback: CallbackQuery, state: FSMContext):
    await safe_edit(
        callback.message,
        "📨 <b>ارسال پیام خصوصی به کاربر</b>\n\n"
        "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
        "💡 آیدی عددی کاربر را می‌توانید از بخش مشتریان دریافت کنید.",
        parse_mode="HTML"
    )
    await state.update_data(send_msg_step="user_id")
    await state.set_state(AdminStates.send_message_to_user)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cust_pv_"), IsAdmin())
async def send_pv_to_customer(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("admin_cust_pv_", ""))
    await state.update_data(send_msg_step="message", target_user_id=user_id)
    await safe_edit(
        callback.message,
        f"📨 <b>ارسال پیام به کاربر</b>\n\n"
        f"👤 آیدی کاربر: <code>{user_id}</code>\n\n"
        f"💬 لطفاً پیام خود را ارسال کنید:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.send_message_to_user)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ticket_pv_"), IsAdmin())
async def send_pv_from_ticket(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.replace("admin_ticket_pv_", ""))
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("❌ تیکت یافت نشد", show_alert=True)
        return
    
    user_id = ticket[1]
    await state.update_data(send_msg_step="message", target_user_id=user_id)
    await safe_edit(
        callback.message,
        f"📨 <b>ارسال پیام خصوصی</b>\n\n"
        f"🎫 از تیکت #{ticket_id}\n"
        f"👤 آیدی کاربر: <code>{user_id}</code>\n\n"
        f"💬 لطفاً پیام خود را ارسال کنید:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.send_message_to_user)
    await callback.answer()


@router.message(AdminStates.send_message_to_user, IsAdmin())
async def handle_send_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    step = data.get("send_msg_step")
    
    if step == "user_id":
        try:
            user_id = int(message.text.strip())
            user = await db.get_user(user_id)
            if not user:
                await message.answer("❌ کاربری با این آیدی یافت نشد.\nدوباره تلاش کنید یا /cancel بزنید.")
                return
            await state.update_data(send_msg_step="message", target_user_id=user_id)
            await message.answer(
                f"✅ کاربر یافت شد:\n\n"
                f"👤 نام: {user[3] or '-'}\n"
                f"📛 یوزرنیم: @{user[2] or '-'}\n\n"
                f"💬 حالا پیام خود را ارسال کنید:"
            )
        except:
            await message.answer("❌ آیدی نامعتبر. دوباره تلاش کنید.")
    
    elif step == "message":
        target_user_id = data.get("target_user_id")
        try:
            await bot.send_message(
                target_user_id,
                f"📨 <b>پیام از پشتیبانی</b>\n\n{message.text}",
                parse_mode="HTML"
            )
            await message.answer(
                f"✅ پیام با موفقیت ارسال شد.\n\n"
                f"👤 به کاربر: <code>{target_user_id}</code>",
                reply_markup=admin_main_kb(),
                parse_mode="HTML"
            )
            await db.log("SEND_PV", message.from_user.id, f"To {target_user_id}", message.from_user.username)
            await state.clear()
        except Exception as e:
            await message.answer(f"❌ خطا در ارسال پیام: {str(e)}\n\nآیا کاربر ربات را استارت کرده است؟")


# ============ EDIT MESSAGES ============
@router.callback_query(F.data == "admin_edit_messages", IsOwner())
async def edit_messages_menu(callback: CallbackQuery):
    await safe_edit(
        callback.message,
        "📝 <b>ویرایش متن‌های ربات</b>\n\n"
        "متن مورد نظر را برای ویرایش انتخاب کنید:\n\n"
        "💡 از تگ‌های HTML می‌توانید استفاده کنید.",
        reply_markup=admin_edit_messages_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_msg_"), IsOwner())
async def edit_message_start(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("admin_edit_msg_", "")
    current_text = await db.get_message(key, "")
    await state.update_data(edit_msg_key=key)
    await state.set_state(AdminStates.edit_message_key)
    await safe_edit(
        callback.message,
        f"📝 <b>ویرایش متن</b>\n\n"
        f"🔑 کلید: <code>{key}</code>\n\n"
        f"📄 <b>متن فعلی:</b>\n{current_text}\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"✏️ <b>متن جدید را ارسال کنید:</b>",
        reply_markup=back_kb("admin_edit_messages"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.edit_message_key, IsOwner())
async def edit_message_save(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("edit_msg_key")
    new_text = message.text
    
    await db.set_message(key, new_text)
    await db.log("EDIT_MSG", message.from_user.id, f"Key: {key}", message.from_user.username)
    await state.clear()
    
    await message.answer(
        f"✅ متن با موفقیت ذخیره شد.\n\n"
        f"🔑 کلید: <code>{key}</code>\n"
        f"📝 طول متن: {len(new_text)} کاراکتر",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ============ ACCOUNTS ============
@router.callback_query(F.data == "admin_accounts", IsAdmin())
@router.callback_query(F.data.regexp(r"^admin_accounts_plan_\d+$"), IsAdmin())
async def show_accounts(callback: CallbackQuery):
    data = callback.data
    plan_id = None
    if "plan_" in data:
        parts = data.split("_")
        idx = parts.index("plan")
        plan_id = int(parts[idx + 1])
    plans = await db.get_all_plans()
    text = "📦 <b>مدیریت اکانت‌ها</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not plan_id:
        text += "🎯 یک پلن را انتخاب کنید:\n\n"
        for p in plans:
            count = await db.count_accounts(plan_id=p[0])
            text += f"🔹 {p[1]}: {count} اکانت\n"
            kb.button(text=f"📋 {p[1]} ({count})", callback_data=f"admin_accounts_plan_{p[0]}")
        kb.adjust(1)
        kb.button(text="📥 دانلود فایل اکانت‌ها", callback_data="admin_acc_download")
    else:
        plan = await db.get_plan(plan_id)
        plan_name = plan[1] if plan else "?"
        text += f"🎯 پلن: <b>{plan_name}</b>\n\n"
        accs = await db.get_all_accounts(plan_id=plan_id)
        if not accs:
            text += "❌ اکانتی نیست.\n"
        else:
            for a in accs:
                emoji = "🟢" if a[4] == "free" else "🔴"
                text += f"{emoji} {a[1]} | {a[2]}\n"
        kb.button(text="➕ افزودن اکانت", callback_data="admin_acc_add")
        kb.button(text="🔙 بازگشت به لیست پلن‌ها", callback_data="admin_accounts")
        kb.adjust(1, 1)
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_acc_download", IsAdmin())
async def download_accounts(callback: CallbackQuery):
    accs = await db.get_all_accounts()
    if not accs:
        await callback.answer("❌ اکانتی نیست!", show_alert=True)
        return
    filename = f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for a in accs:
            plan = await db.get_plan(a[3])
            plan_name = plan[1] if plan else "?"
            f.write(f"{a[1]}:{a[2]} | {plan_name} | {a[4]}\n")
    file = FSInputFile(filename)
    await callback.message.answer_document(file, caption=f"📦 {len(accs)} اکانت")
    os.remove(filename)
    await callback.answer()


@router.callback_query(F.data == "admin_acc_add", IsAdmin())
async def add_acc_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "👤 Username اکانت:")
    await state.set_state(AddAccountStates.username)
    await callback.answer()


@router.message(AddAccountStates.username, IsAdmin())
async def add_acc_username(message: Message, state: FSMContext):
    await state.update_data(acc_user=message.text.strip())
    await message.answer("🔑 Password اکانت:")
    await state.set_state(AddAccountStates.password)


@router.message(AddAccountStates.password, IsAdmin())
async def add_acc_password(message: Message, state: FSMContext):
    await state.update_data(acc_pass=message.text.strip())
    await message.answer("📝 یادداشت (یا /skip):")
    await state.set_state(AddAccountStates.note)


@router.message(AddAccountStates.note, IsAdmin())
async def add_acc_note(message: Message, state: FSMContext):
    note = "" if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(acc_note=note)
    plans = await db.get_all_plans()
    if not plans:
        await state.clear()
        await message.answer("❌ اول پلن بسازید!", reply_markup=admin_main_kb())
        return
    await message.answer("🎯 این اکانت برای کدام پلن؟", reply_markup=admin_acc_plan_select_kb(plans))
    await state.set_state(AddAccountStates.plan)


@router.callback_query(F.data.regexp(r"^admin_acc_plan_\d+$"), AddAccountStates.plan, IsAdmin())
async def add_acc_plan_selected(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    try:
        await db.add_account(data['acc_user'], data['acc_pass'], plan_id, data.get('acc_note', ''))
    except ValueError as e:
        await state.clear()
        await callback.answer(str(e), show_alert=True)
        await callback.message.answer(f"❌ {e}", reply_markup=admin_main_kb())
        return
    plan = await db.get_plan(plan_id)
    await state.clear()
    await callback.message.answer(
        f"✅ اضافه شد!\n\n👤 {data['acc_user']}\n🎯 {plan[1] if plan else '?'}",
        reply_markup=admin_main_kb())
    await db.log("ADD_ACC", callback.from_user.id, data['acc_user'], callback.from_user.username)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_acc_edit_user_\d+$"), IsAdmin())
async def edit_acc_user_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_acc_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "👤 Username جدید:")
    await state.set_state(EditAccountStates.username)
    await callback.answer()


@router.message(EditAccountStates.username, IsAdmin())
async def edit_acc_user_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_account_field(data['edit_acc_id'], "username", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_acc_edit_pass_\d+$"), IsAdmin())
async def edit_acc_pass_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_acc_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "🔑 Password جدید:")
    await state.set_state(EditAccountStates.password)
    await callback.answer()


@router.message(EditAccountStates.password, IsAdmin())
async def edit_acc_pass_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_account_field(data['edit_acc_id'], "password", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_acc_edit_note_\d+$"), IsAdmin())
async def edit_acc_note_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_acc_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "📝 یادداشت جدید (یا /skip):")
    await state.set_state(EditAccountStates.note)
    await callback.answer()


@router.message(EditAccountStates.note, IsAdmin())
async def edit_acc_note_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    note = "" if message.text.strip() == "/skip" else message.text.strip()
    await db.update_account_field(data['edit_acc_id'], "note", note)
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_acc_delete_\d+$"), IsAdmin())
async def ask_delete_acc(callback: CallbackQuery):
    aid = int(callback.data.split("_")[-1])
    await safe_edit(callback.message, f"⚠️ حذف اکانت #{aid}؟", confirm_delete_kb("acc", aid, "admin_accounts"))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^confirm_delete_acc_\d+$"), IsAdmin())
async def confirm_delete_acc(callback: CallbackQuery):
    await db.delete_account(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_accounts(callback)


# ============ PLANS ============
@router.callback_query(F.data == "admin_plans", IsAdmin())
async def show_plans(callback: CallbackQuery):
    plans = await db.get_all_plans()
    text = "💎 <b>پلن‌ها:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not plans:
        text += "❌ پلنی نیست."
    else:
        for p in plans:
            emoji = "🟢" if p[4] else "🔴"
            text += f"{emoji} #{p[0]} | {p[1]} | {p[2]:,}ت | {p[3]} روز\n"
            kb.button(text=f"{emoji} {p[1]}", callback_data=f"admin_plan_view_{p[0]}")
        kb.adjust(1)
    kb.button(text="➕ افزودن", callback_data="admin_plan_add")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1, 1)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_plan_view_\d+$"), IsAdmin())
async def view_plan(callback: CallbackQuery):
    pid = int(callback.data.split("_")[-1])
    p = await db.get_plan(pid)
    text = (f"💎 <b>پلن #{p[0]}</b>\n\n📛 {p[1]}\n💰 {p[2]:,} تومان\n"
            f"📅 {p[3]} روز\n📊 {'فعال 🟢' if p[4] else 'غیرفعال 🔴'}")
    await safe_edit(callback.message, text, admin_plan_actions_kb(pid, p[4]), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_plan_add", IsAdmin())
async def add_plan_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "📛 نام پلن:")
    await state.set_state(AddPlanStates.name)
    await callback.answer()


@router.message(AddPlanStates.name, IsAdmin())
async def add_plan_name(message: Message, state: FSMContext):
    await state.update_data(plan_name=message.text.strip())
    await message.answer("💰 قیمت (عدد):")
    await state.set_state(AddPlanStates.price)


@router.message(AddPlanStates.price, IsAdmin())
async def add_plan_price(message: Message, state: FSMContext):
    try:
        await state.update_data(plan_price=int(message.text.strip()))
        await message.answer("📅 مدت (روز):")
        await state.set_state(AddPlanStates.days)
    except:
        await message.answer("❌ عدد معتبر.")


@router.message(AddPlanStates.days, IsAdmin())
async def add_plan_days(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        await db.add_plan(data['plan_name'], data['plan_price'], int(message.text.strip()))
        await state.clear()
        await message.answer("✅ اضافه شد.", reply_markup=admin_main_kb())
    except:
        await message.answer("❌ خطا.")


@router.callback_query(F.data.regexp(r"^admin_plan_edit_name_\d+$"), IsAdmin())
async def edit_plan_name_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_plan_id=int(callback.data.split("_")[-1]), edit_field="name")
    await safe_edit(callback.message, "📛 نام جدید:")
    await state.set_state(EditPlanStates.name)
    await callback.answer()


@router.message(EditPlanStates.name, IsAdmin())
async def edit_plan_name_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_plan_field(data['edit_plan_id'], "name", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_plan_edit_price_\d+$"), IsAdmin())
async def edit_plan_price_menu(callback: CallbackQuery):
    pid = int(callback.data.split("_")[-1])
    p = await db.get_plan(pid)
    await safe_edit(callback.message, "💰 قیمت:", admin_plan_price_kb(pid, p[2]), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_plan_price_(up|down)_\d+_\d+$"), IsAdmin())
async def edit_plan_price_change(callback: CallbackQuery):
    parts = callback.data.split("_")
    d, pid, amt = parts[3], int(parts[4]), int(parts[5])
    p = await db.get_plan(pid)
    np = max(0, p[2] + (amt if d == "up" else -amt))
    await db.update_plan_field(pid, "price", np)
    await callback.answer(f"✅ {np:,}", show_alert=True)
    await safe_edit(callback.message, "💰 قیمت:", admin_plan_price_kb(pid, np), "HTML")


@router.callback_query(F.data.regexp(r"^admin_plan_price_custom_\d+$"), IsAdmin())
async def edit_plan_price_custom(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_plan_id=int(callback.data.split("_")[-1]), edit_field="price")
    await safe_edit(callback.message, "💰 قیمت دلخواه (عدد):")
    await state.set_state(EditPlanStates.price)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_plan_edit_days_\d+$"), IsAdmin())
async def edit_plan_days_menu(callback: CallbackQuery):
    pid = int(callback.data.split("_")[-1])
    p = await db.get_plan(pid)
    await safe_edit(callback.message, "📅 مدت:", admin_plan_days_kb(pid, p[3]), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_plan_days_(up|down)_\d+_\d+$"), IsAdmin())
async def edit_plan_days_change(callback: CallbackQuery):
    parts = callback.data.split("_")
    d, pid, amt = parts[3], int(parts[4]), int(parts[5])
    p = await db.get_plan(pid)
    nd = max(1, p[3] + (amt if d == "up" else -amt))
    await db.update_plan_field(pid, "days", nd)
    await callback.answer(f"✅ {nd} روز", show_alert=True)
    await safe_edit(callback.message, "📅 مدت:", admin_plan_days_kb(pid, nd), "HTML")


@router.callback_query(F.data.regexp(r"^admin_plan_days_custom_\d+$"), IsAdmin())
async def edit_plan_days_custom(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_plan_id=int(callback.data.split("_")[-1]), edit_field="days")
    await safe_edit(callback.message, "📅 مدت دلخواه (روز):")
    await state.set_state(EditPlanStates.days)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_plan_toggle_\d+$"), IsAdmin())
async def toggle_plan(callback: CallbackQuery):
    pid = int(callback.data.split("_")[-1])
    p = await db.get_plan(pid)
    await db.update_plan_field(pid, "is_active", 0 if p[4] else 1)
    await callback.answer("✅ تغییر کرد.", show_alert=True)
    await view_plan(callback)


@router.callback_query(F.data.regexp(r"^admin_plan_delete_\d+$"), IsAdmin())
async def ask_delete_plan(callback: CallbackQuery):
    pid = int(callback.data.split("_")[-1])
    await safe_edit(callback.message, f"⚠️ حذف پلن #{pid}؟", confirm_delete_kb("plan", pid, f"admin_plan_view_{pid}"))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^confirm_delete_plan_\d+$"), IsAdmin())
async def confirm_delete_plan(callback: CallbackQuery):
    await db.delete_plan(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_plans(callback)


# ============ COUPONS ============
@router.callback_query(F.data == "admin_coupons", IsAdmin())
async def show_coupons(callback: CallbackQuery):
    coupons = await db.get_all_coupons()
    text = "🎟 <b>کدهای تخفیف:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not coupons:
        text += "❌ کدی نیست."
    else:
        for c in coupons:
            emoji = "🟢" if c[5] else "🔴"
            text += f"{emoji} {c[1]} | {c[2]}% | {c[4]}/{c[3]}\n"
            kb.button(text=f"{emoji} {c[1]}", callback_data=f"admin_coupon_view_{c[0]}")
        kb.adjust(1)
    kb.button(text="➕ افزودن", callback_data="admin_coupon_add")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1, 1)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_coupon_view_\d+$"), IsAdmin())
async def view_coupon(callback: CallbackQuery):
    cid = int(callback.data.split("_")[-1])
    c = await db.get_coupon_by_id(cid)
    text = f"🎟 <b>#{c[0]}</b>\n\n🔖 <code>{c[1]}</code>\n💯 {c[2]}%\n🔢 {c[4]}/{c[3]}\n📊 {'🟢' if c[5] else '🔴'}"
    await safe_edit(callback.message, text, admin_coupon_actions_kb(cid, c[5]), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_coupon_add", IsAdmin())
async def add_coupon_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "🎟 کد تخفیف:")
    await state.set_state(AddCouponStates.code)
    await callback.answer()


@router.message(AddCouponStates.code, IsAdmin())
async def add_coupon_code(message: Message, state: FSMContext):
    await state.update_data(coupon_code=message.text.strip())
    await message.answer("💯 درصد (عدد):")
    await state.set_state(AddCouponStates.discount)


@router.message(AddCouponStates.discount, IsAdmin())
async def add_coupon_discount(message: Message, state: FSMContext):
    try:
        await state.update_data(coupon_discount=int(message.text.strip()))
        await message.answer("🔢 محدودیت:")
        await state.set_state(AddCouponStates.limit)
    except:
        await message.answer("❌ عدد معتبر.")


@router.message(AddCouponStates.limit, IsAdmin())
async def add_coupon_limit(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        await db.add_coupon(data['coupon_code'], data['coupon_discount'], int(message.text.strip()))
        await state.clear()
        await message.answer("✅ اضافه شد.", reply_markup=admin_main_kb())
    except Exception as e:
        await message.answer(f"❌ خطا: {e}")


@router.callback_query(F.data.regexp(r"^admin_coupon_edit_code_\d+$"), IsAdmin())
async def edit_coupon_code_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_coupon_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "🎟 کد جدید:")
    await state.set_state(EditCouponStates.code)
    await callback.answer()


@router.message(EditCouponStates.code, IsAdmin())
async def edit_coupon_code_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_coupon_field(data['edit_coupon_id'], "code", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_coupon_edit_discount_\d+$"), IsAdmin())
async def edit_coupon_discount_menu(callback: CallbackQuery):
    cid = int(callback.data.split("_")[-1])
    c = await db.get_coupon_by_id(cid)
    await safe_edit(callback.message, "% تخفیف:", admin_coupon_discount_kb(cid, c[2]), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_coupon_discount_(up|down)_\d+_\d+$"), IsAdmin())
async def edit_coupon_discount_change(callback: CallbackQuery):
    parts = callback.data.split("_")
    d, cid, amt = parts[3], int(parts[4]), int(parts[5])
    c = await db.get_coupon_by_id(cid)
    nd = max(0, min(100, c[2] + (amt if d == "up" else -amt)))
    await db.update_coupon_field(cid, "discount_percent", nd)
    await callback.answer(f"✅ {nd}%", show_alert=True)
    await safe_edit(callback.message, "% تخفیف:", admin_coupon_discount_kb(cid, nd), "HTML")


@router.callback_query(F.data.regexp(r"^admin_coupon_discount_custom_\d+$"), IsAdmin())
async def edit_coupon_discount_custom(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_coupon_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "💯 درصد دلخواه:")
    await state.set_state(EditCouponStates.discount)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_coupon_edit_limit_\d+$"), IsAdmin())
async def edit_coupon_limit_menu(callback: CallbackQuery):
    cid = int(callback.data.split("_")[-1])
    c = await db.get_coupon_by_id(cid)
    await safe_edit(callback.message, "🔢 محدودیت:", admin_coupon_limit_kb(cid, c[3]), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_coupon_limit_(up|down)_\d+_\d+$"), IsAdmin())
async def edit_coupon_limit_change(callback: CallbackQuery):
    parts = callback.data.split("_")
    d, cid, amt = parts[3], int(parts[4]), int(parts[5])
    c = await db.get_coupon_by_id(cid)
    nl = max(1, c[3] + (amt if d == "up" else -amt))
    await db.update_coupon_field(cid, "uses_limit", nl)
    await callback.answer(f"✅ {nl}", show_alert=True)
    await safe_edit(callback.message, "🔢 محدودیت:", admin_coupon_limit_kb(cid, nl), "HTML")


@router.callback_query(F.data.regexp(r"^admin_coupon_limit_custom_\d+$"), IsAdmin())
async def edit_coupon_limit_custom(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_coupon_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "🔢 محدودیت دلخواه:")
    await state.set_state(EditCouponStates.limit)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_coupon_toggle_\d+$"), IsAdmin())
async def toggle_coupon(callback: CallbackQuery):
    cid = int(callback.data.split("_")[-1])
    c = await db.get_coupon_by_id(cid)
    await db.update_coupon_field(cid, "is_active", 0 if c[5] else 1)
    await callback.answer("✅ تغییر کرد.", show_alert=True)
    await view_coupon(callback)


@router.callback_query(F.data.regexp(r"^admin_coupon_delete_\d+$"), IsAdmin())
async def ask_delete_coupon(callback: CallbackQuery):
    cid = int(callback.data.split("_")[-1])
    await safe_edit(callback.message, f"⚠️ حذف #{cid}؟", confirm_delete_kb("coupon", cid, f"admin_coupon_view_{cid}"))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^confirm_delete_coupon_\d+$"), IsAdmin())
async def confirm_delete_coupon(callback: CallbackQuery):
    await db.delete_coupon(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_coupons(callback)


# ============ TUTORIALS ============
@router.callback_query(F.data == "admin_tutorials", IsAdmin())
async def show_tutorials(callback: CallbackQuery):
    tuts = await db.get_all_tutorials()
    text = "📚 <b>آموزش‌ها:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not tuts:
        text += "❌ آموزشی نیست."
    else:
        for t in tuts:
            text += f"🔹 #{t[0]} | {t[1]} - {t[2]}\n"
            kb.button(text=f"{t[1]}", callback_data=f"admin_tut_view_{t[0]}")
        kb.adjust(1)
    kb.button(text="➕ افزودن", callback_data="admin_tut_add")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1, 1)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_tut_view_\d+$"), IsAdmin())
async def view_tutorial(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    t = await db.get_tutorial(tid)
    text = f"📚 <b>#{t[0]}</b>\n\n📱 {t[1]}\n📛 {t[2]}\n\n📝 {t[3]}"
    await safe_edit(callback.message, text, admin_tutorial_actions_kb(tid), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_tut_add", IsAdmin())
async def add_tut_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "📱 پلتفرم:")
    await state.set_state(AddTutorialStates.platform)
    await callback.answer()


@router.message(AddTutorialStates.platform, IsAdmin())
async def add_tut_platform(message: Message, state: FSMContext):
    await state.update_data(tut_platform=message.text.strip())
    await message.answer("📛 عنوان:")
    await state.set_state(AddTutorialStates.title)


@router.message(AddTutorialStates.title, IsAdmin())
async def add_tut_title(message: Message, state: FSMContext):
    await state.update_data(tut_title=message.text.strip())
    await message.answer("📝 محتوا:")
    await state.set_state(AddTutorialStates.content)


@router.message(AddTutorialStates.content, IsAdmin())
async def add_tut_content(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_tutorial(data['tut_platform'], data['tut_title'], message.text.strip())
    await state.clear()
    await message.answer("✅ اضافه شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_tut_edit_platform_\d+$"), IsAdmin())
async def edit_tut_platform_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_tut_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "📱 پلتفرم جدید:")
    await state.set_state(EditTutorialStates.platform)
    await callback.answer()


@router.message(EditTutorialStates.platform, IsAdmin())
async def edit_tut_platform_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_tutorial_field(data['edit_tut_id'], "platform", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_tut_edit_title_\d+$"), IsAdmin())
async def edit_tut_title_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_tut_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "📛 عنوان جدید:")
    await state.set_state(EditTutorialStates.title)
    await callback.answer()


@router.message(EditTutorialStates.title, IsAdmin())
async def edit_tut_title_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_tutorial_field(data['edit_tut_id'], "title", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_tut_edit_content_\d+$"), IsAdmin())
async def edit_tut_content_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(edit_tut_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "📝 محتوای جدید:")
    await state.set_state(EditTutorialStates.content)
    await callback.answer()


@router.message(EditTutorialStates.content, IsAdmin())
async def edit_tut_content_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_tutorial_field(data['edit_tut_id'], "content", message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_tut_delete_\d+$"), IsAdmin())
async def ask_delete_tut(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    await safe_edit(callback.message, f"⚠️ حذف #{tid}؟", confirm_delete_kb("tut", tid, f"admin_tut_view_{tid}"))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^confirm_delete_tut_\d+$"), IsAdmin())
async def confirm_delete_tut(callback: CallbackQuery):
    await db.delete_tutorial(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_tutorials(callback)


# ============ TICKETS ============
@router.callback_query(F.data == "admin_tickets", IsAdmin())
@router.callback_query(F.data.regexp(r"^admin_tickets(_status_(open|closed))?(_page_\d+)?$"), IsAdmin())
async def show_tickets(callback: CallbackQuery):
    data = callback.data
    status = None
    page = 1
    if "status_open" in data: status = "open"
    elif "status_closed" in data: status = "closed"
    if "page_" in data: page = int(data.split("_")[-1])
    offset = (page - 1) * ITEMS_PER_PAGE
    tickets = await db.get_all_tickets(status=status, offset=offset, limit=ITEMS_PER_PAGE)
    total = await db.count_tickets(status=status)
    text = f"🎫 <b>تیکت‌ها</b>"
    if status: text += f" ({'باز 🟢' if status == 'open' else 'بسته 🔴'})"
    text += "\n\n"
    kb = InlineKeyboardBuilder()
    if not tickets:
        text += "❌ تیکتی نیست."
    else:
        for t in tickets:
            emoji = "🟢" if t[3] == "open" else "🔴"
            un = t[7] or t[8] or "?"
            text += f"{emoji} #{t[0]} | {un[:15]} | {t[2][:25]}\n"
            kb.button(text=f"{emoji} #{t[0]} | {un[:15]}", callback_data=f"admin_ticket_view_{t[0]}")
        kb.adjust(1)
    if total > ITEMS_PER_PAGE:
        tp = max(1, math.ceil(total / ITEMS_PER_PAGE))
        prefix = f"admin_tickets_status_{status}" if status else "admin_tickets"
        if page > 1: kb.button(text="⬅️", callback_data=f"{prefix}_page_{page-1}")
        else: kb.button(text="⬅️", callback_data="noop")
        kb.button(text=f"📄 {page}/{tp}", callback_data="noop")
        if page < tp: kb.button(text="➡️", callback_data=f"{prefix}_page_{page+1}")
        else: kb.button(text="➡️", callback_data="noop")
        kb.adjust(3)
    kb.button(text="🟢 باز", callback_data="admin_tickets_status_open")
    kb.button(text="🔴 بسته", callback_data="admin_tickets_status_closed")
    kb.button(text="📋 همه", callback_data="admin_tickets")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(3, 1)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_ticket_view_\d+$"), IsAdmin())
async def view_ticket(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    t = await db.get_ticket(tid)
    messages = await db.get_ticket_messages(tid)
    text = f"🎫 <b>#{tid}</b>\n👤 {t[1]}\n📝 {t[2]}\n📊 {t[3]}\n\n<b>مکالمات:</b>\n"
    for m in messages:
        sender = "👤 کاربر" if m[2] == "user" else "🛡️ پشتیبانی"
        text += f"\n{sender}:\n{m[3]}\n"
    
    # ✅ بررسی اینکه کاربر owner هست یا نه
    is_owner_ticket = await db.is_owner(t[1])
    
    await safe_edit(callback.message, text, admin_ticket_actions_kb(tid, t[3], is_owner_ticket), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_ticket_reply_\d+$"), IsAdmin())
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(reply_ticket_id=int(callback.data.split("_")[-1]))
    await safe_edit(callback.message, "💬 پاسخ:")
    await state.set_state(AdminStates.ticket_reply)
    await callback.answer()


@router.message(AdminStates.ticket_reply, IsAdmin())
async def ticket_reply_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tid = data['reply_ticket_id']
    t = await db.get_ticket(tid)
    fid = message.photo[-1].file_id if message.photo else None
    await db.add_ticket_message(tid, "admin", message.from_user.id, message.text or "📎", fid)
    await state.clear()
    try:
        await bot.send_message(t[1], f"🛡️ پاسخ #{tid}:\n\n{message.text or '📎'}")
    except:
        pass
    await message.answer("✅ ارسال شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data.regexp(r"^admin_ticket_close_\d+$"), IsAdmin())
async def close_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[-1])
    await db.update_ticket_status(tid, "closed")
    t = await db.get_ticket(tid)
    try:
        await bot.send_message(t[1], f"🔒 تیکت #{tid} بسته شد.")
    except:
        pass
    await callback.answer("✅ بسته شد.", show_alert=True)
    await view_ticket(callback)


@router.callback_query(F.data.regexp(r"^admin_ticket_reopen_\d+$"), IsAdmin())
async def reopen_ticket(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    await db.update_ticket_status(tid, "open")
    await callback.answer("✅ باز شد.", show_alert=True)
    await view_ticket(callback)


# ============ CUSTOMERS ============
@router.callback_query(F.data == "admin_customers", IsAdmin())
@router.callback_query(F.data.regexp(r"^admin_customers_page_\d+$"), IsAdmin())
async def show_customers(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1]) if "page" in callback.data else 1
    offset = (page - 1) * ITEMS_PER_PAGE
    users = await db.get_all_users(offset=offset, limit=ITEMS_PER_PAGE)
    total = await db.count_users()
    text = f"👥 <b>مشتریان ({page}/{max(1, math.ceil(total/ITEMS_PER_PAGE))})</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not users:
        text += "❌ مشتری‌ای نیست."
    else:
        for u in users:
            emoji = "🔴" if u[4] else "🟢"
            un = u[2] or u[3] or "?"
            text += f"{emoji} {un} (<code>{u[1]}</code>)\n"
            kb.button(text=f"{emoji} {un[:20]}", callback_data=f"admin_cust_view_{u[1]}")
        kb.adjust(1)
    if total > ITEMS_PER_PAGE:
        tp = max(1, math.ceil(total / ITEMS_PER_PAGE))
        if page > 1: kb.button(text="⬅️", callback_data=f"admin_customers_page_{page-1}")
        else: kb.button(text="⬅️", callback_data="noop")
        kb.button(text=f"📄 {page}/{tp}", callback_data="noop")
        if page < tp: kb.button(text="➡️", callback_data=f"admin_customers_page_{page+1}")
        else: kb.button(text="➡️", callback_data="noop")
        kb.adjust(3)
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_cust_view_\d+$"), IsAdmin())
async def view_customer(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    u = await db.get_user(tid)
    if not u:
        await callback.answer("❌ یافت نشد.", show_alert=True)
        return
    orders = (await db.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (tid,)))[0][0]
    text = (f"👤 <b>مشتری</b>\n\n🆔 <code>{u[1]}</code>\n📛 @{u[2] or '-'}\n👤 {u[3] or '-'}\n"
            f"📊 {'🔴' if u[4] else '🟢'}\n🛒 {orders}\n📅 {u[5][:10] if u[5] else '-'}")
    await safe_edit(callback.message, text, admin_customer_actions_kb(tid, u[4]), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_cust_ban_\d+$"), IsAdmin())
async def ban_customer(callback: CallbackQuery):
    await db.ban_user(int(callback.data.split("_")[-1]), True)
    await callback.answer("🔴 مسدود.", show_alert=True)
    await view_customer(callback)


@router.callback_query(F.data.regexp(r"^admin_cust_unban_\d+$"), IsAdmin())
async def unban_customer(callback: CallbackQuery):
    await db.ban_user(int(callback.data.split("_")[-1]), False)
    await callback.answer("🟢 رفع.", show_alert=True)
    await view_customer(callback)


# ============ ADMINS ============
@router.callback_query(F.data == "admin_admins", IsAdmin())
async def show_admins(callback: CallbackQuery):
    admins = await db.get_all_admins()
    text = "👑 <b>ادمین‌ها:</b>\n\n"
    kb = InlineKeyboardBuilder()
    for a in admins:
        emoji = "👑" if a[1] == "OWNER" else "🛡️"
        text += f"{emoji} <code>{a[0]}</code> - {a[1]}\n"
        kb.button(text=f"{emoji} {a[0]}", callback_data=f"admin_admin_view_{a[0]}")
    kb.adjust(1)
    kb.button(text="➕ افزودن", callback_data="admin_admin_add")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1, 1)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_admin_view_\d+$"), IsAdmin())
async def view_admin(callback: CallbackQuery):
    uid = int(callback.data.split("_")[-1])
    admins = await db.get_all_admins()
    a = next((x for x in admins if x[0] == uid), None)
    if not a:
        await callback.answer("❌", show_alert=True)
        return
    text = f"👑 <b>ادمین</b>\n\n🆔 <code>{a[0]}</code>\n🛡️ {a[1]}\n📅 {a[2][:10]}"
    is_own = await db.is_owner(callback.from_user.id)
    await safe_edit(callback.message, text, admin_admin_actions_kb(uid, a[1], is_own), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_admin_add", IsOwner())
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "🆔 آیدی عددی:")
    await state.set_state(AdminStates.new_admin_id)
    await callback.answer()


@router.message(AdminStates.new_admin_id, IsOwner())
async def add_admin_handler(message: Message, state: FSMContext):
    try:
        nid = int(message.text.strip())
        await db.add_admin(nid, "ADMIN")
        await state.clear()
        await message.answer("✅ اضافه شد.", reply_markup=admin_main_kb())
        await db.log("ADD_ADMIN", message.from_user.id, str(nid), message.from_user.username)
    except:
        await message.answer("❌ آیدی معتبر نیست.")


@router.callback_query(F.data.regexp(r"^admin_admin_remove_\d+$"), IsOwner())
async def remove_admin(callback: CallbackQuery):
    await db.remove_admin(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_admins(callback)


# ============ WAITLIST ============
@router.callback_query(F.data == "admin_waitlist", IsAdmin())
async def show_waitlist(callback: CallbackQuery):
    waitlist = await db.get_waitlist()
    text = "🎯 <b>لیست انتظار:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not waitlist:
        text += "❌ کسی در لیست نیست."
    else:
        for w in waitlist:
            username = w[7] or w[8] or "?"
            plan_name = w[9] or "?"
            status = "🔔" if w[4] else "⏳"
            text += f"{status} {username} | {plan_name}\n"
            kb.button(text=f"🗑 {username[:15]} | {plan_name[:10]}", callback_data=f"admin_waitlist_remove_{w[0]}")
        kb.adjust(1)
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_waitlist_remove_\d+$"), IsAdmin())
async def remove_from_waitlist(callback: CallbackQuery):
    await db.remove_from_waitlist(int(callback.data.split("_")[-1]))
    await callback.answer("✅ حذف شد.", show_alert=True)
    await show_waitlist(callback)


# ============ TERMS ============
@router.callback_query(F.data == "admin_terms", IsAdmin())
async def show_terms_menu(callback: CallbackQuery):
    terms_text = await db.get_terms_text()
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش قوانین", callback_data="admin_terms_edit")
    kb.button(text="👁 پیش‌نمایش", callback_data="admin_terms_preview")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1)
    await safe_edit(callback.message,
        f"📜 <b>مدیریت قوانین</b>\n\n📝 طول: {len(terms_text)} کاراکتر",
        kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_terms_edit", IsAdmin())
async def start_edit_terms(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "📜 متن جدید قوانین را ارسال کنید:")
    await state.set_state(AdminStates.editing_terms)
    await callback.answer()


@router.message(AdminStates.editing_terms, IsAdmin())
async def save_terms(message: Message, state: FSMContext):
    await db.set_terms_text(message.text)
    await db.log("TERMS_UPDATED", message.from_user.id, f"Length: {len(message.text)}", message.from_user.username)
    await state.clear()
    await message.answer("✅ قوانین بروزرسانی شد.", reply_markup=admin_main_kb())


@router.callback_query(F.data == "admin_terms_preview", IsAdmin())
async def preview_terms(callback: CallbackQuery):
    terms_text = await db.get_terms_text()
    await safe_edit(callback.message, terms_text, back_kb("admin_terms"), "HTML")
    await callback.answer()


# ============ LOGS ============
@router.callback_query(F.data == "admin_logs", IsAdmin())
@router.callback_query(F.data.regexp(r"^admin_logs_page_\d+$"), IsAdmin())
async def show_logs(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1]) if "page" in callback.data else 1
    offset = (page - 1) * 10
    logs = await db.get_logs(offset=offset, limit=10)
    total = await db.count_logs()
    text = f"📜 <b>لاگ‌ها ({page}/{max(1, math.ceil(total/10))})</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not logs:
        text += "❌ لاگی نیست."
    else:
        for l in logs:
            text += f"📝 {l[1]} | {l[2]} | {l[5][:16]}\n"
            kb.button(text=f"📝 {l[1]} | {l[5][:10]}", callback_data=f"admin_log_view_{l[0]}")
        kb.adjust(1)
    if total > 10:
        tp = max(1, math.ceil(total / 10))
        if page > 1: kb.button(text="⬅️", callback_data=f"admin_logs_page_{page-1}")
        else: kb.button(text="⬅️", callback_data="noop")
        kb.button(text=f"📄 {page}/{tp}", callback_data="noop")
        if page < tp: kb.button(text="➡️", callback_data=f"admin_logs_page_{page+1}")
        else: kb.button(text="➡️", callback_data="noop")
        kb.adjust(3)
    kb.button(text="🗑 پاک کردن", callback_data="admin_logs_clear")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(2)
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_log_view_\d+$"), IsAdmin())
async def view_log(callback: CallbackQuery):
    lid = int(callback.data.split("_")[-1])
    logs = await db.execute("SELECT * FROM logs WHERE id=?", (lid,))
    if not logs:
        await callback.answer("❌", show_alert=True)
        return
    l = logs[0]
    text = f"📝 <b>#{l[0]}</b>\n\n🔧 {l[1]}\n👤 {l[2]}\n📛 @{l[3] or '-'}\n📝 {l[4]}\n📅 {l[5]}"
    await safe_edit(callback.message, text, back_kb("admin_logs"), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_logs_clear", IsOwner())
async def ask_clear_logs(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ بله", callback_data="confirm_logs_clear")
    kb.button(text="❌ انصراف", callback_data="admin_logs")
    kb.adjust(2)
    await safe_edit(callback.message, "⚠️ پاک شوند؟", kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "confirm_logs_clear", IsOwner())
async def confirm_clear_logs(callback: CallbackQuery):
    await db.clear_logs()
    await callback.answer("✅ پاک شد.", show_alert=True)
    await show_logs(callback)


# ============ SETTINGS ============
@router.callback_query(F.data == "admin_settings", IsAdmin())
async def show_settings(callback: CallbackQuery):
    card = await db.get_setting("card_number")
    support = await db.get_setting("support_username")
    text = f"⚙️ <b>تنظیمات</b>\n\n💳 <code>{card}</code>\n🛡️ {support}"
    await safe_edit(callback.message, text, admin_settings_kb(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_set_card", IsAdmin())
async def set_card(callback: CallbackQuery, state: FSMContext):
    await state.update_data(setting_key="card_number")
    await safe_edit(callback.message, "💳 شماره کارت جدید:")
    await state.set_state(AdminStates.setting_value)
    await callback.answer()


@router.callback_query(F.data == "admin_set_support", IsAdmin())
async def set_support(callback: CallbackQuery, state: FSMContext):
    await state.update_data(setting_key="support_username")
    await safe_edit(callback.message, "🛡️ یوزر پشتیبانی:")
    await state.set_state(AdminStates.setting_value)
    await callback.answer()


@router.message(AdminStates.setting_value, IsAdmin())
async def setting_value_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.set_setting(data['setting_key'], message.text.strip())
    await state.clear()
    await message.answer("✅ ذخیره شد.", reply_markup=admin_main_kb())


# ============ BROADCAST ============
@router.callback_query(F.data == "admin_broadcast", IsAdmin())
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit(callback.message, "📢 متن پیام:")
    await state.set_state(AdminStates.broadcast_text)
    await callback.answer()


@router.message(AdminStates.broadcast_text, IsAdmin())
async def broadcast_handler(message: Message, state: FSMContext, bot: Bot):
    users = await db.execute("SELECT telegram_id FROM users WHERE is_banned=0")
    sent = failed = 0
    status_msg = await message.answer("📤 در حال ارسال...")
    for u in users:
        try:
            await bot.send_message(u[0], f"📢 {message.text}")
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)  # BUG FIX: rate limit - جلوگیری از flood ban
    await state.clear()
    await status_msg.edit_text(f"✅ موفق: {sent}\n❌ ناموفق: {failed}")


# ============ STATS ============
@router.callback_query(F.data == "admin_stats", IsAdmin())
async def show_stats(callback: CallbackQuery):
    s = await db.get_stats()
    text = (
        f"📊 <b>آمار کامل</b>\n\n"
        f"👥 کاربران: {s['users']} (🔴 مسدود: {s['banned']})\n"
        f"👥 معرفی‌شده: {s['referrals']}\n\n"
        f"📦 اکانت آزاد: {s['free']}\n"
        f"⏸ رزرو (pending): {s['pending_acc']}\n"
        f"🛒 فروخته: {s['sold']}\n\n"
        f"📥 سفارش در انتظار: {s['pending']}\n"
        f"❌ رد شده: {s['rejected']}\n"
        f"💰 درآمد: {s['revenue']:,} ت\n\n"
        f"🎫 تیکت باز: {s['open_tickets']}\n"
        f"💳 موجودی کل کیف پول: {s['wallet_total']:,} ت\n"
        f"💳 شارژ در انتظار: {s['wallet_topups']}\n"
        f"🔓 آنلاک در جریان: {s['apple_pending']}"
    )
    await safe_edit(callback.message, text, back_kb("admin_back"), "HTML")
    await callback.answer()


# ============ WALLET TOPUPS ============
@router.callback_query(F.data == "admin_wallet_topups", IsAdmin())
async def admin_wallet_topups(callback: CallbackQuery):
    topups = await db.get_pending_wallet_topups()
    kb = InlineKeyboardBuilder()
    text = "💳 <b>شارژ کیف پول در انتظار</b>\n\n"
    if not topups:
        text += "❌ موردی نیست."
    else:
        for t in topups:
            text += f"#{t[0]} | 👤 {t[1]} | 💰 {t[2]:,} ت\n"
            kb.button(text=f"#{t[0]} | {t[2]:,}ت", callback_data=f"admin_wtopup_{t[0]}")
        kb.adjust(1)
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_wtopup_\d+$"), IsAdmin())
async def admin_wallet_topup_view(callback: CallbackQuery):
    tid = int(callback.data.split("_")[-1])
    t = await db.get_wallet_topup(tid)
    if not t:
        await callback.answer("❌ یافت نشد", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    if t[3] == "pending":
        kb.button(text="✅ تایید", callback_data=f"admin_wtopup_ok_{tid}")
        kb.button(text="❌ رد", callback_data=f"admin_wtopup_no_{tid}")
        kb.adjust(2)
    kb.button(text="🔙 بازگشت", callback_data="admin_wallet_topups")
    text = f"💳 <b>شارژ #{tid}</b>\n👤 {t[1]}\n💰 {t[2]:,} ت\n📊 {t[3]}"
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_wtopup_ok_\d+$"), IsAdmin())
async def admin_wallet_topup_approve(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[-1])
    t = await db.get_wallet_topup(tid)
    if await db.approve_wallet_topup(tid):
        try:
            await bot.send_message(t[1], f"✅ شارژ #{tid} به مبلغ {t[2]:,} تومان تایید شد.")
        except Exception:
            pass
        await callback.answer("✅ تایید شد", show_alert=True)
    else:
        await callback.answer("⚠️ قبلاً پردازش شده", show_alert=True)
    await admin_wallet_topups(callback)


@router.callback_query(F.data.regexp(r"^admin_wtopup_no_\d+$"), IsAdmin())
async def admin_wallet_topup_reject(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[-1])
    t = await db.get_wallet_topup(tid)
    await db.reject_wallet_topup(tid)
    try:
        await bot.send_message(t[1], f"❌ درخواست شارژ #{tid} رد شد.")
    except Exception:
        pass
    await callback.answer("❌ رد شد", show_alert=True)
    await admin_wallet_topups(callback)


# ============ APPLE UNLOCK ADMIN ============
@router.callback_query(F.data == "admin_apple_unlocks", IsAdmin())
async def admin_apple_unlocks(callback: CallbackQuery):
    orders = await db.get_all_apple_unlocks(limit=30)
    kb = InlineKeyboardBuilder()
    text = "🔓 <b>سفارش‌های آنلاک Apple ID</b>\n\n"
    if not orders:
        text += "❌ سفارشی نیست."
    else:
        for o in orders:
            text += f"#{o[0]} | {o[2][:20]} | {o[12]}\n"
            kb.button(text=f"#{o[0]}", callback_data=f"admin_apple_{o[0]}")
        kb.adjust(3)
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_apple_\d+$"), IsAdmin())
async def admin_apple_view(callback: CallbackQuery):
    oid = int(callback.data.split("_")[-1])
    o = await db.get_apple_unlock(oid)
    if not o:
        await callback.answer("❌ یافت نشد", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    st = o[12]
    if st == "info_submitted":
        kb.button(text="💰 تعیین قیمت", callback_data=f"admin_apple_price_{oid}")
    elif st == "payment_submitted":
        kb.button(text="✅ تایید پرداخت", callback_data=f"admin_apple_payok_{oid}")
    elif st == "payment_approved":
        kb.button(text="🔓 آنلاک شد", callback_data=f"admin_apple_done_{oid}")
    kb.button(text="🔙 بازگشت", callback_data="admin_apple_unlocks")
    text = (
        f"🔓 <b>#{oid}</b>\n👤 {o[1]}\n📧 {o[2]}\n🔑 {o[3]}\n"
        f"🎂 {o[4]}\n❓ {o[5]}\n📊 {st}\n"
        f"💰 {o[10] or 0:,} ت | ⏰ {o[11] or '-'}"
    )
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_apple_price_\d+$"), IsAdmin())
async def admin_apple_price_start(callback: CallbackQuery, state: FSMContext):
    oid = int(callback.data.split("_")[-1])
    await state.update_data(apple_order_id=oid)
    await safe_edit(callback.message, "💰 قیمت (تومان) را وارد کنید:", back_kb("admin_apple_unlocks"))
    await state.set_state(AdminStates.apple_set_price)
    await callback.answer()


@router.message(AdminStates.apple_set_price, IsAdmin())
async def admin_apple_price_save(message: Message, state: FSMContext):
    try:
        price = int(message.text.replace(",", "").strip())
    except ValueError:
        await message.answer("❌ عدد نامعتبر")
        return
    await state.update_data(apple_price=price)
    await message.answer("⏰ زمان تقریبی آنلاک را وارد کنید:\n💡 مثال: 24 ساعت")
    await state.set_state(AdminStates.apple_set_time)


@router.message(AdminStates.apple_set_time, IsAdmin())
async def admin_apple_time_save(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    oid = data["apple_order_id"]
    await db.set_apple_unlock_price(oid, data["apple_price"], message.text.strip())
    order = await db.get_apple_unlock(oid)
    await state.clear()
    await message.answer("✅ قیمت ثبت شد.", reply_markup=admin_main_kb())
    try:
        await bot.send_message(
            order[1],
            f"🔓 سفارش #{oid}\n💰 مبلغ: {data['apple_price']:,} ت\n"
            f"⏰ زمان: {message.text.strip()}\n\n"
            f"از منو «آنلاک Apple ID» فیش را ارسال کنید.",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.regexp(r"^admin_apple_payok_\d+$"), IsAdmin())
async def admin_apple_payok(callback: CallbackQuery, bot: Bot):
    oid = int(callback.data.split("_")[-1])
    await db.approve_apple_payment(oid)
    order = await db.get_apple_unlock(oid)
    try:
        await bot.send_message(order[1], f"✅ پرداخت سفارش #{oid} تایید شد. در حال آنلاک...")
    except Exception:
        pass
    await callback.answer("✅ تایید شد", show_alert=True)
    await admin_apple_view(callback)


@router.callback_query(F.data.regexp(r"^admin_apple_done_\d+$"), IsAdmin())
async def admin_apple_done(callback: CallbackQuery, bot: Bot):
    oid = int(callback.data.split("_")[-1])
    await db.mark_apple_unlocked(oid)
    order = await db.get_apple_unlock(oid)
    msg = await db.get_message("apple_unlock_done")
    try:
        await bot.send_message(order[1], msg, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("🎉 آنلاک ثبت شد", show_alert=True)
    await admin_apple_view(callback)


# ============ BACKUP ============
@router.callback_query(F.data == "admin_backup", IsAdmin())
async def admin_backup(callback: CallbackQuery):
    try:
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DB_NAME, filename)
        file = FSInputFile(filename)
        await callback.message.answer_document(file, caption="💾 بکاپ دیتابیس")
        os.remove(filename)
        await callback.answer("✅ بکاپ ارسال شد!", show_alert=True)
        await db.log("BACKUP", callback.from_user.id, "Manual backup", callback.from_user.username)
    except Exception as e:
        await callback.answer(f"❌ خطا: {e}", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()