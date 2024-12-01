# bot_api/urls.py
from django.urls import path

from . import views
from .views import telegram_webhook


urlpatterns = [
    # /webhook/ emas, /bot/webhook/ bo'lishi kerak
    path('bot/webhook/<str:token>/', views.process_webhook, name='webhook'),
]