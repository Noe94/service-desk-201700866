# Iteraciones de mejora de Prompt Engineering

Fecha: 30 de septiembre de 2026

Herramienta: ChatGPT

Modelo utilizado: GPT-5.6 Sol

Este documento registra dos situaciones donde el contexto o el resultado inicial obligaron a mejorar la instrucción de trabajo antes de continuar.

---

## Iteración 1 - Interpretación del Excel

### Enfoque inicial

Al inicio podía interpretarse que el archivo entregado definía exactamente el universo del sistema:

    12 N1
    46 N2

Esto podía producir una implementación demasiado acoplada al archivo original.

### Nueva información

El catedrático aclaró que el Excel era un ejemplo o "machote".

Podrían existir:

- más servicios;
- más requerimientos;
- más registros.

### Prompt mejorado

Diseñar el sistema tomando la estructura del Excel como referencia, pero no los 12 N1 y 46 N2 como límites del dominio.

Los valores 12 y 46 deben utilizarse solamente como controles del archivo original de evaluación.

No hardcodear códigos de servicios concretos.

### Mejora obtenida

El sistema permite nuevos N1 y N2.

El importador analiza la estructura y no limita el catálogo a 12/46.

La opción `--verify-original` utiliza 12/46 únicamente cuando se desea comprobar el fixture original.

---

## Iteración 2 - Pruebas de autorización

### Enfoque inicial

Para comprobar rápidamente los roles se creó una ruta temporal:

    /admin-test/

Las pruebas verificaban la autorización contra esa ruta.

### Problema detectado

Cuando se implementó el CRUD real de usuarios se eliminó la ruta temporal.

El harness detectó tres errores:

    NoReverseMatch: admin_test

### Prompt mejorado

No restaurar una ruta temporal solamente para satisfacer pruebas antiguas.

Actualizar las pruebas para verificar la autorización contra una operación administrativa real:

    accounts:user_create

Mantener los mismos criterios:

- ADMIN permitido;
- CONSULTA HTTP 403;
- anónimo redirigido al login.

### Mejora obtenida

Las pruebas quedaron vinculadas a funcionalidad utilizada realmente por la aplicación.

Resultado inmediato:

    24 tests
    OK

Resultado posterior de la suite ampliada:

    45 tests
    OK

---

## Conclusión

Las iteraciones no consistieron únicamente en reformular texto.

Cada mejora respondió a nueva evidencia:

- aclaración del catedrático;
- fallo detectado por el harness.

Esto permitió reducir supuestos y mantener la implementación alineada con el problema real.
