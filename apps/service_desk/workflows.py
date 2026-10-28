from django.core.exceptions import ValidationError

from .models import Process


# Flujos diferenciados: cada proceso conserva sus pasos y controles de salida.
STEPS = {
    Process.NEW_SERVICE: {
        "SOLICITADO": ["ANALISIS"],
        "ANALISIS": ["PENDIENTE_APROBACION"],
        "PENDIENTE_APROBACION": ["APROBADO", "RECHAZADO"],
        "APROBADO": ["IMPLEMENTACION"],
        "IMPLEMENTACION": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "RECHAZADO": ["RESUELTO"],
        "REABIERTO": ["ANALISIS"],
    },
    Process.CHANGE: {
        "SOLICITADO": ["EVALUACION"],
        "EVALUACION": ["PENDIENTE_APROBACION"],
        "PENDIENTE_APROBACION": ["APROBADO", "RECHAZADO"],
        "APROBADO": ["PLANIFICADO"],
        "PLANIFICADO": ["EJECUCION"],
        "EJECUCION": ["VALIDACION"],
        "VALIDACION": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "RECHAZADO": ["RESUELTO"],
        "REABIERTO": ["EVALUACION"],
    },
    Process.INCIDENT: {
        "REGISTRADO": ["CLASIFICADO"],
        "CLASIFICADO": ["DIAGNOSTICO"],
        "DIAGNOSTICO": ["ATENCION", "ESCALADO"],
        "ATENCION": ["ESCALADO", "RECUPERADO"],
        "ESCALADO": ["ATENCION", "RECUPERADO"],
        "RECUPERADO": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "REABIERTO": ["DIAGNOSTICO"],
    },
    Process.EVENT: {
        "REGISTRADO": ["CLASIFICADO"],
        "CLASIFICADO": ["EVALUADO"],
        "EVALUADO": ["RESPONDIDO"],
        "RESPONDIDO": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "REABIERTO": ["EVALUADO"],
    },
    Process.PROBLEM: {
        "REGISTRADO": ["INVESTIGACION"],
        "INVESTIGACION": ["SOLUCION_TEMPORAL", "ERROR_CONOCIDO", "SOLUCION_DEFINITIVA"],
        "SOLUCION_TEMPORAL": ["ERROR_CONOCIDO", "SOLUCION_DEFINITIVA"],
        "ERROR_CONOCIDO": ["SOLUCION_DEFINITIVA"],
        "SOLUCION_DEFINITIVA": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "REABIERTO": ["INVESTIGACION"],
    },
    Process.ACCESS: {
        "SOLICITADO": ["PENDIENTE_APROBACION"],
        "PENDIENTE_APROBACION": ["APROBADO", "RECHAZADO"],
        "APROBADO": ["PROVISIONADO"],
        "PROVISIONADO": ["VALIDADO"],
        "VALIDADO": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "RECHAZADO": ["RESUELTO"],
        "REABIERTO": ["PENDIENTE_APROBACION"],
    },
    Process.SERVICE: {
        "SOLICITADO": ["VALIDACION"],
        "VALIDACION": ["ASIGNACION"],
        "ASIGNACION": ["CUMPLIMIENTO"],
        "CUMPLIMIENTO": ["CONFIRMACION"],
        "CONFIRMACION": ["RESUELTO"],
        "RESUELTO": ["CERRADO"],
        "REABIERTO": ["VALIDACION"],
    },
}

INITIAL_STATE = {
    process: "REGISTRADO" if "REGISTRADO" in states else "SOLICITADO"
    for process, states in STEPS.items()
}


# Mapeo visual de la diapositiva 16. P1/P2 representan la banda ALTA.
INCIDENT_GUIDANCE = {
    "I0": {"band": "BAJA", "priority": "P4", "redundancy": True},
    "I1": {"band": "MEDIA", "priority": "P3", "redundancy": False},
    "I2": {"band": "MEDIA", "priority": "P3", "redundancy": False},
    "I3": {"band": "ALTA", "priority": "P2", "redundancy": False},
    "I4": {"band": "ALTA", "priority": "P2", "redundancy": False},
    "I5": {"band": "ALTA", "priority": "P2", "redundancy": False},
    "I6": {"band": "ALTA", "priority": "P1", "redundancy": False},
}


def propose_incident_category(minutes=None, *, interruption=True, security=False):
    """Regla COMPLEMENTARIA, no clasificación automática atribuida a la lección."""
    if security:
        return "I6"
    if not interruption:
        return "I0"
    if minutes is None or minutes < 0:
        raise ValidationError("Indique una estimación válida para proponer categoría.")
    if minutes <= 180:
        return "I1"
    if minutes <= 480:
        return "I2"
    if minutes <= 2880:
        return "I3"
    if minutes < 43200:
        return "I4"  # Cubre la laguna >1 semana y <1 mes; decisión del proyecto.
    return "I5"


def valid_destinations(ticket):
    return STEPS.get(ticket.process, {}).get(ticket.status, [])


def check_transition_requirements(ticket, destination):
    if destination not in valid_destinations(ticket):
        raise ValidationError("Transición inválida para este proceso y estado.")

    data = ticket.details or {}

    def require(*keys):
        missing = [key for key in keys if not data.get(key)]
        if missing:
            raise ValidationError("Faltan datos del proceso: " + ", ".join(missing))

    if ticket.process == Process.CHANGE:
        if destination == "PENDIENTE_APROBACION":
            require("evaluacion_riesgo", "evaluacion_impacto")
        if destination == "EJECUCION":
            require("plan_pruebas", "plan_reversion")
            if not ticket.approvals.filter(decision="APROBADO").exists():
                raise ValidationError("No se puede ejecutar un cambio sin aprobación previa.")
    elif ticket.process == Process.ACCESS:
        if destination == "PENDIENTE_APROBACION":
            require("beneficiario", "recurso", "permiso")
        if destination == "PROVISIONADO" and not ticket.approvals.filter(decision="APROBADO").exists():
            raise ValidationError("El acceso debe estar aprobado antes de provisionarse.")
    elif ticket.process == Process.NEW_SERVICE and destination == "PENDIENTE_APROBACION":
        require("necesidad", "viabilidad")
    elif ticket.process == Process.PROBLEM and destination == "SOLUCION_DEFINITIVA":
        require("causa_raiz")
    elif ticket.process == Process.INCIDENT and destination == "RESUELTO":
        require("solucion")
    elif ticket.process == Process.SERVICE and destination == "CONFIRMACION":
        require("cumplimiento")
    elif ticket.process == Process.EVENT and destination == "RESPONDIDO":
        if ticket.event_category in {"E2", "E3"}:
            if not hasattr(ticket, "generated_incident") or not hasattr(ticket, "incident_notice"):
                raise ValidationError("E2/E3 requieren un incidente relacionado y notificación verificable.")
    if destination == "RESUELTO":
        require("resolucion")
