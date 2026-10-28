from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMIN", "Administrador"
        CONSULTA = "CONSULTA", "Consulta"
        OPERATIVO = "OPERATIVO", "Solicitante / Agente / Aprobador"

    email = models.EmailField(unique=True)

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.CONSULTA,
    )

    puesto = models.ForeignKey(
        "organization.Puesto",
        on_delete=models.PROTECT,
        related_name="usuarios",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email", "puesto"]

    class Meta:
        ordering = ["username"]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def clean(self):
        super().clean()

        if self.puesto_id and not self.puesto.activo:
            raise ValidationError(
                {"puesto": "No se puede asociar un usuario a un puesto inactivo."}
            )

    def __str__(self):
        return f"{self.username} - {self.get_full_name() or self.email}"
