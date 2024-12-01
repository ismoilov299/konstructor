from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.static import static


from django.urls import path

from bot_api import views

# from . import views       .

from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.static import static

urlpatterns = [
    path('', include('bot_api.urls')),  # bot/ prefiksini olib tashladik

    path('bot/webhook/<str:token>/', views.process_webhook, name='webhook'),  # slash qo'shilgan


    path('admin/', admin.site.urls),
    path('', include('modul.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# urlpatterns = [
#     path('bot', include('bot_api.urls')),
#     path('admin/', admin.site.urls),
#     path('', include('modul.urls')),
#    path('bot/', include('bot_api.urls'))
# ]

#if settings.DEBUG:
#    import debug_toolbar
#    urlpatterns = [
#        path('__debug__/', include(debug_toolbar.urls)),
#    ] + urlpatterns

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
