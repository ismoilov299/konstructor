import logging
from django.urls import path, re_path
from . import views

logger = logging.getLogger(__name__)

logger.debug("Loading bot_api URLs")
urlpatterns = [
    # re_path yordamida barcha belgilarni qabul qilamiz
    re_path(r'^webhook/(?P<token>[\w\-\.:]+)/?$', views.telegram_webhook, name='telegram_webhook'),
]