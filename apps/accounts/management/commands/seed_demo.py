import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import (
    Area,
    Departamento,
    Empresa,
    Puesto,
    Seccion,
)


User = get_user_model()


class Command(BaseCommand):
    help = "Crea o actualiza datos y usuarios demo reproducibles."

    @transaction.atomic
    def handle(self, *args, **options):
        admin_password = os.getenv("DEMO_ADMIN_PASSWORD")
        consulta_password = os.getenv("DEMO_CONSULTA_PASSWORD")

        if not admin_password or not consulta_password:
            raise CommandError(
                "Debe definir DEMO_ADMIN_PASSWORD y "
                "DEMO_CONSULTA_PASSWORD en el entorno."
            )

        empresa, _ = Empresa.objects.update_or_create(
            codigo="EMP-DEMO",
            defaults={
                "nombre": "Empresa Demo",
                "activo": True,
            },
        )

        area, _ = Area.objects.update_or_create(
            empresa=empresa,
            codigo="TI",
            defaults={
                "nombre": "Tecnología de Información",
                "activo": True,
            },
        )

        departamento, _ = Departamento.objects.update_or_create(
            area=area,
            codigo="SERV",
            defaults={
                "nombre": "Servicios de TI",
                "activo": True,
            },
        )

        seccion, _ = Seccion.objects.update_or_create(
            departamento=departamento,
            codigo="CAT",
            defaults={
                "nombre": "Gestión del Catálogo",
                "activo": True,
            },
        )

        puesto_admin, _ = Puesto.objects.update_or_create(
            seccion=seccion,
            codigo="ADMIN",
            defaults={
                "nombre": "Administrador del Catálogo",
                "activo": True,
            },
        )

        puesto_consulta, _ = Puesto.objects.update_or_create(
            seccion=seccion,
            codigo="CONSULTA",
            defaults={
                "nombre": "Consulta del Catálogo",
                "activo": True,
            },
        )

        admin, _ = User.objects.update_or_create(
            username="admin_demo",
            defaults={
                "email": "admin_demo@example.local",
                "first_name": "Administrador",
                "last_name": "Demo",
                "rol": User.Rol.ADMINISTRADOR,
                "puesto": puesto_admin,
                "is_active": True,
            },
        )

        admin.set_password(admin_password)
        admin.save()

        consulta, _ = User.objects.update_or_create(
            username="consulta_demo",
            defaults={
                "email": "consulta_demo@example.local",
                "first_name": "Consulta",
                "last_name": "Demo",
                "rol": User.Rol.CONSULTA,
                "puesto": puesto_consulta,
                "is_active": True,
            },
        )

        consulta.set_password(consulta_password)
        consulta.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Datos demo creados o actualizados correctamente."
            )
        )

        self.stdout.write(
            "Usuarios disponibles: admin_demo, consulta_demo"
        )

        self.stdout.write(
            "Las contraseñas se obtuvieron del entorno y no se muestran."
        )
