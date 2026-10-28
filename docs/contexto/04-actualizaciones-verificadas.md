# Actualizaciones verificadas de contexto

Fecha: 28 de octubre de 2026.

Proyecto: Service Desk y CMDB.
Autor: Erick Noe Gomez Lopez.
Repositorio: Noe94/service-desk-201700866.

## Objetivo

Relacionar las decisiones, comprobaciones y actualizaciones
documentales con commits reales del repositorio.

Este registro no afirma que los commits se realizaron antes
de la implementacion inicial. Describe la evolucion verificable
desde que el proyecto se versiono en Git.

## Estado inicial

Commit: 00ad0f8

Se publico la base del proyecto:
- Catalogo de servicios.
- Sistema de tickets.
- Siete procesos.
- CMDB.
- Docker Compose.
- Harness.
- Documentacion inicial.

## Actualizacion 1: resultados reales de Docker

Commit: 8333c14

Contexto incorporado:
- Entorno Windows y PostgreSQL.
- 80 pruebas automatizadas aprobadas.
- Evento E2 con incidente generado.
- Primera comprobacion de persistencia.

Justificacion:
Sustituir la incertidumbre sobre la ejecucion Docker
por resultados comprobados en el equipo del estudiante.

## Actualizacion 2: persistencia y trazabilidad

Commit: 1644c8c

Contexto incorporado:
- Catalogo N1 y N2 conservados.
- 5000 CI conservados.
- 38 tickets conservados.
- 163 registros de auditoria conservados.
- Vinculo evento-incidente conservado.

Justificacion:
Ampliar la evidencia P18 para incluir integridad
referencial y trazabilidad.

## Actualizacion 3: siete procesos completos

Commit: f5de16b

Contexto incorporado:
- Recorridos completos de los siete procesos.
- Rechazo de transiciones invalidas.
- Aprobaciones y bitacora.
- Harness actualizado a 81 pruebas.

Justificacion:
La primera suite no demostraba una ruta completa
de cada uno de los siete procesos.

## Actualizacion 4: categorias E0-E3

Commit: 0e2044e

Contexto incorporado:
- Eventos E0 y E1 sin incidente.
- Evento E2 con incidente I1.
- Evento E3 con incidente I6.
- Reprocesamiento sin duplicados.
- Harness actualizado a 82 pruebas.

Justificacion:
Completar la comprobacion automatizada de las
cuatro categorias definidas por la leccion 25.

## Actualizacion 5: rendimiento CMDB

Commit: 8a57843

Contexto incorporado:
- 5000 dispositivos reales en PostgreSQL.
- 167 paginas.
- Tiempos observados de paginacion.
- Filtro de 1000 servidores.

Justificacion:
Reemplazar estimaciones de rendimiento por mediciones
reales y reproducibles.

## Separacion de contexto e instrucciones

Los archivos Excel y las presentaciones se trataron
como fuentes de datos y requisitos del curso.

AGENTS.md, MODELO.md, PROCESOS.md y PRUEBAS.md
conservan las decisiones y reglas del proyecto.

Las instrucciones del asistente se diferenciaron de
los datos externos para evitar interpretar contenido
de archivos como ordenes de ejecucion.

## Limitaciones de la evidencia

Los commits anteriores son reales y verificables.
No prueban por si solos que existieron tres cambios
de contexto previos al desarrollo.

La evidencia de Prompt Engineering debe contener
prompts literales realmente utilizados.
No deben inventarse mensajes ni resultados.