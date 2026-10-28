# Matriz requisito - implementación - prueba - evidencia

## Objetivo

Relacionar los requisitos principales con su implementación, control y evidencia verificable.

| Requisito | Implementación | Prueba o control | Evidencia |
| --- | --- | --- | --- |
| Login local | Backend usuario/correo + Django Auth | AuthenticationTests | `apps/accounts/` |
| Logout | LogoutView y sesión Django | test_logout_invalidates_session | `apps/accounts/tests.py` |
| Usuario inactivo | Backend bloquea `is_active=False` | test_inactive_user_cannot_login | `apps/accounts/tests.py` |
| Roles ADMIN/CONSULTA | `User.rol` + `admin_required` | AuthorizationTests | `apps/accounts/` |
| CRUD Empresa | Organización | OrganizationCrudTests | `apps/organization/` |
| CRUD Área | Organización | OrganizationCrudTests | `apps/organization/` |
| CRUD Departamento | Organización | OrganizationCrudTests | `apps/organization/` |
| CRUD Sección | Organización | OrganizationCrudTests | `apps/organization/` |
| CRUD Puesto | Organización | OrganizationCrudTests | `apps/organization/` |
| CRUD Usuario | Accounts | UserCrudTests | `apps/accounts/` |
| Jerarquía completa | Relaciones FK | OrganizationHierarchyRecoveryTests | `apps/organization/tests.py` |
| Bajas lógicas | `activo` + controles de dependencia | OrganizationCrudTests | `apps/organization/views.py` |
| Servicios N1 | Modelo, formulario y vistas | CatalogWebTests | `apps/catalog/` |
| Servicios N2 | Modelo, formulario y vistas | CatalogWebTests | `apps/catalog/` |
| Desactivar N2 | `n2_toggle` | test_admin_can_toggle_n2_service | `apps/catalog/tests.py` |
| Clase | Catálogo maestro | CatalogOptionTests | `apps/catalog/` |
| Criticidad | Catálogo maestro | CatalogOptionTests | `apps/catalog/` |
| Tipo | Catálogo maestro | CatalogOptionTests | `apps/catalog/` |
| Búsqueda | Query por código/nombre | test_search_by_code | `apps/catalog/tests.py` |
| Filtros | N1/estado/clase/criticidad/tipo | test_combined_filters | `apps/catalog/tests.py` |
| Paginación | Django Paginator | test_pagination_preserves_active_filters | `apps/catalog/tests.py` |
| Filtro revisión | `requiere_revision=True` | test_revision_filter_uses_review_flag | `apps/catalog/tests.py` |
| Mínimo <= máximo | `ServicioNivel2.clean()` | ServiceValidationTests | `apps/catalog/models.py` |
| Responsable/sección | Validación de modelo | test_wrong_section_responsible_is_rejected | `apps/catalog/tests.py` |
| 3 responsables demo | `seed_demo_assignments` | comando + consulta SQL | `apps/catalog/management/commands/` |
| Análisis Excel | `excel_catalog.py` | CatalogWorkbookAnalysisTests | `apps/imports/services/` |
| Celdas combinadas | lector consciente de rangos | pruebas de análisis | `docs/contexto/02-analisis-excel.md` |
| Conflicto SE.12 | política canónica + observación | tests SE.12 | `apps/imports/tests.py` |
| Ausencias | NULL + revisión | tests SE.12 | `apps/imports/tests.py` |
| Importación 12/46 | `import_catalog` | CatalogImportTests | `apps/imports/` |
| Idempotencia | sincronización por código | test_repeated_import_is_idempotent | `apps/imports/tests.py` |
| Trazabilidad | Importacion/Registro/Observacion | tests importador | `apps/imports/models.py` |
| Context Engineering | `AGENTS.md` + 3 contextos | revisión documental | `docs/contexto/` |
| Prompt Engineering | 5 prompts + 2 iteraciones | revisión documental | `docs/prompts/` |
| Harness Engineering | prepare/verify/persistencia | ejecución reproducible | `scripts/` |
| P01-P12 | 49 pruebas + persistencia | suite + P12 | `docs/evidencias/01-p01-p12.md` |
| Persistencia | volumen PostgreSQL | test_persistence.ps1 | `compose.yaml` |
| Docker | web + db + healthcheck | compose + check | `Dockerfile`, `compose.yaml` |
| Sin secretos | `.gitignore` + `.env.example` | `git status` | `.gitignore` |
| Excel original intacto | archivo versionado + SHA-256 | importador | `data/CatalogoServicios.xlsx` |

## Resultado

La suite automatizada actual contiene:

    Found 49 test(s).
    Ran 49 tests
    OK

El control P12 verifica adicionalmente persistencia fuera de la base temporal de pruebas.
