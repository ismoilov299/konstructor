from .handlers.bot import client_bot_router

# davinci_install funksiyasini alohida export qilamiz
async def davinci_install():
    """Davinci modulini o'rnatish"""
    print("✅ Davinci module installed successfully!")

__all__ = ["client_bot_router", "davinci_install"]