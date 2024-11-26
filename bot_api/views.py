import asyncio
import logging
import time
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from contextlib import asynccontextmanager
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.dispatch import receiver
from django.core.signals import request_started
from asgiref.sync import async_to_sync
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties

from modul.loader import bot_session, dp, main_bot, client_bot_router, main_bot_router
from modul.bot.main_bot.main import init_bot_handlers
from modul.clientbot.handlers.annon_bot.handlers.admin import admin_panel
from modul.clientbot.handlers.annon_bot.handlers.bot import anon_bot_handlers
from modul.clientbot.handlers.chat_gpt_bot.handlers.main import chat_gpt_bot_handlers
from modul.clientbot.handlers.main import start_bot_client
from modul.helpers.filters import setup_main_bot_filter
from modul.clientbot.shortcuts import get_bot_by_token
from modul.config import scheduler, settings_conf

logger = logging.getLogger(__name__)
default = DefaultBotProperties(parse_mode="HTML")




def setup_routers():
    """Setup message routers and handlers"""
    if not hasattr(dp, 'routers_setup'):
        try:
            # Initialize all handlers
            chat_gpt_bot_handlers()
            start_bot_client()
            admin_panel()
            init_bot_handlers()
            anon_bot_handlers()

            # Setup filters and include routers
            setup_main_bot_filter(main_bot_router, client_bot_router)
            dp.include_router(main_bot_router)
            dp.include_router(client_bot_router)
            dp.routers_setup = True
            logger.info("Routers setup completed")
        except Exception as e:
            logger.error(f"Error setting up routers: {e}")
            raise


@asynccontextmanager
async def get_session():
    """Create new aiohttp session with timeout"""
    timeout = ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with ClientSession(timeout=timeout, connector=connector) as session:
        try:
            yield session
        finally:
            await session.close()

async def set_webhook(bot):
    """Set webhook for bot with proper session management"""
    try:
        webhook_url = settings_conf.WEBHOOK_URL.format(token=bot.token)
        logger.info(f"Setting webhook to: {webhook_url}")

        # Test webhook URL accessibility
        async with get_session() as session:
            try:
                async with session.get(webhook_url) as response:
                    if response.status != 200:
                        logger.error(f"Webhook URL test failed with status {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Failed to test webhook URL: {str(e)}")
                return False

        # Get current webhook info
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Current webhook: {webhook_info.url}")

        if webhook_info.url != webhook_url:
            # Delete old webhook
            await bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(1)

            # Set new webhook
            result = await bot.set_webhook(
                url=webhook_url,
                allowed_updates=settings_conf.USED_UPDATE_TYPES,
                max_connections=100,
                drop_pending_updates=True
            )

            if result:
                logger.info("Webhook set successfully")
                return True
            else:
                logger.error("Failed to set webhook")
                return False

        logger.info("Webhook already correctly set")
        return True

    except Exception as e:
        logger.error(f"Error in set_webhook: {str(e)}", exc_info=True)
        return False


async def telegram_webhook(request, token):
    """Handle webhook updates with proper session and error handling"""
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        # Parse update
        update = Update.parse_raw(request.body.decode())

        # Get bot instance
        if token == settings_conf.BOT_TOKEN:
            bot = main_bot
        else:
            bot = await get_bot_by_token(token)
            if not bot:
                logger.error(f"Bot not found for token {token}")
                return HttpResponse(status=404)

        # Process update
        async with bot.context() as bot:
            await dp.feed_raw_update(bot, update.dict())

        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Webhook handler error: {str(e)}", exc_info=True)
        return HttpResponse(status=500)


async def check_ngrok_url():
    """Verify ngrok URL is accessible"""
    try:
        webhook_base = settings_conf.WEBHOOK_HOST
        async with aiohttp.ClientSession() as session:
            async with session.get(webhook_base) as response:
                if response.status == 200:
                    logger.info("Ngrok URL is accessible")
                    return True
                else:
                    logger.error(f"Ngrok URL returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Failed to check ngrok URL: {str(e)}")
        return False

async def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL is accessible"""
    async with get_session() as session:
        try:
            async with session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to validate webhook URL: {str(e)}")
            return False

async def startup():
    """Initialize bot application with retry logic"""
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            logger.info(f"Startup attempt {attempt + 1}")

            # Setup routers
            setup_routers()

            # Setup webhook
            async with main_bot.context() as bot:
                success = await set_webhook(bot)
                if success:
                    logger.info("Bot startup completed successfully")
                    return

            logger.error("Failed to set webhook")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        except Exception as e:
            logger.error(f"Startup error: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise

@receiver(request_started)
def startup_signal(sender, **kwargs):
    """Handle application startup"""
    try:
        async_to_sync(startup)()
        logger.info("Bot application started")
    except Exception as e:
        logger.error(f"Failed to start bot application: {e}")


async def update_bot_settings(request):
    """Update bot settings endpoint"""
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        bot_token = request.POST.get('bot_token')
        module = request.POST.get('module')

        bot = await get_bot_by_token(bot_token)
        if not bot:
            return HttpResponse("Bot not found", status=400)

        # Reset all modules
        for mod in ['music', 'download', 'leo', 'chatgpt', 'horoscope',
                    'anon', 'sms', 'refs', 'kino']:
            setattr(bot, f'enable_{mod}', False)

        # Enable requested module
        enable_module = f'enable_{module}'
        if hasattr(bot, enable_module):
            setattr(bot, enable_module, True)
            await bot.save()
            return HttpResponse("Settings updated")

        return HttpResponse("Invalid module", status=400)
    except Exception as e:
        logger.error(f"Error updating bot settings: {e}", exc_info=True)
        return HttpResponse(status=500)


async def get_bot_info(request, id):
    """Get bot information endpoint"""
    try:
        bot = await get_bot_by_token(str(id))
        if not bot:
            return JsonResponse({'error': 'Bot not found'}, status=404)

        # Determine active module
        modules = ['leo', 'refs', 'kino', 'chatgpt', 'anon', 'download']
        active_module = 'no_module'

        for module in modules:
            if getattr(bot, f'enable_{module}', False):
                active_module = module
                break

        return JsonResponse({
            'token': bot.token,
            'module': active_module,
            'is_enabled': getattr(bot, 'bot_enable', True),
            'username': getattr(bot, 'username', '')
        })
    except Exception as e:
        logger.error(f"Error getting bot info: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

