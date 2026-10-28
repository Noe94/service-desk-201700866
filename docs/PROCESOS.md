# Procesos de Service Desk y niveles de soporte

## Tipos, colas y estados

Lección 25, diapositiva 14: seis tipos; la tarea exige **siete** procesos, por eso
`NUEVOS_SERVICIOS` comparte el tipo `REQUISICION_SERVICIO` pero tiene flujo propio.

| Proceso | Cola de demostración | Tipo de ticket | Ruta principal |
|---|---|---|---|
| Nuevos servicios | `Q-NUEVOS` | Requisición de servicio | Solicitado → Análisis → Pendiente aprobación → Aprobado → Implementación → Resuelto → Cerrado |
| Cambios | `Q-CAMBIOS` | Solicitud de cambio | Solicitado → Evaluación → Pendiente aprobación → Aprobado → Planificado → Ejecución → Validación → Resuelto → Cerrado |
| Incidentes | `Q-INCIDENTES` | Incidente | Registrado → Clasificado → Diagnóstico → Atención → Recuperado → Resuelto → Cerrado |
| Eventos | `Q-EVENTOS` | Evento | Registrado → Clasificado → Evaluado → Respondido → Resuelto → Cerrado |
| Problemas | `Q-PROBLEMAS` | Problema | Registrado → Investigación → Solución temporal / Error conocido → Solución definitiva → Resuelto → Cerrado |
| Accesos | `Q-ACCESOS` | Solicitud de acceso | Solicitado → Pendiente aprobación → Aprobado → Provisionado → Validado → Resuelto → Cerrado |
| Servicios TI | `Q-SERVICIOS` | Requisición de servicio | Solicitado → Validación → Asignación → Cumplimiento → Confirmación → Resuelto → Cerrado |

Las rutas y ramificaciones exactas están en `apps/service_desk/workflows.py`.
Una transición fuera de las aristas permitidas se rechaza. Cada proceso expone
campos distintos en `PROCESS_DETAIL_FIELDS`. Cambios exige impacto, riesgo, pruebas,
reversión y aprobación antes de ejecutar. Accesos exige beneficiario, recurso,
permiso y una aprobación distinta del solicitante. Incidentes requieren solución
antes de resolver. Problemas piden causa raíz antes de la solución definitiva.
Los servicios nuevos piden necesidad y viabilidad antes de aprobar.

**Limitación explícita:** los campos de código propuesto y de cambio correctivo están
documentados como información de expediente; la creación automática de un catálogo nuevo
y la vinculación formal problema–cambio mediante selector dedicado siguen pendientes.
No se deben prometer en la defensa como automatismos ya implementados.

## Roles y autorizaciones

El rol base `ADMIN` administra configuración; `CONSULTA` conserva solo lectura
sin elevación por grupos. El rol `OPERATIVO` admite grupos simultáneos
`SOLICITANTE`, `AGENTE` y `APROBADOR` según el caso. Cada cola concede por
grupo o usuario cinco permisos independientes: ver, atender, transferir,
aprobar, administrar. El servidor revalida cada acción; `administrar` habilita
editar la configuración de la cola propia, mientras que crear colas o delegar
permisos queda reservado a `ADMIN`.

Política de asignación **manual**, con ordenamiento de colas
**prioridad → antigüedad → ID**. `claim_ticket()` utiliza `select_for_update`
en una transacción y rechaza el segundo intento. Al transferir se valida
proceso compatible, motivo y cola activa; se elimina la asignación anterior.
No se desactiva una cola con tickets abiertos ni un usuario con tickets abiertos
asignados. No se permite modificar la bitácora mediante `save`/`delete` del modelo.

## Eventos E0-E3

Lección 25, diapositiva 15:

| Categoría | Comportamiento |
|---|---|
| E0 | Programado: conservar registro. No crear incidente. |
| E1 | No programado sin impacto: documentar evaluación. No respuesta operativa obligatoria. |
| E2 | Impacto al servicio: al pasar a Respondido, crear incidente y notificación interna verificable. |
| E3 | Impacto de seguridad: igual a E2; incidente generado con categoría I6. |

`EventIncident` tiene una relación uno a uno sobre el evento: procesar de nuevo
no genera duplicados. `DeskNotification` contiene el aviso en la aplicación, visible
en el detalle del evento, sin correo real. Un evento no avanza a Respondido
sin poder crear el incidente y el aviso en la misma transacción.

## Incidentes I0-I6

Transcripción visual de la **diapositiva 16** de la lección 25:

| Categoría | Duración / criterio de la diapositiva | Banda de prioridad | Redundancia en la tabla |
|---|---|---|---|
| I0 | No hay interrupción | Baja | Existe |
| I1 | Hasta 3 horas (incluye degradaciones) | Media | No existe |
| I2 | Hasta 8 horas (incluye degradaciones) | Media | No existe |
| I3 | Hasta 2 días | Alta | No existe |
| I4 | Hasta 1 semana | Alta | No existe |
| I5 | 1 mes o más | Alta | No existe |
| I6 | Seguridad de información y recursos | Alta | No existe |

**Decisión del proyecto, no de las diapositivas:** para una sugerencia de categoría
basada en duración estimada se elige el menor intervalo aplicable: hasta 180 min I1,
hasta 480 I2, hasta 2,880 I3; desde ese punto y menos de 43,200 I4 (incluye
declaradamente la laguna de más de una semana y menos de un mes); desde
43,200 I5. Si no hay interrupción, I0; si es seguridad, I6 prevalece.
`propose_incident_category()` implementa la regla y su prueba cubre los límites.
La categoría real se puede elegir manualmente: tiempos son clasificación,
**no** un SLA de resolución por sí solos.

Se recomienda P4 para Baja, P3 para Media y P2/P1 para Alta. El sistema conserva
prioridad editable por separado, y guarda `estimated_interruption_minutes`,
`actual_interruption_minutes` y `redundancy_available`.

## Nivel de soporte y escalamiento

La figura 11 muestra niveles 0–4 (Autoservicio, Help Desk, Soporte Técnico,
Ingenieros, Externo). El texto de diapositivas 12–13 usa 0–3 y denomina
proveedor externo al nivel 3. Este proyecto usa los **cinco niveles de la figura 11**:

| Nivel | Implementación adoptada |
|---|---|
| 0 | FAQ y portal de conocimiento |
| 1 | Help Desk / atención inicial |
| 2 | Soporte técnico especializado |
| 3 | Ingeniería y resolución avanzada |
| 4 | Proveedores externos |

`Queue.support_level` admite 0–4 y permite transferir dentro del proceso
a otra cola (incluida una de nivel superior). El texto de lección 25 usa
equivalencias diferentes para niveles 2/3; no se fuerza 20/70/5/5 % como cuota.

## Indicadores y objetivos

`/mesa/tablero/` calcula, sobre tickets autorizados: conteos por cola, proceso,
prioridad y estado; tickets abiertos; tickets pausados; mayor antigüedad de abiertos;
promedio de primera respuesta; promedio de resolución; y porcentaje dentro del
objetivo configurado de cada cola. La unidad es **tiempo calendario**.

Fórmula: `minutos_efectivos = (momento - creación) / 60 - pausas_acumuladas / 60`.
Las pausas abiertas se descuentan hasta el momento observado. Los tickets sin
primera respuesta o resolución aún no entran en sus promedios ni en el denominador
de cumplimiento, pero cuentan como abiertos; el tablero lo documenta.
La reapertura conserva el historial y el número de reaperturas, y la nueva
resolución reemplaza la marca anterior para medir el ciclo corriente.

## Regla de cierre y reapertura

Cerrar requiere resolución previa. La reapertura solo procede dentro de siete días
del cierre y con motivo. Cada acción registra fecha, actor y valores anterior/nuevo.
No se permite transición con pausa activa sin reanudar primero.
