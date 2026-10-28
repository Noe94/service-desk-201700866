import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    ClaseServicio,
    Criticidad,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)
from apps.imports.models import (
    Importacion,
    ObservacionImportacion,
    RegistroImportacion,
)
from apps.imports.services.excel_catalog import CatalogWorkbookReader


def file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def optional_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def optional_decimal(value):
    if value is None or str(value).strip() == "":
        return None

    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"No se pudo interpretar como número: {value}"
        ) from exc


def parse_active(value):
    normalized = str(value or "").strip().upper()

    if normalized == "S":
        return True

    if normalized == "N":
        return False

    return None


class CatalogImporter:
    def __init__(
        self,
        path,
        sheet_name="Servicios Externos",
        verify_original=False,
    ):
        self.path = Path(path)
        self.sheet_name = sheet_name
        self.verify_original = verify_original

    def run(self):
        reader = CatalogWorkbookReader(
            self.path,
            self.sheet_name,
        )

        parsed = reader.parse()

        if self.verify_original:
            self._verify_original(parsed)

        importacion = Importacion.objects.create(
            archivo_nombre=self.path.name,
            archivo_sha256=file_sha256(self.path),
            hoja=parsed["hoja"],
        )

        try:
            with transaction.atomic():
                summary = self._persist(
                    importacion,
                    parsed,
                )

            importacion.creados = summary["creados"]
            importacion.actualizados = summary["actualizados"]
            importacion.omitidos = summary["omitidos"]
            importacion.observados = summary["observados"]
            importacion.estado = Importacion.Estado.COMPLETADA
            importacion.finalizado_en = timezone.now()

            importacion.save(
                update_fields=[
                    "creados",
                    "actualizados",
                    "omitidos",
                    "observados",
                    "estado",
                    "finalizado_en",
                ]
            )

            return importacion, summary

        except Exception:
            importacion.estado = Importacion.Estado.FALLIDA
            importacion.finalizado_en = timezone.now()

            importacion.save(
                update_fields=[
                    "estado",
                    "finalizado_en",
                ]
            )

            raise

    def _verify_original(self, parsed):
        n1_count = len(parsed["nivel1"])
        n2_count = len(parsed["nivel2"])

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
            raise ValidationError("; ".join(errors))

    def _persist(self, importacion, parsed):
        counters = {
            "creados": 0,
            "actualizados": 0,
            "omitidos": 0,
            "observados": 0,
            "n1": len(parsed["nivel1"]),
            "n2": len(parsed["nivel2"]),
        }

        catalogs = self._sync_catalogs(
            parsed["opciones"]
        )

        n1_objects = self._sync_n1(
            importacion,
            parsed["nivel1"],
            counters,
        )

        self._sync_n2(
            importacion,
            parsed["nivel2"],
            n1_objects,
            catalogs,
            counters,
        )

        self._save_observations(
            importacion,
            parsed["observaciones"],
            counters,
        )

        return counters

    def _sync_catalogs(self, options):
        classes = {}

        for name in options["clase"]:
            obj, _ = ClaseServicio.objects.get_or_create(
                nombre=name
            )
            classes[name] = obj

        criticalities = {}

        for name in options["criticidad"]:
            obj, _ = Criticidad.objects.get_or_create(
                nombre=name
            )
            criticalities[name] = obj

        types = {}

        for name in options["tipo"]:
            obj, _ = TipoServicio.objects.get_or_create(
                nombre=name
            )
            types[name] = obj

        return {
            "clase": classes,
            "criticidad": criticalities,
            "tipo": types,
        }

    def _sync_n1(
        self,
        importacion,
        rows,
        counters,
    ):
        objects = {}

        for row in rows:
            obj = ServicioNivel1.objects.filter(
                codigo=row["codigo"]
            ).first()

            if obj is None:
                obj = ServicioNivel1(
                    codigo=row["codigo"],
                    nombre=row["nombre"],
                )

                obj.full_clean()
                obj.save()

                result = RegistroImportacion.Resultado.CREADO
                counters["creados"] += 1

            elif obj.nombre != row["nombre"]:
                obj.nombre = row["nombre"]

                obj.full_clean()
                obj.save(
                    update_fields=[
                        "nombre",
                        "actualizado_en",
                    ]
                )

                result = RegistroImportacion.Resultado.ACTUALIZADO
                counters["actualizados"] += 1

            else:
                result = RegistroImportacion.Resultado.OMITIDO
                counters["omitidos"] += 1

            objects[obj.codigo] = obj

            RegistroImportacion.objects.create(
                importacion=importacion,
                hoja=self.sheet_name,
                fila_inicio=row["fila_inicio"],
                fila_fin=row["fila_fin"],
                rango_origen=row["rango_origen"],
                codigo_n1_original=row["codigo"],
                nombre_n1_original=row["nombre"],
                servicio_nivel1=obj,
                resultado=result,
            )

        return objects

    def _sync_n2(
        self,
        importacion,
        rows,
        n1_objects,
        catalogs,
        counters,
    ):
        for row in rows:
            parent = n1_objects.get(
                row["nivel1_codigo"]
            )

            if parent is None:
                raise ValidationError(
                    "No existe el servicio N1 "
                    f"{row['nivel1_codigo']} requerido "
                    f"por {row['codigo']}."
                )

            clase = (
                catalogs["clase"].get(row["clase"])
                if row["clase"]
                else None
            )

            criticidad = (
                catalogs["criticidad"].get(
                    row["criticidad"]
                )
                if row["criticidad"]
                else None
            )

            tipo = (
                catalogs["tipo"].get(row["tipo"])
                if row["tipo"]
                else None
            )

            desired = {
                "nivel1": parent,
                "nombre": row["nombre"],
                "activo": parse_active(
                    row["activo_original"]
                ),
                "activo_original": row["activo_original"],
                "clase": clase,
                "criticidad": criticidad,
                "tipo": tipo,
                "descripcion": optional_text(
                    row["descripcion"]
                ),
                "metrica": optional_text(
                    row["metrica"]
                ),
                "minimo": optional_decimal(
                    row["minimo"]
                ),
                "maximo": optional_decimal(
                    row["maximo"]
                ),
                "requiere_revision": row[
                    "requiere_revision"
                ],
            }

            obj = ServicioNivel2.objects.filter(
                codigo=row["codigo"]
            ).first()

            if obj is None:
                obj = ServicioNivel2(
                    codigo=row["codigo"],
                    **desired,
                )

                obj.full_clean()
                obj.save()

                result = RegistroImportacion.Resultado.CREADO
                counters["creados"] += 1

            elif self._has_changes(obj, desired):
                for field, value in desired.items():
                    setattr(obj, field, value)

                obj.full_clean()
                obj.save()

                result = RegistroImportacion.Resultado.ACTUALIZADO
                counters["actualizados"] += 1

            else:
                result = RegistroImportacion.Resultado.OMITIDO
                counters["omitidos"] += 1

            RegistroImportacion.objects.create(
                importacion=importacion,
                hoja=self.sheet_name,
                fila_inicio=row["fila_inicio"],
                fila_fin=row["fila_fin"],
                rango_origen=row["rango_origen"],
                codigo_n1_original=row["nivel1_codigo"],
                nombre_n1_original=row["nivel1_nombre"],
                codigo_n2_original=row["codigo"],
                nombre_n2_original=row["nombre"],
                servicio_nivel1=parent,
                servicio_nivel2=obj,
                resultado=result,
                transformaciones=row["transformaciones"],
            )

    def _has_changes(self, obj, desired):
        for field, expected in desired.items():
            current = getattr(obj, field)

            if field in {
                "nivel1",
                "clase",
                "criticidad",
                "tipo",
            }:
                current_id = (
                    current.pk
                    if current is not None
                    else None
                )

                expected_id = (
                    expected.pk
                    if expected is not None
                    else None
                )

                if current_id != expected_id:
                    return True

            elif current != expected:
                return True

        return False

    def _save_observations(
        self,
        importacion,
        observations,
        counters,
    ):
        for observation in observations:
            ObservacionImportacion.objects.create(
                importacion=importacion,
                tipo=observation["tipo"],
                nivel=observation["nivel"],
                codigo=observation["codigo"],
                mensaje=observation["mensaje"],
                hoja=self.sheet_name,
                fila_inicio=observation["fila_inicio"],
                fila_fin=observation["fila_fin"],
                rango_origen=observation["rango_origen"],
                valores_originales=observation[
                    "valores_originales"
                ],
                valor_canonico=observation[
                    "valor_canonico"
                ],
            )

            counters["observados"] += 1
