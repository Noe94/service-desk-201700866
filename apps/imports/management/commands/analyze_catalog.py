from django.core.management.base import BaseCommand, CommandError

from apps.imports.services.excel_catalog import CatalogWorkbookReader


class Command(BaseCommand):
    help = "Analiza el Excel del catálogo sin modificar la base de datos."

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
                "Comprueba los controles 12 N1 y 46 N2 "
                "del archivo original de evaluación."
            ),
        )

    def handle(self, *args, **options):
        try:
            reader = CatalogWorkbookReader(
                options["path"],
                options["sheet"],
            )

            result = reader.parse()

        except Exception as exc:
            raise CommandError(str(exc)) from exc

        n1_count = len(result["nivel1"])
        n2_count = len(result["nivel2"])

        self.stdout.write("")
        self.stdout.write("ANÁLISIS DEL CATÁLOGO")
        self.stdout.write("--------------------")

        self.stdout.write(
            f"Hoja: {result['hoja']}"
        )

        self.stdout.write(
            f"Fila de encabezados: "
            f"{result['fila_encabezado']}"
        )

        self.stdout.write(
            f"Fila de opciones: "
            f"{result['fila_opciones']}"
        )

        self.stdout.write(
            f"Servicios N1: {n1_count}"
        )

        self.stdout.write(
            f"Servicios N2: {n2_count}"
        )

        self.stdout.write(
            f"Observaciones: "
            f"{len(result['observaciones'])}"
        )

        self.stdout.write("")
        self.stdout.write("OPCIONES")

        for key, values in result["opciones"].items():
            self.stdout.write(
                f"- {key}: {', '.join(values)}"
            )

        self.stdout.write("")
        self.stdout.write("OBSERVACIONES")

        for observation in result["observaciones"]:
            self.stdout.write(
                f"- {observation['tipo']} | "
                f"{observation['codigo']} | "
                f"fila {observation['fila_inicio']}"
            )

        if options["verify_original"]:
            errors = []

            if n1_count != 12:
                errors.append(
                    f"Esperado N1=12, obtenido N1={n1_count}"
                )

            if n2_count != 46:
                errors.append(
                    f"Esperado N2=46, obtenido N2={n2_count}"
                )

            if errors:
                raise CommandError(
                    "; ".join(errors)
                )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Control del archivo original: OK (12 N1 / 46 N2)"
                )
            )
