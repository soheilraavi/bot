"""توابع مشترک handlers"""

from database import db


async def get_msg(key, **kwargs):
    text = await db.get_message(key)
    if not text:
        return key
    try:
        return text.format(**kwargs)
    except Exception:
        return text


async def delete_user_message(message):
    try:
        await message.delete()
    except Exception:
        pass
