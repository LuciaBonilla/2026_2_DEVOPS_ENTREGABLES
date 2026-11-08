#!/usr/bin/env bash
# Genera tráfico para poblar el dashboard. Requiere el port-forward de start-components.sh.
# Uso: scripts/generate-traffic.sh [rondas=60] [pausa_seg=0.5]   (60 rondas superan las 40 validaciones/2 min de la alerta)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"
# Válidas, dígito verificador incorrecto, mal formadas.
CIS=(1.234.567-2 123.456-1 12345671 abc 123)

for ((i = 1; i <= ${1:-60}; i++)); do
  for n in "${CIS[@]}"; do curl -s -o /dev/null "$BASE_URL/ci/$n"; done
  sleep "${2:-0.5}"
done
