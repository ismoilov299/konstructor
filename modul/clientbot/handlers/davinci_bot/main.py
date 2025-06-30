from aiogram import Router
from .handlers.bot import davinci_router
from .admin.admin_handlers import admin_davinci_router


def register_davinci_handlers(main_router: Router):
    """
    Register all Davinci bot handlers with the main router

    Args:
        main_router: The main bot router
    """
    # Register user handlers
    main_router.include_router(davinci_router)

    # Register admin handlers
    main_router.include_router(admin_davinci_router)