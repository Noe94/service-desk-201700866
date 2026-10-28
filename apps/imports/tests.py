from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import (
    ServicioNivel1,
    ServicioNivel2,
)
from apps.imports.models import (
    Importacion,
    ObservacionImportacion,
)
from apps.imports.services.catalog_importer import CatalogImporter
from apps.imports.services.excel_catalog import CatalogWorkbookReader


EXCEL_PATH = (
    Path(settings.BASE_DIR)
    / "data"
    / "CatalogoServicios.xlsx"
)


class CatalogWorkbookAnalysisTests(TestCase):
    def test_original_workbook_has_expected_counts(self):
        reader = CatalogWorkbookReader(EXCEL_PATH)

        result = reader.parse()

        self.assertEqual(len(result["nivel1"]), 12)
        self.assertEqual(len(result["nivel2"]), 46)
        self.assertEqual(len(result["observaciones"]), 5)

    def test_original_workbook_detects_se12_conflict(self):
        reader = CatalogWorkbookReader(EXCEL_PATH)

        result = reader.parse()

        conflicts = [
            item
            for item in result["observaciones"]
            if item["tipo"] == "CONFLICTING_N1_NAME"
        ]

        self.assertEqual(len(conflicts), 1)

        conflict = conflicts[0]

        self.assertEqual(conflict["codigo"], "SE.12")
        self.assertEqual(
            conflict["valor_canonico"],
            "Suministrar Analitica",
        )


class CatalogImportTests(TestCase):
    def import_original(self):
        importer = CatalogImporter(
            path=EXCEL_PATH,
            verify_original=True,
        )

        return importer.run()

    def test_original_import_creates_expected_services(self):
        importacion, summary = self.import_original()

        self.assertEqual(summary["n1"], 12)
        self.assertEqual(summary["n2"], 46)

        self.assertEqual(summary["creados"], 58)
        self.assertEqual(summary["actualizados"], 0)
        self.assertEqual(summary["omitidos"], 0)
        self.assertEqual(summary["observados"], 5)

        self.assertEqual(
            ServicioNivel1.objects.count(),
            12,
        )

        self.assertEqual(
            ServicioNivel2.objects.count(),
            46,
        )

        self.assertEqual(
            importacion.estado,
            Importacion.Estado.COMPLETADA,
        )

    def test_repeated_import_is_idempotent(self):
        self.import_original()

        _, second_summary = self.import_original()

        self.assertEqual(second_summary["creados"], 0)
        self.assertEqual(second_summary["actualizados"], 0)
        self.assertEqual(second_summary["omitidos"], 58)
        self.assertEqual(second_summary["observados"], 5)

        self.assertEqual(
            ServicioNivel1.objects.count(),
            12,
        )

        self.assertEqual(
            ServicioNivel2.objects.count(),
            46,
        )

        self.assertEqual(
            Importacion.objects.count(),
            2,
        )

    def test_se12_uses_canonical_name(self):
        self.import_original()

        service = ServicioNivel1.objects.get(
            codigo="SE.12"
        )

        self.assertEqual(
            service.nombre,
            "Suministrar Analitica",
        )

        observation = (
            ObservacionImportacion.objects
            .filter(
                tipo="CONFLICTING_N1_NAME",
                codigo="SE.12",
            )
            .first()
        )

        self.assertIsNotNone(observation)

        self.assertEqual(
            observation.valor_canonico,
            "Suministrar Analitica",
        )

    def test_se12_children_keep_original_codes_and_nulls(self):
        self.import_original()

        services = list(
            ServicioNivel2.objects
            .filter(codigo__startswith="SE.12.")
            .order_by("codigo")
        )

        self.assertEqual(
            [item.codigo for item in services],
            [
                "SE.12.1",
                "SE.12.2",
                "SE.12.3",
            ],
        )

        for service in services:
            self.assertIsNone(service.activo)
            self.assertIsNone(service.clase)
            self.assertIsNone(service.criticidad)
            self.assertIsNone(service.tipo)

            self.assertTrue(
                service.requiere_revision
            )

    def test_import_records_file_hash(self):
        importacion, _ = self.import_original()

        self.assertEqual(
            importacion.archivo_sha256,
            (
                "de3b478a5faeeeaebce1aa7726e0e332"
                "1188a68e41bbb656e1d17b0c5b74dcf0"
            ),
        )


class ServiceValidationTests(TestCase):
    def test_minimum_cannot_be_greater_than_maximum(self):
        parent = ServicioNivel1.objects.create(
            codigo="TEST.01",
            nombre="Servicio de prueba",
        )

        service = ServicioNivel2(
            nivel1=parent,
            codigo="TEST.01.01",
            nombre="Servicio inválido",
            minimo=100,
            maximo=50,
        )

        with self.assertRaises(ValidationError):
            service.full_clean()
