from aiogram import Router
from .handlers import davinci_router

def register_davinci_handlers(router: Router):
    """Register all davinci bot handlers"""
    router.include_router(davinci_router)