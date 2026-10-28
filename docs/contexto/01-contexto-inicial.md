# Contexto inicial del proyecto

Fecha: 30 de septiembre de 2026

## Objetivo

Preparar el contexto inicial utilizado para comenzar el desarrollo del
Parcial Práctico 2 de Software Avanzado.

## Documentos utilizados

- Enunciado del parcial.
- CatalogoServicios.xlsx.
- Aclaración verbal del catedrático respecto al Excel como machote.

## Decisiones iniciales

Se utilizará:

- Django
- PostgreSQL
- Docker Compose
- openpyxl
- Bootstrap

Se eligió una arquitectura monolítica para reducir complejidad de
infraestructura y concentrar el esfuerzo en los requisitos
evaluados.

## Interpretación del Excel

El archivo constituye una fuente inicial de datos y referencia
estructural.

Los 12 códigos de Nivel 1 y los 46 códigos de Nivel 2 corresponden
al archivo original de evaluación y no representan límites del
sistema.

La aplicación debe permitir agregar servicios adicionales.

## Reglas identificadas

- No modificar el Excel original.
- Conservar códigos como texto.
- No inventar atributos ausentes.
- Resolver celdas combinadas utilizando los rangos reales.
- Registrar conflictos de información.
- Mantener trazabilidad del origen de los datos.