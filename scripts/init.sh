#!/usr/bin/env bash
# Inicializa minikube, el addon metrics-server, la imagen de la app y los manifiestos.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-2.1.1}"

minikube status >/dev/null 2>&1 || minikube start --driver=docker
minikube addons enable metrics-server

docker build -f "$ROOT/ci-validator-api/Dockerfile" -t "ci-validator-api:$VERSION" "$ROOT/ci-validator-api/v$VERSION"
minikube image load "ci-validator-api:$VERSION"

"$ROOT/scripts/deploy.sh"
kubectl get deploy,svc,pods
