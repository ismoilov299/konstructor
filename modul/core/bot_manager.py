from contextlib import asynccontextmanager
import logging
from typing import Optional
import asyncio
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self._session: Optional[AiohttpSession] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bots = {}

    async def init(self):
        """Initialize bot manager"""
        self._session = AiohttpSession()
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    async def close(self):
        """Cleanup resources"""
        if self._session and not getattr(self._session, '_closed', False):
            await self._session.close()
        self._session = None
        for bot in self._bots.values():
            await bot.session.close()
        self._bots.clear()

    def get_bot(self, token: str) -> Optional[Bot]:
        """Get or create bot instance"""
        if token not in self._bots:
            self._bots[token] = Bot(token=token, session=self._session)
        return self._bots[token]

    @asynccontextmanager
    async def create_session(self):
        """Context manager for bot session"""
        if not self._session:
            await self.init()
        try:
            yield self._session
        finally:
            await self.close()

    @asynccontextmanager
    async def get_running_loop(self):
        """Context manager for event loop"""
        try:
            if self._loop and self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            yield self._loop
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()