from aiogram.filters import Filter
from aiogram.types import Message
from aiogram import Bot

from modul.clientbot import shortcuts


class DavinciBotFilter(Filter):
    """Filter to check if davinci module is enabled for single module bot"""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "davinci")


class DavinciEnabledFilter(Filter):
    """Filter to check if davinci module is enabled (regardless of other modules)"""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return bool(bot_db.enable_davinci)
