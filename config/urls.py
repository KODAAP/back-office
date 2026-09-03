from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import permissions

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

admin_url = getattr(settings, "ADMIN_URL", None) or "admin/"

schema_view = get_schema_view(
    openapi.Info(
        title=" Koda API",
        default_version="v1",
        description="Data management API",
        contact=openapi.Contact(email="ekue.ayi@kodaap.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path(admin_url, admin.site.urls),
    path("api/v1/auth/", include("djoser.urls")),
    path("api/v1/auth/", include("core_apps.users.urls")),
    path("api/v1/invitations/", include("core_apps.invitations.urls")),
    path("api/v1/profiles/", include("core_apps.profiles.urls")),
    path("api/v1/projects/", include("core_apps.projects.urls")),
    path("api/v1/odk/", include("core_apps.odk.urls")),
]

admin.site.site_header = "Kodaap"
admin.site.site_title = "Koda Admin Portal"
admin.site.index_title = "Welcome to Koda Survey App"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
