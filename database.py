"""
مدیریت دیتابیس - نسخه نهایی کامل + bug fixes
"""

import aiosqlite
import logging
from datetime import datetime, timedelta
from config import DB_NAME, OWNER_ID

# ============ فیلدهای مجاز برای جلوگیری از SQL Injection ============
ALLOWED_ACCOUNT_FIELDS = {"username", "password", "note", "status", "plan_id", "sold_to", "sold_at"}
REFERRAL_BONUS = 50000
ALLOWED_PLAN_FIELDS = {"name", "price", "days", "is_active", "sort_order"}
ALLOWED_COUPON_FIELDS = {"code", "discount_percent", "uses_limit", "is_active", "expire_at"}
ALLOWED_TUTORIAL_FIELDS = {"platform", "title", "content", "sort_order"}


class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self._conn = None

    async def get_conn(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_name)
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute("PRAGMA cache_size=-64000")
        return self._conn

    async def init(self):
        conn = await self.get_conn()
        await conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE,
                username TEXT, first_name TEXT, is_banned INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                price INTEGER, days INTEGER, is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT,
                password TEXT, plan_id INTEGER, status TEXT DEFAULT 'free',
                sold_to INTEGER, sold_at TEXT, note TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                plan_id INTEGER, price INTEGER, status TEXT DEFAULT 'pending',
                receipt_file_id TEXT, account_id INTEGER, created_at TEXT,
                expire_at TEXT
            );
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE,
                discount_percent INTEGER, uses_limit INTEGER,
                used_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
                created_at TEXT, expire_at TEXT
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY, role TEXT, added_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT,
                title TEXT, content TEXT, sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                subject TEXT, status TEXT DEFAULT 'open',
                created_at TEXT, closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER,
                sender_type TEXT, sender_id INTEGER, message TEXT,
                file_id TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT,
                user_id INTEGER, username TEXT, details TEXT, time TEXT
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, plan_id INTEGER,
                status TEXT DEFAULT 'waiting',
                notified INTEGER DEFAULT 0,
                created_at TEXT, notified_at TEXT
            );
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'fa',
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_acc_status ON accounts(status);
            CREATE INDEX IF NOT EXISTS idx_acc_plan ON accounts(plan_id);
            CREATE INDEX IF NOT EXISTS idx_ord_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_ord_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_tick_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_users_tg ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_wait_status ON waitlist(status);
            CREATE INDEX IF NOT EXISTS idx_wait_plan ON waitlist(plan_id);
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, message_id INTEGER, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount INTEGER, type TEXT,
                description TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS wallet_topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount INTEGER, status TEXT DEFAULT 'pending',
                receipt_file_id TEXT, created_at TEXT, approved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS apple_unlock_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, apple_id TEXT, password TEXT,
                birthday TEXT, security_question TEXT,
                imei_photo TEXT, about_photo TEXT, box_photo TEXT,
                price INTEGER DEFAULT 0, unlock_time TEXT,
                receipt_file_id TEXT, status TEXT DEFAULT 'info_submitted',
                created_at TEXT, updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_wallet_user ON wallet_transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_apple_status ON apple_unlock_orders(status);
        ''')
        await conn.commit()

        # Migrations
        for col, definition in [
            ("expire_at", "TEXT"),
            ("phone", "TEXT"),
            ("terms_accepted", "INTEGER DEFAULT 0"),
            ("admin_message_id", "INTEGER DEFAULT 0"),
        ]:
            table = "orders" if col in ("expire_at", "admin_message_id") else "users"
            if col == "expire_at":
                try:
                    await conn.execute("SELECT expire_at FROM orders LIMIT 1")
                except:
                    await conn.execute("ALTER TABLE orders ADD COLUMN expire_at TEXT")
                    await conn.commit()
            elif col == "phone":
                try:
                    await conn.execute("SELECT phone FROM users LIMIT 1")
                except:
                    await conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                    await conn.commit()
            elif col == "terms_accepted":
                try:
                    await conn.execute("SELECT terms_accepted FROM users LIMIT 1")
                except:
                    await conn.execute("ALTER TABLE users ADD COLUMN terms_accepted INTEGER DEFAULT 0")
                    await conn.commit()
            elif col == "admin_message_id":
                try:
                    await conn.execute("SELECT admin_message_id FROM orders LIMIT 1")
                except:
                    await conn.execute("ALTER TABLE orders ADD COLUMN admin_message_id INTEGER DEFAULT 0")
                    await conn.commit()

        try:
            await conn.execute("SELECT expire_at FROM coupons LIMIT 1")
        except:
            await conn.execute("ALTER TABLE coupons ADD COLUMN expire_at TEXT")
            await conn.commit()

        for col, sql in [
            ("wallet_balance", "ALTER TABLE users ADD COLUMN wallet_balance INTEGER DEFAULT 0"),
            ("referred_by", "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0"),
            ("referral_code", "ALTER TABLE users ADD COLUMN referral_code TEXT"),
            ("menu_message_id", "ALTER TABLE user_settings ADD COLUMN menu_message_id INTEGER DEFAULT 0"),
        ]:
            table = "users" if col in ("wallet_balance", "referred_by", "referral_code") else "user_settings"
            try:
                await conn.execute(f"SELECT {col} FROM {table} LIMIT 1")
            except Exception:
                await conn.execute(sql)
                await conn.commit()

        try:
            await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_acc_username ON accounts(username)")
            await conn.commit()
        except Exception:
            pass

        # داده‌های پیش‌فرض
        await self.add_admin(OWNER_ID, "OWNER")
        await self.set_setting("card_number", "6037-9999-9999-9999")
        await self.set_setting("support_username", "@SupportAdmin")

        terms_text = await self.get_setting("terms_text")
        if not terms_text:
            default_terms = """📜 <b>قوانین و مقررات استفاده از سرویس</b>

1️⃣ <b>شرایط استفاده:</b>
• استفاده از سرویس فقط برای مقاصد قانونی مجاز است
• کاربر مسئول حفظ اطلاعات حساب خود می‌باشد
• هرگونه سوءاستفاده منجر به قطع سرویس می‌شود

2️⃣ <b>پرداخت و بازگشت وجه:</b>
• پرداخت فقط از طریق روش‌های اعلام شده مجاز است
• بازگشت وجه تا ۲۴ ساعت پس از خرید امکان‌پذیر است
• پس از استفاده از سرویس، بازگشت وجه امکان‌پذیر نیست

3️⃣ <b>حریم خصوصی:</b>
• اطلاعات شخصی شما محفوظ می‌ماند
• شماره تلفن فقط برای احراز هویت استفاده می‌شود
• ما اطلاعات شما را با شخص ثالث به اشتراک نمی‌گذاریم

4️⃣ <b>مسئولیت‌ها:</b>
• کاربر مسئول استفاده صحیح از سرویس است
• در صورت قطعی سرویس، پشتیبانی در اسرع وقت پاسخگو خواهد بود
• تغییرات قوانین از طریق ربات اطلاع‌رسانی می‌شود

✅ با کلیک روی دکمه \"قبول می‌کنم\"، شما با تمام قوانین فوق موافقت می‌کنید."""
            await self.set_setting("terms_text", default_terms)

        # پیام‌های پیش‌فرض
        default_messages = {
            "welcome": (
                "🌹 سلام {name} عزیز!\n\n"
                "🌐 «در دنیای بی‌مرز، آزادی نفسِ اولین قدم است\n"
                "هر لحظه اتصال، پنجره‌ای به سوی دانایی و امنیت»\n\n"
                "✨ به ربات سرویس VPN خوش آمدید\n"
                "🛡️ اینجا دروازه‌ای است به اینترنت آزاد و امن\n\n"
                "👇 از منوی زیر گزینه مورد نظر را انتخاب کنید:"
            ),
            "apple_unlock_done": (
                "🎉 Apple ID شما با موفقیت آنلاک شد!\n\n"
                "📱 لطفاً گوشی خود را Restore کنید.\n\n"
                "🛡️ در صورت نیاز با پشتیبانی در ارتباط باشید."
            ),
            "receipt_received": "✅ رسید پرداخت شما با موفقیت دریافت شد.\n\n⏳ لطفاً صبر کنید تا همکاران ما رسید رو بررسی کنن.\n\n🕐 حداکثر زمان بررسی: 1 ساعت\n\nاز صبر و شکیبایی شما سپاسگزاریم 🙏",
            "order_approved": "🎉 تبریک! سفارش شما تایید شد.\n\n🎯 پلن: {plan}\n👤 Username: <code>{username}</code>\n🔑 Password: <code>{password}</code>\n\n📅 مدت اشتراک: {days} روز\n⏰ تاریخ انقضا: {expire_date}\n\n✅ اطلاعات بالا رو با دقت ذخیره کنید.",
            "order_rejected": "❌ متأسفانه سفارش شما تایید نشد.\n\nدر صورت وجود هرگونه سوال، با پشتیبانی در ارتباط باشید.\n\n🛡️ پشتیبانی: {support}",
            "coupon_applied": "🎁 کد تخفیف شما با موفقیت اعمال شد!\n\n💰 تخفیف: {discount}%\n💵 مبلغ نهایی: {new_price:,} تومان\n\n🏦 شماره کارت: <code>{card}</code>\n\n📸 لطفاً رسید پرداخت رو ارسال کنید.",
            "ticket_created": "✅ تیکت شما با موفقیت ثبت شد.\n\n🎫 شماره تیکت: #{ticket_id}\n📝 موضوع: {subject}\n\n🕐 همکاران ما در اسرع وقت پاسخگو خواهند بود.\nاز شکیبایی شما سپاسگزاریم 🙏",
            "ticket_reply": "🛡️ پاسخ پشتیبانی:\n\n{reply}",
        }
        for key, value in default_messages.items():
            existing = await self.get_setting(f"msg_{key}")
            if not existing:
                await self.set_setting(f"msg_{key}", value)

        if (await self.execute("SELECT COUNT(*) FROM plans"))[0][0] == 0:
            for n, p, d in [("🔹 1 ماهه", 150000, 30), ("🔹 3 ماهه", 390000, 90),
                            ("🔹 6 ماهه", 700000, 180), ("🔹 12 ماهه", 1200000, 365)]:
                await self.execute("INSERT INTO plans (name, price, days, sort_order) VALUES (?,?,?,?)", (n, p, d, 0))

        if (await self.execute("SELECT COUNT(*) FROM tutorials"))[0][0] == 0:
            for pl, ti, co in [("📱 iPhone", "آموزش آیفون", "۱. نصب\n۲. کانفیگ\n۳. اتصال"),
                               ("🤖 Android", "آموزش اندروید", "۱. نصب\n۲. لینک\n۳. اتصال"),
                               ("💻 Windows", "آموزش ویندوز", "۱. نصب\n۲. لاگین\n۳. Connect"),
                               ("🍎 Mac", "آموزش مک", "۱. نصب\n۲. تنظیمات")]:
                await self.execute("INSERT INTO tutorials (platform, title, content) VALUES (?,?,?)", (pl, ti, co))

    async def execute(self, query: str, params: tuple = ()):
        conn = await self.get_conn()
        async with conn.execute(query, params) as cursor:
            await conn.commit()
            rows = await cursor.fetchall()
            return [tuple(row) for row in rows]

    async def execute_one(self, query: str, params: tuple = ()):
        conn = await self.get_conn()
        async with conn.execute(query, params) as cursor:
            await conn.commit()
            row = await cursor.fetchone()
            return tuple(row) if row else None

    async def log(self, action, user_id, details, username=None):
        await self.execute("INSERT INTO logs (action, user_id, username, details, time) VALUES (?,?,?,?,?)",
                           (action, user_id, username, details, datetime.now().isoformat()))

    # ============ Settings ============
    async def get_setting(self, key, default=""):
        r = await self.execute_one("SELECT value FROM settings WHERE key=?", (key,))
        return r[0] if r else default

    async def set_setting(self, key, value):
        await self.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))

    # ============ Users ============
    async def add_user(self, telegram_id, username, first_name, referred_by=0):
        await self.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, first_name, referred_by, created_at) VALUES (?,?,?,?,?)",
            (telegram_id, username, first_name, referred_by, datetime.now().isoformat()))
        if referred_by:
            await self.execute("UPDATE users SET referred_by=? WHERE telegram_id=? AND referred_by=0",
                               (referred_by, telegram_id))

    async def set_referred_by(self, telegram_id, referrer_id):
        if telegram_id == referrer_id:
            return False
        r = await self.execute_one("SELECT referred_by FROM users WHERE telegram_id=?", (telegram_id,))
        if r and r[0]:
            return False
        await self.execute("UPDATE users SET referred_by=? WHERE telegram_id=?", (referrer_id, telegram_id))
        return True

    async def get_referrer(self, telegram_id):
        r = await self.execute_one("SELECT referred_by FROM users WHERE telegram_id=?", (telegram_id,))
        return r[0] if r and r[0] else 0

    async def count_referrals(self, user_id):
        r = await self.execute_one("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        return r[0] if r else 0

    async def count_referral_purchases(self, user_id):
        r = await self.execute_one("""
            SELECT COUNT(DISTINCT o.user_id) FROM orders o
            JOIN users u ON o.user_id=u.telegram_id
            WHERE u.referred_by=? AND o.status='approved'
        """, (user_id,))
        return r[0] if r else 0

    async def get_user(self, telegram_id):
        return await self.execute_one("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))

    async def get_all_users(self, offset=0, limit=5):
        return await self.execute("SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))

    async def count_users(self):
        r = await self.execute_one("SELECT COUNT(*) FROM users")
        return r[0] if r else 0

    async def ban_user(self, telegram_id, banned):
        await self.execute("UPDATE users SET is_banned=? WHERE telegram_id=?", (int(banned), telegram_id))

    async def is_banned(self, telegram_id):
        r = await self.execute_one("SELECT is_banned FROM users WHERE telegram_id=?", (telegram_id,))
        return bool(r and r[0])

    async def update_user_phone(self, telegram_id, phone):
        await self.execute("UPDATE users SET phone=? WHERE telegram_id=?", (phone, telegram_id))

    async def get_user_phone(self, telegram_id):
        r = await self.execute_one("SELECT phone FROM users WHERE telegram_id=?", (telegram_id,))
        return r[0] if r and r[0] else None

    async def accept_terms(self, telegram_id):
        await self.execute("UPDATE users SET terms_accepted=1 WHERE telegram_id=?", (telegram_id,))

    async def has_accepted_terms(self, telegram_id):
        r = await self.execute_one("SELECT terms_accepted FROM users WHERE telegram_id=?", (telegram_id,))
        return bool(r and r[0])

    # ============ Admins ============
    async def is_admin(self, telegram_id):
        r = await self.execute_one("SELECT 1 FROM admins WHERE user_id=?", (telegram_id,))
        return r is not None

    async def is_owner(self, telegram_id):
        r = await self.execute_one("SELECT role FROM admins WHERE user_id=?", (telegram_id,))
        return r is not None and r[0] == "OWNER"

    async def add_admin(self, user_id, role="ADMIN"):
        await self.execute("INSERT OR IGNORE INTO admins (user_id, role, added_at) VALUES (?,?,?)",
                           (user_id, role, datetime.now().isoformat()))

    async def remove_admin(self, user_id):
        await self.execute("DELETE FROM admins WHERE user_id=?", (user_id,))

    async def get_all_admins(self):
        return await self.execute("SELECT user_id, role, added_at FROM admins")

    # ============ Plans ============
    async def get_active_plans(self):
        return await self.execute("SELECT id, name, price, days FROM plans WHERE is_active=1 ORDER BY sort_order, id")

    async def get_all_plans(self):
        return await self.execute("SELECT * FROM plans ORDER BY sort_order, id")

    async def get_plan(self, plan_id):
        return await self.execute_one("SELECT * FROM plans WHERE id=?", (plan_id,))

    async def add_plan(self, name, price, days):
        await self.execute("INSERT INTO plans (name, price, days) VALUES (?,?,?)", (name, price, days))

    async def update_plan_field(self, plan_id, field, value):
        # BUG FIX: جلوگیری از SQL Injection با whitelist
        if field not in ALLOWED_PLAN_FIELDS:
            raise ValueError(f"فیلد غیرمجاز: {field}")
        await self.execute(f"UPDATE plans SET {field}=? WHERE id=?", (value, plan_id))

    async def delete_plan(self, plan_id):
        await self.execute("DELETE FROM plans WHERE id=?", (plan_id,))

    # ============ Accounts ============
    async def get_free_account(self, plan_id=None):
        try:
            if plan_id:
                return await self.execute_one(
                    "SELECT id, username, password FROM accounts WHERE status='free' AND plan_id=? LIMIT 1",
                    (plan_id,))
            return await self.execute_one(
                "SELECT id, username, password FROM accounts WHERE status='free' LIMIT 1")
        except Exception as e:
            logging.error(f"Error in get_free_account: {e}")
            return None

    async def reserve_account(self, plan_id, user_id, order_id):
        """رزرو اکانت به حالت pending برای سفارش"""
        acc = await self.get_free_account(plan_id)
        if not acc:
            acc = await self.get_free_account()
        if not acc:
            return None
        acc_id = acc[0]
        await self.execute(
            "UPDATE accounts SET status='pending', sold_to=?, note=? WHERE id=? AND status='free'",
            (user_id, f"order:{order_id}", acc_id))
        check = await self.execute_one("SELECT status FROM accounts WHERE id=?", (acc_id,))
        if not check or check[0] != 'pending':
            return None
        await self.execute("UPDATE orders SET account_id=? WHERE id=?", (acc_id, order_id))
        return acc_id

    async def release_pending_account(self, order_id):
        o = await self.get_order(order_id)
        if not o or not o[6]:
            return
        acc_id = o[6]
        await self.execute(
            "UPDATE accounts SET status='free', sold_to=NULL, note='' WHERE id=? AND status='pending'",
            (acc_id,))

    async def account_username_exists(self, username, exclude_id=None):
        if exclude_id:
            r = await self.execute_one(
                "SELECT id FROM accounts WHERE username=? AND id!=?", (username, exclude_id))
        else:
            r = await self.execute_one("SELECT id FROM accounts WHERE username=?", (username,))
        return r is not None

    async def get_all_accounts(self, status=None, plan_id=None, offset=0, limit=5):
        q = "SELECT a.*, p.name as plan_name FROM accounts a LEFT JOIN plans p ON a.plan_id=p.id WHERE 1=1"
        params = []
        if status:
            q += " AND a.status=?"
            params.append(status)
        if plan_id:
            q += " AND a.plan_id=?"
            params.append(plan_id)
        q += " ORDER BY a.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return await self.execute(q, tuple(params))

    async def count_accounts(self, status=None, plan_id=None):
        q = "SELECT COUNT(*) FROM accounts WHERE 1=1"
        params = []
        if status:
            q += " AND status=?"
            params.append(status)
        if plan_id:
            q += " AND plan_id=?"
            params.append(plan_id)
        r = await self.execute_one(q, tuple(params))
        return r[0] if r else 0

    async def get_pending_account_for_order(self, order_id):
        o = await self.get_order(order_id)
        if not o or not o[6]:
            return None
        return await self.get_account(o[6])

    async def get_account(self, account_id):
        return await self.execute_one(
            "SELECT a.*, p.name as plan_name FROM accounts a LEFT JOIN plans p ON a.plan_id=p.id WHERE a.id=?",
            (account_id,))

    async def add_account(self, username, password, plan_id, note=""):
        if await self.account_username_exists(username):
            raise ValueError(f"Username تکراری: {username}")
        await self.execute(
            "INSERT INTO accounts (username, password, plan_id, note, created_at) VALUES (?,?,?,?,?)",
            (username, password, plan_id, note, datetime.now().isoformat()))

    async def update_account_field(self, account_id, field, value):
        if field not in ALLOWED_ACCOUNT_FIELDS:
            raise ValueError(f"فیلد غیرمجاز: {field}")
        if field == "username" and await self.account_username_exists(value, exclude_id=account_id):
            raise ValueError(f"Username تکراری: {value}")
        await self.execute(f"UPDATE accounts SET {field}=? WHERE id=?", (value, account_id))

    async def delete_account(self, account_id):
        await self.execute("DELETE FROM accounts WHERE id=?", (account_id,))

    async def sell_account(self, account_id, user_id):
        try:
            await self.execute(
                "UPDATE accounts SET status='sold', sold_to=?, sold_at=? WHERE id=? AND status IN ('free','pending')",
                (user_id, datetime.now().isoformat(), account_id))
            logging.info(f"✅ Account {account_id} sold to user {user_id}")
        except Exception as e:
            logging.error(f"Error in sell_account: {e}")
            raise

    async def search_accounts(self, query, limit=10):
        return await self.execute(
            "SELECT a.*, p.name as plan_name FROM accounts a LEFT JOIN plans p ON a.plan_id=p.id WHERE a.username LIKE ? OR a.password LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit))

    # ============ Orders ============
    async def create_order(self, user_id, plan_id, price, receipt_file_id):
        await self.execute("INSERT INTO orders (user_id, plan_id, price, receipt_file_id, created_at) VALUES (?,?,?,?,?)",
                           (user_id, plan_id, price, receipt_file_id, datetime.now().isoformat()))
        r = await self.execute_one("SELECT id FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        return r[0] if r else None

    async def get_all_orders(self, status=None, offset=0, limit=5):
        q = "SELECT * FROM orders WHERE 1=1"
        params = []
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return await self.execute(q, tuple(params))

    async def count_orders(self, status=None):
        if status:
            r = await self.execute_one("SELECT COUNT(*) FROM orders WHERE status=?", (status,))
        else:
            r = await self.execute_one("SELECT COUNT(*) FROM orders")
        return r[0] if r else 0

    async def get_order(self, order_id):
        return await self.execute_one("SELECT * FROM orders WHERE id=?", (order_id,))

    async def update_order_status(self, order_id, status, account_id=None):
        try:
            current = await self.get_order(order_id)
            if not current:
                return False
            current_status = current[4]
            if current_status in ["approved", "rejected"]:
                logging.warning(f"Order {order_id} already {current_status}, skipping")
                return False
            if account_id:
                await self.execute("UPDATE orders SET status=?, account_id=? WHERE id=?",
                                   (status, account_id, order_id))
            else:
                await self.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
            logging.info(f"Order {order_id} updated to {status}")
            return True
        except Exception as e:
            logging.error(f"Error in update_order_status: {e}")
            return False

    async def update_order_expire(self, order_id, expire_at):
        await self.execute("UPDATE orders SET expire_at=? WHERE id=?", (expire_at, order_id))

    async def delete_order(self, order_id):
        await self.execute("DELETE FROM orders WHERE id=?", (order_id,))

    async def get_order_admin_message_id(self, order_id):
        try:
            r = await self.execute_one("SELECT admin_message_id FROM orders WHERE id=?", (order_id,))
            return r[0] if r and r[0] else None
        except:
            return None

    async def update_order_admin_message_id(self, order_id, admin_message_id):
        try:
            await self.execute("UPDATE orders SET admin_message_id=? WHERE id=?",
                               (admin_message_id, order_id))
        except Exception as e:
            logging.error(f"Error updating admin_message_id: {e}")

    async def get_user_orders(self, user_id):
        return await self.execute(
            "SELECT o.*, p.name as plan_name, p.days as plan_days, "
            "a.username as acc_user, a.password as acc_pass, o.expire_at "
            "FROM orders o "
            "LEFT JOIN plans p ON o.plan_id=p.id "
            "LEFT JOIN accounts a ON o.account_id=a.id "
            "WHERE o.user_id=? AND o.status='approved' ORDER BY o.id DESC", (user_id,))

    async def get_expiring_orders(self, days=3):
        threshold = (datetime.now() + timedelta(days=days)).isoformat()
        return await self.execute(
            "SELECT o.*, u.telegram_id, u.username, p.name as plan_name "
            "FROM orders o "
            "LEFT JOIN users u ON o.user_id=u.telegram_id "
            "LEFT JOIN plans p ON o.plan_id=p.id "
            "WHERE o.status='approved' AND o.expire_at IS NOT NULL "
            "AND o.expire_at <= ? AND o.expire_at > ?",
            (threshold, datetime.now().isoformat()))

    # ============ Coupons ============
    async def get_coupon(self, code):
        r = await self.execute_one("SELECT * FROM coupons WHERE code=? AND is_active=1", (code,))
        if not r:
            return None
        if r[7]:
            try:
                expire_at = datetime.fromisoformat(r[7])
                if datetime.now() > expire_at:
                    return None
            except:
                pass
        return r

    async def get_coupon_info(self, code):
        r = await self.execute_one("SELECT * FROM coupons WHERE code=?", (code,))
        if not r:
            return {"valid": False, "message": "کد تخفیف یافت نشد"}
        if not r[5]:
            return {"valid": False, "message": "این کد تخفیف غیرفعال شده است"}
        if r[7]:
            try:
                expire_at = datetime.fromisoformat(r[7])
                if datetime.now() > expire_at:
                    return {"valid": False, "message": "تاریخ انقضای این کد گذشته است"}
            except:
                pass
        if r[4] >= r[3]:
            return {"valid": False, "message": f"ظرفیت این کد تمام شده ({r[4]}/{r[3]})"}
        return {
            "valid": True,
            "code": r[1],
            "discount": r[2],
            "used": r[4],
            "limit": r[3],
            "expire_at": r[7]
        }

    async def get_all_coupons(self):
        return await self.execute("SELECT * FROM coupons ORDER BY id DESC")

    async def get_coupon_by_id(self, coupon_id):
        return await self.execute_one("SELECT * FROM coupons WHERE id=?", (coupon_id,))

    async def add_coupon(self, code, discount, limit, expire_days=None):
        expire_at = None
        if expire_days and expire_days > 0:
            expire_at = (datetime.now() + timedelta(days=expire_days)).isoformat()
        await self.execute(
            "INSERT INTO coupons (code, discount_percent, uses_limit, expire_at, created_at) VALUES (?,?,?,?,?)",
            (code, discount, limit, expire_at, datetime.now().isoformat()))

    async def update_coupon_field(self, coupon_id, field, value):
        # BUG FIX: جلوگیری از SQL Injection با whitelist
        if field not in ALLOWED_COUPON_FIELDS:
            raise ValueError(f"فیلد غیرمجاز: {field}")
        await self.execute(f"UPDATE coupons SET {field}=? WHERE id=?", (value, coupon_id))

    async def delete_coupon(self, coupon_id):
        await self.execute("DELETE FROM coupons WHERE id=?", (coupon_id,))

    async def use_coupon(self, code):
        await self.execute("UPDATE coupons SET used_count=used_count+1 WHERE code=?", (code,))

    # ============ Tutorials ============
    async def get_all_tutorials(self):
        return await self.execute("SELECT * FROM tutorials ORDER BY sort_order, id")

    async def get_tutorial(self, tid):
        return await self.execute_one("SELECT * FROM tutorials WHERE id=?", (tid,))

    async def add_tutorial(self, platform, title, content):
        await self.execute("INSERT INTO tutorials (platform, title, content) VALUES (?,?,?)", (platform, title, content))

    async def update_tutorial_field(self, tid, field, value):
        # BUG FIX: جلوگیری از SQL Injection با whitelist
        if field not in ALLOWED_TUTORIAL_FIELDS:
            raise ValueError(f"فیلد غیرمجاز: {field}")
        await self.execute(f"UPDATE tutorials SET {field}=? WHERE id=?", (value, tid))

    async def delete_tutorial(self, tid):
        await self.execute("DELETE FROM tutorials WHERE id=?", (tid,))

    # ============ Tickets ============
    async def create_ticket(self, user_id, subject):
        await self.execute("INSERT INTO tickets (user_id, subject, created_at) VALUES (?,?,?)",
                           (user_id, subject, datetime.now().isoformat()))
        r = await self.execute_one("SELECT id FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        return r[0] if r else None

    async def add_ticket_message(self, ticket_id, sender_type, sender_id, message, file_id=None):
        await self.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_type, sender_id, message, file_id, created_at) VALUES (?,?,?,?,?,?)",
            (ticket_id, sender_type, sender_id, message, file_id, datetime.now().isoformat()))

    async def get_ticket(self, tid):
        return await self.execute_one("SELECT * FROM tickets WHERE id=?", (tid,))

    async def get_ticket_messages(self, tid):
        return await self.execute("SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY id", (tid,))

    async def get_all_tickets(self, status=None, offset=0, limit=5):
        base = "SELECT t.*, u.username, u.first_name FROM tickets t LEFT JOIN users u ON t.user_id=u.telegram_id"
        if status:
            return await self.execute(f"{base} WHERE t.status=? ORDER BY t.id DESC LIMIT ? OFFSET ?", (status, limit, offset))
        return await self.execute(f"{base} ORDER BY t.id DESC LIMIT ? OFFSET ?", (limit, offset))

    async def count_tickets(self, status=None):
        if status:
            r = await self.execute_one("SELECT COUNT(*) FROM tickets WHERE status=?", (status,))
        else:
            r = await self.execute_one("SELECT COUNT(*) FROM tickets")
        return r[0] if r else 0

    async def update_ticket_status(self, tid, status):
        if status == "closed":
            await self.execute("UPDATE tickets SET status='closed', closed_at=? WHERE id=?",
                               (datetime.now().isoformat(), tid))
        else:
            await self.execute("UPDATE tickets SET status=? WHERE id=?", (status, tid))

    async def get_user_open_ticket(self, user_id):
        r = await self.execute_one(
            "SELECT id FROM tickets WHERE user_id=? AND status='open' ORDER BY id DESC LIMIT 1", (user_id,))
        return r[0] if r else None

    async def get_user_tickets(self, user_id, limit=20):
        return await self.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))

    # ============ Waitlist ============
    async def add_to_waitlist(self, user_id, plan_id):
        # BUG FIX: جلوگیری از ثبت‌نام تکراری
        existing = await self.execute_one(
            "SELECT id FROM waitlist WHERE user_id=? AND plan_id=? AND status='waiting'",
            (user_id, plan_id)
        )
        if existing:
            return False  # قبلاً ثبت‌نام کرده
        await self.execute("INSERT INTO waitlist (user_id, plan_id, created_at) VALUES (?,?,?)",
                           (user_id, plan_id, datetime.now().isoformat()))
        return True

    async def get_waitlist(self, plan_id=None, status='waiting'):
        if plan_id:
            return await self.execute(
                "SELECT w.*, u.username, u.first_name, p.name as plan_name "
                "FROM waitlist w LEFT JOIN users u ON w.user_id=u.telegram_id "
                "LEFT JOIN plans p ON w.plan_id=p.id "
                "WHERE w.plan_id=? AND w.status=? ORDER BY w.id",
                (plan_id, status))
        return await self.execute(
            "SELECT w.*, u.username, u.first_name, p.name as plan_name "
            "FROM waitlist w LEFT JOIN users u ON w.user_id=u.telegram_id "
            "LEFT JOIN plans p ON w.plan_id=p.id "
            "WHERE w.status=? ORDER BY w.id",
            (status,))

    async def get_unnotified_waitlist(self):
        # BUG FIX: ایندکس‌های query با کد tasks.py هماهنگ شد
        # ستون‌ها: 0=id, 1=user_id, 2=plan_id, 3=status, 4=notified,
        #          5=created_at, 6=notified_at, 7=telegram_id, 8=username, 9=plan_name
        return await self.execute(
            "SELECT w.id, w.user_id, w.plan_id, w.status, w.notified, "
            "w.created_at, w.notified_at, u.telegram_id, u.username, p.name as plan_name "
            "FROM waitlist w "
            "LEFT JOIN users u ON w.user_id=u.telegram_id "
            "LEFT JOIN plans p ON w.plan_id=p.id "
            "WHERE w.notified=0 AND w.status='waiting'")

    async def count_waitlist(self, plan_id=None):
        if plan_id:
            r = await self.execute_one("SELECT COUNT(*) FROM waitlist WHERE plan_id=? AND status='waiting'", (plan_id,))
        else:
            r = await self.execute_one("SELECT COUNT(*) FROM waitlist WHERE status='waiting'")
        return r[0] if r else 0

    async def mark_waitlist_notified(self, waitlist_id):
        await self.execute("UPDATE waitlist SET notified=1, notified_at=?, status='notified' WHERE id=?",
                           (datetime.now().isoformat(), waitlist_id))

    async def remove_from_waitlist(self, waitlist_id):
        await self.execute("DELETE FROM waitlist WHERE id=?", (waitlist_id,))

    async def get_user_waitlist_position(self, user_id, plan_id):
        r = await self.execute_one(
            "SELECT COUNT(*) FROM waitlist WHERE plan_id=? AND status='waiting' AND id < "
            "(SELECT id FROM waitlist WHERE user_id=? AND plan_id=? AND status='waiting')",
            (plan_id, user_id, plan_id))
        return r[0] + 1 if r else 0

    # ============ User Settings ============
    async def get_user_language(self, user_id):
        r = await self.execute_one("SELECT language FROM user_settings WHERE user_id=?", (user_id,))
        return r[0] if r else 'fa'

    async def set_user_language(self, user_id, language):
        existing = await self.execute_one("SELECT menu_message_id FROM user_settings WHERE user_id=?", (user_id,))
        menu_id = existing[0] if existing else 0
        await self.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, language, menu_message_id, created_at) VALUES (?,?,?,?)",
            (user_id, language, menu_id, datetime.now().isoformat()))

    async def get_menu_message_id(self, user_id):
        r = await self.execute_one("SELECT menu_message_id FROM user_settings WHERE user_id=?", (user_id,))
        return r[0] if r and r[0] else None

    async def set_menu_message_id(self, user_id, message_id):
        lang = await self.get_user_language(user_id)
        await self.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, language, menu_message_id, created_at) VALUES (?,?,?,?)",
            (user_id, lang, message_id, datetime.now().isoformat()))

    async def track_chat_message(self, user_id, message_id):
        await self.execute(
            "INSERT INTO chat_messages (user_id, message_id, created_at) VALUES (?,?,?)",
            (user_id, message_id, datetime.now().isoformat()))

    async def get_tracked_messages(self, user_id):
        rows = await self.execute("SELECT message_id FROM chat_messages WHERE user_id=?", (user_id,))
        return [r[0] for r in rows]

    async def clear_tracked_messages(self, user_id, keep=None):
        if keep:
            await self.execute("DELETE FROM chat_messages WHERE user_id=? AND message_id!=?", (user_id, keep))
        else:
            await self.execute("DELETE FROM chat_messages WHERE user_id=?", (user_id,))

    async def get_all_chat_users(self):
        rows = await self.execute("SELECT DISTINCT user_id FROM user_settings WHERE menu_message_id > 0")
        admin_rows = await self.execute("SELECT user_id FROM admins")
        ids = {r[0] for r in rows} | {r[0] for r in admin_rows}
        return list(ids)

    # ============ Wallet ============
    async def get_wallet_balance(self, user_id):
        r = await self.execute_one("SELECT wallet_balance FROM users WHERE telegram_id=?", (user_id,))
        return r[0] if r and r[0] else 0

    async def add_wallet_balance(self, user_id, amount, description="شارژ"):
        await self.execute(
            "UPDATE users SET wallet_balance=COALESCE(wallet_balance,0)+? WHERE telegram_id=?",
            (amount, user_id))
        await self.execute(
            "INSERT INTO wallet_transactions (user_id, amount, type, description, created_at) VALUES (?,?,?,?,?)",
            (user_id, amount, "credit", description, datetime.now().isoformat()))

    async def deduct_wallet_balance(self, user_id, amount, description="خرید"):
        balance = await self.get_wallet_balance(user_id)
        if balance < amount:
            return False
        await self.execute(
            "UPDATE users SET wallet_balance=wallet_balance-? WHERE telegram_id=?",
            (amount, user_id))
        await self.execute(
            "INSERT INTO wallet_transactions (user_id, amount, type, description, created_at) VALUES (?,?,?,?,?)",
            (user_id, -amount, "debit", description, datetime.now().isoformat()))
        return True

    async def create_wallet_topup(self, user_id, amount, receipt_file_id):
        await self.execute(
            "INSERT INTO wallet_topups (user_id, amount, receipt_file_id, created_at) VALUES (?,?,?,?)",
            (user_id, amount, receipt_file_id, datetime.now().isoformat()))
        r = await self.execute_one("SELECT id FROM wallet_topups WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        return r[0] if r else None

    async def get_wallet_topup(self, topup_id):
        return await self.execute_one("SELECT * FROM wallet_topups WHERE id=?", (topup_id,))

    async def approve_wallet_topup(self, topup_id):
        t = await self.get_wallet_topup(topup_id)
        if not t or t[3] != 'pending':
            return False
        await self.execute(
            "UPDATE wallet_topups SET status='approved', approved_at=? WHERE id=?",
            (datetime.now().isoformat(), topup_id))
        await self.add_wallet_balance(t[1], t[2], f"شارژ #{topup_id}")
        return True

    async def reject_wallet_topup(self, topup_id):
        await self.execute("UPDATE wallet_topups SET status='rejected' WHERE id=? AND status='pending'", (topup_id,))

    async def get_pending_wallet_topups(self):
        return await self.execute("SELECT * FROM wallet_topups WHERE status='pending' ORDER BY id DESC")

    async def process_referral_bonus(self, buyer_id):
        referrer = await self.get_referrer(buyer_id)
        if not referrer:
            return
        key = f"ref_bonus_{buyer_id}"
        if await self.get_setting(key):
            return
        prior = await self.execute_one(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status='approved'", (buyer_id,))
        if not prior or prior[0] != 1:
            return
        await self.add_wallet_balance(referrer, REFERRAL_BONUS, f"پاداش معرفی کاربر {buyer_id}")
        await self.set_setting(key, "1")

    # ============ Apple Unlock ============
    async def create_apple_unlock(self, user_id, apple_id, password, birthday, security_question):
        now = datetime.now().isoformat()
        await self.execute("""
            INSERT INTO apple_unlock_orders
            (user_id, apple_id, password, birthday, security_question, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (user_id, apple_id, password, birthday, security_question, 'info_submitted', now, now))
        r = await self.execute_one(
            "SELECT id FROM apple_unlock_orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        return r[0] if r else None

    async def update_apple_unlock_photos(self, order_id, imei=None, about=None, box=None):
        if imei:
            await self.execute("UPDATE apple_unlock_orders SET imei_photo=?, updated_at=? WHERE id=?",
                               (imei, datetime.now().isoformat(), order_id))
        if about:
            await self.execute("UPDATE apple_unlock_orders SET about_photo=?, updated_at=? WHERE id=?",
                               (about, datetime.now().isoformat(), order_id))
        if box:
            await self.execute("UPDATE apple_unlock_orders SET box_photo=?, updated_at=? WHERE id=?",
                               (box, datetime.now().isoformat(), order_id))

    async def get_apple_unlock(self, order_id):
        return await self.execute_one("SELECT * FROM apple_unlock_orders WHERE id=?", (order_id,))

    async def get_all_apple_unlocks(self, status=None, limit=50):
        if status:
            return await self.execute(
                "SELECT * FROM apple_unlock_orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))
        return await self.execute("SELECT * FROM apple_unlock_orders ORDER BY id DESC LIMIT ?", (limit,))

    async def count_apple_unlocks(self, status=None):
        if status:
            r = await self.execute_one("SELECT COUNT(*) FROM apple_unlock_orders WHERE status=?", (status,))
        else:
            r = await self.execute_one("SELECT COUNT(*) FROM apple_unlock_orders")
        return r[0] if r else 0

    async def set_apple_unlock_price(self, order_id, price, unlock_time):
        await self.execute("""
            UPDATE apple_unlock_orders SET price=?, unlock_time=?, status='awaiting_payment', updated_at=?
            WHERE id=?
        """, (price, unlock_time, datetime.now().isoformat(), order_id))

    async def set_apple_unlock_receipt(self, order_id, receipt_file_id):
        await self.execute("""
            UPDATE apple_unlock_orders SET receipt_file_id=?, status='payment_submitted', updated_at=? WHERE id=?
        """, (receipt_file_id, datetime.now().isoformat(), order_id))

    async def approve_apple_payment(self, order_id):
        await self.execute("""
            UPDATE apple_unlock_orders SET status='payment_approved', updated_at=? WHERE id=? AND status='payment_submitted'
        """, (datetime.now().isoformat(), order_id))

    async def mark_apple_unlocked(self, order_id):
        await self.execute("""
            UPDATE apple_unlock_orders SET status='unlocked', updated_at=? WHERE id=?
        """, (datetime.now().isoformat(), order_id))

    async def get_user_active_apple_unlock(self, user_id):
        return await self.execute_one("""
            SELECT id FROM apple_unlock_orders WHERE user_id=? AND status NOT IN ('unlocked','rejected')
            ORDER BY id DESC LIMIT 1
        """, (user_id,))

    async def has_set_language(self, user_id):
        """BUG FIX: چک میکنه آیا کاربر قبلاً زبان انتخاب کرده یا نه"""
        r = await self.execute_one("SELECT language FROM user_settings WHERE user_id=?", (user_id,))
        return r is not None

    async def get_terms_text(self):
        return await self.get_setting("terms_text", "قوانین ثبت نشده است.")

    async def set_terms_text(self, text):
        await self.set_setting("terms_text", text)

    # ============ Custom Messages ============
    async def get_message(self, key, default=""):
        return await self.get_setting(f"msg_{key}", default)

    async def set_message(self, key, value):
        await self.set_setting(f"msg_{key}", value)

    # ============ Logs ============
    async def get_logs(self, offset=0, limit=10):
        return await self.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))

    async def count_logs(self):
        r = await self.execute_one("SELECT COUNT(*) FROM logs")
        return r[0] if r else 0

    async def clear_logs(self):
        await self.execute("DELETE FROM logs")

    # ============ Stats ============
    async def get_stats(self):
        r = await self.execute_one("""
            SELECT
                (SELECT COUNT(*) FROM users),
                (SELECT COUNT(*) FROM users WHERE is_banned=1),
                (SELECT COUNT(*) FROM accounts WHERE status='free'),
                (SELECT COUNT(*) FROM accounts WHERE status='sold'),
                (SELECT COUNT(*) FROM accounts WHERE status='pending'),
                (SELECT COALESCE(SUM(price),0) FROM orders WHERE status='approved'),
                (SELECT COUNT(*) FROM orders WHERE status='pending'),
                (SELECT COUNT(*) FROM orders WHERE status='rejected'),
                (SELECT COUNT(*) FROM tickets WHERE status='open'),
                (SELECT COALESCE(SUM(wallet_balance),0) FROM users),
                (SELECT COUNT(*) FROM apple_unlock_orders WHERE status NOT IN ('unlocked','rejected')),
                (SELECT COUNT(*) FROM wallet_topups WHERE status='pending'),
                (SELECT COUNT(*) FROM users WHERE referred_by > 0)
        """)
        if not r:
            return {"users": 0, "banned": 0, "free": 0, "sold": 0, "pending_acc": 0,
                    "revenue": 0, "pending": 0, "rejected": 0, "open_tickets": 0,
                    "wallet_total": 0, "apple_pending": 0, "wallet_topups": 0, "referrals": 0}
        return {
            "users": r[0], "banned": r[1], "free": r[2], "sold": r[3], "pending_acc": r[4],
            "revenue": r[5], "pending": r[6], "rejected": r[7], "open_tickets": r[8],
            "wallet_total": r[9], "apple_pending": r[10], "wallet_topups": r[11], "referrals": r[12],
        }

    async def get_dashboard_stats(self):
        today = datetime.now().date().isoformat()
        month_start = datetime.now().replace(day=1).date().isoformat()
        r = await self.execute_one("""
            SELECT
                (SELECT COUNT(*) FROM users),
                (SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?),
                (SELECT COUNT(*) FROM orders WHERE status='approved'),
                (SELECT COUNT(*) FROM orders WHERE status='approved' AND DATE(created_at) = ?),
                (SELECT COUNT(*) FROM orders WHERE status='approved' AND created_at >= ?),
                (SELECT COALESCE(SUM(price),0) FROM orders WHERE status='approved'),
                (SELECT COALESCE(SUM(price),0) FROM orders WHERE status='approved' AND DATE(created_at) = ?),
                (SELECT COUNT(*) FROM accounts WHERE status='free'),
                (SELECT COUNT(*) FROM accounts WHERE status='pending'),
                (SELECT COUNT(*) FROM tickets WHERE status='open'),
                (SELECT COUNT(*) FROM waitlist WHERE status='waiting'),
                (SELECT COUNT(*) FROM orders WHERE status='pending'),
                (SELECT COALESCE(SUM(wallet_balance),0) FROM users),
                (SELECT COUNT(*) FROM apple_unlock_orders WHERE status NOT IN ('unlocked','rejected')),
                (SELECT COUNT(*) FROM wallet_topups WHERE status='pending')
        """, (today, today, month_start, today))
        if not r:
            return {"total_users": 0, "today_users": 0, "total_orders": 0, "today_orders": 0,
                    "month_orders": 0, "total_revenue": 0, "today_revenue": 0, "free_accounts": 0,
                    "pending_accounts": 0, "open_tickets": 0, "waitlist_count": 0, "pending": 0,
                    "wallet_total": 0, "apple_pending": 0, "wallet_topups": 0}
        return {
            "total_users": r[0], "today_users": r[1],
            "total_orders": r[2], "today_orders": r[3],
            "month_orders": r[4], "total_revenue": r[5],
            "today_revenue": r[6], "free_accounts": r[7],
            "pending_accounts": r[8], "open_tickets": r[9],
            "waitlist_count": r[10], "pending": r[11],
            "wallet_total": r[12], "apple_pending": r[13], "wallet_topups": r[14],
        }

    async def get_sales_chart_data(self, days=30):
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        return await self.execute(
            "SELECT DATE(created_at) as date, COUNT(*) as count, SUM(price) as revenue "
            "FROM orders WHERE status='approved' AND created_at >= ? "
            "GROUP BY DATE(created_at) ORDER BY date",
            (start_date,))


db = Database()
