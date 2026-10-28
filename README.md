# Service Desk y CMDB — Software Avanzado

**Autor:** Erick Noe Gómez López · **Carné:** 201700866  
Extensión independiente del segundo parcial de Catálogo de Servicios TI.

Proyecto Django 5.2, PostgreSQL 17, Python 3.13, Docker Compose, HTML y CSS.
No requiere IA en ejecución; conserva el catálogo, importador, roles,
jerarquía organizacional y pruebas originales. El código fuente es individual.

## 1. Requisitos del equipo

- Docker Desktop activo (motor Linux, Docker Compose V2).
- Git si va a clonar. **No** necesita instalar Python ni PostgreSQL en Windows.
- Puerto local 8000 disponible. Las credenciales se crean localmente y no van al repo.

## 2. Inicio desde un ZIP o clon limpio (Windows / PowerShell)

1. Extraiga esta carpeta en un directorio propio: **no sobreescriba el proyecto del parcial 2**.
2. Abra **esa carpeta** en VS Code y ejecute lo siguiente en su terminal PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

3. Reemplace en `.env` los valores `change-me` por contraseñas locales fuertes e
   irrepetibles, incluidas **las cinco** variables `DEMO_*_PASSWORD`,
   `POSTGRES_PASSWORD` y `DJANGO_SECRET_KEY`. No suba `.env` a Git.
4. Construya y arranque contenedores:

```powershell
docker compose up --build -d
docker compose ps
```

5. Prepare **todas** las tablas y los datos de demostración:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare.ps1
```

6. Abra [http://localhost:8000](http://localhost:8000) e inicie sesión.

**Linux/macOS:** `cp .env.example .env`, configure credenciales, luego
`docker compose up --build -d` y `sh scripts/prepare.sh`.

El script de preparación ejecuta en orden: migraciones, importador 12/46,
cuentas base, asignaciones originales, 5,000 dispositivos y 7 colas + 37 tickets
+ 4 artículos FAQ. Es repetible: los mismos códigos/semilla no se duplican.
No necesita borrar volúmenes entre arranques.

## 3. Cuentas para evaluación

| Usuario | Perfil | Contraseña en `.env` |
|---|---|---|
| `admin_demo` | Administrador | `DEMO_ADMIN_PASSWORD` |
| `consulta_demo` | Consulta sin modificación | `DEMO_CONSULTA_PASSWORD` |
| `solicitante_demo` | Solicitante | `DEMO_SOLICITANTE_PASSWORD` |
| `agente_demo` | Agente / Solicitante | `DEMO_AGENTE_PASSWORD` |
| `aprobador_demo` | Aprobador / Solicitante | `DEMO_APROBADOR_PASSWORD` |

Se utiliza un hash de contraseña de Django; no hay registro público de usuarios.
El rol CONSULTA no se convierte en agente por pertenecer a un grupo de cola.

## 4. Rutas clave para la demostración

| Ruta | Función |
|---|---|
| `/` | Inicio, autenticación |
| `/catalogo/` | Catálogo N1/N2 del parcial anterior |
| `/organizacion/` | Empresa / Área / Departamento / Sección / Puesto |
| `/mesa/` | Tickets, búsqueda, asignación y seguimiento |
| `/mesa/colas/` | Colas y permisos efectivos |
| `/mesa/tablero/` | Indicadores y objetivos de atención |
| `/mesa/conocimiento/` | FAQ/autoservicio nivel 0 |
| `/cmdb/` | 5,000 dispositivos, filtros y paginación |
| `/cmdb/ci/<ID>/` | CI, servicio, relaciones, tickets e impacto potencial |

### Recorrido recomendado en cinco minutos

1. Entrar como administrador y mostrar el catálogo N1/N2, siete colas y el total CMDB.
2. Filtrar por `SERVIDOR` y abrir un CI; navegar sus vínculos y servicios posibles.
3. Entrar como solicitante y crear un ticket con categoría, cola y servicio.
4. Entrar como agente, tomar ticket, agregar diagnóstico, transicionar y ver bitácora.
5. Abrir un evento E2 en `EVALUADO`, responder y mostrar **incidente generado + aviso**.
   Mostrar después `/mesa/tablero/` y una prueba automatizada.

## 5. Comandos directos y harness

```powershell
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py import_catalog data/CatalogoServicios.xlsx --verify-original
docker compose exec -T web python manage.py seed_demo
docker compose exec -T web python manage.py seed_demo_assignments
docker compose exec -T web python manage.py seed_cmdb --seed 201700866 --count 5000
docker compose exec -T web python manage.py seed_service_desk
docker compose exec -T web python manage.py check
docker compose run --rm web python manage.py test -v 1
```

Para ejecutar todo el harness en Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

Para un reinicio **sin borrar datos**:

```powershell
docker compose restart
docker compose ps
```

Los datos PostgreSQL están en el volumen nombrado `postgres_data`; los adjuntos
autorizados en `attachments_data`. Reiniciar o ejecutar `docker compose down`
**sin `-v`** los conserva. **No ejecute `docker compose down -v`: borra volúmenes.**

Logs y apagado:

```powershell
docker compose logs -f web
docker compose logs db
docker compose down
```

Recuperación ante error: verifique Docker Desktop, puerto 8000, `.env`,
`docker compose ps` y `docker compose logs web`. Si faltan datos, ejecute de nuevo
`scripts/prepare.ps1` sin eliminar volúmenes.

## 6. Datos y políticas

- CMDB: 5,000 dispositivos identificados por semilla y código único, 1,000 por
  cada categoría operativa (Servidor, Estación, Portátil, Switch, Router).
  Categorías Hardware/Software provienen de la plantilla; subcategorías son
  decisiones técnicas y se identifican claramente en `docs/MODELO.md`.
- Colas: manual, prioridad → antigüedad, bloqueo transaccional al reclamar.
- Roles por cola: consultar / atender / transferir / aprobar / administrar.
- Tickets: siete flujos diferenciados, comentarios públicos e internos,
  adjuntos de hasta 10 MiB, bitácora, reapertura de hasta siete días.
- Eventos E2/E3: al pasar a Respondido crean o recuperan un único incidente,
  con notificación guardada dentro de la aplicación.
- Se evita imponer IP en todos los CI. Solo hay valores sintéticos, no equipos reales.
- Indicadores: tiempo calendario, con descuento de pausas; detalles en `docs/PROCESOS.md`.

## 7. Documentación y pruebas

- [Modelo, diccionario CMDB y grafos](docs/MODELO.md)
- [Procesos, colas, niveles, E0–E3, I0–I6 e indicadores](docs/PROCESOS.md)
- [Ingenierías asistidas y ciclos de desarrollo](docs/IA.md)
- [Matriz P01–P18 y evidencias reales](docs/PRUEBAS.md)
- [Plan y límites de alcance](docs/PLAN_SERVICE_DESK.md)
- [Enunciado y fuentes docentes preservadas](docs/fuentes/)

**Validación real en Windows (28/10/2026):**

- Docker Compose y PostgreSQL funcionando correctamente.
- Django system check: 0 problemas.
- Suite automatizada mas reciente: 82 de 82 pruebas aprobadas en 33.492 segundos.
- Catálogo: 12 servicios N1 y 46 servicios N2.
- CMDB: 5,000 dispositivos persistidos.
- Service Desk: 7 colas y 37 tickets iniciales de demostración.
- Evento E2 SD-0000020: generó el incidente SD-0000038.
- Persistencia P18: 38 tickets, 5,000 CI, 7 colas,
  163 registros de bitácora y el catálogo conservados tras reiniciar Docker.

Los resultados detallados se encuentran en `docs/PRUEBAS.md`.

## 8. Limitaciones conocidas de esta versión

- La creación de un servicio N2 desde una solicitud aprobada es manual mediante
  el módulo de catálogo. El campo de expediente solo referencia la propuesta.
- Los vínculos entre problema y cambio pueden consultarse mediante relaciones
  de tickets, pero falta una pantalla especializada para ese recorrido.
- La información de prioridad y redundancia de I0–I6 es orientación de clase;
  no se fuerza automáticamente el SLA por la duración.
- Los commits de evolución del contexto deben registrarse en el repositorio
  Git del estudiante; no se simulan hashes ni evidencias.
