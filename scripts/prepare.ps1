$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== PREPARACION - SERVICE DESK + CMDB ==="
Write-Host ""

Write-Host "[1/7] Construyendo y levantando servicios..."
docker compose up --build -d

if ($LASTEXITCODE -ne 0) {
    throw "No fue posible levantar los servicios."
}

Write-Host ""
Write-Host "[2/7] Aplicando migraciones..."
docker compose exec -T web python manage.py migrate

if ($LASTEXITCODE -ne 0) {
    throw "Las migraciones fallaron."
}

Write-Host ""
Write-Host "[3/7] Importando catalogo original..."
docker compose exec -T web python manage.py import_catalog data/CatalogoServicios.xlsx --verify-original

if ($LASTEXITCODE -ne 0) {
    throw "La importacion fallo."
}

Write-Host ""
Write-Host "[4/7] Creando cuentas de evaluacion..."
docker compose exec -T web python manage.py seed_demo

if ($LASTEXITCODE -ne 0) {
    throw "No fue posible crear las cuentas demo."
}

Write-Host ""
Write-Host "[5/7] Configurando asignaciones demo..."
docker compose exec -T web python manage.py seed_demo_assignments

if ($LASTEXITCODE -ne 0) {
    throw "No fue posible crear las asignaciones demo."
}

Write-Host "[6/7] Generando 5000 dispositivos CMDB..."
docker compose exec -T web python manage.py seed_cmdb --seed 201700866 --count 5000
if ($LASTEXITCODE -ne 0) {
    throw "La generacion CMDB fallo."
}

Write-Host "[7/7] Creando colas, roles, 37 tickets y FAQ..."
docker compose exec -T web python manage.py seed_service_desk
if ($LASTEXITCODE -ne 0) {
    throw "La creacion de datos del Service Desk fallo."
}

Write-Host ""
Write-Host "PREPARACION: OK"
Write-Host ""
Write-Host "ADMIN:    admin_demo"
Write-Host "CONSULTA: consulta_demo"
Write-Host "SOLICITANTE: solicitante_demo"
Write-Host "AGENTE: agente_demo"
Write-Host "APROBADOR: aprobador_demo"
Write-Host ""
Write-Host "Las contrasenas se toman del archivo .env."
