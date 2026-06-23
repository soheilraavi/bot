"""
داشبوبورد وب ادمین - نسخه نهایی
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from database import db
from config import DASHBOARD_PASSWORD, DASHBOARD_HOST, DASHBOARD_PORT, DASHBOARD_SECRET, APPLE_CSS, BOT_TOKEN
import bot_instance

app = FastAPI(title="Dashboard")
app.add_middleware(SessionMiddleware, secret_key=DASHBOARD_SECRET)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass


# ============ AUTH ============
async def get_current_user(request: Request):
    user = request.session.get("admin_user")
    role = request.session.get("admin_role")
    if not user:
        raise HTTPException(status_code=401)
    return {"user_id": user, "role": role}


def require_admin(user=Depends(get_current_user)):
    if user["role"] not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403)
    return user


def require_owner(user=Depends(get_current_user)):
    if user["role"] != "OWNER":
        raise HTTPException(status_code=403)
    return user


# ============ SIDEBAR ============
def sidebar(active: str, role: str, stats=None):
    stats = stats or {}
    if role == "OWNER":
        items = [
            ("dashboard", "🏠", "داشبورد", "/dashboard", None),
            ("orders", "📥", "سفارش‌ها", "/orders", stats.get("pending")),
            ("accounts", "📦", "اکانت‌ها", "/accounts", stats.get("free_accounts")),
            ("plans", "💎", "پلن‌ها", "/plans", None),
            ("coupons", "🎟", "کد تخفیف", "/coupons", None),
            ("users", "👥", "کاربران", "/users", None),
            ("tickets", "🎫", "تیکت‌ها", "/tickets", stats.get("open_tickets")),
            ("waitlist", "🎯", "لیست انتظار", "/waitlist", stats.get("waitlist_count")),
            ("terms", "📜", "قوانین", "/terms", None),
            ("settings", "⚙️", "تنظیمات", "/settings", None),
            ("messages", "📝", "متن‌ها", "/messages", None),
            ("apple", "🔓", "آنلاک Apple", "/apple-unlock", stats.get("apple_pending")),
            ("wallet", "💳", "شارژ کیف پول", "/wallet-topups", stats.get("wallet_topups")),
            ("logs", "📊", "لاگ‌ها", "/logs", None),
        ]
    else:
        items = [
            ("dashboard", "🏠", "داشبورد", "/dashboard", None),
            ("orders", "📥", "سفارش‌ها", "/orders", stats.get("pending")),
            ("accounts", "📦", "اکانت‌ها", "/accounts", stats.get("free_accounts")),
            ("tickets", "🎫", "تیکت‌ها", "/tickets", stats.get("open_tickets")),
            ("wallet", "💳", "شارژ کیف پول", "/wallet-topups", stats.get("wallet_topups")),
            ("apple", "🔓", "آنلاک Apple", "/apple-unlock", stats.get("apple_pending")),
        ]
    
    nav_html = ""
    for key, icon, label, url, count in items:
        active_class = "active" if key == active else ""
        badge_html = f'<span class="badge-count">{count}</span>' if count else ""
        nav_html += f'<a href="{url}" class="nav-item {active_class}"><span class="icon">{icon}</span>{label}{badge_html}</a>'
    
    role_badge = '<span class="role-badge role-owner">👑 OWNER</span>' if role == "OWNER" else '<span class="role-badge role-admin">🛡️ ADMIN</span>'
    
    return f"""
    <aside class="sidebar">
        <div class="sidebar-logo">
            <div class="sidebar-logo-icon">👑</div>
            <div>
                <div class="sidebar-logo-text">پنل مدیریت</div>
                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">{role_badge}</div>
            </div>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-section-title">منو</div>
            {nav_html}
        </div>
        <div style="position: absolute; bottom: 24px; right: 16px; left: 16px;">
            <a href="/logout" class="nav-item" style="color: var(--red);">
                <span class="icon">🚪</span> خروج
            </a>
        </div>
    </aside>
    """


# ============ ROUTES ============
@app.get("/")
async def root():
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ورود</title>{APPLE_CSS}
    <style>body{{background:linear-gradient(135deg,#f5f7fa,#e4e8f0);display:flex;align-items:center;justify-content:center;min-height:100vh}}
    .login-card{{background:white;border-radius:24px;padding:48px 40px;box-shadow:0 20px 60px rgba(0,0,0,0.1);max-width:420px;width:100%}}</style></head>
    <body><div class="login-card">
    <div style="width:72px;height:72px;background:linear-gradient(135deg,#0071e3,#5856d6);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 24px">👑</div>
    <h1 style="text-align:center;font-size:26px;font-weight:700;margin-bottom:8px">پنل مدیریت</h1>
    <p style="text-align:center;color:var(--text-secondary);margin-bottom:32px">برای ادامه وارد شوید</p>
    {"<div class='alert alert-danger'>❌ رمز اشتباه</div>" if error else ""}
    <form method="post"><div class="form-group"><label class="form-label">رمز عبور</label><input type="password" name="password" class="form-input" required autofocus></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:13px;font-size:15px;font-weight:600">ورود</button></form></div></body></html>"""
    return HTMLResponse(html)


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == DASHBOARD_PASSWORD:
        request.session["admin_user"] = "owner"
        request.session["admin_role"] = "OWNER"
        return RedirectResponse("/dashboard", status_code=303)
    
    admins = await db.get_all_admins()
    for admin in admins:
        try:
            admin_id = admin[0]
            admin_role = admin[1]
            if admin_role == "ADMIN" and password == str(admin_id):
                request.session["admin_user"] = admin_id
                request.session["admin_role"] = "ADMIN"
                return RedirectResponse("/dashboard", status_code=303)
        except:
            continue
    
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ============ DASHBOARD ============
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {"total_users": 0, "today_users": 0, "total_orders": 0, "today_orders": 0,
                 "total_revenue": 0, "today_revenue": 0, "free_accounts": 0, "open_tickets": 0, "waitlist_count": 0}
    
    role = user["role"]
    quick_actions = ""
    if role == "OWNER":
        quick_actions = """
        <a href="/orders" class="quick-action"><div class="quick-action-icon" style="background:rgba(0,113,227,0.1);color:var(--blue)">📥</div><div class="quick-action-label">سفارش‌ها</div></a>
        <a href="/accounts" class="quick-action"><div class="quick-action-icon" style="background:rgba(52,199,89,0.1);color:var(--green)">📦</div><div class="quick-action-label">اکانت‌ها</div></a>
        <a href="/plans" class="quick-action"><div class="quick-action-icon" style="background:rgba(175,82,222,0.1);color:var(--purple)">💎</div><div class="quick-action-label">پلن‌ها</div></a>
        <a href="/coupons" class="quick-action"><div class="quick-action-icon" style="background:rgba(255,45,85,0.1);color:var(--pink)">🎟</div><div class="quick-action-label">کد تخفیف</div></a>
        <a href="/users" class="quick-action"><div class="quick-action-icon" style="background:rgba(90,200,250,0.1);color:var(--teal)">👥</div><div class="quick-action-label">کاربران</div></a>
        <a href="/tickets" class="quick-action"><div class="quick-action-icon" style="background:rgba(255,149,0,0.1);color:var(--orange)">🎫</div><div class="quick-action-label">تیکت‌ها</div></a>
        <a href="/terms" class="quick-action"><div class="quick-action-icon" style="background:rgba(88,86,214,0.1);color:var(--indigo)">📜</div><div class="quick-action-label">قوانین</div></a>
        <a href="/settings" class="quick-action"><div class="quick-action-icon" style="background:rgba(0,0,0,0.05);color:var(--text-secondary)">⚙️</div><div class="quick-action-label">تنظیمات</div></a>
        """
    else:
        quick_actions = '<a href="/orders" class="quick-action"><div class="quick-action-icon" style="background:rgba(0,113,227,0.1);color:var(--blue)">📥</div><div class="quick-action-label">سفارش‌ها</div></a>'
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>داشبورد</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("dashboard", role, stats)}<main class="main-content fade-in">
    <div class="page-header"><div><h1 class="page-title">داشبورد</h1><p class="page-subtitle">نمای کلی سیستم</p></div></div>
    <div class="stats-grid">
    <div class="stat-card blue"><div class="stat-icon blue">👥</div><div class="stat-label">کل کاربران</div><div class="stat-value">{stats['total_users']}</div><div class="stat-change">+{stats['today_users']} امروز</div></div>
    <div class="stat-card green"><div class="stat-icon green">📥</div><div class="stat-label">سفارش‌ها</div><div class="stat-value">{stats['total_orders']}</div><div class="stat-change">+{stats['today_orders']} امروز</div></div>
    <div class="stat-card purple"><div class="stat-icon purple">💰</div><div class="stat-label">درآمد</div><div class="stat-value">{stats['total_revenue']:,}</div><div class="stat-change">{stats['today_revenue']:,} امروز</div></div>
    <div class="stat-card orange"><div class="stat-icon orange">📦</div><div class="stat-label">موجودی / رزرو</div><div class="stat-value">{stats['free_accounts']}</div><div class="stat-change">⏸ {stats.get('pending_accounts', 0)} رزرو | 🎫 {stats['open_tickets']} تیکت</div></div>
    <div class="stat-card purple"><div class="stat-icon purple">⏳</div><div class="stat-label">در انتظار</div><div class="stat-value">{stats.get('pending', 0)}</div><div class="stat-change">💳 {stats.get('wallet_topups', 0)} شارژ | 🔓 {stats.get('apple_pending', 0)} آنلاک</div></div>
    <div class="stat-card green"><div class="stat-icon green">💳</div><div class="stat-label">کیف پول کاربران</div><div class="stat-value">{stats.get('wallet_total', 0):,}</div><div class="stat-change">تومان</div></div>
    </div>
    <div class="card"><div class="card-title">دسترسی سریع</div><div class="quick-actions">{quick_actions}</div></div>
    </main></div></body></html>"""
    return HTMLResponse(html)


# ============ ORDERS ============
@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, user=Depends(get_current_user)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {"total_orders": 0, "pending": 0}
    
    try:
        orders = await db.get_all_orders(limit=50)
    except Exception as e:
        logging.error(f"Error fetching orders: {e}")
        orders = []
    
    rows = ""
    for o in orders:
        try:
            order_id = o[0]
            user_id = o[1]
            plan_id = o[2]
            price = o[3]
            status = o[4]
            receipt_file_id = o[5] if len(o) > 5 else ""
            created_at = o[7] if len(o) > 7 else ""
            
            try:
                user_info = await db.get_user(user_id)
                username = user_info[2] if user_info and user_info[2] else f"ID:{user_id}"
            except:
                username = f"ID:{user_id}"
            
            try:
                plan_info = await db.get_plan(plan_id)
                plan_name = plan_info[1] if plan_info else "نامشخص"
            except:
                plan_name = "نامشخص"
            
            if status == "pending":
                status_badge = '<span class="badge badge-warning">⏳ در انتظار</span>'
            elif status == "approved":
                status_badge = '<span class="badge badge-success">✓ تایید</span>'
            elif status == "rejected":
                status_badge = '<span class="badge badge-danger">✗ رد</span>'
            else:
                status_badge = '<span class="badge">?</span>'
            
            receipt_btn = ""
            if receipt_file_id:
                receipt_btn = f'<a href="/orders/{order_id}/receipt" target="_blank" class="btn btn-info btn-sm">📷 فیش</a>'
            
            actions = ""
            if status == "pending":
                actions = f"""<div class="btn-group">
                {receipt_btn}
                <a href="/orders/{order_id}/approve" class="btn btn-success btn-sm">✓ تایید</a>
                <a href="/orders/{order_id}/reject" class="btn btn-danger btn-sm">✗ رد</a></div>"""
            else:
                actions = receipt_btn
            
            date_str = str(created_at)[:10] if created_at else "-"
            
            rows += f"""<tr>
            <td style="font-weight:600">#{order_id}</td>
            <td>{username}</td>
            <td>{plan_name}</td>
            <td style="font-weight:600">{price:,} ت</td>
            <td>{status_badge}</td>
            <td style="color:var(--text-tertiary)">{date_str}</td>
            <td>{actions}</td></tr>"""
        except Exception as e:
            logging.error(f"Error processing order: {e}")
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>سفارش‌ها</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("orders", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><div><h1 class="page-title">سفارش‌ها</h1><p class="page-subtitle">مدیریت سفارش‌ها</p></div></div>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>شناسه</th><th>کاربر</th><th>پلن</th><th>مبلغ</th><th>وضعیت</th><th>تاریخ</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="7" style="text-align:center;padding:40px">سفارشی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/orders/{order_id}/receipt")
async def view_receipt(order_id: int, user=Depends(get_current_user)):
    """✅ نمایش عکس فیش"""
    try:
        import bot_instance
        
        o = await db.get_order(order_id)
        if not o:
            return HTMLResponse("<h1 style='text-align:center;padding:40px'>❌ یافت نشد</h1>")
        
        receipt_file_id = o[5] if len(o) > 5 else ""
        if not receipt_file_id:
            return HTMLResponse("<h1 style='text-align:center;padding:40px'>❌ فیشی نیست</h1>")
        
        # ✅ استفاده از متد sync
        file = bot_instance.get_file_sync(receipt_file_id)
        
        # ✅ ساخت URL مستقیم
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        user_info = await db.get_user(o[1])
        username = user_info[2] if user_info and user_info[2] else f"ID:{o[1]}"
        
        html = f"""<!DOCTYPE html>
        <html dir="rtl" lang="fa">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>فیش سفارش #{order_id}</title>
            {APPLE_CSS}
            <style>
                body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
                .receipt-container {{ max-width: 600px; width: 100%; }}
                .receipt-image {{ width: 100%; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
            </style>
        </head>
        <body>
            <div class="receipt-container">
                <div class="card">
                    <h2 style="margin-bottom:20px">📷 فیش سفارش #{order_id}</h2>
                    <p style="margin-bottom:20px;color:var(--text-secondary)">کاربر: {username}</p>
                    <img src="{file_url}" class="receipt-image" alt="فیش پرداخت">
                    <div style="margin-top:20px;text-align:center">
                        <a href="/orders" class="btn btn-secondary">← بازگشت به سفارش‌ها</a>
                    </div>
                </div>
            </div>
        </body>
        </html>"""
        return HTMLResponse(html)
        
    except Exception as e:
        logging.error(f"Error viewing receipt: {e}", exc_info=True)
        return HTMLResponse(f"<h1 style='text-align:center;padding:40px;color:red'>خطا: {str(e)}</h1>")
        
        
@app.get("/orders/{order_id}/approve")
async def approve_order_web(order_id: int, user=Depends(get_current_user)):
    """✅ تایید سفارش از وب - با چک وضعیت و پاک کردن پیام فیش"""
    try:
        import bot_instance
        logging.info(f"🔍 [WEB] Approving order #{order_id}")
        
        o = await db.get_order(order_id)
        if not o:
            logging.error(f"❌ [WEB] Order {order_id} not found")
            return RedirectResponse("/orders", status_code=303)
        
        user_id = o[1]
        plan_id = o[2]
        current_status = o[4]
        
        # ✅ چک وضعیت - اگه قبلاً پردازش شده، دیگه تایید نکن
        if current_status == "approved":
            logging.warning(f"⚠️ [WEB] Order {order_id} already approved")
            return RedirectResponse("/orders", status_code=303)
        
        if current_status == "rejected":
            logging.warning(f"⚠️ [WEB] Order {order_id} already rejected")
            return RedirectResponse("/orders", status_code=303)
        
        logging.info(f"✅ [WEB] Order: user={user_id}, plan={plan_id}, status={current_status}")
        
        p = await db.get_plan(plan_id)
        if not p:
            return RedirectResponse("/orders", status_code=303)
        
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
                logging.error("❌ [WEB] No free account!")
                return RedirectResponse("/orders", status_code=303)
            acc_id, acc_u, acc_p = free
        
        # ✅ استفاده از update_order_status جدید
        success = await db.update_order_status(order_id, "approved", acc_id)
        
        if not success:
            logging.warning(f"⚠️ [WEB] Order {order_id} already processed")
            return RedirectResponse("/orders", status_code=303)
        
        # ✅ فروش اکانت
        await db.sell_account(acc_id, user_id)
        await db.process_referral_bonus(user_id)
        
        try:
            expire_at = (datetime.now() + timedelta(days=p[3])).isoformat()
            await db.update_order_expire(order_id, expire_at)
        except Exception as e:
            logging.error(f"⚠️ [WEB] Expire error: {e}")
        
        # ✅ ارسال پیام به کاربر
        try:
            bot_instance.send_message_sync(
                user_id,
                f"✅ سفارش شما تایید شد!\n\n"
                f"🎯 پلن: {p[1]}\n"
                f"👤 Username: <code>{acc_u}</code>\n"
                f"🔑 Password: <code>{acc_p}</code>",
                parse_mode="HTML"
            )
            logging.info(f"✅ [WEB] Message sent to user {user_id}")
        except Exception as e:
            logging.error(f"❌ [WEB] Send error: {e}")
        
        # ✅ پاک کردن پیام فیش از چت ادمین‌ها
        admin_msg_id = await db.get_order_admin_message_id(order_id)
        if admin_msg_id:
            admins = await db.get_all_admins()
            for admin in admins:
                try:
                    admin_id = admin[0] if isinstance(admin, (list, tuple)) else admin
                    # ✅ تلاش برای پاک کردن پیام فیش
                    bot_instance.send_message_sync(
                        admin_id,
                        f"✅ سفارش #{order_id} از طریق وب تایید شد"
                    )
                    # ✅ پاک کردن پیام اصلی فیش
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            bot_instance.get_bot().delete_message(admin_id, admin_msg_id),
                            bot_instance.get_loop()
                        )
                        future.result(timeout=10)
                        logging.info(f"✅ [WEB] Deleted receipt message {admin_msg_id} from admin {admin_id}")
                    except Exception as e:
                        logging.warning(f"⚠️ [WEB] Could not delete message: {e}")
                except Exception as e:
                    logging.error(f"Error notifying admin: {e}")
        
        logging.info(f"✅ [WEB] Order {order_id} approved successfully")
        
    except Exception as e:
        logging.error(f"❌ [WEB] CRITICAL: {e}", exc_info=True)
    
    return RedirectResponse("/orders", status_code=303)    
@app.get("/orders/{order_id}/reject")
async def reject_order_web(order_id: int, user=Depends(get_current_user)):
    """رد سفارش از وب - با چک وضعیت و پاک کردن پیام فیش"""
    try:
        import bot_instance
        o = await db.get_order(order_id)
        if not o:
            return RedirectResponse("/orders", status_code=303)
        
        user_id = o[1]
        current_status = o[4]
        
        # ✅ چک وضعیت
        if current_status in ["approved", "rejected"]:
            logging.warning(f"⚠️ [WEB] Order {order_id} already {current_status}")
            return RedirectResponse("/orders", status_code=303)
        
        # ✅ استفاده از update_order_status جدید
        success = await db.update_order_status(order_id, "rejected")
        
        if not success:
            return RedirectResponse("/orders", status_code=303)

        await db.release_pending_account(order_id)
        
        try:
            bot_instance.send_message_sync(user_id, "❌ سفارش شما رد شد.")
        except Exception as e:
            logging.error(f"Error sending rejection: {e}")
        
        # ✅ پاک کردن پیام فیش
        admin_msg_id = await db.get_order_admin_message_id(order_id)
        if admin_msg_id:
            admins = await db.get_all_admins()
            for admin in admins:
                try:
                    admin_id = admin[0] if isinstance(admin, (list, tuple)) else admin
                    bot_instance.send_message_sync(
                        admin_id,
                        f"❌ سفارش #{order_id} از طریق وب رد شد"
                    )
                    # ✅ پاک کردن پیام فیش
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            bot_instance.get_bot().delete_message(admin_id, admin_msg_id),
                            bot_instance.get_loop()
                        )
                        future.result(timeout=10)
                    except Exception as e:
                        logging.warning(f"⚠️ Could not delete message: {e}")
                except:
                    pass
    except Exception as e:
        logging.error(f"Error rejecting order: {e}")
    
    return RedirectResponse("/orders", status_code=303)


# ============ ACCOUNTS ============
@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request, user=Depends(require_admin), plan_id: int = Query(None)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    plans = await db.get_all_plans()
    try:
        accounts = await db.get_all_accounts(plan_id=plan_id, limit=200) if plan_id else await db.get_all_accounts(limit=200)
    except:
        accounts = []
    
    rows = ""
    for a in accounts:
        try:
            status_badge = '<span class="badge badge-success">🟢 آزاد</span>' if a[4] == "free" else '<span class="badge badge-danger">🔴 فروخته</span>'
            p_name = a[9] if len(a) > 9 and a[9] else '-'
            rows += f"""<tr><td style="font-weight:600">#{a[0]}</td><td><code>{a[1]}</code></td><td><code>{a[2]}</code></td>
            <td><span class="badge badge-info">{p_name}</span></td><td>{status_badge}</td>
            <td><a href="/accounts/{a[0]}/delete" class="btn btn-danger btn-sm" onclick="return confirm('حذف؟')">حذف</a></td></tr>"""
        except:
            continue
    
    plan_filters = '<div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap">'
    plan_filters += f'<a href="/accounts" class="btn {"btn-primary" if not plan_id else "btn-secondary"}">همه</a>'
    for p in plans:
        count = await db.count_accounts(plan_id=p[0])
        active = "btn-primary" if plan_id == p[0] else "btn-secondary"
        plan_filters += f'<a href="/accounts?plan_id={p[0]}" class="btn {active}">{p[1]} ({count})</a>'
    plan_filters += '</div>'
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>اکانت‌ها</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("accounts", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><div><h1 class="page-title">اکانت‌ها</h1></div>
    <div class="btn-group"><a href="/accounts/add" class="btn btn-primary">+ افزودن</a><a href="/accounts/bulk" class="btn btn-purple">📁 گروهی</a></div></div>
    {plan_filters}
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>ID</th><th>Username</th><th>Password</th><th>پلن</th><th>وضعیت</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;padding:40px">اکانتی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/accounts/add", response_class=HTMLResponse)
async def add_account_form(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    plans = await db.get_all_plans()
    plan_options = "".join([f'<option value="{p[0]}">{p[1]}</option>' for p in plans])
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>افزودن</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("accounts", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">افزودن اکانت</h1><a href="/accounts" class="btn btn-secondary">← بازگشت</a></div>
    <div class="form-card"><form method="post">
    <div class="form-group"><label class="form-label">Username</label><input type="text" name="username" class="form-input" required></div>
    <div class="form-group"><label class="form-label">Password</label><input type="text" name="password" class="form-input" required></div>
    <div class="form-group"><label class="form-label">پلن</label><select name="plan_id" class="form-select" required>{plan_options}</select></div>
    <div class="form-group"><label class="form-label">یادداشت</label><input type="text" name="note" class="form-input"></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">✓ ذخیره</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/accounts/add")
async def add_account_submit(username: str = Form(...), password: str = Form(...),
                             plan_id: int = Form(...), note: str = Form(""), user=Depends(require_admin)):
    try:
        await db.add_account(username, password, plan_id, note)
    except ValueError as e:
        return RedirectResponse(f"/accounts/add?error={str(e)}", status_code=303)
    return RedirectResponse("/accounts", status_code=303)


@app.get("/accounts/{acc_id}/delete")
async def delete_account(acc_id: int, user=Depends(require_admin)):
    await db.delete_account(acc_id)
    return RedirectResponse("/accounts", status_code=303)


@app.get("/accounts/bulk", response_class=HTMLResponse)
async def bulk_upload_form(request: Request, user=Depends(require_admin), success: str = ""):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    plans = await db.get_all_plans()
    plan_options = "".join([f'<option value="{p[0]}">{p[1]}</option>' for p in plans])
    alert = f'<div class="alert alert-success">✓ {success} اکانت اضافه شد</div>' if success else ""
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>گروهی</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("accounts", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">افزودن گروهی</h1><a href="/accounts" class="btn btn-secondary">← بازگشت</a></div>
    {alert}<div class="form-card" style="max-width:700px">
    <div style="background:rgba(0,113,227,0.05);border:1px solid rgba(0,113,227,0.15);border-radius:12px;padding:16px;margin-bottom:24px">
    <div style="font-weight:600;color:var(--blue);margin-bottom:8px">📋 فرمت: <code>username:password</code></div></div>
    <form method="post" enctype="multipart/form-data">
    <div class="form-group"><label class="form-label">پلن</label><select name="plan_id" class="form-select" required>{plan_options}</select></div>
    <div class="form-group"><label class="form-label">فایل</label>
    <label class="file-upload" for="file-input"><div class="file-upload-icon">📄</div><div class="file-upload-text">انتخاب فایل</div>
    <input type="file" id="file-input" name="file" accept=".txt" required></label></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:13px">📤 آپلود</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/accounts/bulk")
async def bulk_upload_submit(plan_id: int = Form(...), file: UploadFile = File(...), user=Depends(require_admin)):
    try:
        content = await file.read()
        text = content.decode('utf-8-sig')
        count = 0
        skipped = 0
        seen = set()
        for line in text.splitlines():
            line = line.strip().replace('\r', '')
            if not line or line.startswith('#'):
                continue
            if ':' not in line:
                continue
            u, p = line.split(':', 1)
            u, p = u.strip(), p.strip()
            if not u or not p or u in seen:
                if u in seen:
                    skipped += 1
                continue
            seen.add(u)
            if await db.account_username_exists(u):
                skipped += 1
                continue
            try:
                await db.add_account(u, p, plan_id)
                count += 1
            except ValueError:
                skipped += 1
        return RedirectResponse(f"/accounts/bulk?success={count}&skipped={skipped}", status_code=303)
    except Exception:
        return RedirectResponse("/accounts/bulk", status_code=303)


# ============ PLANS ============
@app.get("/plans", response_class=HTMLResponse)
async def plans_page(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    plans = await db.get_all_plans()
    rows = ""
    for p in plans:
        try:
            status_badge = '<span class="badge badge-success">فعال</span>' if p[4] else '<span class="badge badge-danger">غیرفعال</span>'
            rows += f"""<tr><td style="font-weight:600">#{p[0]}</td><td style="font-weight:600">{p[1]}</td>
            <td>{p[2]:,} ت</td><td>{p[3]} روز</td><td>{status_badge}</td>
            <td><div class="btn-group">
            <a href="/plans/{p[0]}/edit" class="btn btn-secondary btn-sm">✏️</a>
            <a href="/plans/{p[0]}/toggle" class="btn btn-warning btn-sm">🔄</a>
            <a href="/plans/{p[0]}/delete" class="btn btn-danger btn-sm" onclick="return confirm('حذف؟')">🗑</a></div></td></tr>"""
        except:
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>پلن‌ها</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("plans", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">پلن‌ها</h1><a href="/plans/add" class="btn btn-primary">+ افزودن</a></div>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>ID</th><th>نام</th><th>قیمت</th><th>مدت</th><th>وضعیت</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;padding:40px">پلنی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/plans/add", response_class=HTMLResponse)
async def add_plan_form(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>افزودن</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("plans", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">افزودن پلن</h1><a href="/plans" class="btn btn-secondary">← بازگشت</a></div>
    <div class="form-card"><form method="post">
    <div class="form-group"><label class="form-label">نام</label><input type="text" name="name" class="form-input" required></div>
    <div class="form-group"><label class="form-label">قیمت</label><input type="number" name="price" class="form-input" required></div>
    <div class="form-group"><label class="form-label">مدت (روز)</label><input type="number" name="days" class="form-input" required></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">✓ ذخیره</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/plans/add")
async def add_plan_submit(name: str = Form(...), price: int = Form(...), days: int = Form(...), user=Depends(require_admin)):
    await db.add_plan(name, price, days)
    return RedirectResponse("/plans", status_code=303)


@app.get("/plans/{plan_id}/edit", response_class=HTMLResponse)
async def edit_plan_form(plan_id: int, request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    p = await db.get_plan(plan_id)
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>ویرایش</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("plans", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">ویرایش پلن</h1><a href="/plans" class="btn btn-secondary">← بازگشت</a></div>
    <div class="form-card"><form method="post">
    <div class="form-group"><label class="form-label">نام</label><input type="text" name="name" class="form-input" value="{p[1]}" required></div>
    <div class="form-group"><label class="form-label">قیمت</label><input type="number" name="price" class="form-input" value="{p[2]}" required></div>
    <div class="form-group"><label class="form-label">مدت</label><input type="number" name="days" class="form-input" value="{p[3]}" required></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">✓ ذخیره</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/plans/{plan_id}/edit")
async def edit_plan_submit(plan_id: int, name: str = Form(...), price: int = Form(...), days: int = Form(...), user=Depends(require_admin)):
    await db.update_plan_field(plan_id, "name", name)
    await db.update_plan_field(plan_id, "price", price)
    await db.update_plan_field(plan_id, "days", days)
    return RedirectResponse("/plans", status_code=303)


@app.get("/plans/{plan_id}/toggle")
async def toggle_plan(plan_id: int, user=Depends(require_admin)):
    p = await db.get_plan(plan_id)
    await db.update_plan_field(plan_id, "is_active", 0 if p[4] else 1)
    return RedirectResponse("/plans", status_code=303)


@app.get("/plans/{plan_id}/delete")
async def delete_plan(plan_id: int, user=Depends(require_admin)):
    await db.delete_plan(plan_id)
    return RedirectResponse("/plans", status_code=303)


# ============ COUPONS ============
@app.get("/coupons", response_class=HTMLResponse)
async def coupons_page(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    coupons = await db.get_all_coupons()
    rows = ""
    for c in coupons:
        try:
            usage = f'{c[4]} / {c[3]}'
            expire = "♾️"
            if c[7]:
                try:
                    days_left = (datetime.fromisoformat(c[7]) - datetime.now()).days
                    expire = '❌' if days_left < 0 else f'{days_left}d'
                except:
                    expire = "?"
            status = '🟢' if c[5] else '🔴'
            rows += f"""<tr><td><code style="font-weight:600">{c[1]}</code></td>
            <td><span class="badge badge-purple">{c[2]}%</span></td><td>{usage}</td><td>{expire}</td><td>{status}</td>
            <td><a href="/coupons/{c[0]}/toggle" class="btn btn-warning btn-sm">🔄</a>
            <a href="/coupons/{c[0]}/delete" class="btn btn-danger btn-sm" onclick="return confirm('حذف؟')">🗑</a></td></tr>"""
        except:
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>تخفیف</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("coupons", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">کد تخفیف</h1><a href="/coupons/add" class="btn btn-primary">+ افزودن</a></div>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>کد</th><th>درصد</th><th>استفاده/محدودیت</th><th>انقضا</th><th>وضعیت</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;padding:40px">کدی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/coupons/add", response_class=HTMLResponse)
async def add_coupon_form(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>افزودن</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("coupons", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">افزودن کد</h1><a href="/coupons" class="btn btn-secondary">← بازگشت</a></div>
    <div class="form-card"><form method="post">
    <div class="form-group"><label class="form-label">کد</label><input type="text" name="code" class="form-input" required></div>
    <div class="form-group"><label class="form-label">درصد</label><input type="number" name="discount" class="form-input" min="1" max="100" required></div>
    <div class="form-group"><label class="form-label">محدودیت</label><input type="number" name="limit" class="form-input" min="1" required></div>
    <div class="form-group"><label class="form-label">مدت اعتبار (روز)</label><input type="number" name="expire_days" class="form-input" min="1" placeholder="خالی=نامحدود"></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">✓ ذخیره</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/coupons/add")
async def add_coupon_submit(code: str = Form(...), discount: int = Form(...), limit: int = Form(...),
                           expire_days: int = Form(0), user=Depends(require_admin)):
    await db.add_coupon(code, discount, limit, expire_days if expire_days > 0 else None)
    return RedirectResponse("/coupons", status_code=303)


@app.get("/coupons/{coupon_id}/toggle")
async def toggle_coupon(coupon_id: int, user=Depends(require_admin)):
    c = await db.get_coupon_by_id(coupon_id)
    await db.update_coupon_field(coupon_id, "is_active", 0 if c[5] else 1)
    return RedirectResponse("/coupons", status_code=303)


@app.get("/coupons/{coupon_id}/delete")
async def delete_coupon(coupon_id: int, user=Depends(require_admin)):
    await db.delete_coupon(coupon_id)
    return RedirectResponse("/coupons", status_code=303)


# ============ USERS ============
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, user=Depends(require_admin), search: str = Query("")):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    try:
        if search:
            users = await db.execute(
                "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ? OR CAST(telegram_id AS TEXT) LIKE ? ORDER BY id DESC LIMIT 100",
                (f"%{search}%", f"%{search}%", f"%{search}%")
            )
        else:
            users = await db.get_all_users(limit=200)
    except:
        users = []
    
    rows = ""
    for u in users:
        try:
            status_badge = '<span class="badge badge-danger">مسدود</span>' if u[4] else '<span class="badge badge-success">فعال</span>'
            action = f'<a href="/users/{u[1]}/ban" class="btn btn-danger btn-sm">مسدود</a>' if not u[4] else f'<a href="/users/{u[1]}/unban" class="btn btn-success btn-sm">رفع</a>'
            phone = u[6] if len(u) > 6 and u[6] else '-'
            rows += f"""<tr><td><code>{u[1]}</code></td><td>{u[2] or '-'}</td><td>{u[3] or '-'}</td>
            <td>{phone}</td><td>{status_badge}</td><td style="color:var(--text-tertiary)">{str(u[5])[:10] if u[5] else '-'}</td>
            <td>{action}</td></tr>"""
        except:
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>کاربران</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("users", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">کاربران</h1></div>
    <form method="get" style="margin-bottom:20px"><div style="display:flex;gap:10px">
    <input type="text" name="search" class="form-input" placeholder="🔍 جستجو" value="{search}" style="flex:1">
    <button type="submit" class="btn btn-primary">جستجو</button>
    {f'<a href="/users" class="btn btn-secondary">پاک کردن</a>' if search else ''}</div></form>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>ID</th><th>Username</th><th>نام</th><th>تلفن</th><th>وضعیت</th><th>تاریخ</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="7" style="text-align:center;padding:40px">کاربری نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/users/{user_id}/ban")
async def ban_user(user_id: int, user=Depends(require_admin)):
    await db.ban_user(user_id, True)
    return RedirectResponse("/users", status_code=303)


@app.get("/users/{user_id}/unban")
async def unban_user(user_id: int, user=Depends(require_admin)):
    await db.ban_user(user_id, False)
    return RedirectResponse("/users", status_code=303)


# ============ TICKETS ============
@app.get("/tickets", response_class=HTMLResponse)
async def tickets_page(request: Request, user=Depends(require_admin), status: str = Query("all")):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {"open_tickets": 0}
    try:
        tickets = await db.get_all_tickets(status=status if status != "all" else None, limit=100)
    except:
        tickets = []
    
    rows = ""
    for t in tickets:
        try:
            status_badge = '<span class="badge badge-success">باز</span>' if t[3] == "open" else '<span class="badge badge-secondary">بسته</span>'
            username = t[7] or t[8] or "?"
            rows += f"""<tr><td style="font-weight:600">#{t[0]}</td><td>{username}</td><td>{t[2]}</td>
            <td>{status_badge}</td><td style="color:var(--text-tertiary)">{str(t[4])[:10] if t[4] else '-'}</td>
            <td><a href="/tickets/{t[0]}" class="btn btn-primary btn-sm">مشاهده</a></td></tr>"""
        except:
            continue
    
    filter_tabs = f"""<div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap">
    <a href="/tickets?status=all" class="btn {'btn-primary' if status == 'all' else 'btn-secondary'}">همه</a>
    <a href="/tickets?status=open" class="btn {'btn-success' if status == 'open' else 'btn-secondary'}">🟢 باز ({stats.get('open_tickets', 0)})</a>
    <a href="/tickets?status=closed" class="btn {'btn-secondary' if status == 'closed' else 'btn-secondary'}">🔴 بسته</a></div>"""
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>تیکت‌ها</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("tickets", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">تیکت‌ها</h1></div>
    {filter_tabs}
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>ID</th><th>کاربر</th><th>موضوع</th><th>وضعیت</th><th>تاریخ</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;padding:40px">تیکتی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(ticket_id: int, request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        return RedirectResponse("/tickets", status_code=303)
    messages = await db.get_ticket_messages(ticket_id)
    
    messages_html = ""
    for m in messages:
        try:
            sender_class = "user" if m[2] == "user" else "admin"
            time_str = str(m[6])[:16] if len(m) > 6 and m[6] else ""
            messages_html += f"""<div class="message-item {sender_class}">
            <div class="message-sender">{'👤 کاربر' if m[2] == 'user' else '🛡️ پشتیبانی'}</div>
            <div class="message-text">{m[3]}</div>
            <div class="message-time">{time_str}</div></div>"""
        except:
            continue
    
    reply_form = ""
    close_btn = ""
    if ticket[3] == 'open':
        reply_form = f"""<div class="card"><h3 style="margin-bottom:16px">💬 پاسخ</h3>
        <form method="post" action="/tickets/{ticket_id}/reply"><div class="form-group"><textarea name="reply" class="form-input" rows="4" placeholder="پاسخ..." required></textarea></div>
        <button type="submit" class="btn btn-primary">ارسال</button></form></div>"""
        close_btn = f'<a href="/tickets/{ticket_id}/close" class="btn btn-danger">🔒 بستن</a>'
    else:
        close_btn = f'<a href="/tickets/{ticket_id}/reopen" class="btn btn-success">🔓 باز کردن</a>'
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>تیکت #{ticket_id}</title>{APPLE_CSS}
    <style>.messages-container{{max-height:500px;overflow-y:auto;padding:20px;background:var(--bg-secondary);border-radius:var(--radius);margin-bottom:20px}}
    .message-item{{margin-bottom:16px;padding:12px 16px;border-radius:12px;max-width:80%}}
    .message-item.user{{background:var(--blue);color:white;margin-right:auto}}
    .message-item.admin{{background:white;margin-left:auto;border:1px solid var(--border)}}
    .message-sender{{font-size:12px;font-weight:600;margin-bottom:4px;opacity:0.8}}
    .message-text{{font-size:14px;line-height:1.6}}
    .message-time{{font-size:11px;opacity:0.6;margin-top:6px}}</style></head>
    <body><div class="app-layout">{sidebar("tickets", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><div><h1 class="page-title">تیکت #{ticket_id}</h1><p class="page-subtitle">{ticket[2]}</p></div>
    <div class="btn-group">{close_btn}<a href="/tickets" class="btn btn-secondary">← بازگشت</a></div></div>
    <div class="messages-container">{messages_html if messages_html else '<div style="text-align:center;padding:40px;color:var(--text-hint)">پیامی نیست</div>'}</div>
    {reply_form}</main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/tickets/{ticket_id}/reply")
async def ticket_reply(ticket_id: int, user=Depends(require_admin), reply: str = Form(...)):
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        return RedirectResponse("/tickets", status_code=303)
    await db.add_ticket_message(ticket_id, "admin", user["user_id"], reply)
    try:
        import bot_instance
        bot_instance.send_message_sync(
            ticket[1],
            f"🛡️ پاسخ پشتیبانی (تیکت #{ticket_id}):\n\n{reply}",
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"Ticket notify error: {e}")
    return RedirectResponse(f"/tickets/{ticket_id}?sent=1", status_code=303)


@app.post("/tickets/{ticket_id}")
async def ticket_reply_legacy(ticket_id: int, user=Depends(require_admin), reply: str = Form(...)):
    """مسیر قدیمی — redirect به handler جدید"""
    return await ticket_reply(ticket_id, user, reply)


@app.get("/tickets/{ticket_id}/close")
async def close_ticket(ticket_id: int, user=Depends(require_admin)):
    await db.update_ticket_status(ticket_id, "closed")
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.get("/tickets/{ticket_id}/reopen")
async def reopen_ticket(ticket_id: int, user=Depends(require_admin)):
    await db.update_ticket_status(ticket_id, "open")
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


# ============ WAITLIST ============
@app.get("/waitlist", response_class=HTMLResponse)
async def waitlist_page(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    waitlist = await db.get_waitlist()
    rows = ""
    for w in waitlist:
        try:
            status_badge = '<span class="badge badge-info">اطلاع‌رسانی شده</span>' if w[4] else '<span class="badge badge-warning">در انتظار</span>'
            rows += f"""<tr><td>{w[7] or w[8] or '-'}</td><td><span class="badge badge-purple">{w[9] or '-'}</span></td>
            <td>{status_badge}</td><td style="color:var(--text-tertiary)">{str(w[5])[:10] if w[5] else '-'}</td>
            <td><a href="/waitlist/{w[0]}/remove" class="btn btn-danger btn-sm">حذف</a></td></tr>"""
        except:
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>انتظار</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("waitlist", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">لیست انتظار</h1></div>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>کاربر</th><th>پلن</th><th>وضعیت</th><th>تاریخ</th><th>عملیات</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="5" style="text-align:center;padding:40px">خالی</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/waitlist/{waitlist_id}/remove")
async def remove_waitlist(waitlist_id: int, user=Depends(require_admin)):
    await db.remove_from_waitlist(waitlist_id)
    return RedirectResponse("/waitlist", status_code=303)


# ============ TERMS ============
@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request, user=Depends(require_admin), success: str = ""):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    terms_text = await db.get_terms_text()
    alert = '<div class="alert alert-success">✓ ذخیره شد</div>' if success else ""
    terms_escaped = terms_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>قوانین</title>{APPLE_CSS}
    <style>.terms-editor{{min-height:400px;font-family:'Vazirmatn',monospace;line-height:1.8;resize:vertical}}
    .terms-preview{{background:var(--bg-secondary);padding:20px;border-radius:var(--radius);margin-top:20px;line-height:1.8}}</style></head>
    <body><div class="app-layout">{sidebar("terms", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">📜 مدیریت قوانین</h1></div>
    {alert}
    <div class="card"><form method="post">
    <div class="form-group"><label class="form-label">متن قوانین (HTML)</label>
    <textarea name="terms_text" class="form-input terms-editor" required oninput="updateCounter()">{terms_escaped}</textarea>
    <div style="margin-top:10px;font-size:13px;color:var(--text-hint)">طول: <span id="charCount">{len(terms_text)}</span> کاراکتر</div></div>
    <div class="btn-group"><button type="submit" class="btn btn-primary">✓ ذخیره</button>
    <button type="button" class="btn btn-secondary" onclick="previewTerms()">👁 پیش‌نمایش</button></div></form>
    <div id="termsPreview" class="terms-preview" style="display:none"><h3 style="margin-bottom:15px">👁 پیش‌نمایش:</h3><div id="previewContent"></div></div></div>
    <div class="card" style="margin-top:20px"><h3 style="margin-bottom:15px">💡 راهنما</h3>
    <ul style="line-height:2;color:var(--text-secondary)">
    <li>از تگ‌های HTML استفاده کنید</li><li>ایموجی برای جذابیت</li><li>حداقل 50 کاراکتر</li></ul></div>
    </main></div>
    <script>function updateCounter(){{document.getElementById('charCount').textContent=document.querySelector('textarea').value.length}}
    function previewTerms(){{const t=document.querySelector('textarea').value;document.getElementById('previewContent').innerHTML=t;document.getElementById('termsPreview').style.display='block'}}</script>
    </body></html>"""
    return HTMLResponse(html)


@app.post("/terms")
async def save_terms(request: Request, user=Depends(require_admin), terms_text: str = Form(...)):
    if len(terms_text) < 50:
        return RedirectResponse("/terms?error=short", status_code=303)
    await db.set_terms_text(terms_text)
    return RedirectResponse("/terms?success=1", status_code=303)


# ============ SETTINGS ============
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user=Depends(require_admin), success: str = ""):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    card = await db.get_setting("card_number")
    support = await db.get_setting("support_username")
    alert = '<div class="alert alert-success">✓ ذخیره شد</div>' if success else ""
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>تنظیمات</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("settings", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">تنظیمات</h1></div>
    {alert}
    <div class="form-card" style="max-width:700px"><form method="post">
    <div class="form-group"><label class="form-label">💳 شماره کارت</label><input type="text" name="card_number" class="form-input" value="{card}" required></div>
    <div class="form-group"><label class="form-label">🛡️ پشتیبانی</label><input type="text" name="support_username" class="form-input" value="{support}" required></div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">✓ ذخیره</button></form></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/settings")
async def settings_submit(card_number: str = Form(...), support_username: str = Form(...), user=Depends(require_admin)):
    await db.set_setting("card_number", card_number)
    await db.set_setting("support_username", support_username)
    return RedirectResponse("/settings?success=1", status_code=303)


# ============ LOGS ============
@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, user=Depends(require_admin)):
    try:
        stats = await db.get_dashboard_stats()
    except:
        stats = {}
    logs = await db.get_logs(limit=200)
    rows = ""
    for l in logs:
        try:
            rows += f"""<tr><td><span class="badge badge-info">{l[1]}</span></td><td><code>{l[2]}</code></td>
            <td>{l[3] or '-'}</td><td style="font-size:13px">{l[4]}</td>
            <td style="color:var(--text-tertiary);font-size:13px">{str(l[5])[:16] if l[5] else '-'}</td></tr>"""
        except:
            continue
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>لاگ</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("logs", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">لاگ‌ها</h1>
    <a href="/logs/clear" class="btn btn-danger" onclick="return confirm('پاک شوند؟')">🗑 پاک کردن</a></div>
    <div class="table-wrapper"><div class="table-scroll"><table>
    <thead><tr><th>عملیات</th><th>کاربر</th><th>Username</th><th>جزئیات</th><th>زمان</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="5" style="text-align:center;padding:40px">لاگی نیست</td></tr>'}</tbody>
    </table></div></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/logs/clear")
async def clear_logs(user=Depends(require_owner)):
    await db.clear_logs()
    return RedirectResponse("/logs", status_code=303)


# ============ MESSAGES ============
@app.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request, user=Depends(require_owner)):
    stats = await db.get_dashboard_stats()
    keys = ["welcome", "receipt_received", "order_approved", "order_rejected", "apple_unlock_done"]
    rows = ""
    for k in keys:
        val = await db.get_message(k, "")
        preview = (val[:80] + "...") if len(val) > 80 else val
        rows += f"""<tr><td>{k}</td><td style="font-size:13px">{preview}</td>
        <td><a href="/messages/{k}" class="btn btn-secondary btn-sm">✏️</a></td></tr>"""
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>متن‌ها</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("messages", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">📝 ویرایش متن‌ها</h1>
    <a href="/dashboard" class="btn btn-secondary">← بازگشت</a></div>
    <div class="table-wrapper"><table><thead><tr><th>کلید</th><th>پیش‌نمایش</th><th></th></tr></thead>
    <tbody>{rows}</tbody></table></div></main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/messages/{key}", response_class=HTMLResponse)
async def message_edit_form(key: str, request: Request, user=Depends(require_owner), success: str = ""):
    stats = await db.get_dashboard_stats()
    text = await db.get_message(key, "")
    alert = '<div class="alert alert-success">✓ ذخیره شد</div>' if success else ""
    escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>{key}</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("messages", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">ویرایش: {key}</h1>
    <a href="/messages" class="btn btn-secondary">← بازگشت</a></div>{alert}
    <div class="form-card"><form method="post">
    <textarea name="text" class="form-input" rows="12" required>{escaped}</textarea>
    <button type="submit" class="btn btn-primary" style="margin-top:16px">✓ ذخیره</button></form></div>
    </main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/messages/{key}")
async def message_edit_save(key: str, text: str = Form(...), user=Depends(require_owner)):
    await db.set_message(key, text)
    return RedirectResponse(f"/messages/{key}?success=1", status_code=303)


# ============ WALLET TOPUPS WEB ============
@app.get("/wallet-topups", response_class=HTMLResponse)
async def wallet_topups_page(request: Request, user=Depends(require_admin)):
    stats = await db.get_dashboard_stats()
    topups = await db.get_pending_wallet_topups()
    rows = ""
    for t in topups:
        rows += f"""<tr><td>#{t[0]}</td><td>{t[1]}</td><td>{t[2]:,} ت</td><td>{t[3]}</td>
        <td><a href="/wallet-topups/{t[0]}/approve" class="btn btn-success btn-sm">✓</a>
        <a href="/wallet-topups/{t[0]}/reject" class="btn btn-danger btn-sm">✗</a></td></tr>"""
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>شارژ</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("wallet", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">💳 شارژ کیف پول</h1>
    <a href="/dashboard" class="btn btn-secondary">← بازگشت</a></div>
    <div class="table-wrapper"><table><thead><tr><th>ID</th><th>کاربر</th><th>مبلغ</th><th>وضعیت</th><th></th></tr></thead>
    <tbody>{rows or '<tr><td colspan="5" style="text-align:center;padding:40px">خالی</td></tr>'}</tbody></table></div>
    </main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/wallet-topups/{tid}/approve")
async def wallet_topup_approve_web(tid: int, user=Depends(require_admin)):
    import bot_instance
    t = await db.get_wallet_topup(tid)
    if t and await db.approve_wallet_topup(tid):
        try:
            bot_instance.send_message_sync(t[1], f"✅ شارژ #{tid} به مبلغ {t[2]:,} تومان تایید شد.")
        except Exception:
            pass
    return RedirectResponse("/wallet-topups", status_code=303)


@app.get("/wallet-topups/{tid}/reject")
async def wallet_topup_reject_web(tid: int, user=Depends(require_admin)):
    import bot_instance
    t = await db.get_wallet_topup(tid)
    await db.reject_wallet_topup(tid)
    if t:
        try:
            bot_instance.send_message_sync(t[1], f"❌ درخواست شارژ #{tid} رد شد.")
        except Exception:
            pass
    return RedirectResponse("/wallet-topups", status_code=303)


# ============ APPLE UNLOCK WEB ============
@app.get("/apple-unlock", response_class=HTMLResponse)
async def apple_unlock_page(request: Request, user=Depends(require_admin)):
    stats = await db.get_dashboard_stats()
    orders = await db.get_all_apple_unlocks(limit=50)
    rows = ""
    for o in orders:
        rows += f"""<tr><td>#{o[0]}</td><td>{o[1]}</td><td>{o[2]}</td><td>{o[12]}</td>
        <td>{o[10] or 0:,} ت</td>
        <td><a href="/apple-unlock/{o[0]}" class="btn btn-secondary btn-sm">👁</a></td></tr>"""
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>آنلاک</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("apple", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">🔓 آنلاک Apple ID</h1>
    <a href="/dashboard" class="btn btn-secondary">← بازگشت</a></div>
    <div class="table-wrapper"><table><thead><tr><th>ID</th><th>کاربر</th><th>Apple ID</th><th>وضعیت</th><th>قیمت</th><th></th></tr></thead>
    <tbody>{rows or '<tr><td colspan="6" style="text-align:center;padding:40px">خالی</td></tr>'}</tbody></table></div>
    </main></div></body></html>"""
    return HTMLResponse(html)


@app.get("/apple-unlock/{oid}", response_class=HTMLResponse)
async def apple_unlock_detail(oid: int, request: Request, user=Depends(require_admin)):
    stats = await db.get_dashboard_stats()
    o = await db.get_apple_unlock(oid)
    if not o:
        return RedirectResponse("/apple-unlock", status_code=303)
    actions = ""
    if o[12] == "payment_submitted":
        actions = f'<a href="/apple-unlock/{oid}/pay-ok" class="btn btn-success">✅ تایید پرداخت</a>'
    elif o[12] == "payment_approved":
        actions = f'<a href="/apple-unlock/{oid}/done" class="btn btn-primary">🔓 آنلاک شد</a>'
    html = f"""<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="UTF-8"><title>#{oid}</title>{APPLE_CSS}</head>
    <body><div class="app-layout">{sidebar("apple", user["role"], stats)}<main class="main-content fade-in">
    <div class="page-header"><h1 class="page-title">🔓 #{oid}</h1>
    <a href="/apple-unlock" class="btn btn-secondary">← بازگشت</a></div>
    <div class="card"><p>👤 {o[1]}</p><p>📧 {o[2]}</p><p>🔑 {o[3]}</p><p>🎂 {o[4]}</p>
    <p>❓ {o[5]}</p><p>📊 {o[12]}</p><p>💰 {o[10] or 0:,} ت | ⏰ {o[11] or '-'}</p>
    <div class="btn-group" style="margin-top:16px">{actions}</div></div>
    <div class="form-card"><h3>تعیین قیمت</h3><form method="post" action="/apple-unlock/{oid}/price">
    <input name="price" class="form-input" placeholder="قیمت" required>
    <input name="unlock_time" class="form-input" placeholder="زمان" required style="margin-top:10px">
    <button class="btn btn-primary" style="margin-top:10px">ذخیره</button></form></div>
    </main></div></body></html>"""
    return HTMLResponse(html)


@app.post("/apple-unlock/{oid}/price")
async def apple_unlock_set_price(oid: int, price: int = Form(...), unlock_time: str = Form(...), user=Depends(require_admin)):
    import bot_instance
    await db.set_apple_unlock_price(oid, price, unlock_time)
    o = await db.get_apple_unlock(oid)
    if o:
        try:
            bot_instance.send_message_sync(
                o[1], f"🔓 سفارش #{oid}\n💰 {price:,} ت\n⏰ {unlock_time}\n\nاز ربات فیش ارسال کنید.")
        except Exception:
            pass
    return RedirectResponse(f"/apple-unlock/{oid}", status_code=303)


@app.get("/apple-unlock/{oid}/pay-ok")
async def apple_unlock_pay_ok(oid: int, user=Depends(require_admin)):
    import bot_instance
    await db.approve_apple_payment(oid)
    o = await db.get_apple_unlock(oid)
    if o:
        try:
            bot_instance.send_message_sync(o[1], f"✅ پرداخت #{oid} تایید شد.")
        except Exception:
            pass
    return RedirectResponse(f"/apple-unlock/{oid}", status_code=303)


@app.get("/apple-unlock/{oid}/done")
async def apple_unlock_done(oid: int, user=Depends(require_admin)):
    import bot_instance
    await db.mark_apple_unlocked(oid)
    o = await db.get_apple_unlock(oid)
    msg = await db.get_message("apple_unlock_done")
    if o:
        try:
            bot_instance.send_message_sync(o[1], msg, parse_mode="HTML")
        except Exception:
            pass
    return RedirectResponse("/apple-unlock", status_code=303)


def run_dashboard():
    import uvicorn
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="warning")