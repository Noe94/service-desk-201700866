from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import (
    ClaseServicio,
    Criticidad,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)
from apps.organization.models import (
    Area,
    Departamento,
    Empresa,
    Puesto,
    Seccion,
)


User = get_user_model()


class CatalogWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Empresa.objects.create(
            codigo="EMP-CAT",
            nombre="Empresa Catálogo",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="AREA-CAT",
            nombre="Área Catálogo",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="DEP-CAT",
            nombre="Departamento Catálogo",
        )

        cls.seccion_a = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-A",
            nombre="Sección A",
        )

        cls.seccion_b = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-B",
            nombre="Sección B",
        )

        puesto_a = Puesto.objects.create(
            seccion=cls.seccion_a,
            codigo="PUE-A",
            nombre="Puesto A",
        )

        puesto_b = Puesto.objects.create(
            seccion=cls.seccion_b,
            codigo="PUE-B",
            nombre="Puesto B",
        )

        cls.admin = User.objects.create_user(
            username="admin_catalog",
            email="admin_catalog@example.local",
            password="TestOnly-Admin-Catalog",
            puesto=puesto_a,
            rol=User.Rol.ADMINISTRADOR,
        )

        cls.consulta = User.objects.create_user(
            username="consulta_catalog",
            email="consulta_catalog@example.local",
            password="TestOnly-Consulta-Catalog",
            puesto=puesto_a,
            rol=User.Rol.CONSULTA,
        )

        cls.usuario_otra_seccion = User.objects.create_user(
            username="usuario_seccion_b",
            email="usuario_seccion_b@example.local",
            password="TestOnly-Section-B",
            puesto=puesto_b,
            rol=User.Rol.CONSULTA,
        )

        cls.clase = ClaseServicio.objects.create(
            nombre="RECURRENTE"
        )

        cls.criticidad = Criticidad.objects.create(
            nombre="High"
        )

        cls.tipo = TipoServicio.objects.create(
            nombre="Front End"
        )

        cls.n1 = ServicioNivel1.objects.create(
            codigo="CAT.01",
            nombre="Nivel 1 objetivo",
        )

        cls.n1_other = ServicioNivel1.objects.create(
            codigo="CAT.02",
            nombre="Nivel 1 alterno",
        )

        cls.service = ServicioNivel2.objects.create(
            nivel1=cls.n1,
            codigo="CAT.01.01",
            nombre="Servicio objetivo",
            activo=True,
            activo_original="S",
            clase=cls.clase,
            criticidad=cls.criticidad,
            tipo=cls.tipo,
            descripcion="Descripción de prueba",
            metrica="Métrica de prueba",
            minimo=10,
            maximo=20,
        )

        cls.other_service = ServicioNivel2.objects.create(
            nivel1=cls.n1_other,
            codigo="CAT.02.01",
            nombre="Servicio alterno",
            activo=False,
            activo_original="N",
        )

    def login_admin(self):
        self.client.login(
            username="admin_catalog",
            password="TestOnly-Admin-Catalog",
        )

    def login_consulta(self):
        self.client.login(
            username="consulta_catalog",
            password="TestOnly-Consulta-Catalog",
        )

    def test_anonymous_catalog_redirects_to_login(self):
        response = self.client.get(
            reverse("catalog:n2_list")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )

    def test_consulta_can_view_catalog(self):
        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list")
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Servicio objetivo",
        )

    def test_consulta_cannot_create_service(self):
        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_create")
        )

        self.assertEqual(response.status_code, 403)

    def test_search_by_code(self):
        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list"),
            {"q": "CAT.01.01"},
        )

        self.assertContains(
            response,
            "Servicio objetivo",
        )

        self.assertNotContains(
            response,
            "Servicio alterno",
        )

    def test_combined_filters(self):
        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list"),
            {
                "nivel1": self.n1.pk,
                "estado": "activo",
                "clase": self.clase.pk,
                "criticidad": self.criticidad.pk,
                "tipo": self.tipo.pk,
            },
        )

        self.assertContains(
            response,
            "Servicio objetivo",
        )

        self.assertNotContains(
            response,
            "Servicio alterno",
        )

    def test_detail_shows_service_attributes(self):
        self.login_consulta()

        response = self.client.get(
            reverse(
                "catalog:n2_detail",
                kwargs={"pk": self.service.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Descripción de prueba",
        )

        self.assertContains(
            response,
            "Métrica de prueba",
        )

        self.assertContains(
            response,
            "High",
        )

        self.assertContains(
            response,
            "Front End",
        )

    def test_duplicate_n1_code_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse("catalog:n1_create"),
            {
                "codigo": "CAT.01",
                "nombre": "Duplicado",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            ServicioNivel1.objects.filter(
                codigo="CAT.01"
            ).count(),
            1,
        )

    def test_valid_responsible_assignment(self):
        self.service.seccion_responsable = self.seccion_a
        self.service.usuario_responsable = self.consulta

        self.service.full_clean()
        self.service.save()

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.seccion_responsable,
            self.seccion_a,
        )

        self.assertEqual(
            self.service.usuario_responsable,
            self.consulta,
        )

    def test_wrong_section_responsible_is_rejected(self):
        self.service.seccion_responsable = self.seccion_a
        self.service.usuario_responsable = (
            self.usuario_otra_seccion
        )

        with self.assertRaises(ValidationError):
            self.service.full_clean()

    def test_catalog_list_is_paginated(self):
        for index in range(20):
            ServicioNivel2.objects.create(
                nivel1=self.n1,
                codigo=f"CAT.PAGE.{index:02d}",
                nombre=f"Servicio paginado {index}",
                activo=True,
            )

        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list")
        )

        page = response.context["page"]

        self.assertGreater(
            page.paginator.num_pages,
            1,
        )



    def test_admin_can_toggle_n2_service(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "catalog:n2_toggle",
                kwargs={"pk": self.service.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.service.refresh_from_db()

        self.assertFalse(
            self.service.activo
        )

    def test_consulta_cannot_toggle_n2_service(self):
        self.login_consulta()

        response = self.client.post(
            reverse(
                "catalog:n2_toggle",
                kwargs={"pk": self.service.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.service.refresh_from_db()

        self.assertTrue(
            self.service.activo
        )

    def test_revision_filter_uses_review_flag(self):
        ServicioNivel2.objects.create(
            nivel1=self.n1,
            codigo="CAT.REVIEW.01",
            nombre="Servicio revisión",
            activo=True,
            requiere_revision=True,
        )

        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list"),
            {"revision": "si"},
        )

        self.assertContains(
            response,
            "Servicio revisión",
        )

        self.assertNotContains(
            response,
            "Servicio objetivo",
        )

    def test_pagination_preserves_active_filters(self):
        for index in range(20):
            ServicioNivel2.objects.create(
                nivel1=self.n1,
                codigo=f"CAT.FILTER.{index:02d}",
                nombre=f"Filtro pagina {index}",
                activo=True,
            )

        self.login_consulta()

        response = self.client.get(
            reverse("catalog:n2_list"),
            {
                "q": "Filtro pagina",
                "estado": "activo",
            },
        )

        self.assertContains(
            response,
            "q=Filtro+pagina",
        )

        self.assertContains(
            response,
            "estado=activo",
        )

        self.assertContains(
            response,
            "page=2",
        )

class CatalogOptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Empresa.objects.create(
            codigo="EMP-OPT",
            nombre="Empresa opciones",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="AREA-OPT",
            nombre="Área opciones",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="DEP-OPT",
            nombre="Departamento opciones",
        )

        seccion = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-OPT",
            nombre="Sección opciones",
        )

        puesto = Puesto.objects.create(
            seccion=seccion,
            codigo="PUE-OPT",
            nombre="Puesto opciones",
        )

        cls.admin = User.objects.create_user(
            username="admin_options",
            email="admin_options@example.local",
            password="TestOnly-Admin-Options",
            puesto=puesto,
            rol=User.Rol.ADMINISTRADOR,
        )

        cls.consulta = User.objects.create_user(
            username="consulta_options",
            email="consulta_options@example.local",
            password="TestOnly-Consulta-Options",
            puesto=puesto,
            rol=User.Rol.CONSULTA,
        )

        cls.clase_usada = ClaseServicio.objects.create(
            nombre="CLASE USADA"
        )

        cls.clase_libre = ClaseServicio.objects.create(
            nombre="CLASE LIBRE"
        )

        nivel1 = ServicioNivel1.objects.create(
            codigo="OPT.01",
            nombre="N1 opciones",
        )

        ServicioNivel2.objects.create(
            nivel1=nivel1,
            codigo="OPT.01.01",
            nombre="Servicio opciones",
            clase=cls.clase_usada,
        )

    def login_admin(self):
        self.client.login(
            username="admin_options",
            password="TestOnly-Admin-Options",
        )

    def login_consulta(self):
        self.client.login(
            username="consulta_options",
            password="TestOnly-Consulta-Options",
        )

    def test_consulta_can_view_option_catalog(self):
        self.login_consulta()

        response = self.client.get(
            reverse(
                "catalog:option_list",
                kwargs={"option": "clase"},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "CLASE USADA",
        )

    def test_consulta_cannot_create_option(self):
        self.login_consulta()

        response = self.client.post(
            reverse(
                "catalog:option_create",
                kwargs={"option": "criticidad"},
            ),
            {
                "nombre": "Critical Test",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Criticidad.objects.filter(
                nombre="Critical Test"
            ).exists()
        )

    def test_admin_can_create_option(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "catalog:option_create",
                kwargs={"option": "criticidad"},
            ),
            {
                "nombre": "Critical Test",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Criticidad.objects.filter(
                nombre="Critical Test"
            ).exists()
        )

    def test_used_option_cannot_be_deactivated(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "catalog:option_toggle",
                kwargs={
                    "option": "clase",
                    "pk": self.clase_usada.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        self.clase_usada.refresh_from_db()

        self.assertTrue(
            self.clase_usada.activo
        )

    def test_unused_option_can_be_deactivated(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "catalog:option_toggle",
                kwargs={
                    "option": "clase",
                    "pk": self.clase_libre.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        self.clase_libre.refresh_from_db()

        self.assertFalse(
            self.clase_libre.activo
        )

