# library/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # removed api-auth/ here — it's now handled inside api/urls.py at auth/browse/
]