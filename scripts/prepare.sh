#!/bin/sh
set -eu

echo ""
echo "=== PREPARACION - SERVICE DESK + CMDB ==="
echo ""

echo "[1/7] Construyendo y levantando servicios..."
docker compose up --build -d

echo ""
echo "[2/7] Aplicando migraciones..."
docker compose exec -T web python manage.py migrate

echo ""
echo "[3/7] Importando catalogo original..."
docker compose exec -T web python manage.py import_catalog data/CatalogoServicios.xlsx --verify-original

echo ""
echo "[4/7] Creando cuentas de evaluacion..."
docker compose exec -T web python manage.py seed_demo

echo ""
echo "[5/7] Configurando asignaciones demo..."
docker compose exec -T web python manage.py seed_demo_assignments

echo "[6/7] Generando 5000 dispositivos sintéticos CMDB..."
docker compose exec -T web python manage.py seed_cmdb --seed 201700866 --count 5000

echo "[7/7] Configurando siete colas, tickets, roles y FAQ..."
docker compose exec -T web python manage.py seed_service_desk

echo ""
echo "PREPARACION: OK"
echo ""
echo "ADMIN:    admin_demo"
echo "CONSULTA: consulta_demo"
echo "SOLICITANTE: solicitante_demo"
echo "AGENTE: agente_demo"
echo "APROBADOR: aprobador_demo"
echo ""
echo "Las contrasenas se toman del archivo .env."
