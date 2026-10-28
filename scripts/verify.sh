#!/bin/sh
set -eu

echo ""
echo "=== HARNESS - SERVICE DESK + CMDB ==="
echo ""

echo "[1/3] Levantando servicios..."
docker compose up -d

echo ""
echo "[2/3] Ejecutando Django system check..."
docker compose exec -T web python manage.py check

echo ""
echo "[3/3] Ejecutando suite automatizada..."
docker compose run --rm web python manage.py test -v 1

echo ""
echo "HARNESS PRINCIPAL: OK"
