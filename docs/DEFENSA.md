# Guia de defensa individual - Service Desk y CMDB

Autor: Erick Noe Gomez Lopez.
Carne: 201700866.

Repositorio:
https://github.com/Noe94/service-desk-201700866

URL local:
http://localhost:8000

Usuario de administrador:
admin_demo

La contrasena se obtiene del archivo local .env.

## Minuto 0: presentacion

El proyecto extiende el catalogo de servicios
desarrollado en el segundo parcial.

Conserva autenticacion, organizacion, catalogo N1/N2
y agrega Service Desk y CMDB.

Tecnologias:
Django, PostgreSQL y Docker Compose.

## Minuto 1: catalogo y Service Desk

Mostrar:
- Catalogo con 12 servicios N1 y 46 N2.
- Siete colas.
- Tickets de demostracion.
- Roles y permisos.

Explicar que los tickets se vinculan con servicios,
responsables y dispositivos de configuracion.

## Minuto 2: evento e incidente

Abrir el ticket SD-0000020.

Mostrar:
- Categoria E2.
- Estado RESPONDIDO.
- Incidente generado SD-0000038.
- Notificacion en aplicacion.
- Bitacora de auditoria.

Explicar que el incidente se genera una sola vez
y que el proceso es idempotente.

No repetir transiciones sobre tickets ya avanzados.

## Minuto 3: CMDB y grafos

Abrir CMDB.

Mostrar:
- 5000 dispositivos.
- Clasificacion.
- Filtros y paginacion.
- Relaciones tecnicas.
- Servicios potencialmente afectados.

Explicar los dos grafos:
1. Jerarquia de clasificacion sin ciclos.
2. Grafo tecnico de relaciones y dependencias.

Las conexiones pueden admitir ciclos.
Las dependencias no deben producir ciclos prohibidos.

El impacto calculado es potencial;
no significa interrupcion efectiva.

## Minuto 4: ingenierias

Prompt Engineering:
Explicar una mejora real de instrucciones.

Context Engineering:
Mostrar AGENTS.md, IA.md y los commits.

Harness Engineering:
Mostrar scripts/prepare.ps1 y scripts/verify.ps1.
Resultado comprobado: 82 pruebas aprobadas.

Loop Engineering:
Explicar un defecto, su correccion y nueva verificacion.

Ejemplo:
Evento E2 que originalmente dependia de texto,
corregido mediante relaciones y notificaciones reales.

## Minuto 5: cierre y preguntas

Mostrar el repositorio y el commit mas reciente.

Explicar:
- Persistencia en PostgreSQL.
- 5000 dispositivos sin duplicados.
- Siete flujos automatizados.
- Auditoria y controles de autorizacion.

Estar preparado para modificar un campo,
una validacion o una prueba pequena.

## Limitaciones que deben declararse

- La creacion de catalogo desde un servicio nuevo
  aprobado requiere una operacion manual.
- No todas las rutas tienen una demostracion visual.
- Las mediciones P16 corresponden a Django ORM,
  no a latencia HTTP.
- Los prompts literales requieren evidencia real.

No presentar estas limitaciones como funcionalidades
automaticas ya implementadas.