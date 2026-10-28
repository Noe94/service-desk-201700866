from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.organization.models import Puesto


User = get_user_model()


class LocalAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario o correo",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
            }
        ),
    )


class BaseUserForm(forms.ModelForm):
    roles_operativos = forms.ModelMultipleChoiceField(
        label="Roles operativos (puede seleccionar varios)",
        queryset=Group.objects.filter(name__in=["SOLICITANTE", "AGENTE", "APROBADOR"]),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["roles_operativos"].initial = self.instance.groups.filter(
                name__in=["SOLICITANTE", "AGENTE", "APROBADOR"]
            )

        self.fields["puesto"].queryset = (
            Puesto.objects
            .filter(activo=True)
            .select_related(
                "seccion__departamento__area__empresa"
            )
        )

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def save_roles(self, user):
        # CONSULTA es una barrera explícita incluso si por error le asocian grupos.
        choices = self.cleaned_data.get("roles_operativos")
        role_ids = list(choices.values_list("pk", flat=True)) if choices is not None else []
        if user.rol == "CONSULTA":
            role_ids = []
        user.groups.set(role_ids)


class UserCreateForm(BaseUserForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(),
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "rol",
            "puesto",
        ]

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error(
                "password2",
                "Las contraseñas no coinciden.",
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data["password1"]
        )

        if commit:
            user.full_clean()
            user.save()
            self.save_roles(user)

        return user


class UserUpdateForm(BaseUserForm):
    password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput(),
        help_text="Déjelo vacío para conservar la actual.",
    )

    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        required=False,
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "rol",
            "puesto",
        ]

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 or password2:
            if password1 != password2:
                self.add_error(
                    "password2",
                    "Las contraseñas no coinciden.",
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password1")

        if password:
            user.set_password(password)

        if commit:
            user.full_clean()
            user.save()
            self.save_roles(user)

        return user
