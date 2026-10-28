from django.urls import path

from apps.accounts.views import (
    LocalLoginView,
    LocalLogoutView,
    dashboard,
    user_create,
    user_list,
    user_toggle,
    user_update,
)


app_name = "accounts"


urlpatterns = [
    path(
        "login/",
        LocalLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LocalLogoutView.as_view(),
        name="logout",
    ),
    path(
        "usuarios/",
        user_list,
        name="user_list",
    ),
    path(
        "usuarios/nuevo/",
        user_create,
        name="user_create",
    ),
    path(
        "usuarios/<int:pk>/editar/",
        user_update,
        name="user_update",
    ),
    path(
        "usuarios/<int:pk>/estado/",
        user_toggle,
        name="user_toggle",
    ),
    path(
        "",
        dashboard,
        name="dashboard",
    ),
]
