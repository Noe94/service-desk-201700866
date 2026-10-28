from django import forms

from apps.organization.models import (
    Area,
    Departamento,
    Empresa,
    Puesto,
    Seccion,
)


class BaseOrganizationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class EmpresaForm(BaseOrganizationForm):
    class Meta:
        model = Empresa
        fields = ["codigo", "nombre"]


class AreaForm(BaseOrganizationForm):
    class Meta:
        model = Area
        fields = ["empresa", "codigo", "nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["empresa"].queryset = Empresa.objects.filter(
            activo=True
        )


class DepartamentoForm(BaseOrganizationForm):
    class Meta:
        model = Departamento
        fields = ["area", "codigo", "nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.filter(
            activo=True
        )


class SeccionForm(BaseOrganizationForm):
    class Meta:
        model = Seccion
        fields = ["departamento", "codigo", "nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departamento"].queryset = (
            Departamento.objects.filter(activo=True)
        )


class PuestoForm(BaseOrganizationForm):
    class Meta:
        model = Puesto
        fields = ["seccion", "codigo", "nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["seccion"].queryset = Seccion.objects.filter(
            activo=True
        )
