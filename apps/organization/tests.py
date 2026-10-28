from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.organization.models import (
    Area,
    Departamento,
    Empresa,
    Puesto,
    Seccion,
)


User = get_user_model()


class OrganizationCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            codigo="EMP1",
            nombre="Empresa 1",
        )

        cls.area = Area.objects.create(
            empresa=cls.empresa,
            codigo="AREA1",
            nombre="Área 1",
        )

        cls.departamento = Departamento.objects.create(
            area=cls.area,
            codigo="DEP1",
            nombre="Departamento 1",
        )

        cls.seccion = Seccion.objects.create(
            departamento=cls.departamento,
            codigo="SEC1",
            nombre="Sección 1",
        )

        cls.puesto = Puesto.objects.create(
            seccion=cls.seccion,
            codigo="PUE1",
            nombre="Puesto 1",
        )

        cls.admin = User.objects.create_user(
            username="admin_org",
            email="admin_org@example.local",
            password="TestOnly-Admin-Org",
            puesto=cls.puesto,
            rol=User.Rol.ADMINISTRADOR,
        )

        cls.consulta = User.objects.create_user(
            username="consulta_org",
            email="consulta_org@example.local",
            password="TestOnly-Consulta-Org",
            puesto=cls.puesto,
            rol=User.Rol.CONSULTA,
        )

    def login_admin(self):
        self.client.login(
            username="admin_org",
            password="TestOnly-Admin-Org",
        )

    def login_consulta(self):
        self.client.login(
            username="consulta_org",
            password="TestOnly-Consulta-Org",
        )

    def test_admin_can_create_company(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "organization:create",
                kwargs={"entity": "empresa"},
            ),
            {
                "codigo": "EMP2",
                "nombre": "Empresa 2",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Empresa.objects.filter(
                codigo="EMP2"
            ).exists()
        )

    def test_consulta_cannot_create_company(self):
        self.login_consulta()

        response = self.client.post(
            reverse(
                "organization:create",
                kwargs={"entity": "empresa"},
            ),
            {
                "codigo": "NO-PERMITIDA",
                "nombre": "No permitida",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Empresa.objects.filter(
                codigo="NO-PERMITIDA"
            ).exists()
        )

    def test_duplicate_subordinate_code_same_parent_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "organization:create",
                kwargs={"entity": "area"},
            ),
            {
                "empresa": self.empresa.pk,
                "codigo": "AREA1",
                "nombre": "Duplicada",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Area.objects.filter(
                empresa=self.empresa,
                codigo="AREA1",
            ).count(),
            1,
        )

    def test_same_subordinate_code_different_parent_is_allowed(self):
        self.login_admin()

        empresa2 = Empresa.objects.create(
            codigo="EMP3",
            nombre="Empresa 3",
        )

        response = self.client.post(
            reverse(
                "organization:create",
                kwargs={"entity": "area"},
            ),
            {
                "empresa": empresa2.pk,
                "codigo": "AREA1",
                "nombre": "Área 1 otra empresa",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Area.objects.filter(
                empresa=empresa2,
                codigo="AREA1",
            ).exists()
        )

    def test_invalid_parent_reference_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "organization:create",
                kwargs={"entity": "departamento"},
            ),
            {
                "area": 999999,
                "codigo": "DEP-X",
                "nombre": "Departamento inválido",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Departamento.objects.filter(
                codigo="DEP-X"
            ).exists()
        )

    def test_parent_with_active_dependency_cannot_be_deactivated(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "organization:toggle",
                kwargs={
                    "entity": "empresa",
                    "pk": self.empresa.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        self.empresa.refresh_from_db()

        self.assertTrue(
            self.empresa.activo
        )

    def test_leaf_without_dependencies_can_be_deactivated(self):
        self.login_admin()

        leaf = Puesto.objects.create(
            seccion=self.seccion,
            codigo="LEAF",
            nombre="Puesto sin usuarios",
        )

        response = self.client.post(
            reverse(
                "organization:toggle",
                kwargs={
                    "entity": "puesto",
                    "pk": leaf.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        leaf.refresh_from_db()

        self.assertFalse(
            leaf.activo
        )


class OrganizationHierarchyRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            codigo="EMP-P04",
            nombre="Empresa P04",
        )

        cls.area = Area.objects.create(
            empresa=cls.empresa,
            codigo="AREA-P04",
            nombre="Área P04",
        )

        cls.departamento = Departamento.objects.create(
            area=cls.area,
            codigo="DEP-P04",
            nombre="Departamento P04",
        )

        cls.seccion = Seccion.objects.create(
            departamento=cls.departamento,
            codigo="SEC-P04",
            nombre="Sección P04",
        )

        cls.puesto = Puesto.objects.create(
            seccion=cls.seccion,
            codigo="PUE-P04",
            nombre="Puesto P04",
        )

        cls.usuario = User.objects.create_user(
            username="usuario_p04",
            email="usuario_p04@example.local",
            password="TestOnly-P04",
            puesto=cls.puesto,
            rol=User.Rol.CONSULTA,
        )

    def test_hierarchy_and_user_are_recoverable(self):
        user = (
            User.objects
            .select_related(
                "puesto__seccion__departamento__area__empresa"
            )
            .get(pk=self.usuario.pk)
        )

        self.assertEqual(
            user.puesto,
            self.puesto,
        )

        self.assertEqual(
            user.puesto.seccion,
            self.seccion,
        )

        self.assertEqual(
            user.puesto.seccion.departamento,
            self.departamento,
        )

        self.assertEqual(
            user.puesto.seccion.departamento.area,
            self.area,
        )

        self.assertEqual(
            user.puesto.seccion.departamento.area.empresa,
            self.empresa,
        )
