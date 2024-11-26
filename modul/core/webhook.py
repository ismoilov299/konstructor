import logging
from typing import Optional
import ssl
import aiohttp
from modul.core.bot_manager import BotManager

logger = logging.getLogger(__name__)


class WebhookManager:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager

    async def set_webhook(self, token: str, url: str, cert: Optional[str] = None):
        """Set webhook with SSL verification"""
        try:
            async with self.bot_manager.create_session() as session:
                bot = self.bot_manager.get_bot(token)

                # Setup SSL context
                ssl_context = ssl.create_default_context()
                if cert:
                    ssl_context.load_verify_locations(cert)

                # Set webhook
                webhook_info = await bot.get_webhook_info()
                if webhook_info.url != url:
                    await bot.delete_webhook()
                    await bot.set_webhook(
                        url=url,
                        certificate=cert,
                        allowed_updates=['message', 'edited_message', 'callback_query'],
                        drop_pending_updates=True
                    )
                    logger.info(f"Webhook set for bot {token} to {url}")

        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            raise