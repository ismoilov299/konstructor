# bot_api/urls.py
from django.urls import path
from .views import telegram_webhook

urlpatterns = [
    path('webhook/<str:token>/', telegram_webhook, name='telegram_webhook'),
]
