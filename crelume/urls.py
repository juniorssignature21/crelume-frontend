"""Root URL configuration for Crelume."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Crelume administration"
admin.site.site_title = "Crelume admin"
admin.site.index_title = "Manage events, orders and tickets"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("events/", include("events.urls")),
    path("", include("orders.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"
