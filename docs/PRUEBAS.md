# Pruebas y verificación: matriz P01–P18

## Entorno realmente ejecutado

- Sesión del 27–28 de octubre de 2026, en entorno Linux del asistente,
  con Django 5.2.18 y base SQLite **en memoria** aislada.
- Ejecución: `python -c '... settings.DATABASES["default"] = SQLite ...; manage.py test -v 1'`.
- Resultado de última revisión: **80/80 pruebas** pasaron en 11.51 s,
  con 0 problemas de `manage.py check`.
- Verificación final incluyó categorías, pausas, permiso `can_manage` y regla de duración.
- Datos de integración en SQLite temporal: importador **12 N1 / 46 N2**,
  generador **5,000 nuevos y 0 al repetir**, 7 colas, 37 tickets,
  4 artículos y 25 vínculos de CI con ticket.
- Git commit: **pendiente**, no se ha creado todavía en el nuevo repositorio.
- **Docker y PostgreSQL no disponibles en este entorno**. P18 y mediciones
  reales en PostgreSQL están pendientes en Windows.

## Matriz

| Caso | Implementación | Evidencia actual | Pendiente |
|---|---|---|---|
| P01 | `accounts`, `permissions.py` | 49 tests originales + rechazo CONSULTA | Ensayo web en Docker |
| P02 | `import_catalog --verify-original` | 12/46, conflicto SE.12 retenido | Repetir en PostgreSQL |
| P03 | `seed_cmdb` | Test 5000 + repetición sin duplicados | Medir en PostgreSQL |
| P04 | `CIClass` y fuentes | Validación de ciclos y `MODELO.md` | Contraste visual en defensa |
| P05 | `create_ticket` | Valida cola, solicitante, servicio, motivo CI | Caso más amplio de FK inválidas |
| P06 | `QueueRoleGrant`, `QueueUserGrant` | Pruebas de acceso/grants y CONSULTA | Ensayo web por rol |
| P07 | `claim_ticket`, ordenamiento | Prueba conflicto secuencial + orden SQL | Prueba simultánea PostgreSQL real |
| P08 | `transfer_ticket` | Rechaza proceso incompatible, exige motivo | Ensayo UI |
| P09 | `workflows.py` | Rutas de acceso y cambio, transiciones inválidas | Recorridos completos para 7 procesos |
| P10 | `TicketApproval` | Cambio sin aprobar y autoaprobación rechazados | — |
| P11 | `EventIncident`, `DeskNotification` | E2 crea uno y es idempotente | Escenarios UI E0/E1/E3 completos |
| P12 | `INCIDENT_GUIDANCE`, función complementaria | Pruebas de límites y mapeo | Revisión detallada de I0–I6 UI |
| P13 | `TicketRelation` | Relaciones entre tickets modeladas | Recorrido incidente–problema–cambio |
| P14 | `CIRelation`, `potentially_affected_services` | Ciclos y recorrido inverso probados | Navegación en PostgreSQL |
| P15 | `TicketHistory`, `reopen_ticket` | Reapertura, cierre, actor | — |
| P16 | Vista `cmdb:list`, 30 por página | Filtros unitarios y 5000 insertados | Medir latencia real con 5000 |
| P17 | `dashboard`, `pause_ticket`, `resume_ticket` | Conteos y pausa | Métricas controladas con reapertura |
| P18 | `postgres_data`/`attachments_data` Compose | Persistencia diseñada | **Reinicio real y conteos antes/después** |

No se informa como exitoso un caso parcialmente implementado. Las pruebas
aislan sus datos y no eliminan los registros de evaluación. Para capturas de
P18, ejecutar `docker compose restart`, consultar totales antes y después,
sin `down -v`, y anotar commit, fecha y resultado obtenido.

## Comandos reproducibles en el equipo del estudiante

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1
docker compose exec -T web python manage.py shell -c "from apps.cmdb.models import CI; from apps.service_desk.models import Ticket, Queue; print(CI.objects.filter(classification__is_device=True).count(), Ticket.objects.count(), Queue.objects.count())"
docker compose restart
docker compose exec -T web python manage.py shell -c "from apps.cmdb.models import CI; from apps.service_desk.models import Ticket, Queue; print(CI.objects.filter(classification__is_device=True).count(), Ticket.objects.count(), Queue.objects.count())"
```

Esperado: 5,000 dispositivos del conjunto, por lo menos 37 tickets
y 7 colas antes y después. Anotar **obtenido** solo tras ejecutar.
