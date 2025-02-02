from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.static import static

urlpatterns = [
    path('bot/', include('bot_api.urls')),
    path('admin/', admin.site.urls),
    path('', include('modul.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
