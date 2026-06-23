"""کیف پول، آنلاک Apple ID، معرفی به دوستان"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database import db, REFERRAL_BONUS
from states import UserStates
from keyboards import back_kb, wallet_kb, apple_skip_kb, apple_unlock_status_kb, user_main_kb, admin_main_kb
from chat_manager import show_panel, track_message
from handlers.utils import get_msg, delete_user_message

router = Router()

STATUS_FA = {
    "info_submitted": "⏳ در انتظار بررسی",
    "awaiting_payment": "💰 در انتظار پرداخت",
    "payment_submitted": "📸 فیش ارسال شد",
    "payment_approved": "✅ پرداخت تایید شد — در حال آنلاک",
    "unlocked": "🎉 آنلاک شد",
    "rejected": "❌ رد شده",
}


# ============ کیف پول ============
@router.callback_query(F.data == "menu_wallet")
async def menu_wallet(callback: CallbackQuery, bot: Bot):
    balance = await db.get_wallet_balance(callback.from_user.id)
    text = (
        f"💳 <b>کیف پول</b>\n\n"
        f"💰 موجودی: <b>{balance:,}</b> تومان\n\n"
        f"💡 می‌توانید کیف پول را شارژ کنید و با موجودی، سرویس بخرید."
    )
    from keyboards import wallet_kb
    await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                     text, wallet_kb(), callback=callback)
    await callback.answer()


@router.callback_query(F.data == "wallet_topup")
async def wallet_topup_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_panel(
        bot, callback.from_user.id, callback.message.chat.id,
        "➕ <b>شارژ کیف پول</b>\n\nمبلغ شارژ را به تومان وارد کنید:\n\n"
        "💡 مثال: 100000",
        back_kb(), callback=callback,
    )
    await state.set_state(UserStates.wallet_topup_amount)
    await callback.answer()


@router.message(UserStates.wallet_topup_amount, F.text)
async def wallet_topup_amount(message: Message, state: FSMContext, bot: Bot):
    await delete_user_message(message)
    try:
        amount = int(message.text.replace(",", "").strip())
        if amount < 10000:
            raise ValueError()
    except ValueError:
        msg = await message.answer("❌ مبلغ نامعتبر. حداقل ۱۰,۰۰۰ تومان.")
        await track_message(message.from_user.id, msg.message_id)
        return
    await state.update_data(topup_amount=amount)
    card = await db.get_setting("card_number")
    text = (
        f"💳 <b>شارژ {amount:,} تومان</b>\n\n"
        f"شماره کارت:\n<code>{card}</code>\n\n"
        f"📸 پس از واریز، تصویر فیش را ارسال کنید."
    )
    mid = await show_panel(bot, message.from_user.id, message.chat.id, text, back_kb(), force_new=True)
    await state.update_data(panel_msg_id=mid)
    await state.set_state(UserStates.wallet_topup_receipt)


@router.message(UserStates.wallet_topup_receipt, F.photo)
async def wallet_topup_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data.get("topup_amount", 0)
    file_id = message.photo[-1].file_id
    topup_id = await db.create_wallet_topup(message.from_user.id, amount, file_id)
    await state.clear()
    await delete_user_message(message)

    text = (
        f"✅ درخواست شارژ #{topup_id} ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"⏳ پس از تایید ادمین، موجودی شما افزایش می‌یابد."
    )
    await show_panel(bot, message.from_user.id, message.chat.id, text, user_main_kb(), force_new=True)

    admins = await db.get_all_admins()
    for a in admins:
        try:
            await bot.send_photo(
                a[0], file_id,
                caption=f"💳 <b>شارژ کیف پول #{topup_id}</b>\n👤 {message.from_user.id}\n💰 {amount:,} ت",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data == "pay_wallet")
async def pay_with_wallet(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if "selected_plan_id" not in data:
        await callback.answer("❌ ابتدا پلن انتخاب کنید.", show_alert=True)
        return
    price = data.get("final_price", 0)
    balance = await db.get_wallet_balance(callback.from_user.id)
    if balance < price:
        await callback.answer(f"❌ موجودی کافی نیست. ({balance:,} ت)", show_alert=True)
        return

    plan_id = data["selected_plan_id"]
    plan = await db.get_plan(plan_id)
    if not plan:
        await callback.answer("❌ پلن یافت نشد.", show_alert=True)
        return

    if not await db.deduct_wallet_balance(callback.from_user.id, price, f"خرید {plan[1]}"):
        await callback.answer("❌ خطا در پرداخت.", show_alert=True)
        return

    order_id = await db.create_order(callback.from_user.id, plan_id, price, "wallet")
    reserved = await db.reserve_account(plan_id, callback.from_user.id, order_id)
    if not reserved:
        await db.add_wallet_balance(callback.from_user.id, price, "بازگشت — موجودی اکانت")
        await callback.answer("❌ اکانت آزاد نیست.", show_alert=True)
        return

    await db.update_order_status(order_id, "approved", reserved)
    await db.sell_account(reserved, callback.from_user.id)
    expire_at = (datetime.now() + timedelta(days=plan[3])).isoformat()
    await db.update_order_expire(order_id, expire_at)
    await db.process_referral_bonus(callback.from_user.id)

    acc = await db.get_account(reserved)
    expire_date = (datetime.now() + timedelta(days=plan[3])).strftime("%Y/%m/%d")
    approval = await get_msg("order_approved", plan=plan[1], username=acc[1],
                             password=acc[2], days=plan[3], expire_date=expire_date)
    await state.clear()
    await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                     approval, user_main_kb(), callback=callback)
    await callback.answer("✅ خرید با موفقیت انجام شد!")


# ============ معرفی به دوستان ============
@router.callback_query(F.data == "menu_referral")
async def menu_referral(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    refs = await db.count_referrals(uid)
    purchases = await db.count_referral_purchases(uid)
    text = (
        f"👥 <b>معرفی به دوستان</b>\n\n"
        f"🔗 لینک دعوت شما:\n<code>{link}</code>\n\n"
        f"🎁 به ازای هر دوستی که اولین خریدش را انجام دهد،\n"
        f"<b>{REFERRAL_BONUS:,} تومان</b> به کیف پول شما اضافه می‌شود.\n\n"
        f"📊 معرفی‌شده‌ها: {refs} نفر\n"
        f"🛒 خریدهای موفق: {purchases} نفر"
    )
    await show_panel(bot, uid, callback.message.chat.id, text, back_kb(), callback=callback)
    await callback.answer()


# ============ آنلاک Apple ID ============
@router.callback_query(F.data == "menu_apple_unlock")
async def menu_apple_unlock(callback: CallbackQuery, state: FSMContext, bot: Bot):
    active = await db.get_user_active_apple_unlock(callback.from_user.id)
    if active:
        order = await db.get_apple_unlock(active[0])
        st = STATUS_FA.get(order[12], order[12])
        text = (
            f"🔓 <b>سفارش آنلاک #{order[0]}</b>\n\n"
            f"📧 Apple ID: <code>{order[2]}</code>\n"
            f"📊 وضعیت: {st}\n"
        )
        if order[10] and order[12] == "awaiting_payment":
            text += f"\n💰 مبلغ: {order[10]:,} تومان\n⏰ زمان: {order[11] or '-'}"
        await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                         text, apple_unlock_status_kb(order[0], order[12]), callback=callback)
        await callback.answer()
        return

    await show_panel(
        bot, callback.from_user.id, callback.message.chat.id,
        "🔓 <b>آنلاک Apple ID</b>\n\n📧 Apple ID خود را وارد کنید:",
        back_kb(), callback=callback,
    )
    await state.set_state(UserStates.apple_id)
    await callback.answer()


@router.message(UserStates.apple_id, F.text)
async def apple_id_input(message: Message, state: FSMContext, bot: Bot):
    await delete_user_message(message)
    await state.update_data(apple_id=message.text.strip())
    await show_panel(bot, message.from_user.id, message.chat.id,
                     "🔑 Password Apple ID را وارد کنید:", back_kb(), force_new=True)
    await state.set_state(UserStates.apple_password)


@router.message(UserStates.apple_password, F.text)
async def apple_password_input(message: Message, state: FSMContext, bot: Bot):
    await delete_user_message(message)
    await state.update_data(apple_password=message.text.strip())
    await show_panel(bot, message.from_user.id, message.chat.id,
                     "🎂 تاریخ تولد را وارد کنید:\n💡 مثال: 1370/05/15", back_kb(), force_new=True)
    await state.set_state(UserStates.apple_birthday)


@router.message(UserStates.apple_birthday, F.text)
async def apple_birthday_input(message: Message, state: FSMContext, bot: Bot):
    await delete_user_message(message)
    await state.update_data(apple_birthday=message.text.strip())
    await show_panel(bot, message.from_user.id, message.chat.id,
                     "❓ سوال امنیتی و پاسخ را وارد کنید:", back_kb(), force_new=True)
    await state.set_state(UserStates.apple_security)


@router.message(UserStates.apple_security, F.text)
async def apple_security_input(message: Message, state: FSMContext, bot: Bot):
    await delete_user_message(message)
    data = await state.get_data()
    order_id = await db.create_apple_unlock(
        message.from_user.id, data["apple_id"], data["apple_password"],
        data["apple_birthday"], message.text.strip(),
    )
    await state.update_data(apple_order_id=order_id)
    await show_panel(
        bot, message.from_user.id, message.chat.id,
        "📸 <b>عکس صفحه IMEI</b>\n\nدر گوشی *#06# بزنید و از صفحه عکس بگیرید.",
        apple_skip_kb("imei"), force_new=True,
    )
    await state.set_state(UserStates.apple_photo_imei)

    admins = await db.get_all_admins()
    for a in admins:
        try:
            await bot.send_message(
                a[0],
                f"🔓 <b>سفارش آنلاک جدید #{order_id}</b>\n"
                f"👤 {message.from_user.id}\n"
                f"📧 {data['apple_id']}",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(UserStates.apple_photo_imei, F.photo)
async def apple_photo_imei(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.update_apple_unlock_photos(data["apple_order_id"], imei=message.photo[-1].file_id)
    await delete_user_message(message)
    await show_panel(
        bot, message.from_user.id, message.chat.id,
        "📸 <b>عکس صفحه About</b>\n\nSettings → General → About",
        apple_skip_kb("about"), force_new=True,
    )
    await state.set_state(UserStates.apple_photo_about)


@router.callback_query(F.data == "apple_skip_imei", UserStates.apple_photo_imei)
async def skip_imei(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_panel(
        bot, callback.from_user.id, callback.message.chat.id,
        "📸 <b>عکس صفحه About</b>\n\nSettings → General → About",
        apple_skip_kb("about"), callback=callback,
    )
    await state.set_state(UserStates.apple_photo_about)
    await callback.answer()


@router.message(UserStates.apple_photo_about, F.photo)
async def apple_photo_about(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.update_apple_unlock_photos(data["apple_order_id"], about=message.photo[-1].file_id)
    await delete_user_message(message)
    await show_panel(
        bot, message.from_user.id, message.chat.id,
        "📸 <b>عکس پشت جعبه گوشی</b>",
        apple_skip_kb("box"), force_new=True,
    )
    await state.set_state(UserStates.apple_photo_box)


@router.callback_query(F.data == "apple_skip_about", UserStates.apple_photo_about)
async def skip_about(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_panel(
        bot, callback.from_user.id, callback.message.chat.id,
        "📸 <b>عکس پشت جعبه گوشی</b>",
        apple_skip_kb("box"), callback=callback,
    )
    await state.set_state(UserStates.apple_photo_box)
    await callback.answer()


@router.message(UserStates.apple_photo_box, F.photo)
async def apple_photo_box(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.update_apple_unlock_photos(data["apple_order_id"], box=message.photo[-1].file_id)
    await _finish_apple_photos(message, state, bot)


@router.callback_query(F.data == "apple_skip_box", UserStates.apple_photo_box)
async def skip_box(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await _finish_apple_photos_cb(callback, state, bot)


async def _finish_apple_photos(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await delete_user_message(message)
    text = (
        "✅ اطلاعات شما ثبت شد.\n\n"
        "⏳ ادمین قیمت و زمان آنلاک را تعیین می‌کند.\n"
        "سپس از شما فیش واریز درخواست می‌شود."
    )
    await show_panel(bot, message.from_user.id, message.chat.id, text, user_main_kb(), force_new=True)


async def _finish_apple_photos_cb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    text = (
        "✅ اطلاعات شما ثبت شد.\n\n"
        "⏳ ادمین قیمت و زمان آنلاک را تعیین می‌کند.\n"
        "سپس از شما فیش واریز درخواست می‌شود."
    )
    await show_panel(bot, callback.from_user.id, callback.message.chat.id,
                     text, user_main_kb(), callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("apple_pay_"))
async def apple_pay_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    order_id = int(callback.data.split("_")[-1])
    order = await db.get_apple_unlock(order_id)
    if not order or order[12] != "awaiting_payment":
        await callback.answer("❌ سفارش نامعتبر.", show_alert=True)
        return
    card = await db.get_setting("card_number")
    text = (
        f"💳 <b>پرداخت آنلاک #{order_id}</b>\n\n"
        f"💰 مبلغ: {order[10]:,} تومان\n"
        f"⏰ زمان تقریبی: {order[11] or '-'}\n\n"
        f"کارت:\n<code>{card}</code>\n\n"
        f"📸 فیش واریز را ارسال کنید."
    )
    await state.update_data(apple_pay_order_id=order_id)
    await show_panel(bot, callback.from_user.id, callback.message.chat.id, text, back_kb(), callback=callback)
    await state.set_state(UserStates.apple_payment_receipt)
    await callback.answer()


@router.message(UserStates.apple_payment_receipt, F.photo)
async def apple_payment_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data["apple_pay_order_id"]
    await db.set_apple_unlock_receipt(order_id, message.photo[-1].file_id)
    await state.clear()
    await delete_user_message(message)
    await show_panel(
        bot, message.from_user.id, message.chat.id,
        "✅ فیش ارسال شد. پس از تایید ادمین، آنلاک انجام می‌شود.",
        user_main_kb(), force_new=True,
    )
    admins = await db.get_all_admins()
    for a in admins:
        try:
            await bot.send_photo(
                a[0], message.photo[-1].file_id,
                caption=f"🔓 فیش آنلاک #{order_id} — کاربر {message.from_user.id}",
                parse_mode="HTML",
            )
        except Exception:
            pass
