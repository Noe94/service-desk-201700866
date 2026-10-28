$ErrorActionPreference = "Stop"

function Get-PersistenceSnapshot {
    $command = @"
from django.contrib.auth import get_user_model
from apps.catalog.models import ServicioNivel1, ServicioNivel2
from apps.imports.models import Importacion

print(
    f'{ServicioNivel1.objects.count()}|'
    f'{ServicioNivel2.objects.count()}|'
    f'{get_user_model().objects.count()}|'
    f'{Importacion.objects.count()}|'
    f'{ServicioNivel2.objects.filter(seccion_responsable__isnull=False, usuario_responsable__isnull=False).count()}'
)
"@

    $output = docker compose exec -T web `
        python manage.py shell -c $command

    if ($LASTEXITCODE -ne 0) {
        throw "No fue posible obtener el estado de la base de datos."
    }

    return ($output | Select-Object -Last 1).Trim()
}


Write-Host ""
Write-Host "=== P12 - PERSISTENCIA DOCKER ==="
Write-Host ""

docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "No fue posible levantar los servicios."
}

$before = Get-PersistenceSnapshot

Write-Host "Antes:   $before"

Write-Host ""
Write-Host "Deteniendo contenedores SIN eliminar volumen..."

docker compose down

if ($LASTEXITCODE -ne 0) {
    throw "docker compose down fallo."
}

Write-Host ""
Write-Host "Levantando nuevamente..."

docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "docker compose up fallo."
}

$ready = $false

for ($attempt = 1; $attempt -le 30; $attempt++) {
    docker compose exec -T web python manage.py check *> $null

    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }

    Start-Sleep -Seconds 2
}

if (-not $ready) {
    throw "La aplicacion no estuvo lista dentro del tiempo esperado."
}

$after = Get-PersistenceSnapshot

Write-Host "Despues: $after"
Write-Host ""

if ($before -ne $after) {
    throw "P12 FALLO: los datos cambiaron despues del reinicio."
}

Write-Host "P12 OK: los datos persistieron sin eliminar el volumen."
Write-Host ""
