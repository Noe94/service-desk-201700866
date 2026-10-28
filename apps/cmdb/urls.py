from django.urls import path

from . import views

app_name = "cmdb"

urlpatterns = [
    path("", views.ci_list, name="list"),
    path("ci/nuevo/", views.ci_edit, name="create"),
    path("ci/<int:pk>/", views.ci_detail, name="detail"),
    path("ci/<int:pk>/editar/", views.ci_edit, name="edit"),
    path("ci/<int:pk>/relaciones/", views.relation_add, name="relation_add"),
    path("clasificacion/nueva/", views.class_edit, name="class_create"),
    path("clasificacion/<int:pk>/editar/", views.class_edit, name="class_edit"),
    path("ubicacion/nueva/", views.location_edit, name="location_create"),
    path("ubicacion/<int:pk>/editar/", views.location_edit, name="location_edit"),
    path("ticket/<int:ticket_pk>/asociar/", views.ticket_ci_add, name="ticket_ci_add"),
]
