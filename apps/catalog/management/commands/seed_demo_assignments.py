from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import ServicioNivel2
from apps.organization.models import Seccion


User = get_user_model()


class Command(BaseCommand):
    help = "Asigna responsables válidos a tres servicios demo."

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            section = Seccion.objects.get(
                codigo="CAT",
                departamento__codigo="SERV",
            )

            admin = User.objects.get(
                username="admin_demo"
            )

            consulta = User.objects.get(
                username="consulta_demo"
            )

        except (
            Seccion.DoesNotExist,
            User.DoesNotExist,
        ) as exc:
            raise CommandError(
                "Primero debe ejecutar seed_demo."
            ) from exc

        services = list(
            ServicioNivel2.objects
            .order_by("codigo")[:3]
        )

        if len(services) < 3:
            raise CommandError(
                "Se requieren al menos tres servicios N2 "
                "importados."
            )

        users = [
            admin,
            consulta,
            admin,
        ]

        for service, user in zip(
            services,
            users,
            strict=True,
        ):
            service.seccion_responsable = section
            service.usuario_responsable = user

            service.full_clean()

            service.save(
                update_fields=[
                    "seccion_responsable",
                    "usuario_responsable",
                    "actualizado_en",
                ]
            )

            self.stdout.write(
                f"{service.codigo} -> "
                f"{section.codigo} / "
                f"{user.username}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "3 asignaciones demo válidas configuradas."
            )
        )
