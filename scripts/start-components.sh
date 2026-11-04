#!/usr/bin/env bash
# Levanta Jenkins y expone la app, Prometheus y Grafana en localhost.
# Los port-forward quedan en segundo plano; sus PIDs se guardan para que cleanup.sh los detenga.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${TMPDIR:-/tmp}/ci-validator-portforward.pids"

echo "==> Jenkins"
# kubeconfig aplanado que apunta a la IP de minikube dentro de su red de Docker.
JENKINS_KUBECONFIG="$HOME/.kube/jenkins-minikube-config"
kubectl config view --flatten --minify --context minikube > "$JENKINS_KUBECONFIG"
MINIKUBE_IP="$(minikube ip)"
sed -i.bak -E "s#server: https://[^[:space:]]+#server: https://${MINIKUBE_IP}:8443#" "$JENKINS_KUBECONFIG"
rm -f "$JENKINS_KUBECONFIG.bak"
export JENKINS_KUBECONFIG REPO_DIR="$ROOT"
docker compose -f "$ROOT/jenkins/docker-compose.yml" up -d --build

echo "==> Port-forward de app, Prometheus y Grafana"
: > "$PID_FILE"
kubectl port-forward svc/ci-validator-api 5000:5000 >/dev/null 2>&1 & echo $! >> "$PID_FILE"
kubectl port-forward svc/prometheus 9090:9090 >/dev/null 2>&1 & echo $! >> "$PID_FILE"
kubectl port-forward svc/grafana 3000:3000 >/dev/null 2>&1 & echo $! >> "$PID_FILE"

cat <<MSG

App:        http://localhost:5000/docs
Prometheus: http://localhost:9090/targets
Grafana:    http://localhost:3000   (admin/admin) -> dashboard "CI Validator API - Entregable 4"
Jenkins:    http://localhost:8080   (admin/admin) -> job "ci-validator-api" (Build with Parameters)
MSG
