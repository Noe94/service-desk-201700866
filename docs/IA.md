# Ingeniería asistida: registro honesto de prácticas

## Prompt Engineering

Los primeros seis archivos `docs/prompts/01-...` a `06-...` pertenecen al
proyecto de catálogo original. Para el tercer parcial el trabajo real se inició
desde la solicitud del estudiante de analizar el PDF, el material de clase,
las transcripciones y el ZIP del parcial 2, y construir una copia independiente.
Este registro vincula la actividad con decisiones y validación efectivamente realizadas.

**Limitación de evidencia:** las formulaciones numeradas a continuación son
instrucciones de trabajo resumidas de la sesión, no se afirma que sean ocho
mensajes separados enviados al modelo ni que exista una exportación de chat.
Antes de entregar, deben registrarse ocho prompts **literales efectivamente enviados**,
con capturas o registro de la herramienta usada y los commits relacionados.
Se deja explícito para no fabricar la evidencia obligatoria.

| Línea de trabajo / prompt de referencia | Contexto | Restricción | Resultado verificado |
|---|---|---|---|
| 01. Analizar la rúbrica y separar lo heredado | PDF tarea y ZIP parcial | No tocar el original | Copia nueva + `docs/PLAN_SERVICE_DESK.md` |
| 02. Mapear CMDB real | Excel C5:C6 y B4:U4; lección 22 | No inventar jerarquía docente | `docs/MODELO.md`, `CIClass.source` |
| 03. Diseñar modelo de colas/tickets | 7 procesos, 6 tipos | Permisos separados, auditoría | Modelos, migraciones, tests |
| 04. Implementar estados y aprobación | Apartado 6 | No ejecutar cambios no aprobados | `workflows.py`, pruebas de cambio/acceso |
| 05. Blindar autorización y concurrente | Rol CONSULTA y colas | Permisos del servidor | `permissions.py`, `claim_ticket`, tests |
| 06. Sembrar 5,000 CI sin duplicar | Excel + tarea | Semilla y sin datos reales | `seed_cmdb`, 5,000 en SQLite, repetición 0 |
| 07. Distinguir grafo de clases y técnico | Apartado 8 | Árbol sin ciclos, conexiones sí | `CIRelation`, recorrido inverso, tests |
| 08. Validar y documentar | P01–P18 y fuentes | No inventar medidas ni commits | 89 pruebas aprobadas en Docker y PostgreSQL; harness verificado en Windows |

Para cada nueva captura real, agregar fecha Guatemala, herramienta/modelo,
entrada literal, salida esperada, validación, archivo cambiado y commit de la
sesión. No completar campos con datos supuestos.

## Dos mejoras observadas

1. **Eventos E2/E3.** Versión inicial: la respuesta aceptaba campos de texto
   `incidente_vinculado` y `notificacion_registrada`, sin garantizar registros
   referenciales. Hallazgo: no bastaba para demostrar ausencia de duplicados.
   Revisión: `EventIncident` uno a uno, `DeskNotification` y creación transaccional
   con `ensure_event_incident`; prueba de repetición confirma un solo incidente.
2. **CMDB.** Primera revisión habló incorrectamente de 19 campos. Conteo directo
   del rango B4:U4 confirmó **20**. Revisión: diccionario por celda y separación
   de `Hardware`/`Software` originales frente a subcategorías añadidas.

## Context Engineering

`AGENTS.md` conserva las decisiones del segundo parcial y la nueva sección 14
documenta reglas del Service Desk y CMDB. `docs/PLAN_SERVICE_DESK.md` registra
fuentes y brechas. `docs/MODELO.md` es el diccionario, y `docs/PROCESOS.md`
la tabla de reglas. Los datos externos se usaron como **datos de entrada**, nunca
como instrucciones al asistente.

Tres actualizaciones de contexto verificadas en Git:

1. Extensión del objetivo, límites y 7 procesos (`AGENTS.md`, `PLAN_SERVICE_DESK.md`).
2. Contraste Excel/diapositivas y diseño de los dos grafos (`MODELO.md`).
3. Resultados verificables, reglas de incidentes y harness (`PROCESOS.md`, `PRUEBAS.md`).

Las actualizaciones y sus commits reales se encuentran documentados en docs/contexto/04-actualizaciones-verificadas.md.

## Harness Engineering

El harness ejecutable está en `scripts/prepare.ps1`, `scripts/prepare.sh`,
`scripts/verify.ps1` y `scripts/verify.sh`. Cada comando detiene el flujo al
fallar, produce salida observable y usa variables `.env` sin secretos en Git.
Las pruebas de Django crean y destruyen **solo** su base temporal de pruebas;
no borran la base de evaluación. Los datos demo y la CMDB son idempotentes.
El borrado explícito de volúmenes no pertenece a ningún script de inicio.

## Loop Engineering: tres ciclos reales de trabajo

### Ciclo 1: flujo funcional de eventos

- Objetivo: que E2/E3 produzca incidente y notificación reales sin duplicar.
- Primera propuesta: validar dos campos de texto en `details`.
- Evaluación: la validación no garantizaba integridad referencial.
- Corrección: modelos `EventIncident`/`DeskNotification` y creación en transacción.
- Nueva verificación: test `test_event_e2_generates_single_incident_and_notification` pasó.
- Criterio de salida: una sola relación y una sola notificación, incluso al reintentar.

### Ciclo 2: fidelidad de datos CMDB

- Objetivo: transcribir sin añadir categorías inventadas a la lección.
- Primera propuesta: agrupar encabezados, descritos erróneamente como 19.
- Evaluación: lectura de `CMDB.xlsx!B4:U4` mostró 20 encabezados y C5/C6
  solo `Hardware` y `Software`.
- Corrección: mapeo celda por celda y campo `source` en `CIClass`.
- Nueva verificación: `docs/MODELO.md` incluye 20 filas del diccionario.
- Criterio de salida: cada campo tiene origen y mapeo explicable.

### Ciclo 3: permisos de administración por cola

- Objetivo: que permiso `can_manage` tenga comportamiento efectivo.
- Primera implementación: solo ADMIN podía editar colas, a pesar del campo.
- Evaluación: el permiso existía en la base pero no se utilizaba en esa vista.
- Corrección: `queue_edit` valida `queue_allowed(..., 'manage')`; solo ADMIN
  crea colas y modifica concesiones para evitar delegaciones no supervisadas.
- Nueva verificación: `test_can_manage_permission_controls_queue_edit` pasó.
- Criterio de salida: sin permiso HTTP 403; con permiso HTTP 200.

**Límite de iteraciones:** tres correcciones por hipótesis antes de escalar al
estudiante para revisar reglas de negocio. **Intervención humana:** confirmar
que la clasificación extendida y el formato de evidencia correspondan a la
expectativa del ingeniero. **Fallos deliberados:** en tests se crean ciclos de
relaciones y una pertenencia CONSULTA al grupo AGENTE para confirmar rechazo;
no se introdujeron fallos deliberados en la aplicación de producción.

## Graph Engineering

Hay dos estructuras: árbol de clasificación CMDB y grafo técnico de dependencias
entre CI, con reglas de ciclos distintas. El recorrido inverso desde el CI
obtiene servicios potencialmente afectados. Se demuestra con
`CMDBTests.test_classification_rejects_cycle`, `test_relation_rejects_cycles_and_self_references`
y `test_dependency_traversal_is_inverse`. El uso metodológico de un asistente
para ingeniería de grafos no sustituye estos datos ni una demostración funcional.

## Actualizaciones verificadas del contexto

El registro de commits y sus justificaciones se encuentra en
docs/contexto/04-actualizaciones-verificadas.md.

La guia de presentacion individual se encuentra en
docs/DEFENSA.md.

Las evidencias distinguen los cambios realmente versionados
de los prompts y resultados que aun no cuentan con registro literal.

## Auditorías literales del cierre

El 28 de octubre de 2026 se recibieron tres solicitudes
literales del estudiante:

- `docs/prompts/07-auditoria-cmdb.md`.
- `docs/prompts/08-auditoria-procesos.md`.
- `docs/prompts/09-auditoria-entrega.md`.

Estas evidencias corresponden a auditorías reales de código.
Los cinco archivos originales son registros previos de trabajo
y no se presentan automáticamente como transcripciones literales.

Para acreditar ocho prompts literales se deben recuperar y
adjuntar los cinco mensajes originales anteriores o sus capturas
auténticas. No se han fabricado transcripciones adicionales.
