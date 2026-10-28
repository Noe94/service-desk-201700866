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
## Validación real en Windows con Docker y PostgreSQL

**Fecha:** 28 de octubre de 2026.
**Responsable:** Erick Noe Gómez López, carné 201700866.
**Entorno:** Windows, PowerShell, Docker Desktop, Django y PostgreSQL.
**Repositorio:** https://github.com/Noe94/service-desk-201700866
**Commit inicial:** 00ad0f8.

### Preparación del entorno

Comando ejecutado:

`powershell -ExecutionPolicy Bypass -File .\scripts\prepare.ps1`

Resultados observados:
- Docker Compose levantó los servicios.
- PostgreSQL alcanzó el estado saludable.
- Se aplicaron las migraciones.
- Se conservaron 12 servicios de nivel 1 y 46 de nivel 2.
- Se generaron 5,000 dispositivos CMDB.
- Se prepararon 7 colas y 37 tickets de demostración.

### Pruebas automatizadas

Comando ejecutado:

`powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1`

Resultados obtenidos:
- Django system check: 0 problemas.
- Pruebas encontradas: 80.
- Pruebas ejecutadas: 80.
- Pruebas aprobadas: 80.
- Tiempo observado: 30.188 segundos.
- Resultado final: HARNESS PRINCIPAL: OK.

La suite creó una base de datos temporal de pruebas y la eliminó
al finalizar, sin borrar los datos preparados para evaluación.

### P18. Persistencia después de reiniciar Docker

Comando utilizado:

`docker compose restart`

Conteos observados antes del reinicio:
- Dispositivos: 5,000.
- Tickets: 37.
- Colas: 7.

Conteos observados después del reinicio:
- Dispositivos: 5,000.
- Tickets: 37.
- Colas: 7.

Resultado: los conteos principales permanecieron iguales.
### Segunda comprobación de P18

Fecha: 28 de octubre de 2026.

Se ejecutó nuevamente `docker compose restart` después
de generar el incidente SD-0000038.

| Información | Antes | Después |
|---|---:|---:|
| Catálogo nivel 1 | 12 | 12 |
| Catálogo nivel 2 | 46 | 46 |
| Dispositivos CMDB | 5,000 | 5,000 |
| Tickets | 38 | 38 |
| Colas | 7 | 7 |
| Registros de bitácora | 163 | 163 |
| Vínculos evento-incidente | 1 | 1 |

Resultado obtenido: los siete conteos permanecieron idénticos.

La prueba confirma la persistencia de los registros principales,
incluido el historial de auditoría y la vinculación del evento E2.
No se verificó la conservación de archivos adjuntos en este ensayo.

### P11. Evento E2 e incidente generado

Prueba funcional realizada desde la aplicación web:

- Ticket de origen: SD-0000020.
- Proceso: Gestión de eventos.
- Categoría: E2.
- Estado inicial: EVALUADO.
- Acción: transición a RESPONDIDO.
- Resultado: incidente SD-0000038 generado automáticamente.
- Se registró una notificación dentro de la aplicación.
- La bitácora registró INCIDENTE_DERIVADO y TRANSICION.
- Actor observado: admin_demo.
- Se conservaron los valores anteriores, nuevos y el motivo.

Después de esta operación, el total de tickets pasó de 37 a 38.

Resultado: caso E2 comprobado funcionalmente.
Pendiente: completar las verificaciones manuales de E0, E1 y E3.

Las capturas fueron revisadas durante la sesión de trabajo.
Falta incorporarlas como archivos de evidencia versionados.

### P11. Verificacion automatizada E0-E3

Fecha: 28 de octubre de 2026.

Comando ejecutado:

`docker compose run --rm web python manage.py test apps.service_desk.tests.DeskTests.test_p11_categorias_eventos_e0_e3 -v 2`

Entrada: cuatro categorias de eventos E0, E1, E2 y E3.

Resultados obtenidos:
- E0: registro sin incidente ni notificacion.
- E1: evaluacion sin incidente ni notificacion.
- E2: incidente I1 y notificacion.
- E3: incidente I6 y notificacion.
- Reprocesamiento E2/E3: no se duplicaron incidentes ni avisos.
- Una prueba automatizada con cuatro subpruebas.
- Tiempo observado: 2.561 segundos.
- Resultado: OK.

Verificacion posterior:
- Suite completa: 82 pruebas.
- Aprobadas: 82.
- Tiempo observado: 33.492 segundos.
- Django system check: 0 problemas.
- Resultado: HARNESS PRINCIPAL: OK.

La prueba utilizo una base temporal de PostgreSQL y no modifico
los datos de demostracion.

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
| P09 | `workflows.py` y `apps/service_desk/tests.py` | Siete recorridos completos con aprobaciones, rechazo de cierre directo y bitácora; prueba aprobada en PostgreSQL | Verificación manual adicional por roles |
| P10 | `TicketApproval` | Cambio sin aprobar y autoaprobación rechazados | — |
| P11 | `EventIncident`, `DeskNotification` y pruebas Django | E0-E3 comprobados en PostgreSQL: E0/E1 sin incidente, E2 con incidente I1 y E3 con incidente I6; E2 verificado tambien en interfaz | Demostracion manual E3 pendiente |
| P12 | `INCIDENT_GUIDANCE`, función complementaria | Pruebas de límites y mapeo | Revisión detallada de I0–I6 UI |
| P13 | `TicketRelation` | Relaciones entre tickets modeladas | Recorrido incidente–problema–cambio |
| P14 | `CIRelation`, `potentially_affected_services` | Ciclos y recorrido inverso probados | Navegación en PostgreSQL |
| P15 | `TicketHistory`, `reopen_ticket` | Reapertura, cierre, actor | — |
| P16 | Vista `cmdb:list`, 30 por página | Medicion real en PostgreSQL sobre 5000 CI: paginas 1, 84, 167 y filtro SERVIDOR; ver `docs/evidencias/P16-medicion-20261028.md` | Latencia HTTP no medida |
| P17 | `dashboard`, `pause_ticket`, `resume_ticket` | Conteos y pausa | Métricas controladas con reapertura |
| P18 | `postgres_data`/`attachments_data` Compose | Reinicio real: 12 N1, 46 N2, 5,000 CI, 38 tickets, 7 colas, 163 registros de auditoría y 1 vínculo evento-incidente conservados | Persistencia de archivos adjuntos aún no ensayada |

No se informa como exitoso un caso parcialmente implementado. Las pruebas
aislan sus datos y no eliminan los registros de evaluación. Para capturas de
P18, ejecutar `docker compose restart`, consultar totales antes y después,
sin `down -v`, y anotar commit, fecha y resultado obtenido.

### P09. Validacion automatizada de los siete procesos

**Fecha:** 28 de octubre de 2026.

**Comando ejecutado:**

`docker compose run --rm web python manage.py test apps.service_desk.tests.DeskTests.test_p09_rutas_completas_siete_procesos -v 2`

**Entrada:** siete procesos configurados, estados diferenciados,
roles de agente y aprobador y datos de prueba aislados.

**Resultado esperado:** cada proceso recorre sus transiciones permitidas
hasta CERRADO; se rechaza el cierre directo; se registran las aprobaciones
correspondientes y la bitacora conserva las transiciones.

**Resultado obtenido:**
- Una prueba automatizada que contiene siete subpruebas.
- Los siete recorridos finalizaron correctamente.
- Tiempo observado: 3.015 segundos.
- Resultado final: OK.

**Verificacion posterior del harness completo:**

`powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1`

- Pruebas encontradas: 81.
- Pruebas aprobadas: 81.
- Tiempo observado: 32.334 segundos.
- Django system check: 0 problemas.
- Resultado final: HARNESS PRINCIPAL: OK.

Los datos se generaron en una base temporal de PostgreSQL.
La base de evaluacion no fue modificada por estas pruebas.

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
