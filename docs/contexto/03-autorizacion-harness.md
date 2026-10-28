# Actualización de contexto 02 - Autorización, validación y harness

Fecha: 30 de septiembre de 2026

## Motivo de la actualización

Durante la implementación funcional se confirmaron decisiones que amplían el contexto inicial del proyecto.

Esta actualización registra decisiones comprobadas mediante código y pruebas automatizadas.

---

## Autenticación

La aplicación utiliza autenticación local de Django.

Se permite iniciar sesión mediante:

- nombre de usuario;
- correo electrónico.

Las contraseñas se almacenan utilizando el mecanismo de hash de Django.

No se almacenan contraseñas funcionales dentro del repositorio.

Las cuentas reproducibles de evaluación reciben sus contraseñas mediante variables de entorno.

---

## Roles

Existen dos roles funcionales:

- `ADMIN`;
- `CONSULTA`.

### ADMIN

Puede realizar operaciones de mantenimiento sobre:

- estructura organizacional;
- usuarios;
- servicios N1;
- servicios N2;
- catálogos maestros.

### CONSULTA

Puede consultar información.

Las operaciones de modificación son rechazadas por el servidor.

La autorización no depende únicamente de ocultar botones en la interfaz.

---

## Bajas lógicas

Las entidades funcionales utilizan desactivación en lugar de eliminación física.

No se aplican cascadas silenciosas.

Ejemplo:

    Empresa
    -> Área
    -> Departamento
    -> Sección
    -> Puesto

Un padre no puede desactivarse mientras existan dependencias activas que requieran mantener la jerarquía.

---

## Usuarios

Cada usuario funcional pertenece a un Puesto.

A partir del Puesto puede recuperarse:

    Puesto
    -> Sección
    -> Departamento
    -> Área
    -> Empresa

Los usuarios inactivos no pueden autenticarse.

Un administrador no puede desactivar su propia cuenta desde el CRUD funcional.

---

## Responsables de servicios

Un servicio N2 puede tener:

- una sección responsable;
- opcionalmente un usuario responsable.

Si se selecciona un usuario responsable:

- debe existir una sección responsable;
- el usuario debe estar activo;
- su puesto debe pertenecer a la sección seleccionada.

Los servicios importados pueden permanecer sin responsable.

La base de demostración mantiene tres asignaciones válidas.

---

## Validaciones del catálogo

Se confirmó que:

- mínimo y máximo pueden ser NULL;
- ausencia no equivale a cero;
- si ambos existen, mínimo debe ser menor o igual que máximo;
- los códigos N1 son únicos;
- N2 pertenece exactamente a un N1;
- los catálogos Clase, Criticidad y Tipo se mantienen como entidades propias;
- los valores inactivos no deben utilizarse para nuevas asociaciones.

---

## Catálogos maestros

Se implementaron catálogos mantenibles para:

- Clase de servicio;
- Criticidad;
- Tipo de servicio.

Un valor utilizado por servicios no se desactiva silenciosamente.

---

## Autorización comprobada

La autorización se valida mediante controles del servidor.

Se comprobaron casos donde CONSULTA intenta acceder directamente a URLs administrativas.

Resultado esperado:

    HTTP 403 Forbidden

ADMIN puede ejecutar las mismas operaciones cuando cuenta con una sesión válida.

---

## Harness principal

El harness principal se encuentra en:

`scripts/verify.ps1`

Realiza:

1. levantamiento de servicios;
2. Django system check;
3. suite automatizada.

Resultado documentado:

    Found 49 test(s).
    Ran 49 tests
    OK
    HARNESS PRINCIPAL: OK

---

## Persistencia Docker

La prueba se encuentra en:

`scripts/test_persistence.ps1`

La prueba:

1. obtiene el estado de la base;
2. ejecuta `docker compose down`;
3. no utiliza `-v`;
4. levanta nuevamente los servicios;
5. obtiene nuevamente el estado;
6. compara ambos valores.

Resultado observado:

    Antes:   12|46|2|2|3
    Despues: 12|46|2|2|3

Resultado:

    P12 OK: los datos persistieron sin eliminar el volumen.

---

## Hallazgo del harness

Durante la evolución del proyecto se eliminó la ruta temporal:

`/admin-test/`

Tres pruebas todavía dependían de esa ruta.

La suite detectó:

    NoReverseMatch: admin_test

Decisión:

no restaurar código temporal solamente para satisfacer pruebas antiguas.

Las pruebas fueron actualizadas para validar una operación administrativa real:

`accounts:user_create`

Resultado posterior:

    Found 24 test(s).
    Ran 24 tests
    OK

Posteriormente la suite evolucionó hasta 49 pruebas satisfactorias.

La evidencia completa se encuentra en:

`docs/evidencias/02-ciclo-harness.md`

---

## Interfaz

La implementación utiliza:

- Django Templates;
- CSS propio.

No se utiliza Bootstrap en la implementación actual.

La presentación visual final será minimalista y utilizará un tema oscuro suave con contraste adecuado.

Los cambios visuales no deberán modificar reglas funcionales.

---

## Estado de aceptación

Los escenarios P01-P12 cuentan con evidencia reproducible.

Matriz:

`docs/evidencias/01-p01-p12.md`

Ciclo de Harness Engineering:

`docs/evidencias/02-ciclo-harness.md`

