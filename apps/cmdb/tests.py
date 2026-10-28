from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import ServicioNivel1, ServicioNivel2
from apps.organization.models import Area, Departamento, Empresa, Puesto, Seccion

from .models import CI, CIClass, CIRelation, Location, potentially_affected_services


class CMDBTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = Empresa.objects.create(codigo="CMDB", nombre="Empresa CMDB")
        area = Area.objects.create(empresa=company, codigo="TI", nombre="TI")
        department = Departamento.objects.create(area=area, codigo="OPS", nombre="Operaciones")
        section = Seccion.objects.create(departamento=department, codigo="S", nombre="Soporte")
        position = Puesto.objects.create(seccion=section, codigo="P", nombre="Agente")
        cls.user = get_user_model().objects.create_user(
            username="cmdb_admin", email="cmdb_admin@example.local",
            password="Secure-12345!", rol="ADMIN", puesto=position,
        )
        n1 = ServicioNivel1.objects.create(codigo="CMDB-N1", nombre="Infraestructura")
        cls.service = ServicioNivel2.objects.create(nivel1=n1, codigo="CMDB-N2", nombre="Aplicación")
        cls.root = CIClass.objects.create(code="ROOT", name="CI")
        cls.hw = CIClass.objects.create(code="HARDWARE", name="Hardware", parent=cls.root, source="EXCEL")
        cls.servers = CIClass.objects.create(code="SERVIDOR", name="Servidor", parent=cls.hw, is_device=True)
        cls.location = Location.objects.create(code="L1", name="Sede ficticia")
        cls.a = CI.objects.create(code="CI-A", name="Servidor A", classification=cls.servers,
                                  location=cls.location, owner=cls.user)
        cls.b = CI.objects.create(code="CI-B", name="Servidor B", classification=cls.servers,
                                  location=cls.location, owner=cls.user)
        cls.c = CI.objects.create(code="CI-C", name="Servidor C", classification=cls.servers,
                                  location=cls.location, owner=cls.user)

    def test_source_classes_and_full_path(self):
        self.assertEqual(self.servers.full_path, "CI / Hardware / Servidor")
        self.assertEqual(self.hw.source, "EXCEL")

    def test_classification_rejects_cycle(self):
        self.root.parent = self.servers
        with self.assertRaises(ValidationError):
            self.root.full_clean()

    def test_relation_rejects_cycles_and_self_references(self):
        CIRelation.objects.create(source=self.a, target=self.b, relation_type="DEPENDE_DE")
        with self.assertRaises(ValidationError):
            CIRelation.objects.create(source=self.b, target=self.a, relation_type="ALOJADO_EN")
        with self.assertRaises(ValidationError):
            CIRelation.objects.create(source=self.a, target=self.a, relation_type="CONECTADO_A")

    def test_connected_cycles_permitted(self):
        CIRelation.objects.create(source=self.a, target=self.b, relation_type="CONECTADO_A")
        CIRelation.objects.create(source=self.b, target=self.a, relation_type="CONECTADO_A")
        self.assertEqual(CIRelation.objects.count(), 2)

    def test_dependency_traversal_is_inverse(self):
        self.a.services.add(self.service)
        CIRelation.objects.create(source=self.a, target=self.b, relation_type="DEPENDE_DE")
        CIRelation.objects.create(source=self.b, target=self.c, relation_type="ALOJADO_EN")
        self.assertEqual(list(potentially_affected_services(self.c)), [self.service])
        self.assertEqual(list(potentially_affected_services(self.a)), [self.service])

    def test_5000_unique_devices_and_idempotence(self):
        # Usa un conjunto identificado por semilla; ningún dato de producción es borrado.
        call_command("seed_cmdb", seed=27, count=5000, verbosity=0)
        first = CI.objects.filter(classification__is_device=True).count()
        self.assertEqual(first, 5003)
        self.assertEqual(CIRelation.objects.count(), 11)
        call_command("seed_cmdb", seed=27, count=5000, verbosity=0)
        self.assertEqual(CI.objects.filter(classification__is_device=True).count(), first)
        self.assertEqual(CIRelation.objects.count(), 11)
        self.assertEqual(CI.objects.exclude(code__in=["CI-A", "CI-B", "CI-C"]).count(), 5000)

    def test_ci_listing_filters_and_pagination(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cmdb:list"), {"q": "CI-A"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"].paginator.count, 1)
        response = self.client.get(reverse("cmdb:list"), {"clase": self.servers.pk})
        self.assertEqual(response.context["page"].paginator.count, 3)

    def test_ci_detail_shows_related_service(self):
        self.a.services.add(self.service)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cmdb:detail", args=[self.a.pk]))
        self.assertContains(response, self.service.codigo)

