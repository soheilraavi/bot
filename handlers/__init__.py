from .user import router as user_router
from .admin import router as admin_router
from .extra import router as extra_router

__all__ = ["user_router", "admin_router", "extra_router"]