from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.catalog.models import ServicioNivel2

from .models import Process, Queue, QueueRoleGrant, QueueUserGrant, Ticket
from .workflows import valid_destinations


# Campos visibles y datos específicos: cada proceso tiene su propio expediente.
PROCESS_DETAIL_FIELDS = {
    Process.NEW_SERVICE: {
        "necesidad": "Necesidad de negocio", "viabilidad": "Análisis de viabilidad",
        "servicio_propuesto": "Servicio propuesto o código a vincular",
        "resolucion": "Resultado de implementación / resolución",
    },
    Process.CHANGE: {
        "evaluacion_impacto": "Evaluación de impacto", "evaluacion_riesgo": "Evaluación de riesgo",
        "plan_pruebas": "Plan de pruebas", "plan_reversion": "Plan de reversión",
        "ci_afectados": "CI afectados (se vincularán a CMDB)",
        "resolucion": "Resultado de validación / resolución",
    },
    Process.INCIDENT: {
        "interrupcion": "Interrupción o degradación", "diagnostico": "Diagnóstico",
        "solucion": "Solución aplicada", "resolucion": "Detalle de resolución",
    },
    Process.EVENT: {
        "origen_evento": "Origen / clave externa del evento",
        "evaluacion": "Evaluación del evento",
        "incidente_vinculado": "Incidente vinculado (número)",
        "notificacion_registrada": "Evidencia de notificación",
        "resolucion": "Resultado de respuesta",
    },
    Process.PROBLEM: {
        "incidentes": "Incidentes relacionados", "causa_raiz": "Investigación de causa raíz",
        "solucion_temporal": "Solución temporal", "error_conocido": "Error conocido",
        "cambio_correctivo": "Cambio correctivo relacionado",
        "resolucion": "Solución definitiva / resolución",
    },
    Process.ACCESS: {
        "beneficiario": "Usuario beneficiario", "recurso": "Recurso o servicio",
        "permiso": "Permiso solicitado", "operacion": "Provisión o revocación",
        "resolucion": "Validación del acceso / resolución",
    },
    Process.SERVICE: {
        "solicitud": "Detalle de la requisición", "validacion": "Validación",
        "cumplimiento": "Evidencia de cumplimiento",
        "resolucion": "Confirmación y resolución",
    },
}


class TicketCreateForm(forms.Form):
    title = forms.CharField(label="Título", max_length=220)
    description = forms.CharField(label="Descripción", widget=forms.Textarea(attrs={"rows": 4}))
    requester = forms.ModelChoiceField(label="Solicitante", queryset=get_user_model().objects.none())
    service = forms.ModelChoiceField(label="Servicio nivel 2", queryset=ServicioNivel2.objects.none())
    queue = forms.ModelChoiceField(label="Cola", queryset=Queue.objects.none())
    priority = forms.ChoiceField(label="Prioridad", choices=Ticket.Priority.choices, initial=Ticket.Priority.P3)
    impact = forms.ChoiceField(label="Impacto", choices=Ticket.Severity.choices)
    urgency = forms.ChoiceField(label="Urgencia", choices=Ticket.Severity.choices)
    channel = forms.ChoiceField(label="Canal", choices=Ticket.Channel.choices)
    no_ci_reason = forms.CharField(
        label="Motivo por el que todavía no se asocia un CI", max_length=255,
        help_text="Después podrá vincular dispositivos afectados desde CMDB.",
    )

    def __init__(self, *args, process=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = process
        if actor is not None:
            self.fields["requester"].queryset = get_user_model().objects.filter(is_active=True)
            self.fields["requester"].initial = actor
        self.fields["service"].queryset = ServicioNivel2.objects.exclude(activo=False).select_related("nivel1")
        self.fields["queue"].queryset = Queue.objects.filter(active=True, process=process)
        if process == Process.EVENT:
            self.fields["event_category"] = forms.ChoiceField(
                label="Categoría del evento", choices=[(f"E{i}", f"E{i}") for i in range(4)]
            )
        if process == Process.INCIDENT:
            self.fields["incident_category"] = forms.ChoiceField(
                label="Categoría del incidente", choices=[(f"I{i}", f"I{i}") for i in range(7)]
            )
            self.fields["estimated_interruption_minutes"] = forms.IntegerField(
                label="Minutos estimados de afectación", min_value=0, required=False,
            )
            self.fields["redundancy_available"] = forms.NullBooleanField(
                label="¿Existe redundancia?", required=False,
            )
        for field_name, label in PROCESS_DETAIL_FIELDS.get(process, {}).items():
            self.fields[field_name] = forms.CharField(
                label=label, required=False, widget=forms.Textarea(attrs={"rows": 2})
            )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def process_details(self):
        return {
            name: self.cleaned_data[name]
            for name in PROCESS_DETAIL_FIELDS.get(self.process, {})
            if self.cleaned_data.get(name)
        }


class TicketDetailsForm(forms.Form):
    def __init__(self, *args, ticket, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket = ticket
        for name, label in PROCESS_DETAIL_FIELDS.get(ticket.process, {}).items():
            self.fields[name] = forms.CharField(
                label=label, required=False, initial=ticket.details.get(name, ""),
                widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            )


class TransitionForm(forms.Form):
    destination = forms.ChoiceField(label="Nuevo estado")
    reason = forms.CharField(label="Motivo / evidencia", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, ticket, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination"].choices = [(s, s.replace("_", " ").title()) for s in valid_destinations(ticket)]


class TransferForm(forms.Form):
    destination = forms.ModelChoiceField(label="Cola destino", queryset=Queue.objects.none())
    reason = forms.CharField(label="Motivo de transferencia", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, ticket, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination"].queryset = Queue.objects.filter(
            active=True, process=ticket.process
        ).exclude(pk=ticket.queue_id)


class CommentForm(forms.Form):
    text = forms.CharField(label="Comentario", widget=forms.Textarea(attrs={"rows": 3}))
    internal = forms.BooleanField(label="Nota interna", required=False)


class QueueForm(forms.ModelForm):
    class Meta:
        model = Queue
        fields = [
            "code", "name", "description", "process", "active", "support_level",
            "ordering_rule", "first_response_target_minutes", "resolution_target_minutes",
        ]


class QueueRoleGrantForm(forms.ModelForm):
    class Meta:
        model = QueueRoleGrant
        fields = ["role", "can_view", "can_attend", "can_transfer", "can_approve", "can_manage"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Group.objects.filter(name__in=["SOLICITANTE", "AGENTE", "APROBADOR"])


class QueueUserGrantForm(forms.ModelForm):
    class Meta:
        model = QueueUserGrant
        fields = ["user", "can_view", "can_attend", "can_transfer", "can_approve", "can_manage"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(is_active=True).exclude(rol="CONSULTA")
