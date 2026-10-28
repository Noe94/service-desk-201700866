from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

from apps.accounts.permissions import admin_required
from apps.service_desk.models import Ticket
from apps.service_desk.permissions import accessible_tickets, queue_allowed
from apps.service_desk.services import log_action

from .forms import CIClassForm, CIForm, CIRelationForm, LocationForm
from .models import CI, CIClass, CIRelation, Location, potentially_affected_services


@login_required
def ci_list(request):
    cis = CI.objects.select_related("classification", "location", "owner")
    query = request.GET.get("q", "").strip()
    if query:
        cis = cis.filter(Q(code__icontains=query) | Q(name__icontains=query) | Q(serial_number__icontains=query))
    if request.GET.get("clase"):
        try:
            cis = cis.filter(classification_id=int(request.GET["clase"]))
        except ValueError:
            cis = cis.none()
    if request.GET.get("estado"):
        cis = cis.filter(status=request.GET["estado"])
    if request.GET.get("ubicacion"):
        try:
            cis = cis.filter(location_id=int(request.GET["ubicacion"]))
        except ValueError:
            cis = cis.none()
    return render(request, "cmdb/ci_list.html", {
        "page": Paginator(cis.order_by("code"), 30).get_page(request.GET.get("pagina")),
        "classes": CIClass.objects.all(), "locations": Location.objects.all(), "states": CI.State.choices,
        "total_devices": CI.objects.filter(classification__is_device=True).count(),
        "categories": CIClass.objects.all(),
    })


@login_required
def ci_detail(request, pk):
    ci = get_object_or_404(CI.objects.select_related("classification", "location", "owner"), pk=pk)
    tickets = accessible_tickets(request.user).filter(cis=ci).select_related("queue")
    return render(request, "cmdb/ci_detail.html", {
        "ci": ci, "services": ci.services.select_related("nivel1"), "tickets": tickets,
        "out_relations": ci.out_relations.select_related("target"),
        "in_relations": ci.in_relations.select_related("source"),
        "affected": potentially_affected_services(ci), "relation_form": CIRelationForm(),
    })


@admin_required
def ci_edit(request, pk=None):
    ci = get_object_or_404(CI, pk=pk) if pk else None
    form = CIForm(request.POST or None, instance=ci)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"CI {saved.code} guardado.")
        return redirect("cmdb:detail", pk=saved.pk)
    return render(request, "cmdb/form.html", {"form": form, "title": "Editar CI" if ci else "Nuevo CI"})


@admin_required
def class_edit(request, pk=None):
    item = get_object_or_404(CIClass, pk=pk) if pk else None
    form = CIClassForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("cmdb:list")
    return render(request, "cmdb/form.html", {"form": form, "title": "Clasificación CMDB"})


@admin_required
def location_edit(request, pk=None):
    item = get_object_or_404(Location, pk=pk) if pk else None
    form = LocationForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("cmdb:list")
    return render(request, "cmdb/form.html", {"form": form, "title": "Ubicación CMDB"})


@admin_required
@require_POST
def relation_add(request, pk):
    ci = get_object_or_404(CI, pk=pk)
    form = CIRelationForm(request.POST)
    if form.is_valid():
        rel = form.save(commit=False)
        rel.source = ci
        try:
            rel.save()
            messages.success(request, "Relación técnica registrada.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    else:
        messages.error(request, "Datos de relación inválidos o duplicados.")
    return redirect("cmdb:detail", pk=pk)


@login_required
@require_POST
def ticket_ci_add(request, ticket_pk):
    ticket = get_object_or_404(Ticket.objects.select_related("queue"), pk=ticket_pk)
    if not queue_allowed(request.user, ticket.queue, "attend"):
        raise PermissionDenied("No tiene permiso para asociar CI.")
    ci = get_object_or_404(CI, code=request.POST.get("ci_code", "").strip())
    if not ticket.cis.filter(pk=ci.pk).exists():
        ticket.cis.add(ci)
        ticket.no_ci_reason = ""
        ticket.save(update_fields=["no_ci_reason", "updated_at"])
        log_action(ticket, request.user, "VINCULO_CI", new={"ci": ci.code})
    return redirect("service_desk:ticket_detail", pk=ticket.pk)

