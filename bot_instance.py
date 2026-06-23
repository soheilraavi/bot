"""
ماژول اشتراکی برای نگهداری instance ربات و event loop
"""

import asyncio
import threading

_bot = None
_loop = None
_lock = threading.Lock()


def set_bot(bot_instance):
    """ذخیره bot و event loop اصلی"""
    global _bot, _loop
    with _lock:
        _bot = bot_instance
        # ✅ استفاده از running loop به جای get_event_loop
        try:
            _loop = asyncio.get_running_loop()
        except RuntimeError:
            _loop = asyncio.get_event_loop()


def get_bot():
    """دریافت bot"""
    return _bot


def get_loop():
    """دریافت event loop"""
    return _loop


def send_message_sync(chat_id: int, text: str, **kwargs):
    """✅ ارسال پیام به صورت sync از thread دیگر"""
    if not _bot:
        raise Exception("Bot not initialized")
    
    if not _loop:
        raise Exception("Event loop not initialized")
    
    # ✅ اجرای coroutine در event loop اصلی
    future = asyncio.run_coroutine_threadsafe(
        _bot.send_message(chat_id, text, **kwargs),
        _loop
    )
    
    # ✅ منتظر نتیجه با timeout
    try:
        return future.result(timeout=30)
    except asyncio.TimeoutError:
        raise Exception("Timeout sending message")
    except Exception as e:
        raise Exception(f"Error sending message: {e}")


def get_file_sync(file_id: str):
    """✅ دریافت فایل به صورت sync از thread دیگر"""
    if not _bot:
        raise Exception("Bot not initialized")
    
    if not _loop:
        raise Exception("Event loop not initialized")
    
    future = asyncio.run_coroutine_threadsafe(
        _bot.get_file(file_id),
        _loop
    )
    
    try:
        return future.result(timeout=30)
    except asyncio.TimeoutError:
        raise Exception("Timeout getting file")
    except Exception as e:
        raise Exception(f"Error getting file: {e}")