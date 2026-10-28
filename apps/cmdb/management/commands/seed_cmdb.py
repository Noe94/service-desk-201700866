import random
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import ServicioNivel2
from apps.cmdb.models import CI, CIClass, CIRelation, Location


CLASSES = [
    ("ROOT", "Elemento de configuración", None, "PROYECTO", False),
    ("HARDWARE", "Hardware", "ROOT", "EXCEL", False),
    ("SOFTWARE", "Software", "ROOT", "EXCEL", False),
    ("SERVIDOR", "Servidor", "HARDWARE", "PROYECTO", True),
    ("ESTACION", "Estación de trabajo", "HARDWARE", "PROYECTO", True),
    ("PORTATIL", "Computadora portátil", "HARDWARE", "PROYECTO", True),
    ("SWITCH", "Switch de red", "HARDWARE", "PROYECTO", True),
    ("ROUTER", "Router", "HARDWARE", "PROYECTO", True),
    ("APLICACION", "Aplicación", "SOFTWARE", "PROYECTO", False),
    ("SISTEMA_OPERATIVO", "Sistema operativo", "SOFTWARE", "PROYECTO", False),
    ("BASE_DATOS", "Base de datos", "SOFTWARE", "PROYECTO", False),
]


class Command(BaseCommand):
    help = "Genera al menos 5000 dispositivos CMDB sintéticos, con semilla y sin duplicados."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=201700866)
        parser.add_argument("--count", type=int, default=5000)

    @transaction.atomic
    def handle(self, *args, **opts):
        count, seed = opts["count"], opts["seed"]
        if count < 5000 or count > 100000:
            raise CommandError("La cantidad debe estar entre 5000 y 100000.")
        if seed < 0 or seed > 999999999:
            raise CommandError("La semilla debe estar entre 0 y 999999999.")
        users = list(get_user_model().objects.filter(is_active=True).order_by("pk"))
        services = list(ServicioNivel2.objects.exclude(activo=False).order_by("codigo"))
        if not users or not services:
            raise CommandError("Primero ejecute import_catalog y seed_demo.")

        classes = {}
        for code, name, parent, source, is_device in CLASSES:
            obj, created = CIClass.objects.get_or_create(code=code, defaults={
                "name": name, "parent": classes.get(parent), "source": source,
                "is_device": is_device,
            })
            if not created and (obj.parent_id != (classes.get(parent).pk if parent else None) or obj.is_device != is_device):
                raise CommandError(f"La clase {code} existe con una estructura distinta; revise la CMDB.")
            classes[code] = obj
        locations = []
        for code, name in [
            ("DC01", "Centro de datos ficticio A"),
            ("SEDE01", "Sede ficticia central"),
            ("SEDE02", "Sede ficticia regional"),
            ("ALMACEN", "Bodega ficticia de TI"),
        ]:
            loc, _ = Location.objects.get_or_create(code=code, defaults={"name": name})
            locations.append(loc)

        rng = random.Random(seed)
        device_classes = [classes[code] for code in ["SERVIDOR", "ESTACION", "PORTATIL", "SWITCH", "ROUTER"]]
        codes = [f"CI-{seed:09d}-{i:06d}" for i in range(1, count + 1)]
        existing = set(CI.objects.filter(code__in=codes).values_list("code", flat=True))
        rows = []
        distribution = Counter()
        for index, code in enumerate(codes, start=1):
            kind = device_classes[(index - 1) % len(device_classes)]
            distribution[kind.code] += 1
            # Generar todos los valores en cada repetición asegura los mismos resultados.
            loc = locations[rng.randrange(len(locations))]
            owner = users[rng.randrange(len(users))]
            octets = (10, 200 + (index // 65536) % 50, (index // 256) % 256, index % 256)
            attrs = {"fabricante": "Fabricante sintético", "modelo": f"{kind.code}-{index % 12 + 1:02d}"}
            if kind.code in {"SERVIDOR", "ESTACION", "PORTATIL"}:
                attrs.update({"cpu": f"{4 + (index % 4) * 4} núcleos", "ram_gb": [8, 16, 32, 64][index % 4]})
            if kind.code in {"SERVIDOR", "SWITCH", "ROUTER"}:
                attrs["ip"] = ".".join(map(str, octets))
            if code not in existing:
                rows.append(CI(
                    code=code, name=f"{kind.name} sintético {index:06d}",
                    classification=kind, description="Activo generado para evaluación académica",
                    serial_number=f"DEMO-{seed:09d}-{index:06d}", status=CI.State.ACTIVE,
                    location=loc, owner=owner, security_level="Medio",
                    compliance="Demostración", configuration_status="Aprobado",
                    attributes=attrs,
                ))
        CI.objects.bulk_create(rows, batch_size=750)
        # Asociación reproducible a servicios existentes (no crea servicios inventados).
        through = CI.services.through
        existing_links = set(through.objects.filter(ci__code__in=codes).values_list("ci_id", flat=True))
        links = []
        for i, ci in enumerate(CI.objects.filter(code__in=codes).only("pk").order_by("code")):
            if ci.pk not in existing_links:
                links.append(through(ci_id=ci.pk, servicionivel2_id=services[i % len(services)].pk))
        through.objects.bulk_create(links, batch_size=1000, ignore_conflicts=True)
        # Grafo técnico de ejemplo para navegación desde un clon limpio.
        # No altera otras relaciones del usuario y las claves son fijas por semilla.
        demo_nodes = list(CI.objects.filter(code__in=codes[:18]).order_by("code"))
        relation_pairs = [
            (0, 1, CIRelation.Type.DEPENDS), (2, 1, CIRelation.Type.DEPENDS),
            (3, 2, CIRelation.Type.HOSTED), (4, 3, CIRelation.Type.DEPENDS),
            (5, 3, CIRelation.Type.HOSTED), (6, 5, CIRelation.Type.DEPENDS),
            (7, 6, CIRelation.Type.DEPENDS), (8, 6, CIRelation.Type.HOSTED),
            (9, 8, CIRelation.Type.DEPENDS), (10, 11, CIRelation.Type.CONNECTED),
            (11, 10, CIRelation.Type.CONNECTED),
        ]
        for source, target, kind in relation_pairs:
            CIRelation.objects.get_or_create(
                source=demo_nodes[source], target=demo_nodes[target], relation_type=kind,
            )
        actual_count = CI.objects.filter(code__in=codes, classification__is_device=True).count()
        if actual_count != count:
            raise CommandError(f"Conteo inválido: {actual_count} dispositivos, se esperaban {count}.")
        self.stdout.write(self.style.SUCCESS(
            f"CMDB: semilla={seed}; esperados={count}; encontrados={actual_count}; nuevos={len(rows)}; "
            f"servicios vinculados={len(links)}; relaciones de ejemplo=11"
        ))
        self.stdout.write("Distribución: " + ", ".join(f"{k}={v}" for k, v in sorted(distribution.items())))
