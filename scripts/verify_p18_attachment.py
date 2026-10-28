import hashlib

from django.core.files.base import ContentFile

from apps.service_desk.models import Ticket, TicketAttachment

ticket = Ticket.objects.order_by("pk").first()

if ticket is None:
    raise RuntimeError("No existe un ticket para probar persistencia.")

nombre = "P18-persistencia-sintetica.txt"

adjunto = TicketAttachment.objects.filter(
    ticket=ticket,
    file__contains=nombre,
).first()

if adjunto is None:
    adjunto = TicketAttachment(
        ticket=ticket,
        uploader=ticket.creator,
    )

    adjunto.file.save(
        nombre,
        ContentFile(
            b"Evidencia sintetica P18 - persistencia Docker PostgreSQL"
        ),
        save=False,
    )

    adjunto.full_clean()
    adjunto.save()

if not adjunto.file.storage.exists(adjunto.file.name):
    raise RuntimeError("El archivo no existe en almacenamiento.")

adjunto.file.open("rb")
contenido = adjunto.file.read()
adjunto.file.close()

if not contenido:
    raise RuntimeError("El archivo esta vacio.")

resumen = hashlib.sha256(contenido).hexdigest()

print(
    "P18_EVIDENCIA="
    + str(adjunto.pk)
    + "|"
    + adjunto.file.name
    + "|"
    + resumen
)