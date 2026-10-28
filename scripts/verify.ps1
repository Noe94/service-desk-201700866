$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== HARNESS - SERVICE DESK + CMDB ==="
Write-Host ""

Write-Host "[1/3] Levantando servicios..."
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "No fue posible levantar los servicios Docker."
}

Write-Host ""
Write-Host "[2/3] Ejecutando Django system check..."

docker compose exec -T web python manage.py check

if ($LASTEXITCODE -ne 0) {
    throw "Django system check fallo."
}

Write-Host ""
Write-Host "[3/3] Ejecutando suite automatizada..."

docker compose run --rm web python manage.py test -v 1

if ($LASTEXITCODE -ne 0) {
    throw "La suite automatizada fallo."
}

Write-Host ""
Write-Host "HARNESS PRINCIPAL: OK"
Write-Host ""
