from django.core.exceptions import ValidationError
from django.db import models


class Empresa(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Area(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="areas",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="uq_area_empresa_codigo",
            )
        ]
        verbose_name = "Área"
        verbose_name_plural = "Áreas"

    def clean(self):
        super().clean()
        if self.empresa_id and not self.empresa.activo:
            raise ValidationError(
                {"empresa": "No se puede asociar un área a una empresa inactiva."}
            )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Departamento(models.Model):
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="departamentos",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["area__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["area", "codigo"],
                name="uq_departamento_area_codigo",
            )
        ]
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"

    def clean(self):
        super().clean()
        if self.area_id and not self.area.activo:
            raise ValidationError(
                {"area": "No se puede asociar un departamento a un área inactiva."}
            )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Seccion(models.Model):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="secciones",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["departamento__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["departamento", "codigo"],
                name="uq_seccion_departamento_codigo",
            )
        ]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"

    def clean(self):
        super().clean()
        if self.departamento_id and not self.departamento.activo:
            raise ValidationError(
                {"departamento": "No se puede asociar una sección a un departamento inactivo."}
            )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Puesto(models.Model):
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="puestos",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["seccion__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["seccion", "codigo"],
                name="uq_puesto_seccion_codigo",
            )
        ]
        verbose_name = "Puesto"
        verbose_name_plural = "Puestos"

    def clean(self):
        super().clean()
        if self.seccion_id and not self.seccion.activo:
            raise ValidationError(
                {"seccion": "No se puede asociar un puesto a una sección inactiva."}
            )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
