#!/usr/bin/env bash
# Envía los 4 ejemplos (uno por estado) a la API y muestra la respuesta del modelo.
# Uso:  ./ejemplos/probar_api.sh                    (usa http://localhost:5000)
#       ./ejemplos/probar_api.sh http://localhost:8080
set -euo pipefail

URL="${1:-http://localhost:5000}"
DIR="$(cd "$(dirname "$0")" && pwd)"

for archivo in "$DIR"/*.json; do
  echo "== $(basename "$archivo")"
  curl -s -X POST "$URL/predecir" \
       -H "Content-Type: application/json" \
       --data @"$archivo"
  echo
done
