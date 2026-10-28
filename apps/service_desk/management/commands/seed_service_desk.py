import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import ServicioNivel2
from apps.cmdb.models import CI
from apps.organization.models import Puesto
from apps.service_desk.models import KnowledgeArticle, Process, Queue, QueueRoleGrant, QueueUserGrant, Ticket
from apps.service_desk.services import claim_ticket, create_ticket, log_action, transition_ticket
from apps.service_desk.workflows import STEPS
from apps.service_desk.workflows import INCIDENT_GUIDANCE


QUEUE_CODES = {
    Process.NEW_SERVICE: "Q-NUEVOS",
    Process.CHANGE: "Q-CAMBIOS",
    Process.INCIDENT: "Q-INCIDENTES",
    Process.EVENT: "Q-EVENTOS",
    Process.PROBLEM: "Q-PROBLEMAS",
    Process.ACCESS: "Q-ACCESOS",
    Process.SERVICE: "Q-SERVICIOS",
}


DETAILS = {
    Process.NEW_SERVICE: {"necesidad": "Nuevo servicio de demostración", "viabilidad": "Viable", "resolucion": "Habilitado"},
    Process.CHANGE: {
        "evaluacion_impacto": "Impacto controlado", "evaluacion_riesgo": "Riesgo bajo",
        "plan_pruebas": "Prueba funcional", "plan_reversion": "Restaurar configuración",
        "resolucion": "Validado",
    },
    Process.INCIDENT: {"interrupcion": "Degradación sintética", "diagnostico": "Revisión", "solucion": "Recuperación", "resolucion": "Restaurado"},
    Process.EVENT: {"origen_evento": "DEMO", "evaluacion": "Revisado", "resolucion": "Registrado"},
    Process.PROBLEM: {"causa_raiz": "Configuración inconsistente", "resolucion": "Corregido"},
    Process.ACCESS: {"beneficiario": "usuario_demo", "recurso": "Aplicación demo", "permiso": "Lectura", "resolucion": "Validado"},
    Process.SERVICE: {"solicitud": "Requisición demo", "cumplimiento": "Entregado", "resolucion": "Confirmado"},
}


class Command(BaseCommand):
    help = "Crea roles, siete colas y 37 tickets demo reproducibles sin duplicarlos."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        try:
            User.objects.get(username="admin_demo")
            puesto = Puesto.objects.filter(activo=True).first()
            service = ServicioNivel2.objects.exclude(activo=False).order_by("pk").first()
        except User.DoesNotExist as exc:
            raise CommandError("Ejecute primero seed_demo.") from exc
        if not puesto or not service:
            raise CommandError("Ejecute primero seed_demo e import_catalog.")

        passwords = {
            "solicitante_demo": os.environ.get("DEMO_SOLICITANTE_PASSWORD"),
            "agente_demo": os.environ.get("DEMO_AGENTE_PASSWORD"),
            "aprobador_demo": os.environ.get("DEMO_APROBADOR_PASSWORD"),
        }
        if not all(passwords.values()):
            raise CommandError("Configure las tres contraseñas DEMO_*_PASSWORD adicionales.")

        groups = {name: Group.objects.get_or_create(name=name)[0]
                  for name in ("SOLICITANTE", "AGENTE", "APROBADOR")}
        users = {}
        for username, group_names in (
            ("solicitante_demo", ["SOLICITANTE"]),
            ("agente_demo", ["AGENTE", "SOLICITANTE"]),
            ("aprobador_demo", ["APROBADOR", "SOLICITANTE"]),
        ):
            user, _ = User.objects.update_or_create(
                username=username, defaults={
                    "email": f"{username}@example.local", "rol": "OPERATIVO",
                    "puesto": puesto, "is_active": True,
                },
            )
            user.set_password(passwords[username])
            user.save()
            user.groups.set([groups[name] for name in group_names])
            users[username] = user

        queues = {}
        for process, label in Process.choices:
            queue, _ = Queue.objects.update_or_create(
                code=QUEUE_CODES[process], defaults={
                    "name": label, "process": process, "active": True, "support_level": 1,
                    "first_response_target_minutes": 240, "resolution_target_minutes": 1440,
                },
            )
            queues[process] = queue
            QueueRoleGrant.objects.update_or_create(queue=queue, role=groups["AGENTE"], defaults={
                "can_view": True, "can_attend": True, "can_transfer": True,
                "can_approve": False, "can_manage": False,
            })
            QueueRoleGrant.objects.update_or_create(queue=queue, role=groups["APROBADOR"], defaults={
                "can_view": True, "can_attend": False, "can_transfer": False,
                "can_approve": process in {Process.NEW_SERVICE, Process.CHANGE, Process.ACCESS},
                "can_manage": False,
            })
        QueueUserGrant.objects.update_or_create(
            queue=queues[Process.CHANGE], user=users["agente_demo"], defaults={
                "can_view": True, "can_attend": True, "can_transfer": True,
                "can_approve": False, "can_manage": False,
            },
        )

        created = 0
        # 5 tickets por proceso, salvo incidentes (7 para cubrir I0-I6).
        for process in Process.values:
            total = 7 if process == Process.INCIDENT else 5
            queue = queues[process]
            for index in range(total):
                key = f"DEMO-{process}-{index}"
                if Ticket.objects.filter(details__demo_key=key).exists():
                    continue
                details = dict(DETAILS[process], demo_key=key)
                ticket = create_ticket(
                    actor=users["solicitante_demo"], requester=users["solicitante_demo"],
                    service=service, queue=queue,
                    title=f"{queue.name} - caso de prueba {index + 1}",
                    description="Caso sintético generado para evaluar el Service Desk.",
                    priority=INCIDENT_GUIDANCE[f"I{index}"]["priority"] if process == Process.INCIDENT else ["P1", "P2", "P3", "P4"][index % 4],
                    impact="MEDIA", urgency="MEDIA", channel="WEB",
                    no_ci_reason="CI no identificado al momento del registro; pendiente de asociación.",
                    details=details,
                    event_category=["E0", "E1", "E2", "E3", "E1"][index] if process == Process.EVENT else "",
                    incident_category=f"I{index}" if process == Process.INCIDENT else "",
                    estimated_interruption_minutes=30 * (index + 1) if process == Process.INCIDENT else None,
                    redundancy_available=INCIDENT_GUIDANCE[f"I{index}"]["redundancy"] if process == Process.INCIDENT else None,
                )
                # Cada avance usa las reglas y la bitácora reales del proceso.
                # Para el demo se recorren estados iniciales, sin forzar el cierre.
                steps_to_take = min(index, 3)
                if process == Process.EVENT and ticket.event_category in {"E2", "E3"}:
                    # Estos casos deben pasar por la vinculación real de incidente y notificación.
                    steps_to_take = min(steps_to_take, 2)
                if steps_to_take:
                    claim_ticket(ticket.pk, users["agente_demo"])
                for step_number in range(steps_to_take):
                    choices = STEPS[process][ticket.status]
                    destination = choices[0]
                    actor = users["aprobador_demo"] if destination in {"APROBADO", "RECHAZADO"} else users["agente_demo"]
                    transition_ticket(ticket.pk, actor, destination, reason="Avance sintético registrado por el generador")
                    ticket.refresh_from_db()
                created += 1

        articles = [
            ("Acceso al portal", "¿Cómo ingreso al Service Desk?", "Utilice su usuario y contraseña institucional de demostración. Si el acceso falla, solicite asistencia a la mesa."),
            ("Crear un ticket", "¿Cómo registro una solicitud?", "Entre en Tickets, seleccione Nuevo ticket, elija uno de los siete procesos e indique el servicio y los detalles del caso."),
            ("Consultar un caso", "¿Cómo reviso el avance?", "En Tickets encontrará sus solicitudes y comentarios públicos. Las notas internas no son visibles para el solicitante."),
            ("Incidente vs. servicio", "¿Qué proceso debo elegir?", "Use Incidentes si algo dejó de funcionar o se degradó; use Servicios de tecnología para una requisición normal."),
        ]
        for title, question, answer in articles:
            KnowledgeArticle.objects.update_or_create(title=title, defaults={
                "question": question, "answer": answer, "active": True,
            })

        # Los ejemplos que tienen dispositivos reales se relacionan en la BD.
        # Si la CMDB aún no está generada, se conserva el motivo de ausencia.
        cis = list(CI.objects.filter(classification__is_device=True).order_by("code")[:25])
        demo_tickets = list(Ticket.objects.filter(details__has_key="demo_key").order_by("pk")[:25])
        for ticket, ci in zip(demo_tickets, cis):
            if not ticket.cis.filter(pk=ci.pk).exists():
                ticket.cis.add(ci)
                ticket.no_ci_reason = ""
                ticket.save(update_fields=["no_ci_reason", "updated_at"])
                log_action(ticket, users["agente_demo"], "VINCULO_CI", new={"ci": ci.code})

        self.stdout.write(self.style.SUCCESS(
            f"Service Desk demo preparado: 7 colas, {Ticket.objects.filter(details__has_key='demo_key').count()} tickets; {created} nuevos."
        ))
