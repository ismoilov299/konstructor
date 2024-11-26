# bot_api/apps.py
from django.apps import AppConfig
import asyncio

class BotApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot_api'

    def ready(self):
        if asyncio._get_running_loop() is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)