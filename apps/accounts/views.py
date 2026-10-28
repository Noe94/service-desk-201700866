from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.forms import (
    LocalAuthenticationForm,
    UserCreateForm,
    UserUpdateForm,
)
from apps.accounts.permissions import admin_required


User = get_user_model()


class LocalLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LocalAuthenticationForm
    redirect_authenticated_user = True


class LocalLogoutView(LogoutView):
    pass


@login_required
def dashboard(request):
    return render(
        request,
        "accounts/dashboard.html",
    )


@login_required
def user_list(request):
    users = (
        User.objects
        .select_related(
            "puesto__seccion__departamento__area__empresa"
        )
        .order_by("username")
    )

    rows = []

    for user in users:
        puesto = user.puesto
        seccion = puesto.seccion
        departamento = seccion.departamento
        area = departamento.area
        empresa = area.empresa

        rows.append(
            {
                "user": user,
                "puesto": puesto,
                "empresa": empresa,
            }
        )

    return render(
        request,
        "accounts/user_list.html",
        {"rows": rows},
    )


@admin_required
def user_create(request):
    form = UserCreateForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Usuario creado correctamente.",
        )

        return redirect(
            "accounts:user_list"
        )

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "accion": "Crear",
        },
    )


@admin_required
def user_update(request, pk):
    user = get_object_or_404(
        User,
        pk=pk,
    )

    form = UserUpdateForm(
        request.POST or None,
        instance=user,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Usuario actualizado correctamente.",
        )

        return redirect(
            "accounts:user_list"
        )

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "accion": "Editar",
            "edited_user": user,
        },
    )


@admin_required
@require_POST
def user_toggle(request, pk):
    user = get_object_or_404(
        User,
        pk=pk,
    )

    if user.pk == request.user.pk:
        messages.error(
            request,
            "No puede desactivar su propia cuenta.",
        )

        return redirect(
            "accounts:user_list"
        )

    if user.is_active:
        # No dejar tickets sin responsable al desactivar usuarios.
        from apps.service_desk.models import Ticket
        if Ticket.objects.filter(assignee=user, closed_at__isnull=True).exists():
            messages.error(request, "Transfiera o reasigne sus tickets abiertos antes de desactivar al usuario.")
            return redirect("accounts:user_list")
        user.is_active = False
        user.save(
            update_fields=[
                "is_active",
                "actualizado_en",
            ]
        )

        messages.success(
            request,
            "Usuario desactivado correctamente.",
        )

    else:
        user.is_active = True

        try:
            user.full_clean()

            user.save(
                update_fields=[
                    "is_active",
                    "actualizado_en",
                ]
            )

        except ValidationError as exc:
            messages.error(
                request,
                "No fue posible reactivar: "
                + " ".join(exc.messages),
            )

        else:
            messages.success(
                request,
                "Usuario reactivado correctamente.",
            )

    return redirect(
        "accounts:user_list"
    )
