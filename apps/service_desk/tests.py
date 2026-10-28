from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import ServicioNivel1, ServicioNivel2
from apps.organization.models import Area, Departamento, Empresa, Puesto, Seccion

from .models import Process, Queue, QueueRoleGrant, QueueUserGrant, Ticket, TicketHistory
from .permissions import accessible_tickets, queue_allowed
from .services import (
    TicketConflict, add_comment, claim_ticket, create_ticket, pause_ticket, resume_ticket, reopen_ticket,
    transition_ticket, transfer_ticket, update_ticket_details,
)


class DeskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = Empresa.objects.create(codigo="TEST", nombre="Test")
        area = Area.objects.create(empresa=company, codigo="TI", nombre="TI")
        dep = Departamento.objects.create(area=area, codigo="DESK", nombre="Desk")
        section = Seccion.objects.create(departamento=dep, codigo="OPS", nombre="Ops")
        cls.position = Puesto.objects.create(seccion=section, codigo="A", nombre="Operador")
        n1 = ServicioNivel1.objects.create(codigo="SD-TEST-N1", nombre="Servicio test")
        cls.service = ServicioNivel2.objects.create(nivel1=n1, codigo="SD-TEST-N2", nombre="Servicio N2")
        cls.group_req = Group.objects.create(name="SOLICITANTE")
        cls.group_agent = Group.objects.create(name="AGENTE")
        cls.group_approver = Group.objects.create(name="APROBADOR")
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username="sd_admin", email="sd_admin@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="ADMIN",
        )
        cls.requester = User.objects.create_user(
            username="sd_requester", email="sd_requester@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="OPERATIVO",
        )
        cls.other_requester = User.objects.create_user(
            username="sd_other", email="sd_other@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="OPERATIVO",
        )
        cls.agent = User.objects.create_user(
            username="sd_agent", email="sd_agent@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="OPERATIVO",
        )
        cls.agent2 = User.objects.create_user(
            username="sd_agent2", email="sd_agent2@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="OPERATIVO",
        )
        cls.approver = User.objects.create_user(
            username="sd_approver", email="sd_approver@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="OPERATIVO",
        )
        cls.consulta = User.objects.create_user(
            username="sd_consulta", email="sd_consulta@example.local", password="Secure-test-123!",
            puesto=cls.position, rol="CONSULTA",
        )
        cls.requester.groups.add(cls.group_req)
        cls.other_requester.groups.add(cls.group_req)
        cls.agent.groups.add(cls.group_agent)
        cls.agent2.groups.add(cls.group_agent)
        cls.approver.groups.add(cls.group_approver)
        cls.consulta.groups.add(cls.group_agent)  # Adrede: nunca debe elevar CONSULTA.
        cls.queues = {}
        for i, process in enumerate(Process.values):
            queue = Queue.objects.create(code=f"Q-{i}", name=f"Cola {i}", process=process)
            cls.queues[process] = queue
            QueueRoleGrant.objects.create(
                queue=queue, role=cls.group_agent,
                can_view=True, can_attend=True, can_transfer=True,
            )
            QueueRoleGrant.objects.create(
                queue=queue, role=cls.group_approver, can_view=True, can_approve=True,
            )

    def make_ticket(self, process=Process.INCIDENT, details=None, requester=None, **kwargs):
        data = {
            "actor": requester or self.requester, "requester": requester or self.requester,
            "service": self.service, "queue": self.queues[process],
            "title": "Prueba del Service Desk", "description": "Caso de prueba",
            "priority": "P2", "impact": "MEDIA", "urgency": "ALTA", "channel": "WEB",
            "no_ci_reason": "No aplica CI para esta etapa de la prueba.",
            "details": details or {"solucion": "Corregido", "resolucion": "Caso resuelto"},
        }
        if process == Process.EVENT:
            data["event_category"] = "E1"
        if process == Process.INCIDENT:
            data["incident_category"] = "I1"
        data.update(kwargs)
        return create_ticket(**data)

    def test_process_type_mapping_for_seven_queues(self):
        for process in Process.values:
            with self.subTest(process=process):
                ticket = self.make_ticket(process=process)
                self.assertEqual(ticket.queue.process, ticket.process)
                self.assertIsNotNone(ticket.ticket_type)

    def test_ticket_number_and_audit(self):
        ticket = self.make_ticket()
        self.assertRegex(ticket.number, r"^SD-\d{7}$")
        self.assertEqual(ticket.history.count(), 1)
        self.assertEqual(ticket.service_level_1.codigo, "SD-TEST-N1")

    def test_audit_cannot_be_updated_or_deleted(self):
        log = self.make_ticket().history.first()
        with self.assertRaises(ValidationError):
            log.save()
        with self.assertRaises(ValidationError):
            log.delete()

    def test_consulta_never_inherits_agent_permission(self):
        queue = self.queues[Process.INCIDENT]
        self.assertFalse(queue_allowed(self.consulta, queue, "attend"))
        with self.assertRaises(PermissionDenied):
            self.make_ticket(requester=self.consulta)

    def test_ticket_visibility_by_owner_or_queue(self):
        own = self.make_ticket()
        other = self.make_ticket(requester=self.other_requester)
        self.assertIn(own, accessible_tickets(self.requester))
        self.assertNotIn(other, accessible_tickets(self.requester))
        self.assertIn(other, accessible_tickets(self.agent))
        self.assertEqual(accessible_tickets(self.consulta).count(), 0)

    def test_only_one_agent_claims_ticket(self):
        ticket = self.make_ticket()
        claim_ticket(ticket.pk, self.agent)
        with self.assertRaises(TicketConflict):
            claim_ticket(ticket.pk, self.agent2)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assignee_id, self.agent.pk)
        self.assertIsNotNone(ticket.first_response_at)
        self.assertEqual(ticket.history.filter(action="ASIGNACION").count(), 1)

    def test_transfer_requires_process_match_and_reason(self):
        ticket = self.make_ticket()
        dest = Queue.objects.create(code="Q-MISMO", name="Destino", process=Process.INCIDENT)
        with self.assertRaises(ValidationError):
            transfer_ticket(ticket.pk, self.agent, self.queues[Process.CHANGE], reason="Prueba")
        transfer_ticket(ticket.pk, self.agent, dest, reason="Escalamiento operativo")
        ticket.refresh_from_db()
        self.assertEqual(ticket.queue_id, dest.pk)
        self.assertIsNone(ticket.assignee)
        self.assertEqual(ticket.history.last().action, "TRANSFERENCIA")

    def test_change_cannot_execute_without_approval(self):
        ticket = self.make_ticket(Process.CHANGE, details={
            "evaluacion_impacto": "Medio", "evaluacion_riesgo": "Bajo",
            "plan_pruebas": "Probar", "plan_reversion": "Revertir", "resolucion": "Validado",
        })
        ticket.status = "PLANIFICADO"
        ticket.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            transition_ticket(ticket.pk, self.agent, "EJECUCION", reason="Intento")

    def test_change_full_approved_route(self):
        ticket = self.make_ticket(Process.CHANGE, details={
            "evaluacion_impacto": "Medio", "evaluacion_riesgo": "Bajo",
            "plan_pruebas": "Probar", "plan_reversion": "Revertir", "resolucion": "Validado",
        })
        claim_ticket(ticket.pk, self.agent)
        for destination in ("EVALUACION", "PENDIENTE_APROBACION"):
            transition_ticket(ticket.pk, self.agent, destination, reason="Control")
        transition_ticket(ticket.pk, self.approver, "APROBADO", reason="Autorizado")
        for destination in ("PLANIFICADO", "EJECUCION", "VALIDACION", "RESUELTO", "CERRADO"):
            transition_ticket(ticket.pk, self.agent, destination, reason="Control")
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.closed_at)
        self.assertEqual(ticket.approvals.count(), 1)

    def test_access_selfapproval_rejected(self):
        self.requester.groups.add(self.group_approver)
        ticket = self.make_ticket(Process.ACCESS, details={
            "beneficiario": "Test", "recurso": "Recurso", "permiso": "Lectura", "resolucion": "OK",
        })
        transition_ticket(ticket.pk, self.agent, "PENDIENTE_APROBACION", reason="Validado")
        with self.assertRaises(PermissionDenied):
            transition_ticket(ticket.pk, self.requester, "APROBADO", reason="Autoaprobación")

    def test_close_without_resolution_rejected(self):
        ticket = self.make_ticket()
        ticket.status = "RESUELTO"
        ticket.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            transition_ticket(ticket.pk, self.agent, "CERRADO", reason="Sin solución")

    def test_reopen_requires_reason_and_tracks_actor(self):
        ticket = self.make_ticket()
        ticket.status = "RESUELTO"
        from django.utils import timezone
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at"])
        transition_ticket(ticket.pk, self.agent, "CERRADO", reason="Validado")
        with self.assertRaises(ValidationError):
            reopen_ticket(ticket.pk, self.requester, reason="")
        reopen_ticket(ticket.pk, self.requester, reason="El problema regresó")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "REABIERTO")
        self.assertEqual(ticket.reopen_count, 1)
        self.assertEqual(ticket.history.last().actor_id, self.requester.pk)

    def test_event_e2_generates_single_incident_and_notification(self):
        ticket = self.make_ticket(Process.EVENT, event_category="E2")
        for status in ("CLASIFICADO", "EVALUADO"):
            transition_ticket(ticket.pk, self.agent, status, reason="Evaluación")
        transition_ticket(ticket.pk, self.agent, "RESPONDIDO", reason="Afectación confirmada")
        from .models import DeskNotification, EventIncident
        self.assertEqual(EventIncident.objects.filter(event=ticket).count(), 1)
        self.assertEqual(DeskNotification.objects.filter(event=ticket).count(), 1)
        incident = EventIncident.objects.get(event=ticket).incident
        self.assertEqual(incident.incident_category, "I1")
        from .services import ensure_event_incident
        self.assertEqual(ensure_event_incident(ticket, self.agent).pk, incident.pk)
        self.assertEqual(EventIncident.objects.filter(event=ticket).count(), 1)

    def test_incident_duration_boundaries_are_project_policy(self):
        from .workflows import INCIDENT_GUIDANCE, propose_incident_category
        self.assertEqual(propose_incident_category(interruption=False), "I0")
        self.assertEqual(propose_incident_category(security=True), "I6")
        for value, expected in [(180, "I1"), (181, "I2"), (480, "I2"),
                                (481, "I3"), (2880, "I3"), (2881, "I4"),
                                (10080, "I4"), (10081, "I4"), (43199, "I4"),
                                (43200, "I5")]:
            self.assertEqual(propose_incident_category(minutes=value), expected)
        self.assertEqual(INCIDENT_GUIDANCE["I0"]["band"], "BAJA")
        self.assertEqual(INCIDENT_GUIDANCE["I1"]["band"], "MEDIA")
        self.assertEqual(INCIDENT_GUIDANCE["I6"]["band"], "ALTA")

    def test_pause_blocks_transition_until_resume(self):
        ticket = self.make_ticket()
        with self.assertRaises(ValidationError):
            pause_ticket(ticket.pk, self.agent, reason="")
        pause_ticket(ticket.pk, self.agent, reason="Esperando insumo")
        with self.assertRaises(TicketConflict):
            transition_ticket(ticket.pk, self.agent, "CLASIFICADO", reason="Avance")
        resume_ticket(ticket.pk, self.agent, reason="Insumo recibido")
        transition_ticket(ticket.pk, self.agent, "CLASIFICADO", reason="Avance")
        self.assertEqual(ticket.history.filter(action="PAUSA").count(), 1)
        self.assertEqual(ticket.history.filter(action="REANUDACION").count(), 1)

    def test_dashboard_shows_visible_ticket_counts(self):
        self.make_ticket()
        self.client.force_login(self.requester)
        response = self.client.get(reverse("service_desk:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 1)
        self.assertEqual(response.context["open"], 1)

    def test_can_manage_permission_controls_queue_edit(self):
        queue = self.queues[Process.INCIDENT]
        self.client.force_login(self.agent)
        response = self.client.get(reverse("service_desk:queue_edit", args=[queue.pk]))
        self.assertEqual(response.status_code, 403)
        grant = QueueRoleGrant.objects.get(queue=queue, role=self.group_agent)
        grant.can_manage = True
        grant.save(update_fields=["can_manage"])
        response = self.client.get(reverse("service_desk:queue_edit", args=[queue.pk]))
        self.assertEqual(response.status_code, 200)

    def test_internal_comment_permission(self):
        ticket = self.make_ticket()
        with self.assertRaises(PermissionDenied):
            add_comment(ticket.pk, self.requester, "Solo interna", internal=True)
        add_comment(ticket.pk, self.agent, "Diagnóstico", internal=True)
        self.assertEqual(ticket.comments.filter(internal=True).count(), 1)

    def test_details_change_is_audited(self):
        ticket = self.make_ticket()
        update_ticket_details(ticket.pk, self.agent, {"diagnostico": "Revisión de logs"})
        ticket.refresh_from_db()
        self.assertEqual(ticket.details["diagnostico"], "Revisión de logs")
        self.assertEqual(ticket.history.last().action, "ACTUALIZACION_PROCESO")

    def test_ticket_list_requires_login(self):
        response = self.client.get(reverse("service_desk:tickets"))
        self.assertEqual(response.status_code, 302)

    def test_portal_create_form_visible(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("service_desk:ticket_create") + "?proceso=INCIDENTES")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Categoría del incidente")

    def test_consulta_cannot_post_ticket(self):
        self.client.force_login(self.consulta)
        response = self.client.post(reverse("service_desk:ticket_create") + "?proceso=INCIDENTES", {})
        self.assertEqual(response.status_code, 403)

    def test_queue_grants_separate_actions(self):
        queue = self.queues[Process.INCIDENT]
        self.assertTrue(queue_allowed(self.agent, queue, "attend"))
        self.assertFalse(queue_allowed(self.agent, queue, "approve"))
        self.assertTrue(queue_allowed(self.approver, queue, "approve"))
        QueueUserGrant.objects.create(queue=queue, user=self.other_requester, can_view=True)
        self.assertTrue(queue_allowed(self.other_requester, queue, "view"))
        self.assertFalse(queue_allowed(self.other_requester, queue, "attend"))


    def test_p09_rutas_completas_siete_procesos(self):
        rutas = {
            Process.NEW_SERVICE: [
                "ANALISIS", "PENDIENTE_APROBACION", "APROBADO",
                "IMPLEMENTACION", "RESUELTO", "CERRADO",
            ],
            Process.CHANGE: [
                "EVALUACION", "PENDIENTE_APROBACION", "APROBADO",
                "PLANIFICADO", "EJECUCION", "VALIDACION",
                "RESUELTO", "CERRADO",
            ],
            Process.INCIDENT: [
                "CLASIFICADO", "DIAGNOSTICO", "ATENCION",
                "RECUPERADO", "RESUELTO", "CERRADO",
            ],
            Process.EVENT: [
                "CLASIFICADO", "EVALUADO", "RESPONDIDO",
                "RESUELTO", "CERRADO",
            ],
            Process.PROBLEM: [
                "INVESTIGACION", "SOLUCION_TEMPORAL",
                "ERROR_CONOCIDO", "SOLUCION_DEFINITIVA",
                "RESUELTO", "CERRADO",
            ],
            Process.ACCESS: [
                "PENDIENTE_APROBACION", "APROBADO",
                "PROVISIONADO", "VALIDADO",
                "RESUELTO", "CERRADO",
            ],
            Process.SERVICE: [
                "VALIDACION", "ASIGNACION", "CUMPLIMIENTO",
                "CONFIRMACION", "RESUELTO", "CERRADO",
            ],
        }

        requisitos = {
            Process.NEW_SERVICE: {
                "necesidad": "Nuevo servicio solicitado",
                "viabilidad": "Viable",
            },
            Process.CHANGE: {
                "evaluacion_impacto": "Impacto controlado",
                "evaluacion_riesgo": "Riesgo bajo",
                "plan_pruebas": "Verificar operacion",
                "plan_reversion": "Restaurar configuracion anterior",
            },
            Process.PROBLEM: {
                "causa_raiz": "Configuracion incorrecta",
            },
            Process.ACCESS: {
                "beneficiario": "Usuario de prueba",
                "recurso": "Sistema de prueba",
                "permiso": "Lectura",
            },
            Process.SERVICE: {
                "cumplimiento": "Solicitud atendida",
            },
        }

        for proceso, estados in rutas.items():
            with self.subTest(proceso=proceso):

                detalles = {
                    "solucion": "Servicio recuperado",
                    "resolucion": "Caso resuelto y validado",
                    **requisitos.get(proceso, {}),
                }

                ticket = self.make_ticket(
                    process=proceso,
                    details=detalles,
                )

                claim_ticket(ticket.pk, self.agent)

                with self.assertRaises(ValidationError):
                    transition_ticket(
                        ticket.pk,
                        self.agent,
                        "CERRADO",
                        reason="Cierre directo no permitido",
                    )

                for estado in estados:
                    actor = (
                        self.approver
                        if estado in {"APROBADO", "RECHAZADO"}
                        else self.agent
                    )

                    transition_ticket(
                        ticket.pk,
                        actor,
                        estado,
                        reason="Verificacion automatizada P09",
                    )

                ticket.refresh_from_db()

                self.assertEqual(ticket.status, "CERRADO")
                self.assertIsNotNone(ticket.resolved_at)
                self.assertIsNotNone(ticket.closed_at)

                self.assertEqual(
                    ticket.history.filter(
                        action="TRANSICION"
                    ).count(),
                    len(estados),
                )

                procesos_aprobacion = {
                    Process.NEW_SERVICE,
                    Process.CHANGE,
                    Process.ACCESS,
                }

                aprobaciones_esperadas = (
                    1 if proceso in procesos_aprobacion else 0
                )

                self.assertEqual(
                    ticket.approvals.filter(
                        decision="APROBADO"
                    ).count(),
                    aprobaciones_esperadas,
                )


    def test_p11_categorias_eventos_e0_e3(self):
        from .models import DeskNotification, EventIncident
        from .services import ensure_event_incident

        for categoria in ("E0", "E1", "E2", "E3"):
            with self.subTest(categoria=categoria):

                ticket = self.make_ticket(
                    process=Process.EVENT,
                    event_category=categoria,
                )

                self.assertEqual(ticket.status, "REGISTRADO")

                if categoria != "E0":
                    claim_ticket(ticket.pk, self.agent)

                    transition_ticket(
                        ticket.pk,
                        self.agent,
                        "CLASIFICADO",
                        reason="Clasificacion del evento",
                    )

                    transition_ticket(
                        ticket.pk,
                        self.agent,
                        "EVALUADO",
                        reason="Evaluacion del evento",
                    )

                if categoria in {"E2", "E3"}:
                    transition_ticket(
                        ticket.pk,
                        self.agent,
                        "RESPONDIDO",
                        reason="Impacto confirmado",
                    )

                    enlace = EventIncident.objects.get(event=ticket)
                    incidente = enlace.incident

                    categoria_esperada = (
                        "I6" if categoria == "E3" else "I1"
                    )

                    self.assertEqual(
                        incidente.incident_category,
                        categoria_esperada,
                    )

                    self.assertEqual(
                        DeskNotification.objects.filter(
                            event=ticket
                        ).count(),
                        1,
                    )

                    # Reprocesar no debe duplicar el incidente.
                    incidente_repetido = ensure_event_incident(
                        ticket,
                        self.agent,
                    )

                    self.assertEqual(
                        incidente_repetido.pk,
                        incidente.pk,
                    )

                    self.assertEqual(
                        EventIncident.objects.filter(
                            event=ticket
                        ).count(),
                        1,
                    )

                    self.assertEqual(
                        DeskNotification.objects.filter(
                            event=ticket
                        ).count(),
                        1,
                    )

                else:
                    self.assertEqual(
                        EventIncident.objects.filter(
                            event=ticket
                        ).count(),
                        0,
                    )

                    self.assertEqual(
                        DeskNotification.objects.filter(
                            event=ticket
                        ).count(),
                        0,
                    )

                ticket.refresh_from_db()

                if categoria == "E0":
                    self.assertEqual(ticket.status, "REGISTRADO")
                elif categoria == "E1":
                    self.assertEqual(ticket.status, "EVALUADO")
                else:
                    self.assertEqual(ticket.status, "RESPONDIDO")
