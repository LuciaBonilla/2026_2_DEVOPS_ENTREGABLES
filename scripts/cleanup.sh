#!/usr/bin/env bash
# Borra port-forwards, Jenkins y los recursos de Kubernetes. Con --all elimina también minikube.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${TMPDIR:-/tmp}/ci-validator-portforward.pids"
E2="$ROOT/ci-validator-api/k8s-entregable2"

# Cada PID es un bucle de reintento: se matan sus kubectl hijos y luego el bucle.
if [[ -f "$PID_FILE" ]]; then
  while read -r pid; do pkill -P "$pid" 2>/dev/null || true; kill "$pid" 2>/dev/null || true; done < "$PID_FILE"
fi
rm -f "$PID_FILE" "${TMPDIR:-/tmp}/ci-validator-portforward.log"

JENKINS_KUBECONFIG="$HOME/.kube/jenkins-minikube-config" REPO_DIR="$ROOT" \
  docker compose -f "$ROOT/jenkins/docker-compose.yml" down -v || true
rm -f "$HOME/.kube/jenkins-minikube-config"

kubectl delete --ignore-not-found -f "$ROOT/ci-validator-api/k8s-entregable4/" \
  -f "$E2/app-service.yaml" -f "$E2/monitoring/prometheus/" -f "$E2/monitoring/grafana/service.yaml" || true
kubectl delete --ignore-not-found configmap/grafana-dashboard
minikube addons disable metrics-server || true

[[ "${1:-}" == "--all" ]] && minikube delete
exit 0
