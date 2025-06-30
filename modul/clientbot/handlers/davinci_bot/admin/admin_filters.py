from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

from modul.clientbot import shortcuts


class AdminFilter(Filter):
    """Filter for admin users"""

    async def __call__(self, update, bot: Bot) -> bool:
        if isinstance(update, (Message, CallbackQuery)):
            user_id = update.from_user.id
            # Check if user is admin (you can customize this logic)
            return await shortcuts.is_admin(user_id, bot)
        return False