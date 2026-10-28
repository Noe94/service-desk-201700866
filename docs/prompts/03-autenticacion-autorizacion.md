# Prompt 03 - Autenticación y autorización

Fecha: 30 de septiembre de 2026

Herramienta: ChatGPT

Modelo utilizado: GPT-5.6 Sol

## Objetivo

Implementar autenticación local y autorización mediante dos roles.

## Contexto proporcionado

El parcial requiere:

- usuario o correo más contraseña;
- almacenamiento seguro de contraseñas;
- usuario ADMIN;
- usuario CONSULTA;
- usuario inactivo sin acceso;
- operaciones protegidas en servidor.

## Prompt de trabajo utilizado

Implementar autenticación local utilizando Django.

Permitir login mediante:

- username;
- email.

Crear los roles:

- ADMIN;
- CONSULTA.

ADMIN puede mantener información.

CONSULTA puede visualizar información, pero cualquier intento de modificación debe ser rechazado por el servidor aunque conozca la URL.

Crear cuentas demo reproducibles sin almacenar sus contraseñas dentro del repositorio.

## Restricciones

- no almacenar contraseñas en texto plano;
- no guardar contraseñas reales en Git;
- no depender solamente de ocultar botones;
- usuario inactivo no puede autenticarse;
- las rutas administrativas deben estar protegidas en servidor.

## Salida esperada

- backend de autenticación;
- login/logout;
- control reusable de rol;
- cuentas demo;
- pruebas automatizadas.

## Criterio de aceptación

Debe comprobarse:

    login válido -> permitido
    login inválido -> rechazado
    usuario inactivo -> rechazado
    CONSULTA modificación -> HTTP 403
    ADMIN modificación -> permitido
    logout -> sesión invalidada
