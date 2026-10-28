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


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Empresa.objects.create(
            codigo="EMP-TEST",
            nombre="Empresa de prueba",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="AREA-TEST",
            nombre="Área de prueba",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="DEP-TEST",
            nombre="Departamento de prueba",
        )

        seccion = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-TEST",
            nombre="Sección de prueba",
        )

        cls.puesto = Puesto.objects.create(
            seccion=seccion,
            codigo="PUE-TEST",
            nombre="Puesto de prueba",
        )

        cls.user = User.objects.create_user(
            username="usuario_test",
            email="usuario_test@example.local",
            password="TestOnly-Password-001",
            puesto=cls.puesto,
            rol=User.Rol.CONSULTA,
        )

    def test_valid_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "usuario_test",
                "password": "TestOnly-Password-001",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
        )

    def test_valid_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "usuario_test@example.local",
                "password": "TestOnly-Password-001",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
        )

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "usuario_test",
                "password": "incorrecta",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_protected_page_requires_session(self):
        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "usuario_test",
                "password": "TestOnly-Password-001",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_invalidates_session(self):
        logged_in = self.client.login(
            username="usuario_test",
            password="TestOnly-Password-001",
        )

        self.assertTrue(logged_in)

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertEqual(response.status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )


class AuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Empresa.objects.create(
            codigo="EMP-AUTH",
            nombre="Empresa autorización",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="AREA-AUTH",
            nombre="Área autorización",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="DEP-AUTH",
            nombre="Departamento autorización",
        )

        seccion = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-AUTH",
            nombre="Sección autorización",
        )

        puesto = Puesto.objects.create(
            seccion=seccion,
            codigo="PUE-AUTH",
            nombre="Puesto autorización",
        )

        cls.admin_user = User.objects.create_user(
            username="admin_auth_test",
            email="admin_auth_test@example.local",
            password="TestOnly-Admin-001",
            puesto=puesto,
            rol=User.Rol.ADMINISTRADOR,
        )

        cls.consulta_user = User.objects.create_user(
            username="consulta_auth_test",
            email="consulta_auth_test@example.local",
            password="TestOnly-Consulta-001",
            puesto=puesto,
            rol=User.Rol.CONSULTA,
        )

    def test_admin_can_access_admin_operation(self):
        self.client.login(
            username="admin_auth_test",
            password="TestOnly-Admin-001",
        )

        response = self.client.get(
            reverse("accounts:user_create")
        )

        self.assertEqual(response.status_code, 200)

    def test_consulta_is_rejected_by_server(self):
        self.client.login(
            username="consulta_auth_test",
            password="TestOnly-Consulta-001",
        )

        response = self.client.get(
            reverse("accounts:user_create")
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("accounts:user_create")
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )



class UserCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Empresa.objects.create(
            codigo="EMP-USERS",
            nombre="Empresa usuarios",
        )

        area = Area.objects.create(
            empresa=empresa,
            codigo="AREA-USERS",
            nombre="Área usuarios",
        )

        departamento = Departamento.objects.create(
            area=area,
            codigo="DEP-USERS",
            nombre="Departamento usuarios",
        )

        seccion = Seccion.objects.create(
            departamento=departamento,
            codigo="SEC-USERS",
            nombre="Sección usuarios",
        )

        cls.puesto = Puesto.objects.create(
            seccion=seccion,
            codigo="PUE-USERS",
            nombre="Puesto usuarios",
        )

        cls.admin = User.objects.create_user(
            username="admin_users",
            email="admin_users@example.local",
            password="TestOnly-Admin-Users",
            puesto=cls.puesto,
            rol=User.Rol.ADMINISTRADOR,
        )

        cls.consulta = User.objects.create_user(
            username="consulta_users",
            email="consulta_users@example.local",
            password="TestOnly-Consulta-Users",
            puesto=cls.puesto,
            rol=User.Rol.CONSULTA,
        )

    def login_admin(self):
        self.client.login(
            username="admin_users",
            password="TestOnly-Admin-Users",
        )

    def login_consulta(self):
        self.client.login(
            username="consulta_users",
            password="TestOnly-Consulta-Users",
        )

    def test_admin_can_create_user(self):
        self.login_admin()

        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "nuevo_usuario",
                "email": "nuevo_usuario@example.local",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "rol": User.Rol.CONSULTA,
                "puesto": self.puesto.pk,
                "password1": "TestOnly-New-User",
                "password2": "TestOnly-New-User",
            },
        )

        self.assertEqual(response.status_code, 302)

        user = User.objects.get(
            username="nuevo_usuario"
        )

        self.assertEqual(
            user.rol,
            User.Rol.CONSULTA,
        )

        self.assertEqual(
            user.puesto,
            self.puesto,
        )

        self.assertTrue(
            user.check_password(
                "TestOnly-New-User"
            )
        )

    def test_consulta_cannot_create_user(self):
        self.login_consulta()

        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "usuario_prohibido",
                "email": "prohibido@example.local",
                "first_name": "No",
                "last_name": "Permitido",
                "rol": User.Rol.CONSULTA,
                "puesto": self.puesto.pk,
                "password1": "TestOnly-Prohibited",
                "password2": "TestOnly-Prohibited",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            User.objects.filter(
                username="usuario_prohibido"
            ).exists()
        )

    def test_duplicate_email_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "otro_usuario",
                "email": self.consulta.email,
                "first_name": "Otro",
                "last_name": "Usuario",
                "rol": User.Rol.CONSULTA,
                "puesto": self.puesto.pk,
                "password1": "TestOnly-Other-User",
                "password2": "TestOnly-Other-User",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            User.objects.filter(
                username="otro_usuario"
            ).exists()
        )

    def test_admin_can_deactivate_other_user(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:user_toggle",
                kwargs={
                    "pk": self.consulta.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.consulta.refresh_from_db()

        self.assertFalse(
            self.consulta.is_active
        )

    def test_admin_cannot_deactivate_own_account(self):
        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:user_toggle",
                kwargs={
                    "pk": self.admin.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.admin.refresh_from_db()

        self.assertTrue(
            self.admin.is_active
        )
