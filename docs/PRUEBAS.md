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

## Evidencia final P07 P13 P17 P18

**Fecha:** 28 de octubre de 2026.

**Entorno:** Windows, PowerShell, Docker Compose y PostgreSQL 17.

**Commit de implementacion y pruebas:** `58c8625`.

### P07. Reclamo concurrente real

Comando:

`docker compose run --rm web python manage.py test apps.service_desk.tests.P07ConcurrentClaimTests.test_p07_dos_agentes_reclaman_mismo_ticket_postgresql -v 2`

Entrada:
- Un ticket disponible en una cola de incidentes.
- Dos usuarios operativos autorizados como agentes.
- Dos hilos concurrentes con conexiones independientes a PostgreSQL.

Resultado esperado:
- Una asignacion exitosa.
- Un conflicto para el segundo agente.
- Una sola asignacion conservada en la base de datos.

Resultado obtenido:
- Prueba aprobada.
- Tiempo observado: 0.325 segundos.
- Una asignacion y un conflicto.
- Una sola entrada ASIGNACION en la bitacora.

La prueba utilizo una base temporal y no modifico los tickets de evaluacion.

### P13. Relacion incidente-problema-cambio

Prueba:

`apps.service_desk.tests.DeskTests.test_p13_trazabilidad_incidente_problema_cambio`

Entrada:
- Un incidente.
- Un problema.
- Un cambio.
- Relaciones verificables entre los tres tickets.

Resultado obtenido:
- Incidente vinculado a problema.
- Problema vinculado a cambio.
- Recorrido recuperado desde el ORM.
- Relaciones inversas recuperables.
- Historial de creacion presente.

Limitacion:
- La prueba acredita el modelo y su trazabilidad.
- Falta demostrar el recorrido especializado en la interfaz.

### P17. Indicadores con datos controlados

Prueba:

`apps.service_desk.tests.DeskTests.test_p17_indicadores_controlados_pausas_reaperturas`

Entrada:
- Tres tickets de prueba.
- Uno en pausa.
- Uno cerrado.
- Uno reabierto.

Resultado obtenido:
- Total: 3 tickets.
- Abiertos: 2.
- En pausa: 1.
- Primera atencion promedio: 11.7 minutos.
- Resolucion promedio: 70.0 minutos.
- Mayor antiguedad: 3.3 horas.
- Cumplimiento de primera respuesta: 100 %.
- Cumplimiento de resolucion: 100 %.
- Reapertura registrada en bitacora.

Estos resultados pertenecen a datos controlados en una base temporal.

### P18. Persistencia real de adjunto

Comando de reinicio:

`docker compose restart`

Archivo sintetico:

`desk/ticket_1/P18-persistencia-sintetica.txt`

Resultado antes del reinicio:
- Identificador del adjunto: 1.
- SHA-256:
  `22a50c62d51b57aac317ebfe5fb559b32dd2a7b75610e47c006af4c6c1b5ef9a`

Resultado despues del reinicio:
- Identificador del adjunto: 1.
- Misma ruta.
- Mismo SHA-256.

Conclusion:
- El archivo mantuvo su contenido tras reiniciar los contenedores.
- La base de datos conservo la referencia del adjunto.
- El archivo pertenece a los datos sinteticos de demostracion.

### Harness completo posterior

Comando:

`powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1`

Resultado obtenido:
- PostgreSQL saludable.
- Django system check: 0 problemas.
- Pruebas encontradas: 85.
- Pruebas aprobadas: 85.
- Tiempo observado: 18.675 segundos.
- Resultado: HARNESS PRINCIPAL: OK.
- Commit publicado: `58c8625`.

Las pruebas automatizadas usan una base temporal. No se eliminaron los
5,000 dispositivos ni los tickets preparados para la evaluacion.

### Validacion final de nuevas funciones web

**Fecha:** 28 de octubre de 2026.

**Commit:** `7f7d577`.

**Entorno:** Docker Compose, Django y PostgreSQL.

Se incorporaron dos funciones adicionales:

1. Crear o vincular un servicio de catalogo desde una solicitud aprobada.
2. Relacionar tickets desde la interfaz y consultar los vinculos.

#### Prueba de servicios aprobados

Prueba ejecutada:

`apps.service_desk.tests.DeskTests.test_ui_nuevo_servicio_aprobado_sin_duplicados`

Se verifico:
- Rechazo de la operacion antes de la aprobacion.
- Aprobacion registrada mediante el flujo del ticket.
- Creacion de un servicio N2 desde el ticket.
- Vinculacion con su servicio N1.
- Repeticion sin duplicar el servicio.
- Vinculacion a un servicio N2 existente.
- Bitacora de SERVICIO_VINCULADO.
- Rechazo HTTP 403 para un solicitante sin permiso.

Resultado: OK.

#### Prueba de relaciones desde la interfaz

Prueba ejecutada:

`apps.service_desk.tests.DeskTests.test_ui_relaciones_incidente_problema_cambio`

Se verifico:
- Vinculo incidente-problema.
- Vinculo problema-cambio.
- Relaciones consultables en ambos sentidos.
- Visualizacion desde el detalle del ticket.
- Repeticion sin duplicar la relacion.
- Rechazo de autorrelaciones.
- Rechazo HTTP 403 para operaciones sin permiso.
- Bitacora de VINCULO_TICKET.

Resultado: OK.

#### Pruebas nuevas

Comando:

`docker compose run --rm web python manage.py test apps.service_desk.tests.DeskTests.test_ui_nuevo_servicio_aprobado_sin_duplicados apps.service_desk.tests.DeskTests.test_ui_relaciones_incidente_problema_cambio -v 2`

Resultado:
- Pruebas ejecutadas: 2.
- Pruebas aprobadas: 2.
- Tiempo observado: 1.456 segundos.

#### Harness completo posterior

Comando:

`powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1`

Resultado obtenido:
- Django system check: 0 problemas.
- Pruebas encontradas: 87.
- Pruebas aprobadas: 87.
- Tiempo observado: 18.203 segundos.
- Resultado final: HARNESS PRINCIPAL: OK.

Las pruebas utilizaron una base temporal de PostgreSQL.
No modificaron los datos preparados para evaluacion.

Pendiente: realizar la demostracion manual de las nuevas funciones
en el navegador durante la defensa.

## Matriz

| Caso | Implementación | Evidencia actual | Pendiente |
|---|---|---|---|
| P01 | `accounts`, `permissions.py` | 49 tests originales + rechazo CONSULTA | Ensayo web en Docker |
| P02 | `import_catalog --verify-original` | 12/46, conflicto SE.12 retenido | Repetir en PostgreSQL |
| P03 | `seed_cmdb` | Test 5000 + repetición sin duplicados | Medir en PostgreSQL |
| P04 | `CIClass` y fuentes | Validación de ciclos y `MODELO.md` | Contraste visual en defensa |
| P05 | `create_ticket` | Valida cola, solicitante, servicio, motivo CI | Caso más amplio de FK inválidas |
| P06 | `QueueRoleGrant`, `QueueUserGrant` | Pruebas de acceso/grants y CONSULTA | Ensayo web por rol |
| P07 | claim_ticket y P07ConcurrentClaimTests | Dos agentes simultaneos en PostgreSQL: una asignacion y un conflicto; una sola entrada ASIGNACION. Prueba aprobada en 0.325 s. | — |
| P08 | `transfer_ticket` | Rechaza proceso incompatible, exige motivo | Ensayo UI |
| P09 | `workflows.py` y `apps/service_desk/tests.py` | Siete recorridos completos con aprobaciones, rechazo de cierre directo y bitácora; prueba aprobada en PostgreSQL | Verificación manual adicional por roles |
| P10 | `TicketApproval` | Cambio sin aprobar y autoaprobación rechazados | — |
| P11 | `EventIncident`, `DeskNotification` y pruebas Django | E0-E3 comprobados en PostgreSQL: E0/E1 sin incidente, E2 con incidente I1 y E3 con incidente I6; E2 verificado tambien en interfaz | Demostracion manual E3 pendiente |
| P12 | `INCIDENT_GUIDANCE`, función complementaria | Pruebas de límites y mapeo | Revisión detallada de I0–I6 UI |
| P13 | `TicketRelation`, vistas web y pruebas Django | Incidente-problema-cambio recuperable desde ORM y visible en el detalle web; permisos, vinculación y rechazo de duplicados comprobados. | Ensayo manual adicional en navegador |
| P14 | `CIRelation`, `potentially_affected_services` | Ciclos y recorrido inverso probados | Navegación en PostgreSQL |
| P15 | `TicketHistory`, `reopen_ticket` | Reapertura, cierre, actor | — |
| P16 | Vista `cmdb:list`, 30 por página | Medicion real en PostgreSQL sobre 5000 CI: paginas 1, 84, 167 y filtro SERVIDOR; ver `docs/evidencias/P16-medicion-20261028.md` | Latencia HTTP no medida |
| P17 | dashboard, pausas y reapertura | Tres tickets controlados: 2 abiertos, 1 pausado, primera respuesta promedio 11.7 min, resolucion promedio 70 min y antiguedad maxima 3.3 h. | Demostracion manual adicional |
| P18 | Volúmenes `postgres_data` y `attachments_data` | Reinicio real: catálogo, 5,000 CI, tickets e historial conservados; adjunto sintético recuperado con SHA-256 idéntico. | — |

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

## Cierre adicional de seguridad

Se incorporaron controles específicos para impedir que un
usuario de consulta modifique tickets propios mediante
comentarios, adjuntos o reaperturas.

También se incorporó una validación básica de firma de archivo
para PDF, PNG y JPEG, así como comprobación de contenido textual
UTF-8 y del límite de 10 MiB.

Pruebas añadidas:

- `test_consulta_no_modifica_ticket_propio_por_http`
- `test_adjuntos_rechazan_contenido_falso_y_tamano_excesivo`

Estas pruebas no sustituyen un análisis antivirus ni un
escáner de seguridad de contenido. Su resultado debe validarse
con el harness antes de publicar.

## Validación final de 89 pruebas

Fecha: 28 de octubre de 2026.
Entorno: Windows, Docker Compose y PostgreSQL.

Se incorporaron dos pruebas adicionales de seguridad:

- Rechazo de comentarios, adjuntos y reaperturas desde el rol CONSULTA.
- Rechazo de contenido incompatible con la extensión y de archivos mayores de 10 MiB.

La ejecución aislada de las dos pruebas resultó satisfactoria.
El harness completo aprobó 89 de 89 pruebas.

La validación de firmas es básica; no equivale a inspección antivirus
ni a validación estructural completa de documentos.

Las evidencias de prompts literales 07, 08 y 09 son solicitudes reales.
Los registros previos requieren comprobar su literalidad antes de
declarar completo ese requisito académico.