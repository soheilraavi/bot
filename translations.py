TRANSLATIONS = {
    "fa": {
        "welcome": "👋 سلام {name}!\nبه ربات خوش آمدید.",
        "select_plan": "🛒 پلن را انتخاب کنید:",
        "waitlist_ask": "❌ پلن <b>{plan}</b> ناموجود است.\n\n📊 {count} نفر در لیست انتظار\n\n🎯 می‌خواهی ثبت‌نام کنی؟",
        "waitlist_success": "✅ در لیست انتظار ثبت‌نام شدی.\nبه محض موجود شدن، اطلاع‌رسانی می‌شود.",
        "waitlist_position": "📊 جایگاه شما: {position} از {total}",
        "new_account_available": "🎉 اکانت برای پلن <b>{plan}</b> موجود شد!\nهمین حالا خرید کنید.",
        "renewal_reminder": "⏰ سرویس <b>{plan}</b> شما تا <b>{days}</b> روز دیگر منقضی می‌شود.\nبرای تمدید اقدام کنید.",
        "language_changed": "✅ زبان تغییر کرد: {lang}",
        "refund_title": "💰 <b>قوانین بازگشت وجه:</b>\n\n✅ تا ۲۴ ساعت: بازگشت کامل\n⚠️ بعد از ۲۴ ساعت: بدون بازگشت\n❌ در صورت استفاده: بدون بازگشت",
        "support_title": "🛡️ <b>ارتباط با پشتیبانی:</b>\n\n{support}\n\n⏰ ۹ صبح تا ۱۲ شب",
    },
    "en": {
        "welcome": "👋 Hello {name}!\nWelcome.",
        "select_plan": "🛒 Select a plan:",
        "waitlist_ask": "❌ Plan <b>{plan}</b> is out of stock.\n\n📊 {count} in waitlist\n\n🎯 Join?",
        "waitlist_success": "✅ Joined waitlist.\nYou'll be notified.",
        "waitlist_position": "📊 Position: {position} of {total}",
        "new_account_available": "🎉 Account for <b>{plan}</b> is available!\nBuy now.",
        "renewal_reminder": "⏰ Your <b>{plan}</b> expires in <b>{days}</b> days.\nRenew now.",
        "language_changed": "✅ Language: {lang}",
        "refund_title": "💰 <b>Refund Policy:</b>\n\n✅ 24h: Full refund\n⚠️ After 24h: No refund",
        "support_title": "🛡️ <b>Support:</b>\n\n{support}",
    },
    "ar": {
        "welcome": "👋 مرحبا {name}!\nأهلا بك.",
        "select_plan": "🛒 اختر خطة:",
        "waitlist_ask": "❌ خطة <b>{plan}</b> غير متوفرة.\n\n📊 {count} في القائمة\n\n🎯 انضم؟",
        "waitlist_success": "✅ انضممت للقائمة.",
        "waitlist_position": "📊 موقعك: {position} من {total}",
        "new_account_available": "🎉 حساب <b>{plan}</b> متوفر!",
        "renewal_reminder": "⏰ خدمتك <b>{plan}</b> تنتهي خلال <b>{days}</b> أيام.",
        "language_changed": "✅ اللغة: {lang}",
        "refund_title": "💰 <b>سياسة الاسترداد:</b>\n\n✅ 24 ساعة: استرداد كامل",
        "support_title": "🛡️ <b>الدعم:</b>\n\n{support}",
    }
}

LANG_NAMES = {"fa": "🇮🇷 فارسی", "en": "🇬🇧 English", "ar": "🇸🇦 العربية"}


def t(key: str, lang: str = "fa", **kwargs) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fa"]).get(key, key)
    try:
        return text.format(**kwargs)
    except:
        return text


def get_language_name(code: str) -> str:
    return LANG_NAMES.get(code, code)