import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN, LOG_LEVEL, USE_PROXY, PROXY_URL
from database import db
from handlers import user_router, admin_router, extra_router
from tasks import auto_backup, renewal_reminder, waitlist_notifier
import bot_instance


async def main():
    logging.basicConfig(level=getattr(logging, LOG_LEVEL),
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    await db.init()
    logging.info("✅ DB ready")
    
    if USE_PROXY:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        bot = Bot(token=BOT_TOKEN)
    
    bot_instance.set_bot(bot)
    logging.info("✅ Bot instance saved")
    
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(extra_router)
    dp.include_router(admin_router)
    
    from tasks import chat_cleanup
    tasks = [
        asyncio.create_task(auto_backup()),
        asyncio.create_task(renewal_reminder(bot)),
        asyncio.create_task(waitlist_notifier(bot)),
        asyncio.create_task(chat_cleanup(bot)),
    ]
    
    try:
        from dashboard import run_dashboard
        dashboard_task = asyncio.create_task(asyncio.to_thread(run_dashboard))
        tasks.append(dashboard_task)
        logging.info("🌐 Dashboard: http://localhost:8000")
    except Exception as e:
        logging.warning(f"Dashboard not started: {e}")
    
    logging.info("🚀 Bot started!")
    
    try:
        await dp.start_polling(bot)
    finally:
        logging.info("🛑 Shutting down...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()
        logging.info("✅ Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)