from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import admin_required
from apps.organization.forms import (
    AreaForm,
    DepartamentoForm,
    EmpresaForm,
    PuestoForm,
    SeccionForm,
)
from apps.organization.models import (
    Area,
    Departamento,
    Empresa,
    Puesto,
    Seccion,
)


ENTITIES = {
    "empresa": {
        "model": Empresa,
        "form": EmpresaForm,
        "titulo": "Empresas",
        "singular": "Empresa",
        "parent": None,
    },
    "area": {
        "model": Area,
        "form": AreaForm,
        "titulo": "Áreas",
        "singular": "Área",
        "parent": "empresa",
    },
    "departamento": {
        "model": Departamento,
        "form": DepartamentoForm,
        "titulo": "Departamentos",
        "singular": "Departamento",
        "parent": "area",
    },
    "seccion": {
        "model": Seccion,
        "form": SeccionForm,
        "titulo": "Secciones",
        "singular": "Sección",
        "parent": "departamento",
    },
    "puesto": {
        "model": Puesto,
        "form": PuestoForm,
        "titulo": "Puestos",
        "singular": "Puesto",
        "parent": "seccion",
    },
}


def get_config(entity):
    config = ENTITIES.get(entity)

    if config is None:
        raise Http404("Entidad organizacional no válida.")

    return config


def parent_display(entity, obj):
    config = get_config(entity)
    parent_field = config["parent"]

    if parent_field is None:
        return "-"

    return str(getattr(obj, parent_field))


def has_active_dependencies(entity, obj):
    if entity == "empresa":
        return obj.areas.filter(activo=True).exists()

    if entity == "area":
        return obj.departamentos.filter(activo=True).exists()

    if entity == "departamento":
        return obj.secciones.filter(activo=True).exists()

    if entity == "seccion":
        return obj.puestos.filter(activo=True).exists()

    if entity == "puesto":
        return obj.usuarios.filter(is_active=True).exists()

    return False


@login_required
def index(request):
    entities = []

    for key, config in ENTITIES.items():
        entities.append(
            {
                "key": key,
                "titulo": config["titulo"],
                "total": config["model"].objects.count(),
                "activos": config["model"].objects.filter(
                    activo=True
                ).count(),
            }
        )

    return render(
        request,
        "organization/index.html",
        {"entities": entities},
    )


@login_required
def entity_list(request, entity):
    config = get_config(entity)

    rows = []

    for obj in config["model"].objects.all():
        rows.append(
            {
                "obj": obj,
                "parent": parent_display(entity, obj),
            }
        )

    return render(
        request,
        "organization/list.html",
        {
            "entity": entity,
            "config": config,
            "rows": rows,
        },
    )


@admin_required
def entity_create(request, entity):
    config = get_config(entity)

    form = config["form"](
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        obj.full_clean()
        obj.save()

        messages.success(
            request,
            f"{config['singular']} creada correctamente.",
        )

        return redirect(
            "organization:list",
            entity=entity,
        )

    return render(
        request,
        "organization/form.html",
        {
            "entity": entity,
            "config": config,
            "form": form,
            "accion": "Crear",
        },
    )


@admin_required
def entity_update(request, entity, pk):
    config = get_config(entity)

    obj = get_object_or_404(
        config["model"],
        pk=pk,
    )

    form = config["form"](
        request.POST or None,
        instance=obj,
    )

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        obj.full_clean()
        obj.save()

        messages.success(
            request,
            f"{config['singular']} actualizada correctamente.",
        )

        return redirect(
            "organization:list",
            entity=entity,
        )

    return render(
        request,
        "organization/form.html",
        {
            "entity": entity,
            "config": config,
            "form": form,
            "accion": "Editar",
        },
    )


@admin_required
@require_POST
def entity_toggle(request, entity, pk):
    config = get_config(entity)

    obj = get_object_or_404(
        config["model"],
        pk=pk,
    )

    if obj.activo:
        if has_active_dependencies(entity, obj):
            messages.error(
                request,
                (
                    f"No se puede desactivar {config['singular'].lower()} "
                    "porque tiene dependencias activas."
                ),
            )

            return redirect(
                "organization:list",
                entity=entity,
            )

        obj.activo = False
        obj.save(
            update_fields=[
                "activo",
                "actualizado_en",
            ]
        )

        messages.success(
            request,
            f"{config['singular']} desactivada correctamente.",
        )

    else:
        obj.activo = True

        try:
            obj.full_clean()
            obj.save(
                update_fields=[
                    "activo",
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
                f"{config['singular']} reactivada correctamente.",
            )

    return redirect(
        "organization:list",
        entity=entity,
    )
