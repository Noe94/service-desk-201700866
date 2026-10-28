from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import QueueRoleGrant, QueueUserGrant, Ticket


def is_admin(user):
    return bool(user.is_authenticated and user.is_active and user.rol == "ADMIN")


def is_readonly(user):
    # Pertenecer a una cola nunca convierte al rol CONSULTA en agente.
    return not user.is_authenticated or not user.is_active or user.rol == "CONSULTA"


def can_create(user):
    return is_admin(user) or (
        not is_readonly(user)
        and user.groups.filter(name__in=["SOLICITANTE", "AGENTE"]).exists()
    )


ACTION_FIELDS = {
    "view": "can_view",
    "attend": "can_attend",
    "transfer": "can_transfer",
    "approve": "can_approve",
    "manage": "can_manage",
}


def queue_allowed(user, queue, action):
    if is_admin(user):
        return True
    if is_readonly(user) or not queue.active:
        return False
    flag = ACTION_FIELDS.get(action)
    if flag is None:
        raise ValueError("Permiso de cola desconocido")
    roles = QueueRoleGrant.objects.filter(queue=queue, role__user=user, **{flag: True}).exists()
    direct = QueueUserGrant.objects.filter(queue=queue, user=user, **{flag: True}).exists()
    return roles or direct


def can_view_ticket(user, ticket):
    return bool(
        user.is_authenticated and user.is_active
        and (is_admin(user) or ticket.requester_id == user.pk or queue_allowed(user, ticket.queue, "view"))
    )


def accessible_tickets(user):
    if not user.is_authenticated or not user.is_active:
        return Ticket.objects.none()
    if is_admin(user):
        return Ticket.objects.all()
    permitted_queue_ids = set()
    if not is_readonly(user):
        permitted_queue_ids.update(
            QueueRoleGrant.objects.filter(role__user=user, can_view=True, queue__active=True)
            .values_list("queue_id", flat=True)
        )
        permitted_queue_ids.update(
            QueueUserGrant.objects.filter(user=user, can_view=True, queue__active=True)
            .values_list("queue_id", flat=True)
        )
    return Ticket.objects.filter(
        Q(requester=user) | Q(queue_id__in=permitted_queue_ids)
    ).distinct()


def require_ticket_access(user, ticket):
    if not can_view_ticket(user, ticket):
        raise PermissionDenied("No está autorizado para consultar este ticket.")


def require_queue(user, queue, action):
    if not queue_allowed(user, queue, action):
        raise PermissionDenied(f"No tiene permiso para {action} en esta cola.")
