"""
تسک‌های پس‌زمینه - نسخه bug-fixed
"""

import os
import shutil
import asyncio
import logging
from datetime import datetime
from config import DB_NAME, BACKUP_DIR, RENEWAL_REMINDER_DAYS
from database import db
from translations import t

# BUG FIX: حداکثر پیام در ثانیه برای broadcast (جلوگیری از flood ban)
BROADCAST_DELAY = 0.05  # 50ms بین هر پیام = ~20 پیام در ثانیه


async def auto_backup():
    """بکاپ خودکار روزانه"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    while True:
        await asyncio.sleep(86400)
        try:
            name = f"backup_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.db"
            shutil.copy(DB_NAME, os.path.join(BACKUP_DIR, name))
            logging.info(f"✅ Backup: {name}")
        except Exception as e:
            logging.error(f"Backup failed: {e}")


async def renewal_reminder(bot):
    """یادآوری تمدید - هر 6 ساعت"""
    await asyncio.sleep(60)
    while True:
        try:
            expiring = await db.get_expiring_orders(days=RENEWAL_REMINDER_DAYS)
            for order in expiring:
                # ایندکس‌ها: 0=id, 1=user_id, 2=plan_id, 3=price, 4=status,
                #             5=receipt_file_id, 6=account_id, 7=created_at, 8=expire_at,
                #             9=admin_message_id, 10=telegram_id, 11=username, 12=plan_name
                user_id = order[10]   # telegram_id از JOIN
                plan_name = order[12]  # plan_name از JOIN
                expire_str = order[8]  # expire_at

                if not expire_str or not user_id:
                    continue

                try:
                    expire_at = datetime.fromisoformat(expire_str)
                    days_left = max(0, (expire_at - datetime.now()).days)
                    lang = await db.get_user_language(user_id)
                    text = t("renewal_reminder", lang, plan=plan_name, days=days_left)
                    await bot.send_message(user_id, text, parse_mode="HTML")
                    await db.log("RENEWAL_REMINDER", user_id, f"Order {order[0]}, {days_left} days left")
                except Exception as e:
                    logging.error(f"Reminder failed for {user_id}: {e}")

        except Exception as e:
            logging.error(f"Renewal reminder error: {e}")
        await asyncio.sleep(21600)


WAITLIST_CHECK_INTERVAL = 120  # هر ۲ دقیقه
CHAT_CLEANUP_INTERVAL = 1800  # هر ۳۰ دقیقه


async def waitlist_notifier(bot):
    """اطلاع‌رسانی لیست انتظار — فقط وقتی اکانت آزاد برای همان پلن وجود دارد"""
    await asyncio.sleep(60)
    while True:
        try:
            plans = await db.get_all_plans()
            for plan in plans:
                plan_id, plan_name = plan[0], plan[1]
                if not plan[4]:  # پلن غیرفعال
                    continue
                free_count = await db.count_accounts(plan_id=plan_id, status='free')
                if free_count == 0:
                    continue

                waitlist = await db.get_waitlist(plan_id=plan_id, status='waiting')
                for w in waitlist:
                    if w[4]:  # notified=1
                        continue
                    waitlist_id = w[0]
                    user_id = w[1]  # telegram_id
                    if not user_id:
                        continue
                    try:
                        lang = await db.get_user_language(user_id)
                        text = t("new_account_available", lang, plan=plan_name)
                        await bot.send_message(user_id, text, parse_mode="HTML")
                        await db.mark_waitlist_notified(waitlist_id)
                        await db.log("WAITLIST_NOTIFY", user_id, f"Plan {plan_name}")
                        await asyncio.sleep(BROADCAST_DELAY)
                    except Exception as e:
                        logging.error(f"Waitlist notify failed for {user_id}: {e}")
        except Exception as e:
            logging.error(f"Waitlist notifier error: {e}")
        await asyncio.sleep(WAITLIST_CHECK_INTERVAL)


async def chat_cleanup(bot):
    """پاکسازی چت هر ۳۰ دقیقه — فقط منوی اصلی بماند"""
    from chat_manager import cleanup_chat
    await asyncio.sleep(120)
    while True:
        try:
            user_ids = await db.get_all_chat_users()
            all_users = await db.execute("SELECT telegram_id FROM users")
            ids = {uid for uid in user_ids}
            ids.update(u[0] for u in all_users)
            for uid in ids:
                try:
                    await cleanup_chat(bot, uid)
                except Exception as e:
                    logging.error(f"Chat cleanup failed for {uid}: {e}")
                await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Chat cleanup error: {e}")
        await asyncio.sleep(CHAT_CLEANUP_INTERVAL)
