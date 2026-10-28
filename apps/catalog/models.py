from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ClaseServicio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Clase de servicio"
        verbose_name_plural = "Clases de servicio"

    def __str__(self):
        return self.nombre


class Criticidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Criticidad"
        verbose_name_plural = "Criticidades"

    def __str__(self):
        return self.nombre


class TipoServicio(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Tipo de servicio"
        verbose_name_plural = "Tipos de servicio"

    def __str__(self):
        return self.nombre


class ServicioNivel1(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Servicio nivel 1"
        verbose_name_plural = "Servicios nivel 1"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ServicioNivel2(models.Model):
    nivel1 = models.ForeignKey(
        ServicioNivel1,
        on_delete=models.PROTECT,
        related_name="servicios_nivel2",
    )

    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=255)

    # El Excel utiliza S/N, pero puede contener ausencias o valores
    # desconocidos. NULL representa estado desconocido.
    activo = models.BooleanField(
        null=True,
        blank=True,
        default=True,
    )

    # Conserva el valor original recibido durante una importación.
    activo_original = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    clase = models.ForeignKey(
        ClaseServicio,
        on_delete=models.PROTECT,
        related_name="servicios",
        null=True,
        blank=True,
    )

    criticidad = models.ForeignKey(
        Criticidad,
        on_delete=models.PROTECT,
        related_name="servicios",
        null=True,
        blank=True,
    )

    tipo = models.ForeignKey(
        TipoServicio,
        on_delete=models.PROTECT,
        related_name="servicios",
        null=True,
        blank=True,
    )

    descripcion = models.TextField(
        null=True,
        blank=True,
    )

    metrica = models.TextField(
        null=True,
        blank=True,
    )

    minimo = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )

    maximo = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )

    seccion_responsable = models.ForeignKey(
        "organization.Seccion",
        on_delete=models.PROTECT,
        related_name="servicios_responsables",
        null=True,
        blank=True,
    )

    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="servicios_responsables",
        null=True,
        blank=True,
    )

    requiere_revision = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Servicio nivel 2"
        verbose_name_plural = "Servicios nivel 2"

    def clean(self):
        super().clean()

        if self.nivel1_id and not self.nivel1.activo:
            raise ValidationError(
                {
                    "nivel1":
                    "No se puede asociar un servicio a un nivel 1 inactivo."
                }
            )

        if (
            self.minimo is not None
            and self.maximo is not None
            and self.minimo > self.maximo
        ):
            raise ValidationError(
                {
                    "maximo":
                    "El valor máximo debe ser mayor o igual que el mínimo."
                }
            )

        catalogos = (
            ("clase", self.clase),
            ("criticidad", self.criticidad),
            ("tipo", self.tipo),
        )

        for campo, objeto in catalogos:
            if objeto is not None and not objeto.activo:
                raise ValidationError(
                    {
                        campo:
                        "No se puede utilizar un valor de catálogo inactivo."
                    }
                )

        if (
            self.seccion_responsable_id
            and not self.seccion_responsable.activo
        ):
            raise ValidationError(
                {
                    "seccion_responsable":
                    "La sección responsable debe estar activa."
                }
            )

        if (
            self.usuario_responsable_id
            and self.seccion_responsable_id is None
        ):
            raise ValidationError(
                {
                    "usuario_responsable":
                    "Debe seleccionar una sección responsable primero."
                }
            )

        if self.usuario_responsable_id:
            if not self.usuario_responsable.is_active:
                raise ValidationError(
                    {
                        "usuario_responsable":
                        "El usuario responsable debe estar activo."
                    }
                )

            if (
                self.usuario_responsable.puesto.seccion_id
                != self.seccion_responsable_id
            ):
                raise ValidationError(
                    {
                        "usuario_responsable":
                        "El usuario responsable debe pertenecer "
                        "a la sección responsable seleccionada."
                    }
                )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
