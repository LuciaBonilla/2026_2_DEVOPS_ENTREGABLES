# 2026_2_DEVOPS_ENTREGABLES

## Universidad Católica del Uruguay

Entregables para el curso DevOps de la Universidad Católica del Uruguay (año 2026, segundo semestre).

## Equipo

- Rodrigo Perdomo
- Lucía Bonilla

## Entregables

5 entregables progresivos para incorporar DevOps a nuestro flujo de desarrollo:

- [x] [Entregable 1 - Aplicación en Kubernetes](docs/entregable1.md)
- [x] [Entregable 2 - Sistema de Monitoreo y Alertas para una Aplicación en Kubernetes](docs/entregable2.md)
- [ ] [Entregable 3 - DevSecOps para una Aplicación en Kubernetes](docs/entregable3.md)
- [x] [Entregable 4 - Trabajo integrador (Jenkins, Prometheus y Grafana)](docs/entregable4.md)
- [ ] [Entregable 5 - Reporte Final](docs/entregable5.md)

## Cómo levantar, probar y bajar el proyecto (Entregable 4)

Documentación técnica completa: [docs/entregable4.md](docs/entregable4.md).

### Requisitos

- Docker Desktop (corriendo), `minikube` y `kubectl`.
- Los cambios deben estar **commiteados en la rama `feature/entregable4`**: el job de Jenkins lee el repo local y solo ve lo commiteado.
- Los puertos 3000, 5000, 8080 y 9090 libres, y que no exista otro contenedor llamado `jenkins`.

### 1. Levantar

```bash
./scripts/init.sh
```
Arranca minikube (si no estaba), habilita el addon `metrics-server`, construye la imagen `ci-validator-api:2.1.1`, la carga en minikube y aplica los manifiestos (app ×3, Prometheus y Grafana con datasource y dashboard ya provisionados). Escala a 0 los Deployments `blue`/`green` del entregable 1, que comparten el label de la app y ensucian las métricas.

```bash
./scripts/start-components.sh
```
Levanta Jenkins en Docker y deja expuestos en localhost la app, Prometheus y Grafana. Los port-forward se reintentan solos si se caen (cada reintento queda registrado en `$TMPDIR/ci-validator-portforward.log`).

| Componente | URL | Acceso |
|---|---|---|
| App (Swagger) | http://localhost:5000/docs | |
| Prometheus | http://localhost:9090/targets | |
| Grafana | http://localhost:3000 | admin / admin |
| Jenkins | http://localhost:8080 | admin / admin |

### 2. Probar

```bash
./scripts/generate-traffic.sh [rondas=60] [pausa_seg=0.5]
```
Envía a la app cédulas válidas, con dígito verificador incorrecto y mal formadas (5 requests por ronda, unos 40 s con los valores por defecto). Puebla el dashboard y supera las 40 validaciones en 2 minutos, lo que dispara la alerta.

Verificar:

| Qué | Dónde | Resultado esperado |
|---|---|---|
| Pods | `kubectl get pods` | 3 × `ci-validator-api`, `prometheus` y `grafana` en `Running` |
| Targets | http://localhost:9090/targets | `ci-validator-api` (3) y `cadvisor` en `UP` |
| Alerta | http://localhost:9090/alerts | `CIValidatorAltoVolumen` en `Firing` |
| Dashboard | Grafana → "CI Validator API - Entregable 4" (rango *Last 15 minutes*) | RPS, latencia, CPU y memoria por pod, validaciones por resultado |
| Pipeline | Jenkins → job `ci-validator-api` | Tests → Build y carga en minikube → Deploy, en verde |

**Pipeline en Jenkins:** la primera vez usar **Build Now** (los parámetros recién aparecen después de la primera corrida); luego ya se puede usar *Build with Parameters* (`VERSION`, por defecto `2.1.1`).

### 3. Bajar todo

```bash
./scripts/cleanup.sh          # detiene port-forwards, Jenkins (con su volumen) y borra los recursos de Kubernetes
./scripts/cleanup.sh --all    # además elimina el cluster de minikube
```

### Problemas frecuentes

- **`start-components.sh` falla con "container name /jenkins is already in use"**: existe otro contenedor llamado `jenkins`. Renombrarlo (`docker rename jenkins <otro>`) o borrarlo (`docker rm jenkins`) y volver a ejecutar.
- **Un `localhost:<puerto>` no responde**: el port-forward se está reiniciando; esperar unos segundos. Si persiste, volver a ejecutar `./scripts/start-components.sh`.
- **El pipeline falla con el `Jenkinsfile` vacío o sin `scripts/`**: falta commitear en `feature/entregable4`.
