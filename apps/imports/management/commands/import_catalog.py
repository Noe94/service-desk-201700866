from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import (
    ServicioNivel1,
    ServicioNivel2,
)
from apps.imports.services.catalog_importer import CatalogImporter


class Command(BaseCommand):
    help = "Importa de forma idempotente el catálogo de servicios."

    def add_arguments(self, parser):
        parser.add_argument("path")

        parser.add_argument(
            "--sheet",
            default="Servicios Externos",
        )

        parser.add_argument(
            "--verify-original",
            action="store_true",
            help=(
                "Valida los controles 12 N1 y 46 N2 "
                "del archivo original."
            ),
        )

    def handle(self, *args, **options):
        try:
            importer = CatalogImporter(
                path=options["path"],
                sheet_name=options["sheet"],
                verify_original=options["verify_original"],
            )

            importacion, summary = importer.run()

        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("")
        self.stdout.write("IMPORTACIÓN COMPLETADA")
        self.stdout.write("---------------------")

        self.stdout.write(
            f"Importación ID: {importacion.pk}"
        )

        self.stdout.write(
            f"SHA-256: {importacion.archivo_sha256}"
        )

        self.stdout.write(
            f"N1 procesados: {summary['n1']}"
        )

        self.stdout.write(
            f"N2 procesados: {summary['n2']}"
        )

        self.stdout.write(
            f"Creados: {summary['creados']}"
        )

        self.stdout.write(
            f"Actualizados: {summary['actualizados']}"
        )

        self.stdout.write(
            f"Omitidos: {summary['omitidos']}"
        )

        self.stdout.write(
            f"Observados: {summary['observados']}"
        )

        self.stdout.write("")
        self.stdout.write("ESTADO ACTUAL")

        self.stdout.write(
            f"Servicios N1 en BD: "
            f"{ServicioNivel1.objects.count()}"
        )

        self.stdout.write(
            f"Servicios N2 en BD: "
            f"{ServicioNivel2.objects.count()}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "La importación finalizó correctamente."
            )
        )
