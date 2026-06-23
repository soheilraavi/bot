from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database import db
from states import UserStates
from translations import t, get_language_name
from keyboards import (user_main_kb, plans_list_with_stock_kb, payment_kb, tutorials_list_kb,
                       ticket_menu_kb, back_kb, admin_main_kb, waitlist_confirm_kb,
                       language_select_kb, quick_reply_kb)

router = Router()


from handlers.utils import get_msg, delete_user_message
from chat_manager import show_panel, track_message, safe_edit


async def _show_main_menu(target, user_id, first_name, bot=None):
    """نمایش منوی اصلی — تک پیامی"""
    welcome_text = await get_msg("welcome", name=first_name)
    if isinstance(target, CallbackQuery) and bot:
        await show_panel(bot, user_id, target.message.chat.id,
                         welcome_text, user_main_kb(), callback=target)
    elif isinstance(target, Message) and bot:
        await show_panel(bot, user_id, target.chat.id,
                         welcome_text, user_main_kb(), force_new=True)
    elif isinstance(target, CallbackQuery):
        await safe_edit(target.message, welcome_text, user_main_kb(), "HTML")
    else:
        await target.answer(welcome_text, reply_markup=user_main_kb(), parse_mode="HTML")


async def _show_phone_request(target):
    """درخواست شماره تلفن — تابع مشترک"""
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
    contact_button = KeyboardButton(text="📱 اشتراک‌گذاری شماره تلفن", request_contact=True)
    keyboard = ReplyKeyboardMarkup(keyboard=[[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    text = "📱 <b>ثبت شماره تلفن</b>\n\nلطفاً برای تکمیل ثبت‌نام، شماره تلفن خود را به اشتراک بگذارید:"
    if isinstance(target, Message):
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        try:
            await target.message.delete()
        except:
            pass
        await target.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_terms(target, terms_text):
    """نمایش قوانین — تابع مشترک"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ قبول می‌کنم", callback_data="terms_accept")
    kb.button(text="❌ قبول ندارم", callback_data="terms_reject")
    kb.adjust(2)
    if isinstance(target, Message):
        await target.answer(terms_text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await target.message.edit_text(terms_text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    is_adm = await db.is_admin(message.from_user.id)
    if is_adm:
        kb = admin_main_kb()
    else:
        kb = user_main_kb()
    await message.answer("❌ عملیات لغو شد.", reply_markup=kb)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    u = message.from_user

    referred_by = 0
    if message.text and len(message.text.split()) > 1:
        arg = message.text.split(maxsplit=1)[1]
        if arg.startswith("ref_"):
            try:
                referred_by = int(arg.replace("ref_", ""))
            except ValueError:
                referred_by = 0

    await db.add_user(u.id, u.username, u.first_name, referred_by)
    if referred_by:
        await db.set_referred_by(u.id, referred_by)
    await db.log("START", u.id, u.username, u.username)

    # BUG FIX: چک banned بودن
    if await db.is_banned(u.id):
        await message.answer("⛔ حساب شما مسدود شده است.\nبرای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
        return

    is_adm = await db.is_admin(u.id)
    if is_adm:
        s = await db.get_stats()
        text = (f"👑 <b>سلام {u.first_name}!</b>\n\n"
                f"👥 کاربران: {s['users']}\n⏳ سفارش: {s['pending']}\n"
                f"🎫 تیکت: {s['open_tickets']}\n📦 آزاد: {s['free']}\n"
                f"⏸ رزرو: {s['pending_acc']}\n💳 کیف پول: {s['wallet_total']:,}")
        await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")
        return

    # BUG FIX: چک واقعی اینکه کاربر قبلاً زبان انتخاب کرده یا نه
    has_set_lang = await db.has_set_language(u.id)
    if not has_set_lang:
        await message.answer(
            "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید:</b>\n\n"
            "Please select your language:\n\n"
            "يرجى اختيار اللغة المطلوبة:",
            reply_markup=language_select_kb(),
            parse_mode="HTML"
        )
        await state.set_state(UserStates.selecting_language)
        return

    # کاربر قبلاً زبان انتخاب کرده — چک مراحل بعدی
    await _continue_onboarding(message, u.id, u.first_name, bot)


async def _continue_onboarding(target, user_id, first_name, bot=None):
    """BUG FIX: منطق onboarding یکپارچه — از تکرار جلوگیری میکنه"""
    has_accepted = await db.has_accepted_terms(user_id)
    if not has_accepted:
        terms_text = await db.get_terms_text()
        await _show_terms(target, terms_text)
        return

    phone = await db.get_user_phone(user_id)
    if not phone:
        await _show_phone_request(target)
        return

    await _show_main_menu(target, user_id, first_name, bot)


@router.message(UserStates.selecting_language)
async def select_language_msg(message: Message, state: FSMContext):
    await message.answer(
        "🌐 لطفاً از دکمه‌های زیر زبان خود را انتخاب کنید:",
        reply_markup=language_select_kb()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext, bot: Bot):
    lang = callback.data.split("_")[1]
    await db.set_user_language(callback.from_user.id, lang)
    await db.log("SET_LANG", callback.from_user.id, lang, callback.from_user.username)
    await state.clear()

    lang_name = get_language_name(lang)
    await callback.answer(f"{lang_name} ✅")

    # BUG FIX: ادامه onboarding با تابع مشترک
    await _continue_onboarding(callback, callback.from_user.id, callback.from_user.first_name, bot)


@router.callback_query(F.data == "terms_accept")
async def terms_accept(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    await db.accept_terms(user_id)
    await db.log("TERMS_ACCEPTED", user_id, callback.from_user.username, callback.from_user.username)
    await callback.answer("✅ قوانین قبول شد")

    # BUG FIX: ادامه onboarding با تابع مشترک
    await _continue_onboarding(callback, user_id, callback.from_user.first_name, bot)


@router.callback_query(F.data == "terms_reject")
async def terms_reject(callback: CallbackQuery):
    await db.log("TERMS_REJECTED", callback.from_user.id, callback.from_user.username, callback.from_user.username)
    support = await db.get_setting("support_username")
    await callback.message.edit_text(
        "❌ متاسفیم که با قوانین موافق نیستید.\n"
        "برای استفاده از سرویس، باید قوانین را بپذیرید.\n\n"
        f"🛡️ پشتیبانی: {support}"
    )
    await callback.answer()


@router.message(F.contact)
async def handle_contact(message: Message, bot: Bot):
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer("❌ لطفاً شماره تلفن خود را به اشتراک بگذارید.")
        return

    # BUG FIX: چک banned بودن
    if await db.is_banned(message.from_user.id):
        await message.answer("⛔ حساب شما مسدود شده است.")
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"
    await db.update_user_phone(message.from_user.id, phone)
    await db.log("PHONE_RECEIVED", message.from_user.id, phone, message.from_user.username)

    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        f"✅ شماره تلفن شما ثبت شد: {phone}\n\n"
        f"🎉 ثبت‌نام شما تکمیل شد!",
        reply_markup=ReplyKeyboardRemove()
    )

    welcome_text = await get_msg("welcome", name=message.from_user.first_name)
    await show_panel(bot, message.from_user.id, message.chat.id,
                     welcome_text, user_main_kb(), force_new=True)


# ============ منوی اصلی (Inline) ============
@router.callback_query(F.data == "menu_buy")
async def menu_buy(callback: CallbackQuery, bot: Bot):
    # BUG FIX: چک banned
    if await db.is_banned(callback.from_user.id):
        await callback.answer("⛔ حساب شما مسدود شده است.", show_alert=True)
        return

    plans = await db.get_active_plans()
    if not plans:
        await callback.answer("❌ پلنی موجود نیست", show_alert=True)
        return
    stock_counts = {}
    for p in plans:
        stock_counts[p[0]] = await db.count_accounts(plan_id=p[0], status='free')

    text = "🛒 <b>لیست پلن‌های موجود:</b>\n\nلطفاً پلن مورد نظر خود را انتخاب کنید:"
    await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                     text, plans_list_with_stock_kb(plans, stock_counts), callback=callback)
    await callback.answer()


@router.callback_query(F.data == "menu_services")
async def menu_services(callback: CallbackQuery):
    orders = await db.get_user_orders(callback.from_user.id)
    if not orders:
        text = ("📦 <b>سرویس‌های شما</b>\n\n"
                "❌ در حال حاضر سرویس فعالی ندارید.\n\n"
                "💡 برای خرید اشتراک، از منوی اصلی گزینه «🛒 خرید اشتراک» را انتخاب کنید.")
        await safe_edit(callback.message, text, back_kb(), "HTML")
        await callback.answer()
        return

    text = "📦 <b>سرویس‌های فعال شما:</b>\n\n"
    kb = InlineKeyboardBuilder()

    for o in orders:
        # o.*: 0=id,7=created_at,8=expire_at | JOIN: 10=plan_name,12=acc_user,13=acc_pass
        plan_name = o[10] if len(o) > 10 and o[10] else "نامشخص"
        acc_user = o[12] if len(o) > 12 and o[12] else "-"
        acc_pass = o[13] if len(o) > 13 and o[13] else "-"
        created_at = o[7][:10] if len(o) > 7 and o[7] else "-"
        expire_at = o[8][:10] if len(o) > 8 and o[8] else "نامشخص"

        text += (f"━━━━━━━━━━━━━━━\n"
                 f"🎯 <b>{plan_name}</b> (سفارش #{o[0]})\n"
                 f"👤 Username: <code>{acc_user}</code>\n"
                 f"🔑 Password: <code>{acc_pass}</code>\n"
                 f"📅 تاریخ خرید: {created_at}\n"
                 f"⏰ تاریخ انقضا: <b>{expire_at}</b>\n\n")

    text += "━━━━━━━━━━━━━━━\n\n💡 اطلاعات بالا رو با دقت ذخیره کنید."

    kb.button(text="🔙 بازگشت", callback_data="back_home")
    await safe_edit(callback.message, text, kb.as_markup(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_tutorials")
async def menu_tutorials(callback: CallbackQuery):
    tutorials = await db.get_all_tutorials()
    if not tutorials:
        await safe_edit(callback.message, "📚 در حال حاضر آموزشی ثبت نشده است.", back_kb())
        await callback.answer()
        return
    text = "📚 <b>آموزش اتصال</b>\n\nلطفاً پلتفرم مورد نظر خود را انتخاب کنید:"
    await safe_edit(callback.message, text, tutorials_list_kb(tutorials), "HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_ticket")
async def menu_ticket(callback: CallbackQuery):
    # BUG FIX: چک banned
    if await db.is_banned(callback.from_user.id):
        await callback.answer("⛔ حساب شما مسدود شده است.", show_alert=True)
        return
    open_t = await db.get_user_open_ticket(callback.from_user.id)
    text = "🎫 <b>پشتیبانی</b>\n\nدر صورت وجود هرگونه سوال یا مشکل، از این بخش اقدام کنید:"
    await safe_edit(callback.message, text, ticket_menu_kb(bool(open_t)), "HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_faq")
async def menu_faq(callback: CallbackQuery):
    text = "📱 <b>سوالات متداول</b>\n\nلطفاً سوال خود را از لیست زیر انتخاب کنید:"
    await safe_edit(callback.message, text, quick_reply_kb(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_about")
async def menu_about(callback: CallbackQuery):
    support = await db.get_setting("support_username")
    text = (f"ℹ️ <b>درباره ما</b>\n\n"
            f"🌟 ما ارائه‌دهنده خدمات VPN با کیفیت هستیم.\n\n"
            f"✅ سرویس‌های پایدار و پرسرعت\n"
            f"✅ پشتیبانی ۲۴ ساعته\n"
            f"✅ قیمت‌های مناسب\n\n"
            f"🛡️ <b>پشتیبانی:</b> {support}\n\n"
            f"💡 برای هرگونه سوال، با ما در ارتباط باشید.")
    await safe_edit(callback.message, text, back_kb(), "HTML")
    await callback.answer()


# ============ خرید ============
@router.callback_query(F.data.startswith("plan_select_"))
async def select_plan(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # BUG FIX: چک banned
    if await db.is_banned(callback.from_user.id):
        await callback.answer("⛔ حساب شما مسدود شده است.", show_alert=True)
        return

    plan_id = int(callback.data.split("_")[2])
    plan = await db.get_plan(plan_id)
    if not plan or not plan[4]:
        await callback.answer("❌ این پلن در حال حاضر موجود نیست.", show_alert=True)
        return

    await state.update_data(
        selected_plan_id=plan_id,
        original_price=plan[2],  # BUG FIX: نگه‌داری قیمت اصلی
        final_price=plan[2],
        coupon_applied=False
    )
    card = await db.get_setting("card_number")

    text = (f"✅ <b>پلن انتخابی شما:</b>\n\n"
            f"🎯 نام پلن: {plan[1]}\n"
            f"💰 مبلغ: {plan[2]:,} تومان\n"
            f"📅 مدت اشتراک: {plan[3]} روز\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💳 <b>شماره کارت برای واریز:</b>\n"
            f"<code>{card}</code>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📸 لطفاً پس از واریز، تصویر رسید پرداخت را ارسال کنید.\n\n"
            f"💡 در صورت داشتن کد تخفیف، روی دکمه زیر بزنید.")

    await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                     text, payment_kb(), callback=callback)
    await state.set_state(UserStates.waiting_receipt)
    await callback.answer()


@router.callback_query(F.data.startswith("plan_waitlist_"))
async def ask_waitlist(callback: CallbackQuery):
    plan_id = int(callback.data.split("_")[-1])
    plan = await db.get_plan(plan_id)

    # BUG FIX: چک ثبت‌نام تکراری
    existing = await db.execute_one(
        "SELECT id FROM waitlist WHERE user_id=? AND plan_id=? AND status='waiting'",
        (callback.from_user.id, plan_id)
    )
    if existing:
        await callback.answer("⚠️ شما قبلاً در لیست انتظار این پلن ثبت‌نام کرده‌اید.", show_alert=True)
        return

    count = await db.count_waitlist(plan_id)
    lang = await db.get_user_language(callback.from_user.id)
    text = t("waitlist_ask", lang, plan=plan[1], count=count)
    await safe_edit(callback.message, text, waitlist_confirm_kb(plan_id), "HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("waitlist_confirm_"))
async def confirm_waitlist(callback: CallbackQuery):
    plan_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    # BUG FIX: add_to_waitlist حالا False برمیگردونه اگه تکراری باشه
    added = await db.add_to_waitlist(user_id, plan_id)
    if not added:
        await callback.answer("⚠️ شما قبلاً در این لیست ثبت‌نام کرده‌اید.", show_alert=True)
        return

    position = await db.get_user_waitlist_position(user_id, plan_id)
    total = await db.count_waitlist(plan_id)
    plan = await db.get_plan(plan_id)
    lang = await db.get_user_language(user_id)
    text = (t("waitlist_success", lang) +
            f"\n\n{t('waitlist_position', lang, position=position, total=total)}\n\n"
            f"🔔 به محض موجود شدن این پلن، از طریق ربات به شما اطلاع داده خواهد شد.")
    await safe_edit(callback.message, text, back_kb(), "HTML")
    await db.log("WAITLIST_JOIN", user_id, f"Plan {plan[1]}")
    await callback.answer()


@router.callback_query(F.data == "apply_coupon", UserStates.waiting_receipt)
async def ask_coupon(callback: CallbackQuery, state: FSMContext):
    text = ("🎁 <b>اعمال کد تخفیف</b>\n\n"
            "لطفاً کد تخفیف خود را ارسال کنید:\n\n"
            "💡 کد تخفیف باید دقیقاً مطابق اصل وارد شود.")
    await safe_edit(callback.message, text, back_kb(), "HTML")
    await state.set_state(UserStates.waiting_coupon)
    await callback.answer()


@router.message(UserStates.waiting_coupon, F.text)
async def apply_coupon(message: Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    if "selected_plan_id" not in data:
        return

    code = message.text.strip()
    coupon_info = await db.get_coupon_info(code)

    if not coupon_info["valid"]:
        msg = await message.answer(
            f"❌ <b>کد تخفیف نامعتبر</b>\n\n"
            f"🔍 دلیل: {coupon_info['message']}\n\n"
            f"💡 لطفاً کد را دوباره بررسی کنید یا /cancel بزنید.",
            parse_mode="HTML"
        )
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    discount = coupon_info["discount"]
    # BUG FIX: استفاده از original_price برای محاسبه تخفیف، نه final_price
    original_price = data.get('original_price', data['final_price'])
    new_price = int(original_price * (1 - discount / 100))
    await state.update_data(final_price=new_price, coupon_code=code, coupon_applied=True)

    card = await db.get_setting("card_number")

    if "last_bot_msg_id" in data:
        try:
            await message.bot.delete_message(message.chat.id, data["last_bot_msg_id"])
        except:
            pass

    expire_text = ""
    if coupon_info["expire_at"]:
        try:
            expire_date = datetime.fromisoformat(coupon_info["expire_at"])
            expire_text = f"\n📅 تاریخ انقضای کد: {expire_date.strftime('%Y/%m/%d')}"
        except:
            pass

    msg = await message.answer(
        f"🎁 <b>کد تخفیف با موفقیت اعمال شد!</b>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 تخفیف: <b>{discount}%</b>\n"
        f"💵 مبلغ اولیه: {original_price:,} تومان\n"   # BUG FIX: نمایش قیمت اصلی
        f"💵 <b>مبلغ نهایی: {new_price:,} تومان</b>\n"
        f"🎫 استفاده: {coupon_info['used'] + 1}/{coupon_info['limit']}"
        f"{expire_text}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>شماره کارت:</b>\n<code>{card}</code>\n\n"
        f"📸 لطفاً رسید پرداخت رو ارسال کنید.",
        parse_mode="HTML"
    )
    await state.update_data(last_bot_msg_id=msg.message_id)
    await state.set_state(UserStates.waiting_receipt)


@router.message(UserStates.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if "selected_plan_id" not in data:
        return
    file_id = message.photo[-1].file_id
    u = message.from_user
    order_id = await db.create_order(u.id, data['selected_plan_id'], data['final_price'], file_id)
    await db.reserve_account(data['selected_plan_id'], u.id, order_id)
    if data.get('coupon_applied'):
        await db.use_coupon(data['coupon_code'])
    if "last_bot_msg_id" in data:
        try:
            await bot.delete_message(message.chat.id, data["last_bot_msg_id"])
        except:
            pass
    await state.clear()

    receipt_msg = await get_msg("receipt_received")
    await message.answer(receipt_msg, reply_markup=user_main_kb(), parse_mode="HTML")

    admins = await db.get_all_admins()
    plan = await db.get_plan(data['selected_plan_id'])
    from keyboards import admin_order_actions_kb

    for a in admins:
        try:
            sent_msg = await bot.send_photo(
                a[0], file_id,
                caption=(f"📥 <b>سفارش جدید #{order_id}</b>\n\n"
                         f"👤 کاربر: @{u.username or 'بدون یوزرنیم'}\n"
                         f"🆔 آیدی: <code>{u.id}</code>\n"
                         f"📦 پلن: {plan[1]}\n"
                         f"💰 مبلغ: {data['final_price']:,} تومان"),
                reply_markup=admin_order_actions_kb(order_id, "pending"),
                parse_mode="HTML"
            )
            await db.update_order_admin_message_id(order_id, sent_msg.message_id)
        except Exception as e:
            import logging
            logging.error(f"Error sending to admin {a[0]}: {e}")


@router.message(UserStates.waiting_receipt, F.text)
async def handle_text_in_receipt(message: Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    if "last_bot_msg_id" in data:
        try:
            await message.bot.delete_message(message.chat.id, data["last_bot_msg_id"])
        except:
            pass
    msg = await message.answer(
        "⚠️ <b>توجه:</b>\n\n"
        "لطفاً رسید پرداخت را به صورت <b>تصویر</b> ارسال کنید.\n\n"
        "💡 برای لغو، /cancel را بفرستید.",
        parse_mode="HTML"
    )
    await state.update_data(last_bot_msg_id=msg.message_id)


# ============ آموزش ============
@router.callback_query(F.data.startswith("tutorial_view_"))
async def view_tutorial(callback: CallbackQuery):
    tid = int(callback.data.split("_")[2])
    tut = await db.get_tutorial(tid)
    if not tut:
        await callback.answer("❌ یافت نشد.", show_alert=True)
        return
    await safe_edit(callback.message, f"<b>{tut[2]}</b>\n\n{tut[3]}", back_kb(), "HTML")
    await callback.answer()


# ============ تیکت ============
@router.callback_query(F.data == "ticket_new")
async def new_ticket(callback: CallbackQuery, state: FSMContext):
    # BUG FIX: چک banned
    if await db.is_banned(callback.from_user.id):
        await callback.answer("⛔ حساب شما مسدود شده است.", show_alert=True)
        return
    if await db.get_user_open_ticket(callback.from_user.id):
        await callback.answer("❌ شما یک تیکت باز دارید.", show_alert=True)
        return
    await safe_edit(
        callback.message,
        "📝 <b>ایجاد تیکت جدید</b>\n\nلطفاً موضوع تیکت خود را بنویسید:\n\n💡 موضوع را کوتاه و گویا بنویسید.",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.ticket_subject)
    await callback.answer()


@router.message(UserStates.ticket_subject)
async def ticket_subject(message: Message, state: FSMContext):
    await delete_user_message(message)
    subject = message.text.strip()
    ticket_id = await db.create_ticket(message.from_user.id, subject)
    await state.update_data(current_ticket_id=ticket_id, ticket_subject=subject)
    await message.answer(
        "💬 <b>پیام شما</b>\n\n"
        "لطفاً پیام یا مشکل خود را با جزئیات کامل بنویسید.\n"
        "می‌توانید تصویر هم ارسال کنید.",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.ticket_message)


@router.message(UserStates.ticket_message)
async def ticket_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data['current_ticket_id']
    text = message.text or message.caption or "📎 فایل"
    file_id = message.photo[-1].file_id if message.photo else None
    await db.add_ticket_message(ticket_id, "user", message.from_user.id, text, file_id)
    await state.clear()

    ticket_msg = await get_msg("ticket_created", ticket_id=ticket_id, subject=data.get('ticket_subject', ''))
    await message.answer(ticket_msg, reply_markup=user_main_kb(), parse_mode="HTML")

    admins = await db.get_all_admins()
    from keyboards import admin_ticket_actions_kb
    for a in admins:
        try:
            is_owner_ticket = await db.is_owner(message.from_user.id)
            await bot.send_message(
                a[0],
                (f"🎫 <b>تیکت جدید #{ticket_id}</b>\n\n"
                 f"👤 کاربر: @{message.from_user.username or 'بدون یوزرنیم'}\n"
                 f"🆔 آیدی: <code>{message.from_user.id}</code>\n"
                 f"📝 موضوع: {data.get('ticket_subject', '')}\n\n"
                 f"💬 پیام:\n{text}"),
                reply_markup=admin_ticket_actions_kb(ticket_id, "open", is_owner_ticket),
                parse_mode="HTML"
            )
        except:
            pass


@router.callback_query(F.data == "ticket_my_open")
async def my_open_ticket(callback: CallbackQuery):
    ticket_id = await db.get_user_open_ticket(callback.from_user.id)
    if not ticket_id:
        await callback.answer("❌ تیکت بازی ندارید.", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    messages = await db.get_ticket_messages(ticket_id)
    text = f"🎫 <b>تیکت #{ticket_id}</b>\n📝 موضوع: {ticket[2]}\n\n<b>مکالمات:</b>\n"
    for m in messages:
        sender = "👤 شما" if m[2] == "user" else "🛡️ پشتیبانی"
        text += f"\n{sender}:\n{m[3]}\n"
    await safe_edit(callback.message, text, back_kb("back_home"), "HTML")
    await callback.answer()


# ============ Quick Reply ============
@router.callback_query(F.data == "qr_howto")
async def qr_howto(callback: CallbackQuery):
    tutorials = await db.get_all_tutorials()
    await safe_edit(callback.message, "📚 پلتفرم را انتخاب کنید:", tutorials_list_kb(tutorials))
    await callback.answer()


@router.callback_query(F.data == "qr_refund")
async def qr_refund(callback: CallbackQuery):
    lang = await db.get_user_language(callback.from_user.id)
    await safe_edit(callback.message, t("refund_title", lang), back_kb(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "qr_support")
async def qr_support(callback: CallbackQuery):
    support = await db.get_setting("support_username")
    lang = await db.get_user_language(callback.from_user.id)
    await safe_edit(callback.message, t("support_title", lang, support=support), back_kb(), "HTML")
    await callback.answer()


@router.callback_query(F.data == "back_home")
async def back_home(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    is_adm = await db.is_admin(callback.from_user.id)
    if is_adm:
        s = await db.get_stats()
        text = (f"👑 <b>پنل مدیریت</b>\n\n"
                f"👥 کاربران: {s['users']}\n⏳ سفارش: {s['pending']}\n"
                f"🎫 تیکت: {s['open_tickets']}\n📦 آزاد: {s['free']}\n"
                f"⏸ رزرو: {s['pending_acc']}\n💳 کیف پول: {s['wallet_total']:,}\n"
                f"🔓 آنلاک: {s['apple_pending']}")
        await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                         text, admin_main_kb(), callback=callback)
    else:
        u = callback.from_user
        welcome_text = await get_msg("welcome", name=u.first_name)
        await show_panel(bot, u.id, callback.message.chat.id,
                         welcome_text, user_main_kb(), callback=callback)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
