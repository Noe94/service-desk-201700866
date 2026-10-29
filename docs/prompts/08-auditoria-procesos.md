# Prompt 08 — Auditoría de los siete procesos

Fecha: 28 de octubre de 2026, Guatemala.
Herramienta: ChatGPT.
Naturaleza: solicitud literal de auditoría del estudiante.
Repositorio revisado: commit 1d5c18c.
Modalidad: lectura de código y pruebas publicadas.

## Entrada literal

Audita los siete procesos del Service Desk disponible en:

https://github.com/Noe94/service-desk-201700866

Objetivo:
Comprobar que las colas, permisos, estados y transiciones
cumplen los requisitos del parcial.

Verifica:
1. Existencia de los siete procesos obligatorios.
2. Diferenciación real de sus flujos.
3. Configuración de colas y asignaciones.
4. Aprobación y rechazo.
5. Prevención de autoaprobaciones.
6. Creación o vinculación de servicios aprobados.
7. Eventos E0-E3 e incidentes I0-I6.
8. Relaciones incidente-problema-cambio.
9. Historial y trazabilidad.

Restricciones:
- Examina el código y pruebas disponibles.
- No supongas que una funcionalidad existe solo
  porque aparece en la documentación.
- No modifiques archivos ni datos.

Entrega hallazgos comprobados, riesgos,
recomendaciones y criterios de aceptación.

## Resultado resumido

El código presenta siete flujos, permisos específicos por cola,
aprobaciones, eventos, relaciones y bitácora.
Se identificaron pruebas manuales pendientes y una sección
desactualizada en PROCESOS.md.

No se afirma ejecución de nuevas pruebas en esta auditoría.
