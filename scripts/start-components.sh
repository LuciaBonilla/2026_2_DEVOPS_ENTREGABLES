#!/usr/bin/env bash
# Levanta Jenkins y expone la app, Prometheus y Grafana en localhost.
# Los port-forward quedan en segundo plano; sus PIDs se guardan para que cleanup.sh los detenga.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${TMPDIR:-/tmp}/ci-validator-portforward.pids"
LOG_FILE="${TMPDIR:-/tmp}/ci-validator-portforward.log"

echo "==> Jenkins"
# kubeconfig aplanado que apunta a la IP de minikube dentro de su red de Docker.
JENKINS_KUBECONFIG="$HOME/.kube/jenkins-minikube-config"
kubectl config view --flatten --minify --context minikube > "$JENKINS_KUBECONFIG"
MINIKUBE_IP="$(minikube ip)"
sed -i.bak -E "s#server: https://[^[:space:]]+#server: https://${MINIKUBE_IP}:8443#" "$JENKINS_KUBECONFIG"
rm -f "$JENKINS_KUBECONFIG.bak"
export JENKINS_KUBECONFIG REPO_DIR="$ROOT"
docker compose -f "$ROOT/jenkins/docker-compose.yml" up -d --build

echo "==> Port-forward de app, Prometheus y Grafana (se reintentan solos si se caen)"
# Si quedaron port-forwards de una ejecución anterior, se detienen para liberar los puertos.
if [[ -f "$PID_FILE" ]]; then
  while read -r pid; do pkill -P "$pid" 2>/dev/null || true; kill "$pid" 2>/dev/null || true; done < "$PID_FILE"
fi
: > "$PID_FILE"
: > "$LOG_FILE"

# Un bucle por servicio: cuando kubectl port-forward termina (pod reiniciado, conexión cortada)
# se deja constancia en el log y se vuelve a lanzar.
forward() {
  local svc="$1" port="$2"
  nohup bash -c '
    while true; do
      kubectl port-forward "svc/$0" "$1:$1" >/dev/null 2>&1
      echo "$(date +%T) port-forward de $0 ($1) caído, reintentando..." >> "$2"
      sleep 2
    done' "$svc" "$port" "$LOG_FILE" >/dev/null 2>&1 &
  echo $! >> "$PID_FILE"
}
forward ci-validator-api 5000
forward prometheus 9090
forward grafana 3000

cat <<MSG

App:        http://localhost:5000/docs
Prometheus: http://localhost:9090/targets
Grafana:    http://localhost:3000   (admin/admin) -> dashboard "CI Validator API - Entregable 4"
Jenkins:    http://localhost:8080   (admin/admin) -> job "ci-validator-api"

Reintentos de port-forward: $LOG_FILE
MSG
