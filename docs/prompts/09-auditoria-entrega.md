# Prompt 09 — Auditoría de seguridad y entrega

Fecha: 28 de octubre de 2026, Guatemala.
Herramienta: ChatGPT.
Naturaleza: solicitud literal de auditoría del estudiante.
Repositorio revisado: commit 1d5c18c.
Modalidad: inspección pública, sin alteraciones.

## Entrada literal

Audita la preparación final para entregar mi proyecto:

https://github.com/Noe94/service-desk-201700866

Objetivo:
Evaluar seguridad, pruebas automatizadas y
reproducibilidad del sistema según el PDF.

Contexto:
- Django, PostgreSQL y Docker Compose.
- 87 pruebas aprobadas.
- Catálogo con 12 N1 y 46 N2.
- 5,000 dispositivos.
- Siete colas.
- Pruebas P01-P18 documentadas.

Verifica:
1. Autenticación y autorización del servidor.
2. Protección del rol de consulta.
3. Seguridad de adjuntos.
4. Control de concurrencia.
5. Persistencia PostgreSQL.
6. Reproducibilidad del harness.
7. Cobertura P01-P18.
8. Archivos obligatorios de entrega.
9. Riesgos durante la defensa individual.

Restricciones:
- No mostrar secretos.
- No inventar ejecución de pruebas.
- Distinguir evidencia histórica de verificación actual.
- No modificar el repositorio.

Entrega un informe breve con resultados,
riesgos, acciones pendientes y criterios
para declarar el proyecto listo.

## Resultado resumido

La auditoría confirmó evidencia histórica de 87 pruebas y
encontró dos áreas de mejora: escritura desde el rol de consulta
y validación del contenido de los adjuntos.

Esta revisión motivó las pruebas y correcciones de seguridad
del cierre final. No se atribuye ninguna ejecución de pruebas
a la auditoría de solo lectura.
