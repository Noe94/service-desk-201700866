from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    PROCESS_TO_TYPE, DeskNotification, EventIncident, Process, Queue, Ticket,
    TicketApproval, TicketComment, TicketHistory, TicketRelation,
)
from .permissions import can_create, can_view_ticket, is_admin, queue_allowed, require_queue
from .workflows import INITIAL_STATE, check_transition_requirements


class TicketConflict(ValidationError):
    """Regla de concurrencia o estado incumplida; la vista responderá HTTP 409."""


def log_action(ticket, actor, action, *, old=None, new=None, reason=""):
    TicketHistory.objects.create(
        ticket=ticket, actor=actor, action=action,
        old_values=old or {}, new_values=new or {}, reason=reason,
    )


@transaction.atomic
def create_ticket(*, actor, requester, service, queue, title, description,
                  priority, impact, urgency, channel, no_ci_reason, details=None,
                  event_category="", incident_category="", estimated_interruption_minutes=None,
                  redundancy_available=None):
    if not can_create(actor):
        raise PermissionDenied("No tiene permiso para crear tickets.")
    if actor.pk != requester.pk and not (is_admin(actor) or queue_allowed(actor, queue, "attend")):
        raise PermissionDenied("No puede crear tickets a nombre de otro usuario.")
    if not queue.active:
        raise ValidationError("La cola está inactiva.")
    if not no_ci_reason.strip():
        raise ValidationError("Documente por qué el ticket todavía no tiene CI asociado.")
    if queue.process == Process.EVENT and event_category not in {"E0", "E1", "E2", "E3"}:
        raise ValidationError("Indique la categoría E0-E3 del evento.")
    if queue.process == Process.INCIDENT and incident_category not in {
        "I0", "I1", "I2", "I3", "I4", "I5", "I6"
    }:
        raise ValidationError("Indique la categoría I0-I6 del incidente.")
    ticket = Ticket(
        requester=requester, creator=actor, service=service,
        queue=queue, process=queue.process, ticket_type=PROCESS_TO_TYPE[queue.process],
        status=INITIAL_STATE[queue.process], title=title, description=description,
        priority=priority, impact=impact, urgency=urgency, channel=channel,
        no_ci_reason=no_ci_reason, details=details or {},
        event_category=event_category, incident_category=incident_category,
        estimated_interruption_minutes=estimated_interruption_minutes,
        redundancy_available=redundancy_available,
    )
    ticket.full_clean()
    ticket.save()
    ticket.number = f"SD-{ticket.pk:07d}"
    ticket.save(update_fields=["number", "updated_at"])
    log_action(ticket, actor, "CREACION", new={
        "number": ticket.number, "queue": queue.code, "status": ticket.status,
        "requester": requester.pk, "service": service.codigo,
    })
    return ticket


@transaction.atomic
def update_ticket_details(ticket_id, actor, updates):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    require_queue(actor, ticket.queue, "attend")
    if ticket.closed_at:
        raise TicketConflict("No se puede modificar un ticket cerrado.")
    if ticket.assignee_id not in {None, actor.pk} and not is_admin(actor):
        raise PermissionDenied("Este ticket está asignado a otro agente.")
    old_data = ticket.details or {}
    from .forms import PROCESS_DETAIL_FIELDS
    allowed = set(PROCESS_DETAIL_FIELDS.get(ticket.process, {}))
    updated = {k: v for k, v in updates.items() if k in allowed}
    new_data = {**old_data, **updated}
    changes_old = {key: old_data.get(key) for key in updated if old_data.get(key) != new_data.get(key)}
    changes_new = {key: new_data.get(key) for key in changes_old}
    if changes_new:
        ticket.details = new_data
        ticket.save(update_fields=["details", "updated_at"])
        log_action(ticket, actor, "ACTUALIZACION_PROCESO", old=changes_old, new=changes_new)
    return ticket


@transaction.atomic
def claim_ticket(ticket_id, actor):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    require_queue(actor, ticket.queue, "attend")
    if ticket.closed_at is not None:
        raise TicketConflict("El ticket ya está cerrado.")
    if ticket.assignee_id is not None:
        raise TicketConflict("Otro agente ya tomó este ticket.")
    ticket.assignee = actor
    now = timezone.now()
    if ticket.first_response_at is None:
        ticket.first_response_at = now
    ticket.save(update_fields=["assignee", "first_response_at", "updated_at"])
    log_action(ticket, actor, "ASIGNACION", old={"assignee": None}, new={"assignee": actor.pk})
    return ticket


@transaction.atomic
def pause_ticket(ticket_id, actor, *, reason):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    require_queue(actor, ticket.queue, "attend")
    if ticket.closed_at or ticket.paused_at:
        raise TicketConflict("El ticket está cerrado o ya está en pausa.")
    if not reason.strip():
        raise ValidationError("Indique el motivo de la pausa.")
    ticket.paused_at = timezone.now()
    ticket.save(update_fields=["paused_at", "updated_at"])
    log_action(ticket, actor, "PAUSA", new={"paused_at": ticket.paused_at.isoformat()}, reason=reason)
    return ticket


@transaction.atomic
def resume_ticket(ticket_id, actor, *, reason):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    require_queue(actor, ticket.queue, "attend")
    if not ticket.paused_at:
        raise TicketConflict("El ticket no está en pausa.")
    if not reason.strip():
        raise ValidationError("Indique el motivo de reanudación.")
    seconds = int((timezone.now() - ticket.paused_at).total_seconds())
    ticket.paused_seconds += max(0, seconds)
    ticket.paused_at = None
    ticket.save(update_fields=["paused_seconds", "paused_at", "updated_at"])
    log_action(ticket, actor, "REANUDACION", new={"paused_seconds": ticket.paused_seconds}, reason=reason)
    return ticket


@transaction.atomic
def transfer_ticket(ticket_id, actor, destination, *, reason):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    require_queue(actor, ticket.queue, "transfer")
    if not reason.strip():
        raise ValidationError("Debe indicar el motivo de la transferencia.")
    if ticket.closed_at:
        raise TicketConflict("No puede transferirse un ticket cerrado.")
    if not destination.active or destination.process != ticket.process:
        raise ValidationError("La cola destino debe estar activa y pertenecer al mismo proceso.")
    if ticket.queue_id == destination.pk:
        raise ValidationError("La cola destino debe ser distinta.")
    previous_queue = ticket.queue.code
    previous_assignee = ticket.assignee_id
    ticket.queue = destination
    ticket.assignee = None
    ticket.save(update_fields=["queue", "assignee", "updated_at"])
    log_action(ticket, actor, "TRANSFERENCIA", old={
        "queue": previous_queue, "assignee": previous_assignee,
    }, new={"queue": destination.code, "assignee": None}, reason=reason)
    return ticket


def ensure_event_incident(event, actor):
    """Se invoca dentro de la transacción del evento, con fila bloqueada."""
    if event.event_category not in {"E2", "E3"}:
        return None
    link = EventIncident.objects.filter(event=event).select_related("incident").first()
    if link:
        return link.incident
    incident_queue = Queue.objects.filter(active=True, process=Process.INCIDENT).order_by("code").first()
    if incident_queue is None:
        raise ValidationError("Configure una cola activa de incidentes antes de responder E2/E3.")
    incident = Ticket(
        title=f"Incidente derivado de {event.number}: {event.title}"[:220],
        description=f"Evento {event.number} clasificado {event.event_category}. {event.description}",
        requester=event.requester, creator=actor, service=event.service,
        ticket_type=PROCESS_TO_TYPE[Process.INCIDENT], process=Process.INCIDENT,
        queue=incident_queue, status="REGISTRADO", priority=event.priority,
        impact=event.impact, urgency=event.urgency, channel=event.channel,
        no_ci_reason=event.no_ci_reason or "Evento sin CI asociado en el origen",
        incident_category="I6" if event.event_category == "E3" else "I1",
        details={"origen_evento": event.number, "interrupcion": event.description},
    )
    incident.full_clean()
    incident.save()
    incident.number = f"SD-{incident.pk:07d}"
    incident.save(update_fields=["number", "updated_at"])
    if event.cis.exists():
        incident.cis.add(*event.cis.all())
    EventIncident.objects.create(event=event, incident=incident)
    TicketRelation.objects.create(source=event, target=incident, relation_type=TicketRelation.Type.CAUSE)
    DeskNotification.objects.create(
        event=event, recipient=actor,
        message=f"Notificación de incidente: evento {event.number} ({event.event_category}) -> {incident.number}.",
    )
    log_action(event, actor, "INCIDENTE_DERIVADO", new={"incident": incident.number})
    log_action(incident, actor, "CREACION_POR_EVENTO", new={"event": event.number})
    return incident


@transaction.atomic
def transition_ticket(ticket_id, actor, destination, *, reason):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    if destination in {"APROBADO", "RECHAZADO"}:
        require_queue(actor, ticket.queue, "approve")
        if actor.pk == ticket.requester_id or actor.pk == ticket.creator_id:
            raise PermissionDenied("No se permite autoaprobación.")
        if not reason.strip():
            raise ValidationError("Toda aprobación o rechazo requiere un motivo.")
    else:
        require_queue(actor, ticket.queue, "attend")
    if ticket.assignee_id not in {None, actor.pk} and not is_admin(actor) and destination not in {"APROBADO", "RECHAZADO"}:
        raise PermissionDenied("El ticket está asignado a otro agente.")
    if ticket.paused_at:
        raise TicketConflict("Reanude el ticket antes de cambiar su estado.")
    if ticket.process == Process.EVENT and destination == "RESPONDIDO":
        ensure_event_incident(ticket, actor)
    check_transition_requirements(ticket, destination)
    previous = ticket.status
    if destination in {"APROBADO", "RECHAZADO"}:
        TicketApproval.objects.create(ticket=ticket, approver=actor, decision=destination, reason=reason)
    if destination == "RESUELTO":
        ticket.resolved_at = timezone.now()
    if destination == "CERRADO":
        if ticket.resolved_at is None:
            raise ValidationError("No puede cerrar un ticket sin resolución previa.")
        ticket.closed_at = timezone.now()
    ticket.status = destination
    ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
    log_action(ticket, actor, "TRANSICION", old={"status": previous},
               new={"status": destination}, reason=reason)
    return ticket


@transaction.atomic
def reopen_ticket(ticket_id, actor, *, reason):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    if not can_view_ticket(actor, ticket):
        raise PermissionDenied("No puede reabrir este ticket.")
    if actor.pk != ticket.requester_id and not queue_allowed(actor, ticket.queue, "attend"):
        raise PermissionDenied("No puede reabrir este ticket.")
    if not ticket.closed_at:
        raise TicketConflict("El ticket debe estar cerrado antes de reabrirse.")
    if timezone.now() - ticket.closed_at > timedelta(days=7):
        raise ValidationError("La reapertura se permite hasta siete días después del cierre.")
    if not reason.strip():
        raise ValidationError("Indique el motivo de reapertura.")
    old_status = ticket.status
    ticket.status = "REABIERTO"
    ticket.reopen_count += 1
    ticket.closed_at = None
    ticket.resolved_at = None
    ticket.assignee = None
    ticket.save(update_fields=["status", "reopen_count", "closed_at", "resolved_at", "assignee", "updated_at"])
    log_action(ticket, actor, "REAPERTURA", old={"status": old_status},
               new={"status": "REABIERTO", "reopen_count": ticket.reopen_count}, reason=reason)
    return ticket


@transaction.atomic
def add_comment(ticket_id, actor, text, *, internal=False):
    ticket = Ticket.objects.select_for_update().select_related("queue").get(pk=ticket_id)
    if not can_view_ticket(actor, ticket):
        raise PermissionDenied("No puede comentar este ticket.")
    if internal and not queue_allowed(actor, ticket.queue, "attend"):
        raise PermissionDenied("Las notas internas son exclusivas de los agentes autorizados.")
    if not text.strip():
        raise ValidationError("El comentario no puede estar vacío.")
    comment = TicketComment.objects.create(ticket=ticket, author=actor, text=text, internal=internal)
    log_action(ticket, actor, "NOTA_INTERNA" if internal else "COMENTARIO",
               new={"comment_id": comment.pk, "internal": internal})
    return comment
