import asyncio

# Create your views here.
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.dispatch import receiver
from django.core.signals import request_started
from asgiref.sync import async_to_sync
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

from modul import models
from modul.bot.main_bot.main import init_bot_handlers
from modul.clientbot.handlers.admin.universal_admin import admin_panel
from modul.clientbot.handlers.annon_bot.handlers.admin import anon_admin_panel
# from modul.clientbot.handlers.annon_bot.handlers.admin import admin_panel
from modul.clientbot.handlers.annon_bot.handlers.bot import anon_bot_handlers
from modul.clientbot.handlers.chat_gpt_bot.handlers.main import chat_gpt_bot_handlers
# from modul.clientbot.handlers.davinci_bot.handlers.bot import davinchi_bot_handlers
# from modul.clientbot.handlers.main import start_bot_client
# from modul.clientbot.handlers.main import start_client_bot

from modul.clientbot.shortcuts import get_bot_by_token
from modul.config import scheduler, settings_conf
from modul.helpers.filters import setup_main_bot_filter
from modul.loader import dp, main_bot_router, client_bot_router, bot_session, main_bot
import tracemalloc

tracemalloc.start()

print(scheduler.print_jobs())
default = DefaultBotProperties(parse_mode="HTML")

import logging
import time

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def setup_routers():
    logger.info("Setting up routers")
    if not hasattr(dp, 'routers_setup'):
        try:
            if hasattr(dp, 'sub_routers'):
                dp.sub_routers.clear()

            # Handler'larni sozlash
            anon_admin_panel()
            anon_bot_handlers()
            admin_panel()
            chat_gpt_bot_handlers()
            init_bot_handlers()
            # davinchi_bot_handlers()
            setup_main_bot_filter(main_bot_router, client_bot_router)

            if main_bot_router not in dp.sub_routers:
                dp.include_router(main_bot_router)
            if client_bot_router not in dp.sub_routers:
                dp.include_router(client_bot_router)

            dp.routers_setup = True
            logger.info("Router setup completed successfully")
        except Exception as e:
            logger.error(f"Error in router setup: {e}")
            raise


@csrf_exempt
def telegram_webhook(request, token):
    start_time = time.time()
    logger.info(f"Received webhook for token: {token}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.path}")

    if request.method == 'POST':
        try:
            update_data = request.body.decode()
            logger.info(f"Update data: {update_data}")

            if token == settings_conf.BOT_TOKEN:
                logger.info("Processing main bot webhook")
                update = Update.parse_raw(update_data)
                async_to_sync(feed_update)(token, update.dict())
                return HttpResponse(status=200)

            bot = async_to_sync(get_bot_by_token)(token)
            logger.info(f"Bot lookup result: {bot}")

            if bot:
                logger.info(f"Processing client bot webhook: {bot.username}")
                update = Update.parse_raw(update_data)
                async_to_sync(feed_update)(token, update.dict())
                return HttpResponse(status=200)

            logger.warning(f"Unknown bot token: {token}")
            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            return HttpResponse(status=200)

    return HttpResponse(status=200)



async def feed_update(token, update):
    # logger.info(f"Received update: {update}")
    start_time = time.time()
    logger.info(f"Processing update for token: {token}")
    # logger.info(f"Update content: {update}")  # debug uchun
    try:
        async with Bot(token, bot_session, default=default).context(auto_close=False) as bot_:
            await dp.feed_raw_update(bot_, update)
            logger.info("Update successfully processed by dispatcher")
        end_time = time.time()
        logger.info(f"Update processed in {end_time - start_time:.4f} seconds")
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)


@receiver(request_started)
def startup_signal(sender, **kwargs):
    logger.info("Application startup signal received")
    async_to_sync(startup)()


async def startup():
    logger.info("Application startup initiated")
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        await setup_routers()  # To'g'ridan-to'g'ri await qilamiz
        await set_webhook()
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)


def shutdown():
    logger.info("Application shutdown initiated")
    if hasattr(bot_session, 'close'):
        async_to_sync(bot_session.close)()
    scheduler.remove_all_jobs()
    scheduler.shutdown()
    logger.info("Application shutdown completed")


async def set_webhook():
    logger.info("Setting webhook")
    try:
        webhook_url = settings_conf.WEBHOOK_URL.format(token=main_bot.token)
        logger.info(f"Setting webhook URL to: {webhook_url}")

        webhook_info = await main_bot.get_webhook_info()
        logger.info(f"Current webhook info: {webhook_info}")

        if webhook_info.url != webhook_url:
            logger.info("Setting new webhook URL...")
            result = await main_bot.set_webhook(
                webhook_url,
                allowed_updates=settings_conf.USED_UPDATE_TYPES
            )
            logger.info(f"Webhook set result: {result}")
        else:
            logger.info("Webhook URL already correct")

    except Exception as e:
        logger.error(f"Error setting webhook: {e}", exc_info=True)



# from aiogram import Bot, Dispatcher
# async def set_webhook():
#     logger.info("Setting webhook")
#     try:
#         # Ensure webhook URL ends with slash
#         webhook_url = settings_conf.WEBHOOK_URL.format(token=main_bot.token)
#         if not webhook_url.endswith('/'):
#             webhook_url += '/'
#
#         webhook_info = await main_bot.get_webhook_info()
#         if webhook_info.url != webhook_url:
#             await main_bot.set_webhook(webhook_url, allowed_updates=settings_conf.USED_UPDATE_TYPES)
#             logger.info(f"Webhook set to {webhook_url}")
#         else:
#             logger.info("Webhook already set correctly")
#     except RuntimeError as e:
#         if str(e) == "Event loop is closed":
#             logger.warning("Event loop was closed, creating a new one")
#             asyncio.set_event_loop(asyncio.new_event_loop())
#         else:
#             logger.error(f"Error setting webhook: {e}", exc_info=True)
