import logging
from typing import Optional, Dict, Any
from aiogram import Dispatcher, Router
from aiogram.types import Message, CallbackQuery
from modul.core.bot_manager import BotManager

logger = logging.getLogger(__name__)


class HandlerManager:
    def __init__(self, bot_manager: BotManager, dp: Dispatcher):
        self.bot_manager = bot_manager
        self.dp = dp
        self.routers: Dict[str, Router] = {}

    async def setup_handlers(self):
        """Setup message and callback handlers"""
        try:
            # Setup routers
            main_router = Router()
            client_router = Router()

            # Add handlers
            main_router.message.register(self.message_handler)
            main_router.callback_query.register(self.callback_handler)

            # Include routers
            self.dp.include_router(main_router)
            self.dp.include_router(client_router)

        except Exception as e:
            logger.error(f"Error setting up handlers: {e}")
            raise

    async def message_handler(self, message: Message, **kwargs: Any):
        """Handle incoming messages"""
        try:
            # Get bot instance
            bot = self.bot_manager.get_bot(message.bot.token)

            # Process message
            await self.process_message(bot, message)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def callback_handler(self, query: CallbackQuery, **kwargs: Any):
        """Handle callback queries"""
        try:
            # Get bot instance
            bot = self.bot_manager.get_bot(query.bot.token)

            # Process callback
            await self.process_callback(bot, query)

        except Exception as e:
            logger.error(f"Error handling callback: {e}")