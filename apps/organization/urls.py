from django.urls import path

from apps.organization import views


app_name = "organization"


urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),
    path(
        "<str:entity>/",
        views.entity_list,
        name="list",
    ),
    path(
        "<str:entity>/nuevo/",
        views.entity_create,
        name="create",
    ),
    path(
        "<str:entity>/<int:pk>/editar/",
        views.entity_update,
        name="update",
    ),
    path(
        "<str:entity>/<int:pk>/estado/",
        views.entity_toggle,
        name="toggle",
    ),
]
