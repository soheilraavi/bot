from aiogram.filters import Filter
from database import db


class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        return await db.is_admin(event.from_user.id)


class IsOwner(Filter):
    async def __call__(self, event) -> bool:
        return await db.is_owner(event.from_user.id)