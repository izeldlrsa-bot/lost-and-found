"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("items.urls")),
]

# Serve media files — in production WhiteNoise handles static, but media
# still needs Django to serve from MEDIA_ROOT (or use a cloud storage backend).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
