import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
import logging
from typing import Dict, Optional
from modul.config import settings_conf

logger = logging.getLogger(__name__)


class BotSessionManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._session = AiohttpSession()
            self._bots: Dict[str, Bot] = {}
            self._dp = Dispatcher()
            self._loop: Optional[asyncio.AbstractEventLoop] = None
            self._initialized = True

    def setup_loop(self):
        try:
            # Get existing loop or create new one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # If loop is closed, create new one
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._loop = loop
            return loop
        except Exception as e:
            logger.error(f"Error setting up event loop: {e}")
            raise

    def get_bot(self, token: str) -> Bot:
        if token not in self._bots:
            self._bots[token] = Bot(token=token, session=self._session)
        return self._bots[token]

    async def close(self):
        try:
            # Close bot sessions
            for bot in self._bots.values():
                await bot.session.close()
            self._bots.clear()

            # Close main session
            if self._session and not getattr(self._session, '_closed', False):
                await self._session.close()

            # Close loop
            if self._loop and not self._loop.is_closed():
                self._loop.close()
        except Exception as e:
            logger.error(f"Error closing bot session: {e}")

    @property
    def dispatcher(self):
        return self._dp

    def run_async(self, coro):
        """Safely run coroutine in the event loop"""
        try:
            loop = self.setup_loop()
            if loop.is_running():
                return asyncio.create_task(coro)
            return loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Error running async task: {e}")
            raise


# Create single instance
bot_session = BotSessionManager()

# Create main bot instance
main_bot = bot_session.get_bot(settings_conf.BOT_TOKEN)
dp = bot_session.dispatcher

# Create routers
client_bot_router = Router()
main_bot_router = Router()