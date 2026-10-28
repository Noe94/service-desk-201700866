from django.urls import path

from apps.catalog import views


app_name = "catalog"


urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),

    path(
        "nivel-1/",
        views.n1_list,
        name="n1_list",
    ),
    path(
        "nivel-1/nuevo/",
        views.n1_create,
        name="n1_create",
    ),
    path(
        "nivel-1/<int:pk>/",
        views.n1_detail,
        name="n1_detail",
    ),
    path(
        "nivel-1/<int:pk>/editar/",
        views.n1_update,
        name="n1_update",
    ),
    path(
        "nivel-1/<int:pk>/estado/",
        views.n1_toggle,
        name="n1_toggle",
    ),

    path(
        "nivel-2/",
        views.n2_list,
        name="n2_list",
    ),
    path(
        "nivel-2/nuevo/",
        views.n2_create,
        name="n2_create",
    ),
    path(
        "nivel-2/<int:pk>/",
        views.n2_detail,
        name="n2_detail",
    ),
    path(
        "nivel-2/<int:pk>/editar/",
        views.n2_update,
        name="n2_update",
    ),
    path(
        "nivel-2/<int:pk>/estado/",
        views.n2_toggle,
        name="n2_toggle",
    ),

    path(
        "opciones/<str:option>/",
        views.option_list,
        name="option_list",
    ),
    path(
        "opciones/<str:option>/nuevo/",
        views.option_create,
        name="option_create",
    ),
    path(
        "opciones/<str:option>/<int:pk>/editar/",
        views.option_update,
        name="option_update",
    ),
    path(
        "opciones/<str:option>/<int:pk>/estado/",
        views.option_toggle,
        name="option_toggle",
    ),
]

