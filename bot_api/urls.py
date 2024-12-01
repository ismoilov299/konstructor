from django.urls import path
from . import views

print("Loading bot_api URLs")
urlpatterns = [
    path('webhook/<str:token>/', views.telegram_webhook, name='telegram_webhook'),
]
