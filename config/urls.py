from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("mesa/", include("apps.service_desk.urls")),
    path("cmdb/", include("apps.cmdb.urls")),

    path(
        "catalogo/",
        include("apps.catalog.urls"),
    ),

    path(
        "organizacion/",
        include("apps.organization.urls"),
    ),

    path(
        "",
        include("apps.accounts.urls"),
    ),
]
