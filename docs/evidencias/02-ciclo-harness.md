# Evidencia de ciclo de Harness Engineering

Fecha: 30 de septiembre de 2026

## Objetivo

Documentar un ciclo real de trabajo donde un cambio funcional fue validado por el harness, produjo un fallo detectable, se diagnosticó y se corrigió hasta obtener una ejecución satisfactoria.

El fallo documentado no fue introducido artificialmente.

---

## 1. Tarea original

Durante una etapa temprana del desarrollo se creó una ruta temporal:

`/admin-test/`

Su propósito era comprobar de forma rápida que:

- un usuario ADMIN podía acceder a una operación protegida;
- un usuario CONSULTA recibía HTTP 403;
- un usuario anónimo era redirigido al login.

La ruta era únicamente una herramienta temporal de comprobación.

---

## 2. Cambio realizado

Cuando se implementó el CRUD real de usuarios, la ruta temporal dejó de ser necesaria.

Se eliminó:

`accounts:admin_test`

y se comenzó a utilizar una operación administrativa real:

`accounts:user_create`

Esto permitió que las pruebas de autorización se ejecutaran contra funcionalidad real del sistema.

---

## 3. Control automático ejecutado

Después del cambio se ejecutó la suite automatizada:

    docker compose run --rm web python manage.py test apps.accounts apps.organization apps.imports -v 1

---

## 4. Fallo detectado

La suite encontró tres errores.

Resultado observado:

    Found 24 test(s).

    ERROR: test_admin_can_access_admin_operation
    ERROR: test_anonymous_user_is_redirected_to_login
    ERROR: test_consulta_is_rejected_by_server

Los tres errores tenían el mismo origen:

    django.urls.exceptions.NoReverseMatch:
    Reverse for 'admin_test' not found.
    'admin_test' is not a valid view function or pattern name.

---

## 5. Diagnóstico

La aplicación real no estaba fallando.

El problema era que tres pruebas automatizadas todavía dependían de la ruta temporal eliminada.

El harness detectó que los controles habían quedado desactualizados respecto de la implementación actual.

---

## 6. Decisión tomada

No se restauró `/admin-test/`.

Restaurar una ruta temporal únicamente para satisfacer pruebas antiguas habría mantenido código sin valor funcional.

En su lugar, las pruebas fueron actualizadas para utilizar una operación administrativa real:

    reverse("accounts:user_create")

De esta manera se conservaron los mismos objetivos de validación:

- ADMIN puede acceder;
- CONSULTA recibe HTTP 403;
- usuario anónimo es redirigido al login.

---

## 7. Corrección aplicada

Las referencias antiguas:

    reverse("accounts:admin_test")

fueron reemplazadas por:

    reverse("accounts:user_create")

Luego se volvió a ejecutar la suite.

---

## 8. Resultado después de la corrección

Resultado observado:

    Found 24 test(s).
    ........................
    Ran 24 tests

    OK

Esto confirmó que la corrección fue satisfactoria.

---

## 9. Evolución posterior del harness

Después de continuar implementando el proyecto, la suite fue ampliada para cubrir:

- autenticación;
- autorización;
- jerarquía organizacional;
- CRUD de usuarios;
- catálogo N1;
- catálogo N2;
- búsqueda;
- filtros;
- paginación;
- importación Excel;
- idempotencia;
- conflicto SE.12;
- catálogos maestros;
- responsables;
- validaciones de dominio;
- persistencia Docker.

Última ejecución documentada:

    Found 49 test(s).
    .............................................
    Ran 49 tests

    OK

Además, el script principal concluyó:

    HARNESS PRINCIPAL: OK

---

## 10. Persistencia como control adicional

Se agregó:

`scripts/test_persistence.ps1`

Este script compara el estado de la base antes y después de:

    docker compose down
    docker compose up -d

sin eliminar el volumen.

Resultado observado:

    Antes:   12|46|2|2|3
    Despues: 12|46|2|2|3

Resultado final:

    P12 OK: los datos persistieron sin eliminar el volumen.

---

## 11. Conclusión

El harness no se utilizó solamente para confirmar que el sistema funcionaba.

También permitió detectar una inconsistencia real entre:

- la evolución del código;
- las rutas existentes;
- las pruebas automatizadas.

El ciclo demostrado fue:

    tarea
    -> cambio
    -> ejecución de controles
    -> fallo
    -> diagnóstico
    -> corrección
    -> nueva ejecución
    -> éxito

La corrección priorizó mantener pruebas alineadas con funcionalidad real en lugar de conservar código temporal sin utilidad para el usuario final.

