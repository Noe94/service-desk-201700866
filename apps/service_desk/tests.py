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

    def test_consulta_no_modifica_ticket_propio_por_http(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.utils import timezone

        ticket = self.make_ticket(
            requester=self.consulta,
            actor=self.admin,
        )

        self.client.force_login(self.consulta)

        detail = self.client.get(
            reverse("service_desk:ticket_detail", args=[ticket.pk])
        )
        self.assertEqual(detail.status_code, 200)

        comment = self.client.post(
            reverse("service_desk:ticket_comment", args=[ticket.pk]),
            {"text": "Intento de modificación"},
        )
        self.assertEqual(comment.status_code, 403)

        attachment = self.client.post(
            reverse("service_desk:ticket_attachment_upload", args=[ticket.pk]),
            {
                "file": SimpleUploadedFile(
                    "prueba.txt",
                    b"contenido de prueba",
                )
            },
        )
        self.assertEqual(attachment.status_code, 403)

        ticket.status = "CERRADO"
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=["status", "closed_at"])

        reopen = self.client.post(
            reverse("service_desk:ticket_reopen", args=[ticket.pk]),
            {"reason": "Intento de reapertura"},
        )
        self.assertEqual(reopen.status_code, 403)

        self.assertEqual(ticket.comments.count(), 0)
        self.assertEqual(ticket.attachments.count(), 0)
        self.assertEqual(
            ticket.history.filter(action="REAPERTURA").count(),
            0,
        )

    def test_adjuntos_rechazan_contenido_falso_y_tamano_excesivo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import TicketAttachment

        ticket = self.make_ticket()

        invalid_pdf = TicketAttachment(
            ticket=ticket,
            uploader=self.agent,
            file=SimpleUploadedFile(
                "archivo.pdf",
                b"Esto no es un documento PDF",
            ),
        )

        with self.assertRaises(ValidationError):
            invalid_pdf.full_clean()

        invalid_text = TicketAttachment(
            ticket=ticket,
            uploader=self.agent,
            file=SimpleUploadedFile(
                "archivo.txt",
                b"texto\x00binario",
            ),
        )

        with self.assertRaises(ValidationError):
            invalid_text.full_clean()

        valid_pdf = TicketAttachment(
            ticket=ticket,
            uploader=self.agent,
            file=SimpleUploadedFile(
                "valido.pdf",
                b"%PDF-1.7\n%%EOF",
            ),
        )
        valid_pdf.full_clean()

        oversized = TicketAttachment(
            ticket=ticket,
            uploader=self.agent,
            file=SimpleUploadedFile(
                "grande.txt",
                b"A" * (10 * 1024 * 1024 + 1),
            ),
        )

        with self.assertRaises(ValidationError):
            oversized.full_clean()

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


    def test_p13_trazabilidad_incidente_problema_cambio(self):
        from .models import TicketRelation

        incidente = self.make_ticket(Process.INCIDENT)

        problema = self.make_ticket(
            Process.PROBLEM,
            details={
                "causa_raiz": "Fallo recurrente identificado",
                "solucion_temporal": "Procedimiento temporal",
                "error_conocido": "Fallo documentado",
                "resolucion": "Correccion definitiva propuesta",
            },
        )

        cambio = self.make_ticket(
            Process.CHANGE,
            details={
                "evaluacion_impacto": "Impacto medio",
                "evaluacion_riesgo": "Riesgo bajo",
                "plan_pruebas": "Validar el servicio",
                "plan_reversion": "Restaurar configuracion",
                "resolucion": "Implementacion verificada",
            },
        )

        TicketRelation.objects.create(
            source=incidente,
            target=problema,
            relation_type=TicketRelation.Type.RELATED,
        )

        TicketRelation.objects.create(
            source=problema,
            target=cambio,
            relation_type=TicketRelation.Type.CAUSE,
        )

        relacion_incidente = TicketRelation.objects.get(
            source=incidente,
            target__process=Process.PROBLEM,
        )

        self.assertEqual(
            relacion_incidente.target_id,
            problema.pk,
        )

        relacion_cambio = TicketRelation.objects.get(
            source=relacion_incidente.target,
            target__process=Process.CHANGE,
        )

        self.assertEqual(
            relacion_cambio.target_id,
            cambio.pk,
        )

        self.assertEqual(
            incidente.out_relations.count(),
            1,
        )

        self.assertEqual(
            problema.in_relations.count(),
            1,
        )

        self.assertEqual(
            problema.out_relations.count(),
            1,
        )

        self.assertEqual(
            cambio.in_relations.count(),
            1,
        )

        self.assertNotEqual(incidente.number, problema.number)
        self.assertNotEqual(problema.number, cambio.number)

        self.assertTrue(incidente.history.exists())
        self.assertTrue(problema.history.exists())
        self.assertTrue(cambio.history.exists())

    def test_p17_indicadores_controlados_pausas_reaperturas(self):
        from datetime import timedelta
        from django.utils import timezone
        from .views import elapsed_minutes

        ahora = timezone.now()

        pausado = self.make_ticket()

        Ticket.objects.filter(pk=pausado.pk).update(
            created_at=ahora - timedelta(minutes=120),
            first_response_at=ahora - timedelta(minutes=110),
            paused_at=ahora - timedelta(minutes=40),
            paused_seconds=0,
        )

        pausado.refresh_from_db()

        cerrado = self.make_ticket()

        Ticket.objects.filter(pk=cerrado.pk).update(
            created_at=ahora - timedelta(minutes=100),
            first_response_at=ahora - timedelta(minutes=85),
            resolved_at=ahora - timedelta(minutes=30),
            closed_at=ahora - timedelta(minutes=25),
            status="CERRADO",
        )

        cerrado.refresh_from_db()

        reabierto = self.make_ticket()

        Ticket.objects.filter(pk=reabierto.pk).update(
            created_at=ahora - timedelta(minutes=200),
            first_response_at=ahora - timedelta(minutes=190),
            resolved_at=ahora - timedelta(minutes=20),
            closed_at=ahora - timedelta(minutes=10),
            status="CERRADO",
        )

        reopen_ticket(
            reabierto.pk,
            self.requester,
            reason="Se reproduce el inconveniente",
        )

        reabierto.refresh_from_db()

        self.assertEqual(reabierto.status, "REABIERTO")
        self.assertEqual(reabierto.reopen_count, 1)
        self.assertIsNone(reabierto.closed_at)
        self.assertIsNone(reabierto.resolved_at)

        self.assertEqual(
            reabierto.history.filter(action="REAPERTURA").count(),
            1,
        )

        self.assertAlmostEqual(
            elapsed_minutes(pausado, ahora),
            80.0,
            places=1,
        )

        self.client.force_login(self.requester)

        respuesta = self.client.get(
            reverse("service_desk:dashboard")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total"], 3)
        self.assertEqual(respuesta.context["open"], 2)
        self.assertEqual(respuesta.context["paused"], 1)

        self.assertEqual(
            respuesta.context["average_first"],
            11.7,
        )

        self.assertEqual(
            respuesta.context["average_resolved"],
            70.0,
        )

        self.assertEqual(
            respuesta.context["oldest"],
            3.3,
        )

        self.assertEqual(
            respuesta.context["response_pct"],
            100.0,
        )

        self.assertEqual(
            respuesta.context["resolution_pct"],
            100.0,
        )


    def test_ui_nuevo_servicio_aprobado_sin_duplicados(self):
        from django.urls import reverse
        from apps.catalog.models import ServicioNivel2

        ticket = self.make_ticket(
            Process.NEW_SERVICE,
            details={
                "necesidad": "Nuevo servicio para evaluacion",
                "viabilidad": "Viable",
                "resolucion": "Implementado",
            },
        )

        self.client.force_login(self.agent)

        url = reverse(
            "service_desk:ticket_service_link",
            args=[ticket.pk],
        )

        codigo = "SD-PRUEBA-NUEVO-N2"

        datos = {
            "code": codigo,
            "name": "Servicio nuevo de prueba",
            "level1_id": self.service.nivel1_id,
        }

        respuesta = self.client.post(url, datos)

        self.assertEqual(respuesta.status_code, 302)

        self.assertFalse(
            ServicioNivel2.objects.filter(codigo=codigo).exists()
        )

        for estado in ("ANALISIS", "PENDIENTE_APROBACION"):
            transition_ticket(
                ticket.pk,
                self.agent,
                estado,
                reason="Revision del servicio",
            )

        transition_ticket(
            ticket.pk,
            self.approver,
            "APROBADO",
            reason="Solicitud autorizada",
        )

        respuesta = self.client.post(url, datos)

        self.assertEqual(respuesta.status_code, 302)

        ticket.refresh_from_db()

        servicio_nuevo = ServicioNivel2.objects.get(
            codigo=codigo
        )

        self.assertEqual(
            ticket.service_id,
            servicio_nuevo.pk,
        )

        self.assertEqual(
            servicio_nuevo.nivel1_id,
            self.service.nivel1_id,
        )

        self.assertEqual(
            ticket.details.get("servicio_vinculado"),
            codigo,
        )

        self.assertEqual(
            ticket.history.filter(
                action="SERVICIO_VINCULADO"
            ).count(),
            1,
        )

        respuesta = self.client.post(url, datos)

        self.assertEqual(respuesta.status_code, 302)

        self.assertEqual(
            ServicioNivel2.objects.filter(codigo=codigo).count(),
            1,
        )

        self.assertEqual(
            ticket.history.filter(
                action="SERVICIO_VINCULADO"
            ).count(),
            1,
        )

        respuesta = self.client.post(
            url,
            {"code": self.service.codigo},
        )

        self.assertEqual(respuesta.status_code, 302)

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.service_id,
            self.service.pk,
        )

        self.assertEqual(
            ticket.history.filter(
                action="SERVICIO_VINCULADO"
            ).count(),
            2,
        )

        self.client.force_login(self.requester)

        respuesta = self.client.post(
            url,
            {
                "code": "SD-SIN-PERMISO",
                "name": "Servicio no autorizado",
                "level1_id": self.service.nivel1_id,
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.assertFalse(
            ServicioNivel2.objects.filter(
                codigo="SD-SIN-PERMISO"
            ).exists()
        )

    def test_ui_relaciones_incidente_problema_cambio(self):
        from django.urls import reverse
        from .models import TicketRelation

        incidente = self.make_ticket(Process.INCIDENT)
        problema = self.make_ticket(Process.PROBLEM)
        cambio = self.make_ticket(Process.CHANGE)

        self.client.force_login(self.agent)

        url_incidente = reverse(
            "service_desk:ticket_relation_add",
            args=[incidente.pk],
        )

        datos_incidente = {
            "target_number": problema.number,
            "relation_type": "RELACIONADO",
            "reason": "Incidente recurrente",
        }

        respuesta = self.client.post(
            url_incidente,
            datos_incidente,
        )

        self.assertEqual(respuesta.status_code, 302)

        self.assertEqual(
            TicketRelation.objects.filter(
                source=incidente,
                target=problema,
            ).count(),
            1,
        )

        self.assertEqual(
            incidente.history.filter(
                action="VINCULO_TICKET"
            ).count(),
            1,
        )

        self.client.post(url_incidente, datos_incidente)

        self.assertEqual(
            TicketRelation.objects.filter(
                source=incidente,
                target=problema,
            ).count(),
            1,
        )

        self.assertEqual(
            incidente.history.filter(
                action="VINCULO_TICKET"
            ).count(),
            1,
        )

        url_problema = reverse(
            "service_desk:ticket_relation_add",
            args=[problema.pk],
        )

        respuesta = self.client.post(
            url_problema,
            {
                "target_number": cambio.number,
                "relation_type": "CAUSA",
                "reason": "Cambio correctivo",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        self.assertTrue(
            TicketRelation.objects.filter(
                source=problema,
                target=cambio,
            ).exists()
        )

        detalle_incidente = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                args=[incidente.pk],
            )
        )

        self.assertEqual(
            detalle_incidente.status_code,
            200,
        )

        self.assertContains(
            detalle_incidente,
            problema.number,
        )

        detalle_problema = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                args=[problema.pk],
            )
        )

        self.assertContains(
            detalle_problema,
            incidente.number,
        )

        self.assertContains(
            detalle_problema,
            cambio.number,
        )

        respuesta = self.client.post(
            url_incidente,
            {
                "target_number": incidente.number,
                "relation_type": "RELACIONADO",
                "reason": "Intento incorrecto",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        self.assertFalse(
            TicketRelation.objects.filter(
                source=incidente,
                target=incidente,
            ).exists()
        )

        self.client.force_login(self.requester)

        respuesta = self.client.post(
            url_incidente,
            {
                "target_number": cambio.number,
                "relation_type": "RELACIONADO",
                "reason": "Intento sin permiso",
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.assertFalse(
            TicketRelation.objects.filter(
                source=incidente,
                target=cambio,
            ).exists()
        )

from django.test import TransactionTestCase


class P07ConcurrentClaimTests(TransactionTestCase):

    def test_p07_dos_agentes_reclaman_mismo_ticket_postgresql(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.db import connection, connections, close_old_connections

        from apps.catalog.models import ServicioNivel1, ServicioNivel2
        from apps.organization.models import (
            Empresa, Area, Departamento, Seccion, Puesto
        )

        from .models import Process, Queue, QueueRoleGrant, Ticket
        from .services import TicketConflict, claim_ticket, create_ticket

        self.assertEqual(connection.vendor, "postgresql")

        empresa = Empresa.objects.create(
            codigo="P07-EMP",
            nombre="Empresa temporal P07",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="P07-AREA",
            nombre="Area temporal",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="P07-DEP",
            nombre="Departamento temporal",
        )

        seccion = Seccion.objects.create(
            departamento=departamento,
            codigo="P07-SEC",
            nombre="Seccion temporal",
        )

        puesto = Puesto.objects.create(
            seccion=seccion,
            codigo="P07-PUESTO",
            nombre="Agente de pruebas",
        )

        nivel1 = ServicioNivel1.objects.create(
            codigo="P07-N1",
            nombre="Servicio temporal nivel 1",
        )

        servicio = ServicioNivel2.objects.create(
            nivel1=nivel1,
            codigo="P07-N2",
            nombre="Servicio temporal nivel 2",
        )

        cola = Queue.objects.create(
            code="P07-COLA",
            name="Cola concurrencia",
            process=Process.INCIDENT,
        )

        grupo = Group.objects.create(name="AGENTE")

        QueueRoleGrant.objects.create(
            queue=cola,
            role=grupo,
            can_view=True,
            can_attend=True,
        )

        Usuario = get_user_model()

        agente1 = Usuario.objects.create_user(
            username="p07_agente_1",
            email="p07_agente_1@example.local",
            puesto=puesto,
            rol="OPERATIVO",
        )

        agente2 = Usuario.objects.create_user(
            username="p07_agente_2",
            email="p07_agente_2@example.local",
            puesto=puesto,
            rol="OPERATIVO",
        )

        agente1.groups.add(grupo)
        agente2.groups.add(grupo)

        ticket = create_ticket(
            actor=agente1,
            requester=agente1,
            service=servicio,
            queue=cola,
            title="Prueba de concurrencia P07",
            description="Dos agentes intentan tomar el mismo ticket",
            priority="P2",
            impact="MEDIA",
            urgency="ALTA",
            channel="WEB",
            no_ci_reason="Prueba aislada sin CI",
            incident_category="I1",
        )

        barrera = Barrier(3)

        def intentar_asignar(usuario_id):
            close_old_connections()

            try:
                usuario = Usuario.objects.get(pk=usuario_id)

                barrera.wait(timeout=20)

                try:
                    claim_ticket(ticket.pk, usuario)
                    return "ASIGNADO"

                except TicketConflict:
                    return "CONFLICTO"

            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            futuro1 = ejecutor.submit(
                intentar_asignar,
                agente1.pk,
            )

            futuro2 = ejecutor.submit(
                intentar_asignar,
                agente2.pk,
            )

            barrera.wait(timeout=20)

            resultados = [
                futuro1.result(timeout=30),
                futuro2.result(timeout=30),
            ]

        ticket.refresh_from_db()

        self.assertEqual(
            resultados.count("ASIGNADO"),
            1,
            resultados,
        )

        self.assertEqual(
            resultados.count("CONFLICTO"),
            1,
            resultados,
        )

        self.assertIn(
            ticket.assignee_id,
            [agente1.pk, agente2.pk],
        )

        self.assertEqual(
            ticket.history.filter(action="ASIGNACION").count(),
            1,
        )

        self.assertIsNotNone(ticket.first_response_at)
