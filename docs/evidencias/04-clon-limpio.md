# Evidencia de ejecución desde clon limpio

Fecha: 30 de septiembre de 2026

## Objetivo

Comprobar que una persona distinta puede clonar el repositorio, configurar el entorno, construir los contenedores y verificar el sistema sin depender de archivos locales no versionados.

## Procedimiento

Se creó un clon nuevo del repositorio en:

`parcial-catalogo-servicios-clean-test`

El clon inició con:

    git status
    nothing to commit, working tree clean

Se comprobó que `.env` no estaba versionado:

    Test-Path .env
    False

Luego se creó localmente desde:

    Copy-Item .env.example .env

## Construcción

Se ejecutó:

    docker compose up --build -d

Resultado:

- imagen web construida desde el Dockerfile;
- PostgreSQL iniciado;
- healthcheck satisfactorio;
- aplicación disponible en puerto 8000.

## Preparación desde base vacía

Se ejecutó:

    powershell -ExecutionPolicy Bypass -File scripts\prepare.ps1

Las migraciones se aplicaron desde cero.

Primera importación:

    N1 procesados: 12
    N2 procesados: 46
    Creados: 58
    Actualizados: 0
    Omitidos: 0
    Observados: 5

Se crearon las cuentas:

- `admin_demo`
- `consulta_demo`

y tres asignaciones válidas de responsables.

Resultado:

    PREPARACION: OK

## Estado de la base

Después de preparar el clon:

    N1: 12
    N2: 46
    Usuarios: 2
    Importaciones: 1
    Asignaciones: 3

## Suite automatizada

Se ejecutó:

    powershell -ExecutionPolicy Bypass -File scripts\verify.ps1

Resultado:

    Found 49 test(s).
    Ran 49 tests

    OK

    HARNESS PRINCIPAL: OK

## Persistencia

Se ejecutó:

    powershell -ExecutionPolicy Bypass -File scripts\test_persistence.ps1

Antes:

    12|46|2|1|3

Después:

    12|46|2|1|3

Resultado:

    P12 OK: los datos persistieron sin eliminar el volumen.

## Estado final del clon

    git status
    nothing to commit, working tree clean

## Conclusión

La aplicación puede construirse, configurarse, migrarse, poblarse, probarse y reiniciarse desde un clon limpio utilizando únicamente los archivos versionados y un `.env` local basado en `.env.example`.
