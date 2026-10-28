from django.db import models


class Importacion(models.Model):
    class Estado(models.TextChoices):
        EN_PROCESO = "PROCESSING", "En proceso"
        COMPLETADA = "COMPLETED", "Completada"
        FALLIDA = "FAILED", "Fallida"

    archivo_nombre = models.CharField(max_length=255)
    archivo_sha256 = models.CharField(max_length=64)
    hoja = models.CharField(max_length=255)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.EN_PROCESO,
    )

    creados = models.PositiveIntegerField(default=0)
    actualizados = models.PositiveIntegerField(default=0)
    omitidos = models.PositiveIntegerField(default=0)
    observados = models.PositiveIntegerField(default=0)

    iniciado_en = models.DateTimeField(auto_now_add=True)
    finalizado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-iniciado_en"]
        verbose_name = "Importación"
        verbose_name_plural = "Importaciones"

    def __str__(self):
        return f"{self.archivo_nombre} - {self.iniciado_en}"


class RegistroImportacion(models.Model):
    class Resultado(models.TextChoices):
        CREADO = "CREATED", "Creado"
        ACTUALIZADO = "UPDATED", "Actualizado"
        OMITIDO = "SKIPPED", "Omitido"
        OBSERVADO = "OBSERVED", "Observado"

    importacion = models.ForeignKey(
        Importacion,
        on_delete=models.CASCADE,
        related_name="registros",
    )

    hoja = models.CharField(max_length=255)

    fila_inicio = models.PositiveIntegerField()
    fila_fin = models.PositiveIntegerField()

    rango_origen = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    codigo_n1_original = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    nombre_n1_original = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    codigo_n2_original = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    nombre_n2_original = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    servicio_nivel1 = models.ForeignKey(
        "catalog.ServicioNivel1",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_importacion",
    )

    servicio_nivel2 = models.ForeignKey(
        "catalog.ServicioNivel2",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_importacion",
    )

    resultado = models.CharField(
        max_length=20,
        choices=Resultado.choices,
    )

    transformaciones = models.JSONField(
        default=dict,
        blank=True,
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fila_inicio", "id"]
        verbose_name = "Registro de importación"
        verbose_name_plural = "Registros de importación"

    def __str__(self):
        return (
            f"{self.hoja}:{self.fila_inicio}-{self.fila_fin} "
            f"{self.resultado}"
        )


class ObservacionImportacion(models.Model):
    importacion = models.ForeignKey(
        Importacion,
        on_delete=models.CASCADE,
        related_name="observaciones",
    )

    tipo = models.CharField(max_length=100)

    nivel = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    codigo = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    mensaje = models.TextField()

    hoja = models.CharField(max_length=255)

    fila_inicio = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    fila_fin = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    rango_origen = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    valores_originales = models.JSONField(
        default=dict,
        blank=True,
    )

    valor_canonico = models.TextField(
        null=True,
        blank=True,
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Observación de importación"
        verbose_name_plural = "Observaciones de importación"

    def __str__(self):
        return f"{self.tipo} - {self.codigo or 'sin código'}"
