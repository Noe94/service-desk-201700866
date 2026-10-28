from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import admin_required
from apps.catalog.forms import (
    ClaseServicioForm,
    CriticidadForm,
    ServicioNivel1Form,
    ServicioNivel2Form,
    TipoServicioForm,
)
from apps.catalog.models import (
    ClaseServicio,
    Criticidad,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)


@login_required
def index(request):
    return render(
        request,
        "catalog/index.html",
        {
            "n1_total": ServicioNivel1.objects.count(),
            "n2_total": ServicioNivel2.objects.count(),
            "n2_revision": ServicioNivel2.objects.filter(
                requiere_revision=True
            ).count(),
        },
    )


@login_required
def n1_list(request):
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()

    queryset = ServicioNivel1.objects.all()

    if query:
        queryset = queryset.filter(
            Q(codigo__icontains=query)
            | Q(nombre__icontains=query)
        )

    if estado == "activo":
        queryset = queryset.filter(activo=True)

    elif estado == "inactivo":
        queryset = queryset.filter(activo=False)

    paginator = Paginator(
        queryset.order_by("codigo"),
        15,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)

    return render(
        request,
        "catalog/n1_list.html",
        {
            "page": page,
            "pagination_query": pagination_params.urlencode(),
            "query": query,
            "estado": estado,
        },
    )


@login_required
def n1_detail(request, pk):
    service = get_object_or_404(
        ServicioNivel1.objects.prefetch_related(
            "servicios_nivel2"
        ),
        pk=pk,
    )

    return render(
        request,
        "catalog/n1_detail.html",
        {"service": service},
    )


@admin_required
def n1_create(request):
    form = ServicioNivel1Form(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.full_clean()
        service.save()

        messages.success(
            request,
            "Servicio Nivel 1 creado correctamente.",
        )

        return redirect("catalog:n1_list")

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": "Crear Servicio Nivel 1",
            "cancel_url": "catalog:n1_list",
        },
    )


@admin_required
def n1_update(request, pk):
    service = get_object_or_404(
        ServicioNivel1,
        pk=pk,
    )

    form = ServicioNivel1Form(
        request.POST or None,
        instance=service,
    )

    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.full_clean()
        service.save()

        messages.success(
            request,
            "Servicio Nivel 1 actualizado correctamente.",
        )

        return redirect("catalog:n1_list")

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": "Editar Servicio Nivel 1",
            "cancel_url": "catalog:n1_list",
        },
    )


@admin_required
@require_POST
def n1_toggle(request, pk):
    service = get_object_or_404(
        ServicioNivel1,
        pk=pk,
    )

    if service.activo:
        has_dependencies = (
            service.servicios_nivel2
            .exclude(activo=False)
            .exists()
        )

        if has_dependencies:
            messages.error(
                request,
                "No se puede desactivar porque tiene "
                "servicios Nivel 2 activos o sin estado definido.",
            )

            return redirect("catalog:n1_list")

        service.activo = False

    else:
        service.activo = True

    service.full_clean()
    service.save(
        update_fields=[
            "activo",
            "actualizado_en",
        ]
    )

    messages.success(
        request,
        "Estado actualizado correctamente.",
    )

    return redirect("catalog:n1_list")


@login_required
def n2_list(request):
    query = request.GET.get("q", "").strip()
    nivel1 = request.GET.get("nivel1", "").strip()
    estado = request.GET.get("estado", "").strip()
    clase = request.GET.get("clase", "").strip()
    criticidad = request.GET.get("criticidad", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    revision = request.GET.get("revision", "").strip()

    queryset = (
        ServicioNivel2.objects
        .select_related(
            "nivel1",
            "clase",
            "criticidad",
            "tipo",
            "seccion_responsable",
            "usuario_responsable",
        )
    )

    if query:
        queryset = queryset.filter(
            Q(codigo__icontains=query)
            | Q(nombre__icontains=query)
        )

    if nivel1:
        queryset = queryset.filter(
            nivel1_id=nivel1
        )

    if estado == "activo":
        queryset = queryset.filter(activo=True)

    elif estado == "inactivo":
        queryset = queryset.filter(activo=False)

    elif estado == "desconocido":
        queryset = queryset.filter(activo__isnull=True)

    if clase:
        queryset = queryset.filter(
            clase_id=clase
        )

    if criticidad:
        queryset = queryset.filter(
            criticidad_id=criticidad
        )

    if tipo:
        queryset = queryset.filter(
            tipo_id=tipo
        )

    if revision == "si":
        queryset = queryset.filter(
            requiere_revision=True
        )

    paginator = Paginator(
        queryset.order_by("codigo"),
        15,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)

    return render(
        request,
        "catalog/n2_list.html",
        {
            "page": page,
            "pagination_query": pagination_params.urlencode(),
            "query": query,
            "nivel1_selected": nivel1,
            "estado": estado,
            "clase_selected": clase,
            "criticidad_selected": criticidad,
            "tipo_selected": tipo,
            "revision": revision,
            "nivel1_options": ServicioNivel1.objects.order_by("codigo"),
            "clase_options": ClaseServicio.objects.filter(activo=True),
            "criticidad_options": Criticidad.objects.filter(activo=True),
            "tipo_options": TipoServicio.objects.filter(activo=True),
        },
    )


@login_required
def n2_detail(request, pk):
    service = get_object_or_404(
        ServicioNivel2.objects.select_related(
            "nivel1",
            "clase",
            "criticidad",
            "tipo",
            "seccion_responsable",
            "usuario_responsable",
        ),
        pk=pk,
    )

    return render(
        request,
        "catalog/n2_detail.html",
        {"service": service},
    )


@admin_required
def n2_create(request):
    form = ServicioNivel2Form(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.full_clean()
        service.save()

        messages.success(
            request,
            "Servicio Nivel 2 creado correctamente.",
        )

        return redirect(
            "catalog:n2_detail",
            pk=service.pk,
        )

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": "Crear Servicio Nivel 2",
            "cancel_url": "catalog:n2_list",
        },
    )


@admin_required
def n2_update(request, pk):
    service = get_object_or_404(
        ServicioNivel2,
        pk=pk,
    )

    form = ServicioNivel2Form(
        request.POST or None,
        instance=service,
    )

    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.full_clean()
        service.save()

        messages.success(
            request,
            "Servicio Nivel 2 actualizado correctamente.",
        )

        return redirect(
            "catalog:n2_detail",
            pk=service.pk,
        )

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": "Editar Servicio Nivel 2",
            "cancel_url": "catalog:n2_list",
        },
    )


@admin_required
@require_POST
def n2_toggle(request, pk):
    service = get_object_or_404(
        ServicioNivel2,
        pk=pk,
    )

    service.activo = (
        False
        if service.activo is True
        else True
    )

    service.full_clean()

    service.save(
        update_fields=[
            "activo",
            "actualizado_en",
        ]
    )

    messages.success(
        request,
        "Estado actualizado correctamente.",
    )

    return redirect(
        "catalog:n2_detail",
        pk=service.pk,
    )


OPTION_CATALOGS = {
    "clase": {
        "model": ClaseServicio,
        "form": ClaseServicioForm,
        "titulo": "Clases de servicio",
        "singular": "Clase de servicio",
    },
    "criticidad": {
        "model": Criticidad,
        "form": CriticidadForm,
        "titulo": "Criticidades",
        "singular": "Criticidad",
    },
    "tipo": {
        "model": TipoServicio,
        "form": TipoServicioForm,
        "titulo": "Tipos de servicio",
        "singular": "Tipo de servicio",
    },
}


def get_option_config(option):
    config = OPTION_CATALOGS.get(option)

    if config is None:
        from django.http import Http404
        raise Http404("Catálogo no válido.")

    return config


@login_required
def option_list(request, option):
    config = get_option_config(option)

    objects = config["model"].objects.order_by("nombre")

    return render(
        request,
        "catalog/option_list.html",
        {
            "option": option,
            "config": config,
            "objects": objects,
        },
    )


@admin_required
def option_create(request, option):
    config = get_option_config(option)

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
            "catalog:option_list",
            option=option,
        )

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": f"Crear {config['singular']}",
            "cancel_url": "catalog:index",
        },
    )


@admin_required
def option_update(request, option, pk):
    config = get_option_config(option)

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
            "catalog:option_list",
            option=option,
        )

    return render(
        request,
        "catalog/form.html",
        {
            "form": form,
            "titulo": f"Editar {config['singular']}",
            "cancel_url": "catalog:index",
        },
    )


@admin_required
@require_POST
def option_toggle(request, option, pk):
    config = get_option_config(option)

    obj = get_object_or_404(
        config["model"],
        pk=pk,
    )

    if obj.activo:
        if obj.servicios.exists():
            messages.error(
                request,
                "No puede desactivarse porque está "
                "asociado a servicios.",
            )

            return redirect(
                "catalog:option_list",
                option=option,
            )

        obj.activo = False

    else:
        obj.activo = True

    obj.save(
        update_fields=[
            "activo",
            "actualizado_en",
        ]
    )

    messages.success(
        request,
        "Estado actualizado correctamente.",
    )

    return redirect(
        "catalog:option_list",
        option=option,
    )


