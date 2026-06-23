"""
کیبوردهای ربات - نسخه کامل
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ============ USER KEYBOARDS ============

def language_select_kb():
    """کیبورد انتخاب زبان - اولین چیزی که کاربر می‌بینه"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🇮🇷 فارسی", callback_data="lang_fa")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.button(text="🇸🇦 العربية", callback_data="lang_ar")
    kb.adjust(1)
    return kb.as_markup()


def user_main_kb():
    """منوی اصلی کاربر - InlineKeyboard (تک پیامی)"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 خرید اشتراک", callback_data="menu_buy")
    kb.button(text="📦 سرویس‌های من", callback_data="menu_services")
    kb.button(text="💳 کیف پول", callback_data="menu_wallet")
    kb.button(text="🔓 آنلاک Apple ID", callback_data="menu_apple_unlock")
    kb.button(text="📚 آموزش اتصال", callback_data="menu_tutorials")
    kb.button(text="🎫 تیکت پشتیبانی", callback_data="menu_ticket")
    kb.button(text="👥 معرفی به دوستان", callback_data="menu_referral")
    kb.button(text="📱 سوالات متداول", callback_data="menu_faq")
    kb.button(text="ℹ️ درباره ما", callback_data="menu_about")
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()

def plans_list_with_stock_kb(plans, stock_counts):
    """لیست پلن‌ها با نمایش موجودی"""
    kb = InlineKeyboardBuilder()
    for p in plans:
        plan_id, name, price, days = p
        count = stock_counts.get(plan_id, 0)
        if count > 0:
            text = f"{name} | 💰 {price:,} تومان | ✅ موجود: {count}"
            kb.button(text=text, callback_data=f"plan_select_{plan_id}")
        else:
            text = f"{name} | 💰 {price:,} تومان | ❌ ناموجود"
            kb.button(text=text, callback_data=f"plan_waitlist_{plan_id}")
    kb.button(text="🔙 بازگشت به منوی اصلی", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def payment_kb(plan_id=None):
    """کیبورد پرداخت"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 پرداخت با کیف پول", callback_data="pay_wallet")
    kb.button(text="🎁 اعمال کد تخفیف", callback_data="apply_coupon")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def wallet_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ شارژ کیف پول", callback_data="wallet_topup")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def apple_skip_kb(step: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ ندارم", callback_data=f"apple_skip_{step}")
    kb.button(text="🔙 انصراف", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def apple_unlock_status_kb(order_id, status):
    kb = InlineKeyboardBuilder()
    if status == "awaiting_payment":
        kb.button(text="📸 ارسال فیش واریز", callback_data=f"apple_pay_{order_id}")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def tutorials_list_kb(tutorials):
    """لیست آموزش‌ها"""
    kb = InlineKeyboardBuilder()
    for t in tutorials:
        kb.button(text=f"{t[1]} | {t[2]}", callback_data=f"tutorial_view_{t[0]}")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def ticket_menu_kb(has_open):
    """منوی تیکت"""
    kb = InlineKeyboardBuilder()
    if has_open:
        kb.button(text="💬 مشاهده تیکت باز", callback_data="ticket_my_open")
    else:
        kb.button(text="📝 ایجاد تیکت جدید", callback_data="ticket_new")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def back_kb(to: str = "back_home"):
    """دکمه بازگشت"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت", callback_data=to)
    return kb.as_markup()


def confirm_delete_kb(entity: str, item_id, return_to: str):
    """کیبورد تایید حذف"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ بله، حذف کن", callback_data=f"confirm_delete_{entity}_{item_id}")
    kb.button(text="❌ انصراف", callback_data=return_to)
    kb.adjust(2)
    return kb.as_markup()


def waitlist_confirm_kb(plan_id):
    """تایید ثبت‌نام در لیست انتظار"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ بله، ثبت‌نام در لیست انتظار", callback_data=f"waitlist_confirm_{plan_id}")
    kb.button(text="❌ انصراف", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


def quick_reply_kb():
    """سوالات متداول"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔌 چطور وصل شم؟", callback_data="qr_howto")
    kb.button(text="💰 قوانین بازگشت وجه", callback_data="qr_refund")
    kb.button(text="🛡️ ارتباط با پشتیبانی", callback_data="qr_support")
    kb.button(text="🔙 بازگشت", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()


# ============ ADMIN KEYBOARDS ============

def admin_main_kb():
    """منوی اصلی ادمین"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 سفارش‌ها", callback_data="admin_orders")
    kb.button(text="📦 اکانت‌ها", callback_data="admin_accounts")
    kb.button(text="💎 پلن‌ها", callback_data="admin_plans")
    kb.button(text="🎟 کد تخفیف", callback_data="admin_coupons")
    kb.button(text="📚 آموزش‌ها", callback_data="admin_tutorials")
    kb.button(text="🎫 تیکت‌ها", callback_data="admin_tickets")
    kb.button(text="👥 مشتریان", callback_data="admin_customers")
    kb.button(text="👑 ادمین‌ها", callback_data="admin_admins")
    kb.button(text="🎯 لیست انتظار", callback_data="admin_waitlist")
    kb.button(text="📜 قوانین", callback_data="admin_terms")
    kb.button(text="✉️ پیام به کاربر", callback_data="admin_send_msg")
    kb.button(text="📝 ویرایش متن‌ها", callback_data="admin_edit_messages")
    kb.button(text="📊 آمار", callback_data="admin_stats")
    kb.button(text="⚙️ تنظیمات", callback_data="admin_settings")
    kb.button(text="📜 لاگ‌ها", callback_data="admin_logs")
    kb.button(text="📢 پیام همگانی", callback_data="admin_broadcast")
    kb.button(text="💳 شارژ کیف پول", callback_data="admin_wallet_topups")
    kb.button(text="🔓 آنلاک Apple ID", callback_data="admin_apple_unlocks")
    kb.button(text="💾 بکاپ", callback_data="admin_backup")
    kb.adjust(2)
    return kb.as_markup()


def admin_order_actions_kb(order_id, status):
    """دکمه‌های عملیات سفارش"""
    kb = InlineKeyboardBuilder()
    if status == "pending":
        kb.button(text="✅ تایید و تحویل", callback_data=f"admin_order_approve_{order_id}")
        kb.button(text="❌ رد کردن", callback_data=f"admin_order_reject_{order_id}")
        kb.adjust(2)
    kb.button(text="🔙 بازگشت", callback_data="admin_orders")
    kb.adjust(1)
    return kb.as_markup()


def admin_account_actions_kb(acc_id, status):
    """دکمه‌های عملیات اکانت"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش یوزر", callback_data=f"admin_acc_edit_user_{acc_id}")
    kb.button(text="✏️ ویرایش پسورد", callback_data=f"admin_acc_edit_pass_{acc_id}")
    kb.button(text="✏️ ویرایش یادداشت", callback_data=f"admin_acc_edit_note_{acc_id}")
    kb.button(text="🗑 حذف", callback_data=f"admin_acc_delete_{acc_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_accounts")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def admin_plan_actions_kb(plan_id, is_active):
    """دکمه‌های عملیات پلن"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش نام", callback_data=f"admin_plan_edit_name_{plan_id}")
    kb.button(text="💰 تغییر قیمت", callback_data=f"admin_plan_edit_price_{plan_id}")
    kb.button(text="📅 تغییر مدت", callback_data=f"admin_plan_edit_days_{plan_id}")
    if is_active:
        kb.button(text="🔴 غیرفعال", callback_data=f"admin_plan_toggle_{plan_id}")
    else:
        kb.button(text="🟢 فعال", callback_data=f"admin_plan_toggle_{plan_id}")
    kb.button(text="🗑 حذف", callback_data=f"admin_plan_delete_{plan_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_plans")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def admin_plan_price_kb(plan_id, current_price):
    """تغییر قیمت پلن"""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"💰 فعلی: {current_price:,}", callback_data="noop")
    kb.button(text="+1,000", callback_data=f"admin_plan_price_up_{plan_id}_1000")
    kb.button(text="-1,000", callback_data=f"admin_plan_price_down_{plan_id}_1000")
    kb.button(text="+10,000", callback_data=f"admin_plan_price_up_{plan_id}_10000")
    kb.button(text="-10,000", callback_data=f"admin_plan_price_down_{plan_id}_10000")
    kb.button(text="+100,000", callback_data=f"admin_plan_price_up_{plan_id}_100000")
    kb.button(text="-100,000", callback_data=f"admin_plan_price_down_{plan_id}_100000")
    kb.button(text="+1,000,000", callback_data=f"admin_plan_price_up_{plan_id}_1000000")
    kb.button(text="-1,000,000", callback_data=f"admin_plan_price_down_{plan_id}_1000000")
    kb.button(text="✏️ مقدار دلخواه", callback_data=f"admin_plan_price_custom_{plan_id}")
    kb.button(text="🔙 بازگشت", callback_data=f"admin_plan_view_{plan_id}")
    kb.adjust(1, 2, 2, 2, 2, 1, 1)
    return kb.as_markup()


def admin_plan_days_kb(plan_id, current_days):
    """تغییر مدت پلن"""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"📅 فعلی: {current_days} روز", callback_data="noop")
    kb.button(text="+1 روز", callback_data=f"admin_plan_days_up_{plan_id}_1")
    kb.button(text="-1 روز", callback_data=f"admin_plan_days_down_{plan_id}_1")
    kb.button(text="+7 روز", callback_data=f"admin_plan_days_up_{plan_id}_7")
    kb.button(text="-7 روز", callback_data=f"admin_plan_days_down_{plan_id}_7")
    kb.button(text="+30 روز", callback_data=f"admin_plan_days_up_{plan_id}_30")
    kb.button(text="-30 روز", callback_data=f"admin_plan_days_down_{plan_id}_30")
    kb.button(text="✏️ مقدار دلخواه", callback_data=f"admin_plan_days_custom_{plan_id}")
    kb.button(text="🔙 بازگشت", callback_data=f"admin_plan_view_{plan_id}")
    kb.adjust(1, 2, 2, 2, 1, 1)
    return kb.as_markup()


def admin_coupon_actions_kb(coupon_id, is_active):
    """دکمه‌های عملیات کد تخفیف"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش کد", callback_data=f"admin_coupon_edit_code_{coupon_id}")
    kb.button(text="% تغییر تخفیف", callback_data=f"admin_coupon_edit_discount_{coupon_id}")
    kb.button(text="🔢 تغییر محدودیت", callback_data=f"admin_coupon_edit_limit_{coupon_id}")
    if is_active:
        kb.button(text="🔴 غیرفعال", callback_data=f"admin_coupon_toggle_{coupon_id}")
    else:
        kb.button(text="🟢 فعال", callback_data=f"admin_coupon_toggle_{coupon_id}")
    kb.button(text="🗑 حذف", callback_data=f"admin_coupon_delete_{coupon_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_coupons")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def admin_coupon_discount_kb(coupon_id, current):
    """تغییر درصد تخفیف"""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"% فعلی: {current}", callback_data="noop")
    kb.button(text="+5%", callback_data=f"admin_coupon_discount_up_{coupon_id}_5")
    kb.button(text="-5%", callback_data=f"admin_coupon_discount_down_{coupon_id}_5")
    kb.button(text="+10%", callback_data=f"admin_coupon_discount_up_{coupon_id}_10")
    kb.button(text="-10%", callback_data=f"admin_coupon_discount_down_{coupon_id}_10")
    kb.button(text="+20%", callback_data=f"admin_coupon_discount_up_{coupon_id}_20")
    kb.button(text="-20%", callback_data=f"admin_coupon_discount_down_{coupon_id}_20")
    kb.button(text="✏️ مقدار دلخواه", callback_data=f"admin_coupon_discount_custom_{coupon_id}")
    kb.button(text="🔙 بازگشت", callback_data=f"admin_coupon_view_{coupon_id}")
    kb.adjust(1, 2, 2, 2, 1, 1)
    return kb.as_markup()


def admin_coupon_limit_kb(coupon_id, current):
    """تغییر محدودیت کد تخفیف"""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🔢 فعلی: {current}", callback_data="noop")
    kb.button(text="+1", callback_data=f"admin_coupon_limit_up_{coupon_id}_1")
    kb.button(text="-1", callback_data=f"admin_coupon_limit_down_{coupon_id}_1")
    kb.button(text="+5", callback_data=f"admin_coupon_limit_up_{coupon_id}_5")
    kb.button(text="-5", callback_data=f"admin_coupon_limit_down_{coupon_id}_5")
    kb.button(text="+10", callback_data=f"admin_coupon_limit_up_{coupon_id}_10")
    kb.button(text="+50", callback_data=f"admin_coupon_limit_up_{coupon_id}_50")
    kb.button(text="✏️ مقدار دلخواه", callback_data=f"admin_coupon_limit_custom_{coupon_id}")
    kb.button(text="🔙 بازگشت", callback_data=f"admin_coupon_view_{coupon_id}")
    kb.adjust(1, 2, 2, 2, 1, 1)
    return kb.as_markup()


def admin_tutorial_actions_kb(tut_id):
    """دکمه‌های عملیات آموزش"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش پلتفرم", callback_data=f"admin_tut_edit_platform_{tut_id}")
    kb.button(text="✏️ ویرایش عنوان", callback_data=f"admin_tut_edit_title_{tut_id}")
    kb.button(text="✏️ ویرایش محتوا", callback_data=f"admin_tut_edit_content_{tut_id}")
    kb.button(text="🗑 حذف", callback_data=f"admin_tut_delete_{tut_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_tutorials")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def admin_ticket_actions_kb(ticket_id, status, is_owner_ticket=False):
    """دکمه‌های عملیات تیکت"""
    kb = InlineKeyboardBuilder()
    if status == "open":
        kb.button(text="💬 پاسخ", callback_data=f"admin_ticket_reply_{ticket_id}")
        kb.button(text="🔒 بستن", callback_data=f"admin_ticket_close_{ticket_id}")
    else:
        kb.button(text="🔓 باز کردن", callback_data=f"admin_ticket_reopen_{ticket_id}")
    if not is_owner_ticket:
        kb.button(text="📨 پیام خصوصی", callback_data=f"admin_ticket_pv_{ticket_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_tickets")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def admin_customer_actions_kb(telegram_id, is_banned):
    """دکمه‌های عملیات مشتری"""
    kb = InlineKeyboardBuilder()
    if is_banned:
        kb.button(text="🟢 رفع مسدودی", callback_data=f"admin_cust_unban_{telegram_id}")
    else:
        kb.button(text="🔴 مسدود کردن", callback_data=f"admin_cust_ban_{telegram_id}")
    kb.button(text="📨 ارسال پیام خصوصی", callback_data=f"admin_cust_pv_{telegram_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_customers")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def admin_admin_actions_kb(user_id, role, is_owner_caller):
    """دکمه‌های عملیات ادمین"""
    kb = InlineKeyboardBuilder()
    if role != "OWNER" and is_owner_caller:
        kb.button(text="🗑 حذف ادمین", callback_data=f"admin_admin_remove_{user_id}")
    kb.button(text="🔙 بازگشت", callback_data="admin_admins")
    kb.adjust(1, 1)
    return kb.as_markup()


def admin_settings_kb():
    """تنظیمات"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 شماره کارت", callback_data="admin_set_card")
    kb.button(text="🛡️ یوزر پشتیبانی", callback_data="admin_set_support")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1, 1)
    return kb.as_markup()


def admin_acc_plan_select_kb(plans):
    """انتخاب پلن برای اکانت"""
    kb = InlineKeyboardBuilder()
    if not plans:
        kb.button(text="❌ پلنی نیست", callback_data="noop")
    else:
        for p in plans:
            kb.button(text=f"{p[1]} | {p[2]:,}ت", callback_data=f"admin_acc_plan_{p[0]}")
    kb.adjust(1)
    kb.button(text="🔙 انصراف", callback_data="admin_accounts")
    return kb.as_markup()


def admin_edit_messages_kb():
    """کیبورد ویرایش متن‌ها"""
    kb = InlineKeyboardBuilder()
    messages = [
        ("welcome", "👋 پیام خوش‌آمدگویی"),
        ("receipt_received", "📸 پیام دریافت رسید"),
        ("order_approved", "✅ پیام تایید سفارش"),
        ("order_rejected", "❌ پیام رد سفارش"),
        ("coupon_applied", "🎁 پیام اعمال کد تخفیف"),
        ("ticket_created", "🎫 پیام ایجاد تیکت"),
    ]
    for key, label in messages:
        kb.button(text=label, callback_data=f"admin_edit_msg_{key}")
    kb.button(text="🔙 بازگشت", callback_data="admin_back")
    kb.adjust(1)
    return kb.as_markup()