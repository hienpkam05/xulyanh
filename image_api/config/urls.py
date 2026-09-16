from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from images.views import health_check


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", health_check, name="health-check"),
    path("api/v1/", include("images.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

