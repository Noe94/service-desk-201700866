# Actualización de contexto 01 - Análisis del Excel

Fecha: 30 de septiembre de 2026

## Motivo de la actualización

Se ejecutó el analizador real sobre `data/CatalogoServicios.xlsx`.

Esta actualización registra hallazgos comprobados mediante ejecución y sustituye supuestos iniciales por datos observados.

## Comando utilizado

`docker compose run --rm web python manage.py analyze_catalog data/CatalogoServicios.xlsx --verify-original`

## Resultado observado

El análisis identificó:

- hoja: `Servicios Externos`;
- fila de encabezados: 4;
- fila de inicio de opciones: 111;
- 12 códigos distintos de nivel 1;
- 46 códigos distintos de nivel 2;
- 5 observaciones de calidad.

El control automático 12 N1 / 46 N2 finalizó satisfactoriamente.

## Listas controladas observadas

### Activo

- S
- N

### Clase de servicio

- A DEMANDA
- RECURRENTE

### Criticidad

- Very Low
- Low
- Normal
- High
- Very High

### Tipo de servicio

- Back End
- Demostration
- End User Service
- Front End
- IT Management
- IT Operational
- Other
- Project
- Reporting
- Training
- Underpinning Contract

Los textos se conservarán como aparecen en la fuente. No se corregirá silenciosamente `Demostration` ni ninguna otra etiqueta.

## Hallazgo 1 - Celdas combinadas

Las filas físicas del Excel no equivalen directamente a servicios.

Decisión:

- utilizar los rangos reales de celdas combinadas;
- recuperar el valor desde la celda principal exclusivamente cuando la celda pertenece al rango;
- no aplicar forward-fill indiscriminado.

## Hallazgo 2 - Conflicto SE.12

El código `SE.12` presenta dos nombres distintos:

- `Suministrar Analitica`;
- `Mantener Tableros de Control`.

Decisión:

- mantener un solo `SE.12`;
- conservar como canónico el primer nombre válido encontrado;
- registrar el valor conflictivo como observación;
- conservar evidencia del origen.

La regla se implementa de forma general y no mediante una excepción hardcodeada para `SE.12`.

## Hallazgo 3 - SE.12.1, SE.12.2 y SE.12.3

Los códigos deben conservarse exactamente como texto:

- `SE.12.1`
- `SE.12.2`
- `SE.12.3`

No se transformarán a:

- `SE.12.01`
- `SE.12.02`
- `SE.12.03`

## Hallazgo 4 - Atributos incompletos

Los servicios:

- `SE.12.1`;
- `SE.12.2`;
- `SE.12.3`;

presentan atributos sin información.

Decisión:

- no inventar valores;
- conservar ausencias como NULL o estado desconocido;
- marcar los registros que requieren revisión;
- registrar observaciones de importación.

## Hallazgo 5 - Fila 101

`SE.12.3` no recibe su N1 mediante una celda combinada.

Se aplicó una regla explícita:

- obtener el prefijo del código N2;
- `SE.12.3` → `SE.12`;
- utilizarlo solamente cuando dicho N1 existe;
- registrar la transformación como observación trazable.

Esta regla evita realizar una propagación implícita desde la fila anterior.

## Consecuencias para la implementación

El importador deberá ser:

- repetible;
- idempotente;
- transaccional;
- trazable;
- capaz de distinguir creados, actualizados y omitidos;
- capaz de conservar observaciones;
- capaz de validar el archivo original con 12 N1 y 46 N2.

Los valores 12 y 46 son controles del archivo original y no límites del sistema.
