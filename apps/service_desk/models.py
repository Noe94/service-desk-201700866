from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import F, Q


class Process(models.TextChoices):
    NEW_SERVICE = "NUEVOS_SERVICIOS", "Gestión de nuevos servicios"
    CHANGE = "CAMBIOS", "Gestión de cambios"
    INCIDENT = "INCIDENTES", "Gestión de incidentes"
    EVENT = "EVENTOS", "Gestión de eventos"
    PROBLEM = "PROBLEMAS", "Gestión de problemas"
    ACCESS = "ACCESOS", "Gestión de accesos"
    SERVICE = "SERVICIOS_TI", "Gestión de servicios de tecnología"


class TicketType(models.TextChoices):
    ACCESS = "SOLICITUD_ACCESO", "Solicitud de acceso"
    EVENT = "EVENTO", "Evento"
    INCIDENT = "INCIDENTE", "Incidente"
    CHANGE = "SOLICITUD_CAMBIO", "Solicitud de cambio"
    SERVICE = "REQUISICION_SERVICIO", "Requisición de servicio"
    PROBLEM = "PROBLEMA", "Problema"


PROCESS_TO_TYPE = {
    Process.NEW_SERVICE: TicketType.SERVICE,
    Process.CHANGE: TicketType.CHANGE,
    Process.INCIDENT: TicketType.INCIDENT,
    Process.EVENT: TicketType.EVENT,
    Process.PROBLEM: TicketType.PROBLEM,
    Process.ACCESS: TicketType.ACCESS,
    Process.SERVICE: TicketType.SERVICE,
}


class Queue(models.Model):
    class Ordering(models.TextChoices):
        PRIORITY_AGE = "PRIORIDAD_ANTIGUEDAD", "Prioridad y antigüedad"

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    process = models.CharField(max_length=32, choices=Process.choices)
    active = models.BooleanField(default=True)
    support_level = models.PositiveSmallIntegerField(default=1)
    ordering_rule = models.CharField(
        max_length=32, choices=Ordering.choices, default=Ordering.PRIORITY_AGE
    )
    first_response_target_minutes = models.PositiveIntegerField(default=240)
    resolution_target_minutes = models.PositiveIntegerField(default=1440)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["process", "code"]

    def clean(self):
        super().clean()
        if self.support_level > 4:
            raise ValidationError({"support_level": "El nivel debe estar entre 0 y 4."})
        if self.pk and not self.active and self.tickets.filter(closed_at__isnull=True).exists():
            raise ValidationError({"active": "Transfiera o cierre los tickets antes de desactivar la cola."})

    def __str__(self):
        return f"{self.code} - {self.name}"


class GrantFields(models.Model):
    can_view = models.BooleanField(default=False)
    can_attend = models.BooleanField(default=False)
    can_transfer = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)

    class Meta:
        abstract = True


class QueueRoleGrant(GrantFields):
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name="role_grants")
    role = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="desk_grants")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["queue", "role"], name="uq_queue_role_grant")]


class QueueUserGrant(GrantFields):
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name="user_grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="desk_grants")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["queue", "user"], name="uq_queue_user_grant")]


class Ticket(models.Model):
    class Priority(models.TextChoices):
        P1 = "P1", "P1 - Crítica"
        P2 = "P2", "P2 - Alta"
        P3 = "P3", "P3 - Media"
        P4 = "P4", "P4 - Baja"

    class Severity(models.TextChoices):
        HIGH = "ALTA", "Alta"
        MEDIUM = "MEDIA", "Media"
        LOW = "BAJA", "Baja"

    class Channel(models.TextChoices):
        WEB = "WEB", "Portal web"
        EMAIL = "CORREO", "Correo"
        PHONE = "TELEFONO", "Teléfono"
        IN_PERSON = "PRESENCIAL", "Presencial"
        OTHER = "OTRO", "Otro"

    number = models.CharField(max_length=30, unique=True, null=True, blank=True, editable=False)
    title = models.CharField(max_length=220)
    description = models.TextField()
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_tickets")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tickets")
    service = models.ForeignKey("catalog.ServicioNivel2", on_delete=models.PROTECT, related_name="desk_tickets")
    ticket_type = models.CharField(max_length=32, choices=TicketType.choices)
    process = models.CharField(max_length=32, choices=Process.choices)
    queue = models.ForeignKey(Queue, on_delete=models.PROTECT, related_name="tickets")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="assigned_tickets",
    )
    status = models.CharField(max_length=40)
    priority = models.CharField(max_length=2, choices=Priority.choices, default=Priority.P3)
    impact = models.CharField(max_length=8, choices=Severity.choices, default=Severity.MEDIUM)
    urgency = models.CharField(max_length=8, choices=Severity.choices, default=Severity.MEDIUM)
    channel = models.CharField(max_length=12, choices=Channel.choices, default=Channel.WEB)
    no_ci_reason = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    event_category = models.CharField(max_length=2, blank=True)
    incident_category = models.CharField(max_length=2, blank=True)
    estimated_interruption_minutes = models.PositiveIntegerField(null=True, blank=True)
    actual_interruption_minutes = models.PositiveIntegerField(null=True, blank=True)
    redundancy_available = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    paused_seconds = models.PositiveIntegerField(default=0)
    reopen_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["priority", "created_at", "pk"]
        indexes = [
            models.Index(fields=["process", "status", "created_at"]),
            models.Index(fields=["queue", "priority", "created_at"]),
            models.Index(fields=["requester", "created_at"]),
        ]

    @property
    def service_level_1(self):
        return self.service.nivel1

    def clean(self):
        super().clean()
        errors = {}
        if self.queue_id and self.queue.process != self.process:
            errors["queue"] = "La cola debe corresponder al proceso del ticket."
        if self.queue_id and not self.queue.active:
            errors["queue"] = "No se puede usar una cola inactiva."
        if self.service_id and self.service.activo is False:
            errors["service"] = "No se puede usar un servicio inactivo."
        if self.requester_id and not self.requester.is_active:
            errors["requester"] = "El solicitante está inactivo."
        if self.assignee_id and not self.assignee.is_active:
            errors["assignee"] = "El responsable está inactivo."
        if self.process and self.ticket_type != PROCESS_TO_TYPE.get(self.process):
            errors["ticket_type"] = "El tipo no corresponde al proceso seleccionado."
        if self.event_category and self.event_category not in {"E0", "E1", "E2", "E3"}:
            errors["event_category"] = "Categoría de evento inválida."
        if self.incident_category and self.incident_category not in {"I0", "I1", "I2", "I3", "I4", "I5", "I6"}:
            errors["incident_category"] = "Categoría de incidente inválida."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.number or 'Nuevo ticket'}: {self.title}"


class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ticket_actions")
    action = models.CharField(max_length=50)
    old_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("La bitácora es inmutable: registre una acción nueva.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("No se pueden eliminar registros de auditoría.")


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField()
    internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


def evidence_path(instance, filename):
    return f"desk/ticket_{instance.ticket_id}/{Path(filename).name}"


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="attachments")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(
        upload_to=evidence_path,
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "txt", "log"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.file and self.file.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "El adjunto supera el límite de 10 MiB."})


class TicketRelation(models.Model):
    class Type(models.TextChoices):
        RELATED = "RELACIONADO", "Relacionado"
        DUPLICATE = "DUPLICADO", "Duplicado"
        CAUSE = "CAUSA", "Causado por"

    source = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="out_relations")
    target = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="in_relations")
    relation_type = models.CharField(max_length=16, choices=Type.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "target", "relation_type"], name="uq_desk_ticket_relation"),
            models.CheckConstraint(condition=~Q(source=F("target")), name="ck_ticket_not_self"),
        ]

    def clean(self):
        if self.source_id and self.source_id == self.target_id:
            raise ValidationError("Un ticket no puede relacionarse consigo mismo.")


class TicketApproval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "APROBADO", "Aprobado"
        REJECTED = "RECHAZADO", "Rechazado"

    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="approvals")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.ticket_id and self.approver_id == self.ticket.requester_id:
            raise ValidationError("El solicitante no puede aprobar su propia solicitud.")


class EventIncident(models.Model):
    """Una sola incidencia por evento E2/E3; impide duplicados en reintentos."""

    event = models.OneToOneField(Ticket, on_delete=models.PROTECT, related_name="generated_incident")
    incident = models.OneToOneField(Ticket, on_delete=models.PROTECT, related_name="origin_event")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.event_id and self.event.process != Process.EVENT:
            raise ValidationError("El origen debe ser un evento.")
        if self.incident_id and self.incident.process != Process.INCIDENT:
            raise ValidationError("El destino debe ser un incidente.")


class DeskNotification(models.Model):
    """Aviso interno de prueba; no requiere credenciales ni correo externo."""

    event = models.OneToOneField(Ticket, on_delete=models.PROTECT, related_name="incident_notice")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField()
    channel = models.CharField(max_length=16, default="APLICACION")
    created_at = models.DateTimeField(auto_now_add=True)


class KnowledgeArticle(models.Model):
    title = models.CharField(max_length=180)
    question = models.CharField(max_length=255)
    answer = models.TextField()
    process = models.CharField(max_length=32, choices=Process.choices, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
