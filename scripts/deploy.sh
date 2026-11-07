#!/usr/bin/env bash
# Aplica los manifiestos en el cluster actual (lo usan init.sh y el Jenkinsfile).
# Primero la base de entregable 2 y luego k8s-entregable4, que reemplaza los recursos con el mismo nombre.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2="$ROOT/ci-validator-api/k8s-entregable2"

kubectl create configmap grafana-dashboard --from-file="$ROOT/grafana/dashboard.json" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$E2/app-service.yaml" -f "$E2/monitoring/prometheus/" -f "$E2/monitoring/grafana/service.yaml"
kubectl apply -f "$ROOT/ci-validator-api/k8s-entregable4/"

# Los Deployments blue/green del entregable 1 comparten el label app=ci-validator-api con la app actual:
# si siguen activos, el Service y Prometheus mezclan sus pods (v1.x, sin /metrics) con los de v2.1.1.
kubectl scale deployment/ci-validator-api-blue deployment/ci-validator-api-green --replicas=0 2>/dev/null || true

# Los ConfigMap montados no se recargan solos.
kubectl rollout restart deployment/prometheus deployment/grafana
kubectl rollout status deployment/ci-validator-api deployment/prometheus deployment/grafana --timeout=180s
