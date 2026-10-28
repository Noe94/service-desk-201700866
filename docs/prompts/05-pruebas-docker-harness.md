# Prompt 05 - Pruebas, Docker y harness

Fecha: 30 de septiembre de 2026

Herramienta: ChatGPT

Modelo utilizado: GPT-5.6 Sol

## Objetivo

Crear controles reproducibles para comprobar la aplicación antes de la entrega.

## Contexto proporcionado

El parcial define los criterios P01-P12.

También exige:

- Docker;
- PostgreSQL persistente;
- pruebas automatizadas;
- evidencia observable;
- ejecución sin depender de una API de IA.

## Prompt de trabajo utilizado

Crear una suite de pruebas que cubra los criterios P01-P12.

Incluir pruebas de:

- autenticación;
- logout;
- usuario inactivo;
- roles;
- CRUD organizacional;
- usuarios;
- importación;
- idempotencia;
- SE.12;
- mínimo y máximo;
- búsqueda;
- filtros;
- paginación;
- responsables;
- catálogos maestros.

Crear además un harness reproducible que:

1. levante contenedores;
2. ejecute Django check;
3. ejecute las pruebas;
4. devuelva código de salida observable.

Crear un control adicional de persistencia Docker.

## Restricciones

- las pruebas no deben destruir datos normales;
- utilizar una base temporal de tests;
- no eliminar el volumen durante la prueba P12;
- no depender de secretos reales;
- no depender de una API de IA para ejecutar la aplicación.

## Salida esperada

Scripts:

- `scripts/verify.ps1`;
- `scripts/test_persistence.ps1`.

Suite Django automatizada.

## Criterio de aceptación

Harness principal:

    Found 49 test(s).
    Ran 49 tests
    OK
    HARNESS PRINCIPAL: OK

Persistencia:

    Antes:   12|46|2|2|3
    Despues: 12|46|2|2|3
    P12 OK

