# Prompt 04 - Importación idempotente y trazable

Fecha: 30 de septiembre de 2026

Herramienta: ChatGPT

Modelo utilizado: GPT-5.6 Sol

## Objetivo

Importar el catálogo analizado hacia PostgreSQL de forma segura, repetible y trazable.

## Contexto proporcionado

El analizador ya había comprobado:

- 12 N1;
- 46 N2;
- cinco observaciones;
- conflicto de nombre para `SE.12`;
- atributos ausentes;
- existencia de celdas combinadas.

## Prompt de trabajo utilizado

Construir un importador Django que utilice el resultado del analizador.

El importador debe:

- utilizar una transacción;
- calcular SHA-256;
- registrar cada ejecución;
- registrar observaciones;
- conservar origen por fila o rango;
- validar modelos antes de guardar;
- distinguir creados, actualizados y omitidos;
- ser idempotente.

## Restricciones

- no modificar el Excel;
- no inventar valores faltantes;
- no duplicar códigos;
- conservar `SE.12.1`, `SE.12.2` y `SE.12.3`;
- mantener NULL cuando el dato es desconocido;
- no hardcodear servicios concretos;
- utilizar `full_clean()` antes de persistir datos importados.

## Salida esperada

Comando:

    python manage.py import_catalog data/CatalogoServicios.xlsx --verify-original

## Criterio de aceptación

Primera ejecución:

    Creados: 58
    Actualizados: 0
    Omitidos: 0
    N1: 12
    N2: 46

Segunda ejecución:

    Creados: 0
    Actualizados: 0
    Omitidos: 58
    N1: 12
    N2: 46

El SHA-256 registrado debe corresponder al archivo importado.
