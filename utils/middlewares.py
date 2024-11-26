from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram.utils.i18n import gettext as _
from aiogram import BaseMiddleware, types
from aiogram.dispatcher.flags.getter import get_flag
from aiogram.types import TelegramObject, User, CallbackQuery
from aiolimiter import AsyncLimiter
from config import settings, DEBUG

from modul.loader import client_bot_router


class ThrottlingMiddleware:
    def __init__(self, rate_limit=0.5):  # 0.5 sekund interval
        self.rate_limit = rate_limit
        self.last_request = {}

    async def __call__(self, message: types.Message, handler):
        user_id = message.from_user.id
        current_time = datetime.now().timestamp()

        if user_id in self.last_request:
            time_passed = current_time - self.last_request[user_id]
            if time_passed < self.rate_limit:
                return

        self.last_request[user_id] = current_time
        return await handler(message)


# Middleware ni routerga qo'shamiz
client_bot_router.message.middleware(ThrottlingMiddleware())
