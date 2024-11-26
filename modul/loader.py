# modul/loader.py
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
import logging
from typing import Dict, Optional
from modul.config import settings_conf
from aiohttp import ClientTimeout, TCPConnector
import sys

logger = logging.getLogger(__name__)

class BotSessionManager:
    _instance = None
    _initialized = False
    _loop = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.setup_loop()
            self._session = None
            self._bots: Dict[str, Bot] = {}
            self._dp = Dispatcher()
            self.initialize_session()
            self._initialized = True

    def setup_loop(self):
        """Setup event loop"""
        try:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        except Exception as e:
            logger.error(f"Error setting up event loop: {e}")
            raise

    def initialize_session(self):
        """Initialize bot session"""
        try:
            timeout = ClientTimeout(total=30)
            connector = TCPConnector(
                force_close=True,
                verify_ssl=False,
                loop=self._loop
            )
            self._session = AiohttpSession()
            self._session.timeout = timeout
            self._session.connector = connector
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            raise

    def get_bot(self, token: str) -> Bot:
        """Get or create bot instance"""
        try:
            if token not in self._bots:
                default = DefaultBotProperties(parse_mode="HTML")
                self._bots[token] = Bot(
                    token=token,
                    session=self._session,
                    default=default
                )
            return self._bots[token]
        except Exception as e:
            logger.error(f"Error getting bot: {e}")
            raise

    async def close(self):
        """Cleanup resources"""
        try:
            if hasattr(self, '_bots'):
                for bot in self._bots.values():
                    await bot.session.close()
                self._bots.clear()

            if self._session:
                await self._session.close()

            if self._loop and not self._loop.is_closed():
                self._loop.stop()
                self._loop.close()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    @property
    def session(self):
        return self._session

    @property
    def dispatcher(self):
        return self._dp

# Create instances only if not in test environment
if 'test' not in sys.argv:
    try:
        bot_manager = BotSessionManager()
        bot_session = bot_manager.session
        main_bot = bot_manager.get_bot(settings_conf.BOT_TOKEN)
        dp = bot_manager.dispatcher
        client_bot_router = Router()
        main_bot_router = Router()

    except Exception as e:
        logger.error(f"Failed to initialize bot components: {e}")
        raise