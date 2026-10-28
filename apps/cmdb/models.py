from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class CIClass(models.Model):
    """Clasificación jerárquica; el Excel solo identifica Hardware y Software.

    Las subclases operativas son una ampliación explícita del proyecto.
    """

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    source = models.CharField(max_length=30, choices=[("EXCEL", "CMDB.xlsx"), ("PROYECTO", "Ampliación")], default="PROYECTO")
    is_device = models.BooleanField(default=False, help_text="Los 5,000 dispositivos se cuentan solo en clases marcadas.")

    class Meta:
        ordering = ["code"]

    def clean(self):
        super().clean()
        visited = {self.pk} if self.pk else set()
        node = self.parent
        while node is not None:
            if node.pk in visited:
                raise ValidationError({"parent": "La jerarquía no admite ciclos."})
            visited.add(node.pk)
            node = node.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def full_path(self):
        parts = []
        node = self
        visited = set()
        while node and node.pk not in visited:
            parts.append(node.name)
            visited.add(node.pk)
            node = node.parent
        return " / ".join(reversed(parts))

    def __str__(self):
        return self.full_path


class Location(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class CI(models.Model):
    class State(models.TextChoices):
        ACTIVE = "ACTIVO", "Activo"
        MAINTENANCE = "MANTENIMIENTO", "Mantenimiento"
        INACTIVE = "INACTIVO", "Inactivo"

    code = models.CharField(max_length=48, unique=True, help_text="Etiqueta adicional única del proyecto")
    name = models.CharField(max_length=180, help_text="CMDB.xlsx!B4")
    classification = models.ForeignKey(CIClass, on_delete=models.PROTECT, related_name="cis", help_text="CMDB.xlsx!C4")
    description = models.TextField(blank=True, help_text="CMDB.xlsx!D4")
    serial_number = models.CharField(max_length=100, blank=True, help_text="CMDB.xlsx!E4")
    version = models.CharField(max_length=60, blank=True, help_text="CMDB.xlsx!F4")
    acquired_on = models.DateField(null=True, blank=True, help_text="CMDB.xlsx!G4")
    status = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE, help_text="CMDB.xlsx!H4")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="cis", help_text="CMDB.xlsx!K4")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_cis", help_text="CMDB.xlsx!L4")
    last_changed_on = models.DateField(null=True, blank=True, help_text="CMDB.xlsx!M4")
    change_description = models.TextField(blank=True, help_text="CMDB.xlsx!N4")
    documentation = models.TextField(blank=True, help_text="CMDB.xlsx!O4")
    security_level = models.CharField(max_length=40, blank=True, help_text="CMDB.xlsx!Q4")
    compliance = models.CharField(max_length=80, blank=True, help_text="CMDB.xlsx!R4")
    configuration_status = models.CharField(max_length=50, blank=True, help_text="CMDB.xlsx!S4")
    license_number = models.CharField(max_length=100, blank=True, help_text="CMDB.xlsx!T4")
    expires_on = models.DateField(null=True, blank=True, help_text="CMDB.xlsx!U4")
    attributes = models.JSONField(default=dict, blank=True, help_text="Atributos adicionales propios de cada clase")
    services = models.ManyToManyField("catalog.ServicioNivel2", blank=True, related_name="configuration_items")
    tickets = models.ManyToManyField("service_desk.Ticket", blank=True, related_name="cis")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["classification", "status"]), models.Index(fields=["name"])]

    def clean(self):
        if self.owner_id and not self.owner.is_active:
            raise ValidationError({"owner": "El responsable debe estar activo."})
        if self.classification_id and self.classification.code == "ROOT":
            raise ValidationError({"classification": "Debe elegir una clase de CI específica."})

    def __str__(self):
        return f"{self.code} · {self.name}"


class CIRelation(models.Model):
    class Type(models.TextChoices):
        DEPENDS = "DEPENDE_DE", "Depende de"
        CONNECTED = "CONECTADO_A", "Conectado a"
        HOSTED = "ALOJADO_EN", "Alojado en"

    source = models.ForeignKey(CI, on_delete=models.PROTECT, related_name="out_relations")
    target = models.ForeignKey(CI, on_delete=models.PROTECT, related_name="in_relations")
    relation_type = models.CharField(max_length=16, choices=Type.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "target", "relation_type"], name="uq_cmdb_relation"),
            models.CheckConstraint(condition=~Q(source=F("target")), name="ck_cmdb_not_self"),
        ]

    def clean(self):
        super().clean()
        if not self.source_id or not self.target_id:
            return
        if self.source_id == self.target_id:
            raise ValidationError("La relación no puede apuntar al propio CI.")
        if self.relation_type == self.Type.CONNECTED:
            return  # Las conexiones físicas admiten anillos y redes malladas.
        # El grafo técnico de dependencias/alojamiento no permite ciclos.
        visited, pending = set(), [self.target_id]
        while pending:
            current = pending.pop()
            if current == self.source_id:
                raise ValidationError("La relación produciría un ciclo de dependencias.")
            if current in visited:
                continue
            visited.add(current)
            pending.extend(CIRelation.objects.filter(
                source_id=current, relation_type__in=[self.Type.DEPENDS, self.Type.HOSTED]
            ).exclude(pk=self.pk).values_list("target_id", flat=True))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source.code} {self.get_relation_type_display()} {self.target.code}"


def potentially_affected_services(ci):
    """Recorrido inverso: si falla el CI objetivo, detectar dependientes.

    Devuelve servicios POTENCIALMENTE afectados; no afirma una caída real.
    """
    visited, pending = set(), [ci.pk]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(CIRelation.objects.filter(
            target_id=current, relation_type__in=[CIRelation.Type.DEPENDS, CIRelation.Type.HOSTED]
        ).values_list("source_id", flat=True))
    from apps.catalog.models import ServicioNivel2
    return ServicioNivel2.objects.filter(configuration_items__pk__in=visited).distinct().order_by("codigo")
