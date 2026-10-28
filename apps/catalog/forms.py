from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.catalog.models import (
    ClaseServicio,
    Criticidad,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)
from apps.organization.models import Seccion


User = get_user_model()


class BaseCatalogForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class ServicioNivel1Form(BaseCatalogForm):
    class Meta:
        model = ServicioNivel1
        fields = [
            "codigo",
            "nombre",
        ]


class ServicioNivel2Form(BaseCatalogForm):
    class Meta:
        model = ServicioNivel2
        fields = [
            "nivel1",
            "codigo",
            "nombre",
            "activo",
            "clase",
            "criticidad",
            "tipo",
            "descripcion",
            "metrica",
            "minimo",
            "maximo",
            "seccion_responsable",
            "usuario_responsable",
            "requiere_revision",
        ]

        labels = {
            "nivel1": "Servicio Nivel 1",
            "activo": "Estado",
            "minimo": "Mínimo",
            "maximo": "Máximo",
            "seccion_responsable": "Sección responsable",
            "usuario_responsable": "Usuario responsable",
            "requiere_revision": "Requiere revisión",
        }

        widgets = {
            "descripcion": forms.Textarea(
                attrs={"rows": 4}
            ),
            "metrica": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance

        nivel1_query = Q(activo=True)

        if instance and instance.pk and instance.nivel1_id:
            nivel1_query |= Q(pk=instance.nivel1_id)

        self.fields["nivel1"].queryset = (
            ServicioNivel1.objects
            .filter(nivel1_query)
            .order_by("codigo")
        )

        self.fields["clase"].queryset = (
            ClaseServicio.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        self.fields["criticidad"].queryset = (
            Criticidad.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        self.fields["tipo"].queryset = (
            TipoServicio.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        self.fields["seccion_responsable"].queryset = (
            Seccion.objects
            .filter(activo=True)
            .order_by("codigo")
        )

        self.fields["usuario_responsable"].queryset = (
            User.objects
            .filter(is_active=True)
            .select_related("puesto__seccion")
            .order_by("username")
        )



class ClaseServicioForm(BaseCatalogForm):
    class Meta:
        model = ClaseServicio
        fields = ["nombre"]


class CriticidadForm(BaseCatalogForm):
    class Meta:
        model = Criticidad
        fields = ["nombre"]


class TipoServicioForm(BaseCatalogForm):
    class Meta:
        model = TipoServicio
        fields = ["nombre"]
