from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.accounts.permissions import admin_required
from apps.catalog.models import ServicioNivel1

from .forms import (
    CommentForm, QueueForm, QueueRoleGrantForm, QueueUserGrantForm,
    TicketCreateForm, TicketDetailsForm, TransferForm, TransitionForm,
)
from .models import (
    KnowledgeArticle, Process, Queue, QueueRoleGrant, QueueUserGrant, Ticket, TicketAttachment,
)
from .permissions import accessible_tickets, can_create, can_view_ticket, is_admin, queue_allowed, require_ticket_access
from .services import (
    TicketConflict, add_comment, claim_ticket, create_ticket, log_action, pause_ticket,
    reopen_ticket, resume_ticket,
    transfer_ticket, transition_ticket, update_ticket_details,
)


def elapsed_minutes(ticket, when):
    """Tiempo calendario transcurrido menos pausas consolidadas/en curso."""
    paused = ticket.paused_seconds
    if ticket.paused_at and when > ticket.paused_at:
        paused += max(0, (when - ticket.paused_at).total_seconds())
    return max(0, (when - ticket.created_at).total_seconds() - paused) / 60


@login_required
def dashboard(request):
    tickets = list(accessible_tickets(request.user).select_related("queue"))
    now = timezone.now()
    aggregates = {}
    for dimension in ("queue", "process", "priority", "status"):
        counts = {}
        for ticket in tickets:
            name = ticket.queue.code if dimension == "queue" else getattr(ticket, dimension)
            counts[name] = counts.get(name, 0) + 1
        aggregates[dimension] = sorted(counts.items())
    first_response = [elapsed_minutes(t, t.first_response_at) for t in tickets if t.first_response_at]
    resolution = [elapsed_minutes(t, t.resolved_at) for t in tickets if t.resolved_at]
    response_target = [elapsed_minutes(t, t.first_response_at) <= t.queue.first_response_target_minutes
                       for t in tickets if t.first_response_at]
    resolution_target = [elapsed_minutes(t, t.resolved_at) <= t.queue.resolution_target_minutes
                         for t in tickets if t.resolved_at]
    def average(values):
        return round(sum(values) / len(values), 1) if values else None
    def percent(values):
        return round(100 * sum(values) / len(values), 1) if values else None
    return render(request, "service_desk/dashboard.html", {
        "total": len(tickets), "open": sum(1 for t in tickets if not t.closed_at),
        "paused": sum(1 for t in tickets if t.paused_at),
        "oldest": round(max((elapsed_minutes(t, now) for t in tickets if not t.closed_at), default=0) / 60, 1),
        "average_first": average(first_response), "average_resolved": average(resolution),
        "response_pct": percent(response_target), "resolution_pct": percent(resolution_target),
        "aggregates": aggregates,
    })


@login_required
def knowledge_base(request):
    articles = KnowledgeArticle.objects.filter(active=True)
    query = request.GET.get("q", "").strip()
    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(question__icontains=query) | Q(answer__icontains=query))
    return render(request, "service_desk/knowledge.html", {"articles": articles})


@login_required
def ticket_list(request):
    tickets = accessible_tickets(request.user).select_related(
        "service__nivel1", "queue", "requester", "assignee"
    )
    filters = {
        "number__icontains": request.GET.get("numero", "").strip(),
        "process": request.GET.get("proceso", ""),
        "queue_id": request.GET.get("cola", ""),
        "status": request.GET.get("estado", ""),
        "priority": request.GET.get("prioridad", ""),
        "service_id": request.GET.get("servicio", ""),
        "assignee_id": request.GET.get("responsable", ""),
    }
    for field, value in filters.items():
        if value:
            try:
                tickets = tickets.filter(**{field: value})
            except (ValueError, TypeError):
                tickets = tickets.none()
    for name, lookup in (("desde", "created_at__date__gte"), ("hasta", "created_at__date__lte")):
        date = parse_date(request.GET.get(name, ""))
        if date:
            tickets = tickets.filter(**{lookup: date})
    pages = Paginator(tickets.order_by("priority", "created_at", "pk"), 20)
    return render(request, "service_desk/ticket_list.html", {
        "page": pages.get_page(request.GET.get("pagina")),
        "processes": Process.choices,
        "queues": Queue.objects.filter(active=True),
        "can_create": can_create(request.user),
    })


@login_required
def ticket_create(request):
    if not can_create(request.user):
        raise PermissionDenied("No tiene permiso para crear tickets.")
    process = request.GET.get("proceso", "")
    if process not in Process.values:
        return render(request, "service_desk/select_process.html", {"processes": Process.choices})
    form = TicketCreateForm(request.POST or None, process=process, actor=request.user)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            ticket = create_ticket(
                actor=request.user, requester=data["requester"], service=data["service"],
                queue=data["queue"], title=data["title"], description=data["description"],
                priority=data["priority"], impact=data["impact"], urgency=data["urgency"],
                channel=data["channel"], no_ci_reason=data["no_ci_reason"],
                details=form.process_details(),
                event_category=data.get("event_category", ""),
                incident_category=data.get("incident_category", ""),
                estimated_interruption_minutes=data.get("estimated_interruption_minutes"),
                redundancy_available=data.get("redundancy_available"),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Se creó el ticket {ticket.number}.")
            return redirect("service_desk:ticket_detail", pk=ticket.pk)
    return render(request, "service_desk/ticket_form.html", {
        "form": form, "process": process,
    })


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("queue", "requester", "creator", "assignee", "service__nivel1"),
        pk=pk,
    )
    require_ticket_access(request.user, ticket)
    is_agent = queue_allowed(request.user, ticket.queue, "attend")
    comments = ticket.comments.select_related("author")
    if not is_agent:
        comments = comments.filter(internal=False)
    return render(request, "service_desk/ticket_detail.html", {
        "ticket": ticket,
        "history": ticket.history.select_related("actor"),
        "comments": comments,
        "attachments": ticket.attachments.all(),
        "event_incident": getattr(ticket, "generated_incident", None),
        "event_notice": getattr(ticket, "incident_notice", None),
        "linked_targets": [
            item for item in ticket.out_relations.select_related("target")
            if can_view_ticket(request.user, item.target)
        ],
        "linked_sources": [
            item for item in ticket.in_relations.select_related("source")
            if can_view_ticket(request.user, item.source)
        ],
        "active_n1": ServicioNivel1.objects.filter(activo=True),
        "is_agent": is_agent,
        "can_transfer": queue_allowed(request.user, ticket.queue, "transfer"),
        "can_approve": queue_allowed(request.user, ticket.queue, "approve"),
        "can_reopen": ticket.requester_id == request.user.pk or is_agent,
        "transition_form": TransitionForm(ticket=ticket),
        "transfer_form": TransferForm(ticket=ticket),
        "details_form": TicketDetailsForm(ticket=ticket),
        "comment_form": CommentForm(),
    })


def _action_result(request, pk, action):
    try:
        action()
    except TicketConflict as exc:
        return HttpResponse(str(exc), status=409)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Operación registrada correctamente.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_claim(request, pk):
    return _action_result(request, pk, lambda: claim_ticket(pk, request.user))


@login_required
@require_POST
def ticket_transfer(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TransferForm(request.POST, ticket=ticket)
    if not form.is_valid():
        return HttpResponseBadRequest("Cola destino o motivo inválido.")
    return _action_result(request, pk, lambda: transfer_ticket(
        pk, request.user, form.cleaned_data["destination"], reason=form.cleaned_data["reason"]
    ))


@login_required
@require_POST
def ticket_transition(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TransitionForm(request.POST, ticket=ticket)
    if not form.is_valid():
        return HttpResponseBadRequest("Transición no permitida.")
    return _action_result(request, pk, lambda: transition_ticket(
        pk, request.user, form.cleaned_data["destination"], reason=form.cleaned_data["reason"]
    ))


@login_required
@require_POST
def ticket_reopen(request, pk):
    return _action_result(request, pk, lambda: reopen_ticket(
        pk, request.user, reason=request.POST.get("reason", "")
    ))


@login_required
@require_POST
def ticket_comment(request, pk):
    form = CommentForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Comentario inválido.")
    return _action_result(request, pk, lambda: add_comment(
        pk, request.user, form.cleaned_data["text"], internal=form.cleaned_data["internal"]
    ))


@login_required
@require_POST
def ticket_details_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TicketDetailsForm(request.POST, ticket=ticket)
    if not form.is_valid():
        return HttpResponseBadRequest("Datos de proceso inválidos.")
    return _action_result(request, pk, lambda: update_ticket_details(pk, request.user, form.cleaned_data))


@login_required
@require_POST
def ticket_pause(request, pk):
    return _action_result(request, pk, lambda: pause_ticket(pk, request.user, reason=request.POST.get("reason", "")))


@login_required
@require_POST
def ticket_resume(request, pk):
    return _action_result(request, pk, lambda: resume_ticket(pk, request.user, reason=request.POST.get("reason", "")))


@login_required
@require_POST
@transaction.atomic
def ticket_attachment_upload(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_for_update().select_related("queue"), pk=pk)
    require_ticket_access(request.user, ticket)
    upload = request.FILES.get("file")
    if upload is None:
        return HttpResponseBadRequest("Seleccione un archivo.")
    attachment = TicketAttachment(ticket=ticket, uploader=request.user, file=upload)
    try:
        attachment.full_clean()
    except ValidationError as exc:
        return HttpResponseBadRequest("; ".join(exc.messages))
    attachment.save()
    log_action(ticket, request.user, "ADJUNTO", new={"attachment_id": attachment.pk, "filename": upload.name})
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
def ticket_attachment_download(request, pk):
    attachment = get_object_or_404(TicketAttachment.objects.select_related("ticket__queue"), pk=pk)
    require_ticket_access(request.user, attachment.ticket)
    return FileResponse(
        attachment.file.open("rb"), as_attachment=True,
        filename=attachment.file.name.rsplit("/", 1)[-1],
    )


@login_required
def queue_list(request):
    if is_admin(request.user):
        queues = Queue.objects.all()
    else:
        queues = [q for q in Queue.objects.filter(active=True)
                  if queue_allowed(request.user, q, "view") or queue_allowed(request.user, q, "manage")]
    return render(request, "service_desk/queue_list.html", {
        "queues": queues, "is_admin": is_admin(request.user),
        "manageable_ids": {q.pk for q in queues if queue_allowed(request.user, q, "manage")},
    })


@admin_required
def queue_create(request):
    form = QueueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("service_desk:queues")
    return render(request, "service_desk/queue_form.html", {"form": form, "title": "Crear cola"})


@login_required
def queue_edit(request, pk):
    queue = get_object_or_404(Queue, pk=pk)
    if not queue_allowed(request.user, queue, "manage"):
        raise PermissionDenied("No puede administrar esta cola.")
    form = QueueForm(request.POST or None, instance=queue)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("service_desk:queues")
    return render(request, "service_desk/queue_form.html", {"form": form, "title": "Editar cola", "queue": queue})


@admin_required
def queue_role_grant(request, pk):
    queue = get_object_or_404(Queue, pk=pk)
    form = QueueRoleGrantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = form.cleaned_data["role"]
        QueueRoleGrant.objects.update_or_create(
            queue=queue, role=role,
            defaults={field: form.cleaned_data[field] for field in (
                "can_view", "can_attend", "can_transfer", "can_approve", "can_manage"
            )},
        )
        return redirect("service_desk:queue_edit", pk=pk)
    return render(request, "service_desk/queue_grant.html", {
        "form": form, "queue": queue, "title": "Permisos por rol", "grants": queue.role_grants.select_related("role"),
    })


@admin_required
def queue_user_grant(request, pk):
    queue = get_object_or_404(Queue, pk=pk)
    form = QueueUserGrantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        QueueUserGrant.objects.update_or_create(
            queue=queue, user=user,
            defaults={field: form.cleaned_data[field] for field in (
                "can_view", "can_attend", "can_transfer", "can_approve", "can_manage"
            )},
        )
        return redirect("service_desk:queue_edit", pk=pk)
    return render(request, "service_desk/queue_grant.html", {
        "form": form, "queue": queue, "title": "Permisos por usuario", "grants": queue.user_grants.select_related("user"),
    })


@login_required
@require_POST
def ticket_service_link(request, pk):
    from .services import link_approved_catalog_service

    return _action_result(
        request,
        pk,
        lambda: link_approved_catalog_service(
            pk,
            request.user,
            code=request.POST.get("code", ""),
            name=request.POST.get("name", ""),
            level1_id=request.POST.get("level1_id"),
        ),
    )


@login_required
@require_POST
def ticket_relation_add(request, pk):
    from .services import link_related_ticket

    return _action_result(
        request,
        pk,
        lambda: link_related_ticket(
            pk,
            request.user,
            target_number=request.POST.get("target_number", ""),
            relation_type=request.POST.get("relation_type", ""),
            reason=request.POST.get("reason", ""),
        ),
    )
