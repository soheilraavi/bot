"""
تنظیمات ربات
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"متغیر محیطی {key} تنظیم نشده. آن را در فایل .env قرار بده.")
    return value


BOT_TOKEN = _require_env("BOT_TOKEN")
OWNER_ID = int(_require_env("ADMIN_ID"))

DB_NAME = os.getenv("DB_NAME", "bot_database.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "accounts.txt")

ITEMS_PER_PAGE = 5
LOG_LEVEL = "INFO"

USE_PROXY = False
PROXY_URL = "socks5://127.0.0.1:10808"

DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))
DASHBOARD_PASSWORD = _require_env("DASHBOARD_PASSWORD")
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET") or os.urandom(32).hex()

RENEWAL_REMINDER_DAYS = 3

# ============ APPLE STYLE CSS ============
APPLE_CSS = """
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>
:root {
    --bg-primary: #f5f5f7;
    --bg-secondary: #ffffff;
    --text-primary: #1d1d1f;
    --text-secondary: #6e6e73;
    --text-tertiary: #86868b;
    --blue: #0071e3;
    --blue-hover: #0077ed;
    --green: #34c759;
    --red: #ff3b30;
    --orange: #ff9500;
    --purple: #af52de;
    --pink: #ff2d55;
    --teal: #5ac8fa;
    --indigo: #5856d6;
    --border: rgba(0,0,0,0.06);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 20px;
    --transition: cubic-bezier(0.4, 0, 0.2, 1);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    letter-spacing: -0.01em;
}

.app-layout { display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; }

/* Sidebar */
.sidebar {
    background: rgba(255,255,255,0.8);
    backdrop-filter: saturate(180%) blur(20px);
    border-left: 1px solid var(--border);
    padding: 24px 16px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

.sidebar-logo { display: flex; align-items: center; gap: 12px; padding: 8px 12px; margin-bottom: 32px; }
.sidebar-logo-icon {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #0071e3, #5856d6);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; color: white;
}
.sidebar-logo-text { font-size: 17px; font-weight: 600; color: var(--text-primary); }
.sidebar-section { margin-bottom: 24px; }
.sidebar-section-title {
    font-size: 11px; font-weight: 600; color: var(--text-tertiary);
    text-transform: uppercase; letter-spacing: 0.06em; padding: 0 12px; margin-bottom: 8px;
}

.nav-item {
    display: flex; align-items: center; gap: 12px; padding: 9px 12px;
    border-radius: var(--radius-sm); color: var(--text-secondary);
    text-decoration: none; font-size: 14px; font-weight: 500;
    transition: all 0.2s var(--transition); margin-bottom: 2px;
}
.nav-item:hover { background: rgba(0,0,0,0.04); color: var(--text-primary); }
.nav-item.active { background: var(--blue); color: white; font-weight: 600; }
.nav-item .icon { font-size: 18px; width: 22px; text-align: center; }
.nav-item .badge-count {
    margin-right: auto; background: rgba(0,0,0,0.08); color: var(--text-secondary);
    font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
}
.nav-item.active .badge-count { background: rgba(255,255,255,0.25); color: white; }

/* Main Content */
.main-content { padding: 32px 40px; max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; flex-wrap: wrap; gap: 16px; }
.page-title { font-size: 32px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.page-subtitle { font-size: 15px; color: var(--text-secondary); margin-top: 4px; font-weight: 400; }

/* Cards */
.card {
    background: var(--bg-secondary); border-radius: var(--radius-lg); padding: 24px;
    box-shadow: var(--shadow-sm); border: 1px solid var(--border); margin-bottom: 20px;
    transition: all 0.3s var(--transition);
}
.card:hover { box-shadow: var(--shadow-md); }
.card-title { font-size: 17px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; letter-spacing: -0.01em; }

/* Stat Cards */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }
.stat-card {
    background: var(--bg-secondary); border-radius: var(--radius-lg); padding: 22px;
    box-shadow: var(--shadow-sm); border: 1px solid var(--border);
    transition: all 0.3s var(--transition); position: relative; overflow: hidden;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-card::before {
    content: ''; position: absolute; top: 0; right: 0;
    width: 100px; height: 100px; border-radius: 50%; opacity: 0.08; transform: translate(30%, -30%);
}
.stat-card.blue::before { background: var(--blue); }
.stat-card.green::before { background: var(--green); }
.stat-card.purple::before { background: var(--purple); }
.stat-card.orange::before { background: var(--orange); }

.stat-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-bottom: 14px;
}
.stat-icon.blue { background: rgba(0,113,227,0.1); color: var(--blue); }
.stat-icon.green { background: rgba(52,199,89,0.1); color: var(--green); }
.stat-icon.purple { background: rgba(175,82,222,0.1); color: var(--purple); }
.stat-icon.orange { background: rgba(255,149,0,0.1); color: var(--orange); }

.stat-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; line-height: 1; }
.stat-change { font-size: 12px; font-weight: 600; color: var(--green); margin-top: 8px; display: flex; align-items: center; gap: 4px; }

/* Buttons */
.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    padding: 9px 16px; border-radius: 980px; font-size: 14px; font-weight: 500;
    text-decoration: none; border: none; cursor: pointer;
    transition: all 0.2s var(--transition); white-space: nowrap; font-family: inherit;
}
.btn:hover { transform: scale(1.02); }
.btn:active { transform: scale(0.98); }
.btn-primary { background: var(--blue); color: white; }
.btn-primary:hover { background: var(--blue-hover); }
.btn-secondary { background: rgba(0,0,0,0.06); color: var(--text-primary); }
.btn-secondary:hover { background: rgba(0,0,0,0.1); }
.btn-success { background: var(--green); color: white; }
.btn-danger { background: var(--red); color: white; }
.btn-warning { background: var(--orange); color: white; }
.btn-purple { background: var(--purple); color: white; }
.btn-sm { padding: 6px 12px; font-size: 13px; }
.btn-group { display: flex; gap: 8px; flex-wrap: wrap; }

/* Quick Actions */
.quick-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.quick-action {
    display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 24px 16px;
    background: var(--bg-secondary); border-radius: var(--radius-md); text-decoration: none;
    color: var(--text-primary); border: 1px solid var(--border); transition: all 0.3s var(--transition); text-align: center;
}
.quick-action:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--blue); }
.quick-action-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.quick-action-label { font-size: 14px; font-weight: 600; }

/* Tables */
.table-wrapper { background: var(--bg-secondary); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-sm); border: 1px solid var(--border); }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
thead { background: rgba(0,0,0,0.02); }
th { padding: 14px 20px; text-align: right; font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }
td { padding: 16px 20px; font-size: 14px; color: var(--text-primary); border-bottom: 1px solid var(--border); }
tbody tr { transition: background 0.15s; }
tbody tr:hover { background: rgba(0,0,0,0.02); }
tbody tr:last-child td { border-bottom: none; }

/* Badges */
.badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 980px; font-size: 12px; font-weight: 600; gap: 4px; }
.badge-success { background: rgba(52,199,89,0.12); color: #1f8a3d; }
.badge-danger { background: rgba(255,59,48,0.12); color: #c41e1e; }
.badge-warning { background: rgba(255,149,0,0.12); color: #b36b00; }
.badge-info { background: rgba(0,113,227,0.12); color: #0056b3; }
.badge-purple { background: rgba(175,82,222,0.12); color: #7a2fa0; }
.badge-secondary { background: rgba(142,142,147,0.12); color: #636366; }

/* Forms */
.form-card { background: var(--bg-secondary); border-radius: var(--radius-lg); padding: 32px; box-shadow: var(--shadow-sm); border: 1px solid var(--border); max-width: 600px; }
.form-group { margin-bottom: 20px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.form-input, .form-select {
    width: 100%; padding: 11px 14px; border: 1px solid rgba(0,0,0,0.1);
    border-radius: var(--radius-sm); font-size: 15px; font-family: inherit;
    background: var(--bg-primary); color: var(--text-primary); transition: all 0.2s var(--transition);
}
.form-input:focus, .form-select:focus { outline: none; border-color: var(--blue); background: white; box-shadow: 0 0 0 4px rgba(0,113,227,0.1); }
textarea.form-input { resize: vertical; min-height: 80px; }

/* File Upload */
.file-upload {
    border: 2px dashed rgba(0,0,0,0.15); border-radius: var(--radius-md);
    padding: 40px 20px; text-align: center; background: var(--bg-primary);
    transition: all 0.2s var(--transition); cursor: pointer;
}
.file-upload:hover { border-color: var(--blue); background: rgba(0,113,227,0.03); }
.file-upload-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }
.file-upload-text { font-size: 15px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
.file-upload-hint { font-size: 13px; color: var(--text-tertiary); }
.file-upload input[type="file"] { display: none; }

/* Alerts */
.alert { padding: 14px 18px; border-radius: var(--radius-sm); margin-bottom: 20px; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px; }
.alert-success { background: rgba(52,199,89,0.1); color: #1f8a3d; border: 1px solid rgba(52,199,89,0.2); }
.alert-danger { background: rgba(255,59,48,0.1); color: #c41e1e; border: 1px solid rgba(255,59,48,0.2); }
.alert-info { background: rgba(0,113,227,0.1); color: #0056b3; border: 1px solid rgba(0,113,227,0.2); }

/* Role Badge */
.role-badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 980px; font-size: 12px; font-weight: 600; }
.role-owner { background: linear-gradient(135deg, #f093fb, #f5576c); color: white; }
.role-admin { background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; }

/* Animations */
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.fade-in { animation: fadeIn 0.4s var(--transition) forwards; }

/* Empty State */
.empty-state { text-align: center; padding: 60px 20px; color: var(--text-tertiary); }
.empty-state-icon { font-size: 56px; margin-bottom: 16px; opacity: 0.4; }
.empty-state-title { font-size: 17px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.empty-state-desc { font-size: 14px; color: var(--text-secondary); }

/* Responsive */
@media (max-width: 900px) {
    .app-layout { grid-template-columns: 1fr; }
    .sidebar { position: fixed; right: -280px; top: 0; width: 260px; z-index: 100; transition: right 0.3s var(--transition); }
    .sidebar.open { right: 0; }
    .main-content { padding: 20px; }
    .page-title { font-size: 26px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.25); }

code { background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; font-family: 'SF Mono', Monaco, monospace; font-size: 13px; }
</style>
"""