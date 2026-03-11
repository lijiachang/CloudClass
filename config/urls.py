from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("courses/", include("courses.urls")),
    path("resources/", include("resources.urls")),
    path("assignments/", include("assignments.urls")),
    path("discussions/", include("discussions.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
