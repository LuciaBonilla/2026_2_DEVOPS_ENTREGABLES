# Entregable 4 - Trabajo integrador (Jenkins, Prometheus y Grafana) y Reporte Técnico Final

## Índice

1. [Descripción general](#a-descripción-general)
2. [Arquitectura](#b-arquitectura)
3. [Pipeline](#c-pipeline)
4. [Métricas y dashboard de Grafana](#d-métricas-y-dashboard-de-grafana)
5. [Seguridad](#e-seguridad)
6. [Problemas encontrados y soluciones](#f-problemas-encontrados-y-soluciones)
7. [Conclusiones y mejoras](#g-conclusiones-y-oportunidades-de-mejora)
8. [Guía paso a paso: levantar, probar y bajar](#guía-paso-a-paso-levantar-probar-y-bajar)
9. [Capturas de pantalla](#capturas-de-pantalla)

## a. Descripción general

`ci-validator-api` es una API FastAPI que valida cédulas de identidad uruguayas. La versión usada en este entregable es la **v2.1.2** (`ci-validator-api/v2.1.2`). Expone:

| Endpoint | Descripción |
|---|---|
| `GET /ci/{number}` | Valida la cédula (con o sin puntos y guion) y devuelve forma canónica, forma de presentación y dígito verificador esperado |
| `GET /health` | Sonda de salud (readiness de Kubernetes) |
| `GET /metrics` | Métricas en formato de exposición de Prometheus |

Sobre la app se construyó un flujo de trabajo completo en minikube:

- **Pipeline de Jenkins** que ejecuta los tests, construye la imagen, la carga en minikube y despliega.
- **Prometheus**, que recolecta las métricas de la app (`/metrics`) y las de contenedores (cAdvisor), y evalúa reglas de alerta.
- **Grafana**, con el datasource y el dashboard ya provisionados.
- **Scripts de bash** que inicializan, levantan los componentes, generan tráfico y borran todo.

### Estructura del repositorio

```text
   .                                   # Raíz del repositorio
   ├── ci-validator-api/
   │   ├── v1.0.0 ... v2.1.1/          # Código fuente y Dockerfile de cada versión
   │   └── v2.1.2/                     # Versión usada aquí: código, Dockerfile, requirements(-dev).txt, pytest.ini y tests/
   ├── entregable1/ ... entregable3/   # Entregables anteriores (este reutiliza parte de entregable2/k8s/)
   └── entregable4/
       ├── Jenkinsfile                 # Pipeline: Tests -> Build y carga en minikube -> Deploy
       ├── dashboard/dashboard.json    # Dashboard de Grafana exportado
       ├── jenkins/                    # Dockerfile, docker-compose.yml, plugins.txt y casc.yaml
       ├── k8s/                        # App (imagen 2.1.2), Prometheus (+cAdvisor) y Grafana (provisionado)
       ├── scripts/                    # init, start-components, generate-traffic, cleanup y deploy
       └── images/entregable4/         # Diagrama y capturas
```

`entregable4/k8s` se aplica **después** de una parte de `entregable2/k8s`: (el Service de la app, `monitoring/prometheus/` y el Service de Grafana): los recursos con el mismo nombre se reemplazan (la base del entregable 2 no se modificó).

## b. Arquitectura

### Diagrama de componentes

![Diagrama de componentes](./images/entregable4/diagrama.png)

Cómo está conectado:

- **Jenkins** corre en Docker en el host, no dentro del cluster. Usa el socket de Docker del host para construir la imagen y `docker exec -i minikube docker load` para cargarla en el nodo de minikube (no necesita el CLI de minikube). Alcanza el API server por la red Docker `minikube`, con un kubeconfig aplanado que apunta a la IP de minikube.
- **Prometheus** descubre los pods de la app por `kubernetes_sd_configs` (label `app=ci-validator-api`) y lee las métricas de contenedores desde cAdvisor, a través del API server y con el token del ServiceAccount (el RBAC pasa a estar en dos lugares: el ServiceAccount y el binding en `entregable2/k8s/monitoring/prometheus/rbac.yaml`, y el ClusterRole ampliado (con nodes y nodes/proxy) en `k8s/monitoring/prometheus/prometheus.yaml`).
- **Grafana** recibe el datasource y el dashboard por *provisioning*: ConfigMaps montados en `/etc/grafana/provisioning` y `/var/lib/grafana/dashboards`. El ConfigMap del dashboard se genera desde `dashboard/dashboard.json`.
- Los **Services** son `NodePort`; el acceso desde el host es por `kubectl port-forward` (ver `start-components.sh`).

| Componente | Puerto del Service | Puerto en localhost |
|---|---|---|
| ci-validator-api | 5000 (contenedor 8000) | 5000 |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3000 |
| Jenkins | (Docker) | 8080 |


## c. Pipeline

Definido en el [`Jenkinsfile`](Jenkinsfile) de esta carpeta; Jenkins lo ejecuta desde la raíz del repositorio. Parámetro `VERSION` (por defecto `2.1.2`): determina la carpeta `ci-validator-api/v<VERSION>` (código y Dockerfile) y el tag de la imagen.

| Etapa | Qué hace | Herramientas |
|---|---|---|
| **Tests** | Crea un venv, instala `requirements-dev.txt`, ejecuta `pytest` (6 tests) y publica el informe JUnit | Python 3, pytest, plugin `junit` |
| **Build y carga en minikube** | Construye `ci-validator-api:<VERSION>` con el Dockerfile de `ci-validator-api/v<VERSION>` y la carga en el nodo de minikube | Docker CLI (socket del host) |
| **Deploy** | Ejecuta `entregable4/scripts/deploy.sh`: crea el ConfigMap del dashboard, aplica los manifiestos, escala a 0 los blue/green del entregable 1, reinicia Prometheus y Grafana y espera el rollout | kubectl |

Jenkins se configura **como código** (`jenkins/casc.yaml`, plugin Configuration as Code + Job DSL): usuario `admin`, y el job `ci-validator-api` ya creado, que lee el repo local (`file:///repo`, rama `main`). Los plugins están en `jenkins/plugins.txt`.

> **Importante:** el job solo ve lo **commiteado** en `main`. Hay que commitear antes de correrlo.
> **Primera corrida:** usar **Build Now**. Jenkins recién conoce el parámetro `VERSION` después de la primera ejecución; desde la segunda se puede usar *Build with Parameters*.

## d. Métricas y dashboard de Grafana

La app expone (en `/metrics`) tres familias de métricas propias, además de las de proceso de Python:

| Métrica | Tipo | Etiquetas | Uso |
|---|---|---|---|
| `ci_validator_validations_total` | Counter | `result` = `valid`, `invalid_check_digit`, `invalid_format` | **Métrica de negocio** |
| `ci_validator_http_requests_total` | Counter | `method`, `route`, `status` | Tráfico y errores (RPS) |
| `ci_validator_http_request_duration_seconds` | Histogram | `method`, `route` | Latencia |
| `ci_validator_http_requests_in_progress` | Gauge | `method`, `route` | Saturación |

`/metrics` y `/health` no se cuentan en las métricas HTTP (no son tráfico de usuarios).

Dashboard exportado: [`dashboard/dashboard.json`](dashboard/dashboard.json) ("CI Validator API - Entregable 4", refresco cada 10 s):

| Panel | Consulta PromQL | Unidad |
|---|---|---|
| Peticiones por segundo (RPS) | `sum(rate(ci_validator_http_requests_total[1m]))` | req/s |
| Latencia promedio de respuesta | `sum(rate(ci_validator_http_request_duration_seconds_sum[1m])) / sum(rate(ci_validator_http_request_duration_seconds_count[1m]))` | s |
| Uso de CPU por pod | `sum(rate(container_cpu_usage_seconds_total{pod=~"ci-validator-api-.*",container=""}[1m])) by (pod)` | núcleos |
| Uso de memoria por pod | `sum(container_memory_working_set_bytes{pod=~"ci-validator-api-.*",container=""}) by (pod)` | bytes |
| Validaciones de cédula por resultado (últimos 2 min) | `sum(increase(ci_validator_validations_total[2m])) by (result)` | validaciones |

> En este minikube cAdvisor publica las series a nivel de pod (sin etiqueta `container`), por eso los paneles de CPU y memoria filtran con `container=""`.

### Alertas (Prometheus)

| Alerta | Condición | Severidad |
|---|---|---|
| `CIValidatorAltoVolumen` | `sum(increase(ci_validator_validations_total[2m])) > 40` | warning |
| `CIValidatorSinTargets` | `absent(up{job="ci-validator-api"} == 1)` durante 1 min | critical |

Las alertas solo se visualizan en http://localhost:9090/alerts (no hay Alertmanager).

## e. Seguridad

El análisis de seguridad está en el [Entregable 3](../entregable3/): Semgrep y pip-audit, Trivy, KubeLinter, Kyverno y Falco. La imagen v2.1.2 usa el Dockerfile endurecido en ese entregable (usuario no-root, zlib1g corregido, pip 26.2.0). Los manifiestos de este entregable no incluyen el endurecimiento de Kubernetes, así que se despliegan en un minikube sin las políticas de Kyverno.

Consideraciones del entorno de este entregable (laboratorio local, **no apto para producción**):

- Jenkins corre como `root` con el socket de Docker del host montado.
- Jenkins y Grafana usan credenciales por defecto (`admin` / `admin`).
- Prometheus no persiste datos ni tiene Alertmanager.

## f. Problemas encontrados y soluciones

| Problema | Causa | Solución |
|---|---|---|
| Jenkins (en Docker) no alcanzaba el cluster | El kubeconfig de minikube apunta a `127.0.0.1`, inaccesible desde otro contenedor | Kubeconfig aplanado con la IP de minikube y conexión de Jenkins a la red Docker `minikube` (`start-components.sh`) |
| Jenkins no tiene el CLI de minikube | No se puede usar `minikube image load` dentro del contenedor | `docker save \| docker exec -i minikube docker load` usando el socket de Docker del host |
| Los paneles de CPU y memoria salían vacíos | cAdvisor publica series por pod, sin etiqueta `container`; el filtro `container!=""` las descartaba | Consultas con `container=""` |
| Las métricas de la app salían en 0 y la respuesta decía `api_version 1.1.0` | Los Deployments blue/green del entregable 1 comparten el label `app=ci-validator-api`; el port-forward del Service caía en uno de ellos y Prometheus los scrapeaba como targets | `deploy.sh` escala a 0 `ci-validator-api-blue` y `ci-validator-api-green` |
| Stage de build: `docker: not found` | En Debian 13 el paquete `docker.io` ya no incluye el binario `docker` | Instalar `docker-cli` en `jenkins/Dockerfile` |
| Jenkins rechazaba el checkout de `file:///repo` | Git plugin bloquea repositorios locales | `-Dhudson.plugins.git.GitSCM.ALLOW_LOCAL_CHECKOUT=true` |
| `buildWithParameters` devolvía 400 en la primera corrida | Los parámetros se declaran en el Jenkinsfile y Jenkins los conoce recién tras una primera ejecución | Primera corrida con *Build Now* |
| El pipeline fallaba con el `Jenkinsfile` vacío | El job lee el repo local y solo ve lo commiteado | Commitear en `feature/entregable4` antes de correr |
| `container name "/jenkins" is already in use` | Existía otro contenedor llamado `jenkins` (de otro proyecto) | Renombrarlo o borrarlo (`docker rename` / `docker rm`) |
| Los puertos de `localhost` dejaban de responder | `kubectl port-forward` muere cuando el pod se reinicia (por ejemplo tras un deploy) | Bucle de reintento por servicio en `start-components.sh`, con registro en `$TMPDIR/ci-validator-portforward.log` |
| Prometheus/Grafana no tomaban cambios de configuración | Los ConfigMap montados no se recargan solos | `deploy.sh` ejecuta `rollout restart` de ambos |

## g. Conclusiones y oportunidades de mejora

_Conclusiones generales: pendiente de redactar._

**Limitaciones conocidas del estado actual**

- El Deployment de la app usa `image: ci-validator-api:2.1.2` fijo y el pipeline reconstruye siempre ese tag: si el código cambia pero el tag no, `kubectl apply` no reinicia los pods de la app y siguen con la imagen anterior. Además, el parámetro `VERSION` solo cambia el build, no la imagen desplegada.
- No hay verificación posterior al deploy (smoke test) en el pipeline.
- La app no define `resources` ni `livenessProbe`.

**Mejoras posibles:** webhook de Git, registry de imágenes en lugar de cargar la imagen al nodo, `kube-prometheus-stack` con Alertmanager y notificaciones a un canal externo, persistencia para Prometheus y Grafana, etapa de smoke test y de análisis de seguridad en el pipeline.

---

## Guía paso a paso: levantar, probar y bajar

### Requisitos

- Docker Desktop (corriendo), `minikube` y `kubectl`.
- Un minikube sin las políticas de Kyverno del entregable 3 (`minikube delete --all --purge` antes de `init.sh`).
- Los comandos se ejecutan desde la raíz del repositorio, con bash.
- Cambios **commiteados en la rama `main`** (el job de Jenkins lee el repo local).
- Puertos 3000, 5000, 8080 y 9090 libres, y que no exista otro contenedor llamado `jenkins`.

### 1. Levantar

```bash
./entregable4/scripts/init.sh
```
Arranca minikube (si no estaba), habilita el addon `metrics-server`, construye la imagen `ci-validator-api:2.1.2`, la carga en minikube y aplica los manifiestos (app ×3, Prometheus y Grafana con datasource y dashboard provisionados). Escala a 0 los Deployments `blue`/`green` del entregable 1.

```bash
./entregable4/scripts/start-components.sh
```
Levanta Jenkins en Docker y expone en localhost la app, Prometheus y Grafana. Los port-forward se reintentan solos si se caen (cada reintento queda en `$TMPDIR/ci-validator-portforward.log`).

| Componente | URL | Acceso |
|---|---|---|
| App (Swagger) | http://localhost:5000/docs | |
| Prometheus | http://localhost:9090/targets | |
| Grafana | http://localhost:3000 | admin / admin |
| Jenkins | http://localhost:8080 | admin / admin |

### 2. Probar

**Pipeline:** en Jenkins, job `ci-validator-api` → **Build Now** (primera vez; luego *Build with Parameters*). Debe pasar por las etapas Tests, Build y carga en minikube, y Deploy.

**Tráfico:**
```bash
./entregable4/scripts/generate-traffic.sh [rondas=60] [pausa_seg=0.5]
```
Envía cédulas válidas, con dígito verificador incorrecto y mal formadas (5 requests por ronda, unos 40 s con los valores por defecto). Puebla el dashboard y supera las 40 validaciones en 2 minutos, lo que dispara la alerta.

**Verificación:**

| Qué | Dónde | Resultado esperado |
|---|---|---|
| Pods | `kubectl get pods` | 3 × `ci-validator-api`, `prometheus` y `grafana` en `Running` |
| Targets | http://localhost:9090/targets | `ci-validator-api` (3) y `cadvisor` en `UP` |
| Alerta | http://localhost:9090/alerts | `CIValidatorAltoVolumen` en `Firing` |
| Dashboard | Grafana → "CI Validator API - Entregable 4" (rango *Last 15 minutes*) | Los 5 paneles con datos |
| Pipeline | Jenkins → job `ci-validator-api` | Las 3 etapas en verde |

### 3. Bajar todo

```bash
./entregable4/scripts/cleanup.sh          # detiene port-forwards, Jenkins (con su volumen) y borra los recursos de Kubernetes
./entregable4/scripts/cleanup.sh --all    # además elimina el cluster de minikube
```

### Problemas frecuentes

- **`start-components.sh` falla con "container name /jenkins is already in use"**: existe otro contenedor llamado `jenkins`. Renombrarlo (`docker rename jenkins <otro>`) o borrarlo (`docker rm jenkins`) y volver a ejecutar.
- **Un `localhost:<puerto>` no responde**: el port-forward se está reiniciando (tras un deploy tarda unos segundos). Si persiste, volver a ejecutar `./entregable4/scripts/start-components.sh`.
- **El pipeline falla con el `Jenkinsfile` vacío o sin `scripts/`**: falta commitear en `feature/entregable4`.

---

## Capturas de pantalla

Imágenes en [`./images/entregable4/`](./images/entregable4/).

### 1. Pods y servicios en Kubernetes
`kubectl get pods,svc` con la app ×3, Prometheus y Grafana en `Running`.

![Pods y servicios](./images/entregable4/pods-servicios.png)

### 2. Pipeline de Jenkins
Vista de etapas (Stage View) con Tests, Build y carga en minikube, y Deploy en verde, y resultado de los tests.

![Pipeline de Jenkins](./images/entregable4/pipeline.png)

### 3. Targets de Prometheus
http://localhost:9090/targets con `ci-validator-api` y `cadvisor` en `UP`.

![Targets de Prometheus](./images/entregable4/targets.png)

### 4. Dashboard de Grafana
Los cinco paneles con datos tras ejecutar `generate-traffic.sh`.

![Dashboard de Grafana](./images/entregable4/dashboard.png)

### 5. Alerta disparada
http://localhost:9090/alerts con `CIValidatorAltoVolumen` en `Firing`.

![Alerta en Firing](./images/entregable4/alertas.png)

---