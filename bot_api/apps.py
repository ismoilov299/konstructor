from django.apps import AppConfig
from django.core.signals import request_started


class BotApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot_api'

    def ready(self, ):
        from . import views
        request_started.connect(views.startup_signal)
