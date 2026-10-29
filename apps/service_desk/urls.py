from django.urls import path

from . import views

app_name = "service_desk"

urlpatterns = [
    path("", views.ticket_list, name="tickets"),
    path("tablero/", views.dashboard, name="dashboard"),
    path("conocimiento/", views.knowledge_base, name="knowledge"),
    path("tickets/nuevo/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/servicio-aprobado/", views.ticket_service_link, name="ticket_service_link"),
    path("tickets/<int:pk>/relacionar/", views.ticket_relation_add, name="ticket_relation_add"),
    path("tickets/<int:pk>/tomar/", views.ticket_claim, name="ticket_claim"),
    path("tickets/<int:pk>/transferir/", views.ticket_transfer, name="ticket_transfer"),
    path("tickets/<int:pk>/transicion/", views.ticket_transition, name="ticket_transition"),
    path("tickets/<int:pk>/reabrir/", views.ticket_reopen, name="ticket_reopen"),
    path("tickets/<int:pk>/comentario/", views.ticket_comment, name="ticket_comment"),
    path("tickets/<int:pk>/datos/", views.ticket_details_update, name="ticket_details_update"),
    path("tickets/<int:pk>/pausar/", views.ticket_pause, name="ticket_pause"),
    path("tickets/<int:pk>/reanudar/", views.ticket_resume, name="ticket_resume"),
    path("tickets/<int:pk>/adjunto/", views.ticket_attachment_upload, name="ticket_attachment_upload"),
    path("adjuntos/<int:pk>/descargar/", views.ticket_attachment_download, name="ticket_attachment_download"),
    path("colas/", views.queue_list, name="queues"),
    path("colas/nueva/", views.queue_create, name="queue_create"),
    path("colas/<int:pk>/editar/", views.queue_edit, name="queue_edit"),
    path("colas/<int:pk>/rol/", views.queue_role_grant, name="queue_role_grant"),
    path("colas/<int:pk>/usuario/", views.queue_user_grant, name="queue_user_grant"),
]
