# Prompt 02 - Arquitectura y modelo de datos

Fecha: 30 de septiembre de 2026

Herramienta: ChatGPT

Modelo utilizado: GPT-5.6 Sol

## Objetivo

Definir una arquitectura simple, reproducible y adecuada para el parcial.

## Contexto proporcionado

El sistema requiere:

- aplicación web;
- autenticación local;
- usuarios y roles;
- estructura organizacional;
- catálogo N1 y N2;
- importación Excel;
- PostgreSQL;
- Docker;
- pruebas automatizadas.

El proyecto debe poder ejecutarse sin instalar Python ni PostgreSQL directamente en el host.

## Prompt de trabajo utilizado

Diseñar una arquitectura monolítica simple utilizando Django y PostgreSQL.

Modelar:

    Empresa
    -> Área
    -> Departamento
    -> Sección
    -> Puesto
    -> Usuario

y:

    Servicio N1
    -> Servicio N2

Agregar entidades para:

- Clase;
- Criticidad;
- Tipo;
- ejecuciones de importación;
- observaciones;
- trazabilidad por registro.

## Restricciones

- evitar complejidad innecesaria;
- no utilizar React ni una API separada si no son necesarias;
- PostgreSQL debe persistir en volumen Docker;
- los códigos subordinados deben ser únicos dentro de su padre;
- no almacenar secretos reales en Git;
- utilizar migraciones versionadas.

## Salida esperada

- estructura Django;
- modelos;
- relaciones;
- restricciones;
- migraciones;
- configuración Docker.

## Criterio de aceptación

Los siguientes comandos deben finalizar correctamente:

    python manage.py check
    python manage.py makemigrations --dry-run

Las migraciones deben representar la jerarquía organizacional, usuarios, catálogo e importaciones.
