# Entregable 3 - DevSecOps para una Aplicación en Kubernetes

## Consigna

Requisitos de seguridad y herramientas DevSecOps 

- Seguridad en el código 
    - Ejecutar npm audit y guardar el resultado en /reports/npm-audit.txt. 
    - Aplicar un análisis estático de código con Semgrep. 
    - Corregir las alertas más relevantes o justificar brevemente aquellas que se decida mantener.

- Seguridad en la imagen 
    - Escanear la imagen de Docker con Trivy y guardar los resultados en /reports/trivyreport.txt. 
    - Las vulnerabilidades CRITICAL o HIGH deben ser documentadas o resueltas.

- Seguridad en Kubernetes 
    - Aplicar Kyverno para definir tres políticas: 1. Prohibir el uso de imágenes con la etiqueta latest. 2. Exigir límites y solicitudes de recursos en todos los pods. 3. Impedir la ejecución de contenedores como root. 
    - Validar el correcto funcionamiento de las políticas intentando desplegar un manifiesto no conforme. 
    - Analizar los manifiestos con KubeLinter y guardar el resultado en /reports/kubelinter.txt. 

- Seguridad en tiempo de ejecución 
    - Instalar Falco en el cluster (o usar una instalación existente). 
    - Ejecutar dentro de un pod una acción sospechosa (por ejemplo, abrir una shell interactiva). 
    - Verificar que Falco registre el evento y guardar el log o la alerta en /reports/falco-event.log 

# Documentación

## Seguridad en el Código

### Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| Semgrep | 1.184.0 | Análisis estático del código y del Dockerfile |
| pip-audit | 2.10.1 | Vulnerabilidades conocidas en las dependencias Python |

### Por qué pip-audit en lugar de npm audit

`npm audit` analiza dependencias del ecosistema npm a partir de un `package-lock.json`. La aplicación está escrita en Python y no tiene dependencias de Node, así que `npm audit` no tiene nada que analizar. La herramienta equivalente para Python es `pip-audit`, de la Python Packaging Authority (PyPA), que compara cada dependencia con las vulnerabilidades publicadas.

Se audita la lista de paquetes instalados en la imagen (`pip freeze --all`) y no el `requirements.txt`, porque en v2.1.0 las dependencias transitivas no estaban fijadas: auditar el archivo habría resuelto versiones distintas de las que contiene la imagen.

### Resultados

| Informe | Versión de la app |
|---|---|
| [Semgrep, línea base](./reports/baseline/semgrep.txt) | v2.1.0 |
| [Semgrep, final](./reports/final/semgrep.txt) | v2.1.1 |
| [pip-audit, línea base](./reports/baseline/pip-audit.txt) | v2.1.0 |
| [pip-audit, final](./reports/final/pip-audit.txt) | v2.1.1 |

### Hallazgos y decisiones

- Línea base (v2.1.0)
    - Semgrep
        - Se encontró una vulnerabilidad en el Dockerfile: dockerfile.security.missing-user.missing-user
        - Descripción de la vulnerabilidad: Al no especificar un usuario (USER), un programa dentro del contenedor podría ejecutarse como 'root'. Esto supone un riesgo de seguridad.  Si un atacante logra controlar un proceso que se ejecuta como 'root', podría obtener el control del contenedor. Asegúrate de que el último usuario (USER) definido en el Dockerfile sea distinto de 'root'.
    - pip-audit
        - No se encontraron vulnerabilidades en las dependencias directas y transitivas de la app, pero se encontraron vulnerabilidades en la versión de pip (el sistema de gestión de paquetes oficial y estándar del lenguaje de programación Python) que utiliza la imagen (utiliza la v25.0.1).

- Final (v2.1.1)
    - Semgrep
        - Se solucionó la vulnerabilidad creando un usuario no-root en el Dockerfile y ejecutando las instrucciones siguientes con él.
    - pip-audit
        - Se solucionaron las vulnerabilidades actualizando pip a la versión 26.2.0.

En resumen, se hallaron vulnerabilidades con las herramientas en la v2.1.0 de la app, se corrigieron en la v2.1.1 y se verificaron que se solucionaron con las herramientas.

### Comandos para obtener los reportes

Los siguientes comandos fueron ejecutados en PowerShell (>v6.0):

```bash
=== 0. Preparación: fijar las versiones de las herramientas ===

$SEMGREP = "semgrep/semgrep:1.184.0"
$PY = "python:3.12-slim"
$PIP_AUDIT = "pip-audit==2.10.1"

=== 1. Línea base sobre v2.1.0 ===

# 1.1. Semgrep
docker run --rm -v "${PWD}:/src" -w /src $SEMGREP sh -c "semgrep scan --verbose --no-git-ignore --config auto ci-validator-api/v2.1.0 > entregable3/reports/baseline/semgrep.txt 2>&1"
# Detalles del comando:
# -v "${PWD}:/src" -w /src: monta el repositorio dentro del contenedor y trabaja desde ahí.
# --verbose imprimirá en el reporte un listado detallado que dice si se saltearon archivos.
# --no-git-ignore se utiliza para forzar al escáner a analizar todos los archivos y directorios, incluyendo aquellos que estén listados en el archivo .gitignore.
# --config auto: son conjuntos de reglas por defecto del registro de Semgrep.
# > ... 2>&1 dentro de sh -c: la redirección la hace el shell del contenedor, no PowerShell. Así el archivo queda en UTF-8 en cualquier versión de PowerShell, e incluye tanto los hallazgos como el resumen final.

# 1.2. pip-audit

# 1. Construir la imagen v2.1.0 (si no la tienes).
docker build -t ci-validator-api:2.1.0 ./ci-validator-api/v2.1.0

# 2. Listar los paquetes Python instalados en la imagen. --all incluye pip, que también viene en la imagen.
docker run --rm -v "${PWD}/entregable3/reports/baseline:/out" ci-validator-api:2.1.0 sh -c "pip freeze --all > /out/pip-freeze-v2.1.0.txt"

# 3. Auditar esa lista.
docker run --rm -v "${PWD}:/repo" -w /repo $PY sh -c "pip install --no-cache-dir -q $PIP_AUDIT && pip-audit -r entregable3/reports/baseline/pip-freeze-v2.1.0.txt --no-deps --disable-pip --aliases --desc --progress-spinner off -o entregable3/reports/baseline/pip-audit.txt"
# Detalles del comando:
# --no-deps: no resuelve dependencias; exige que todos los requisitos estén fijados a una versión exacta, que es justamente lo que da pip freeze. 
# --disable-pip: no usa pip para resolver dependencias; solo se permite con archivos con hashes o junto con --no-deps. El resultado no depende del estado de PyPI en ese momento. 
# --aliases: agrega los identificadores CVE.
# --desc: agrega la descripción de cada vulnerabilidad.
# -o: escribe el informe directamente en el archivo.

=== 2. Analizar y decidir ===

=== 3. Crear v2.1.1 con las correcciones ===

# Corregir.

# Luego, construir y verificar
docker build -t ci-validator-api:2.1.1 ./ci-validator-api/v2.1.1

# No debe mostrar uid=0(root).
docker run --rm ci-validator-api:2.1.1 id

# La app sigue funcionando.
docker run --rm -d -p 8000:8000 --name ci-validator-test ci-validator-api:2.1.1
curl.exe -s http://127.0.0.1:8000/health
docker stop ci-validator-test

===  4. Informes finales sobre v2.1.1 ===

docker run --rm -v "${PWD}:/src" -w /src $SEMGREP sh -c "semgrep scan --verbose --no-git-ignore --config auto ci-validator-api/v2.1.1 > entregable3/reports/final/semgrep.txt 2>&1"

docker run --rm -v "${PWD}/entregable3/reports/final:/out" ci-validator-api:2.1.1 sh -c "pip freeze --all > /out/pip-freeze-v2.1.1.txt"

docker run --rm -v "${PWD}:/repo" -w /repo $PY sh -c "pip install --no-cache-dir -q $PIP_AUDIT && pip-audit -r entregable3/reports/final/pip-freeze-v2.1.1.txt --no-deps --disable-pip --aliases --desc --progress-spinner off > entregable3/reports/final/pip-audit.txt 2>&1"
```

## Seguridad en la Imagen

### Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| Trivy | 0.76.2 | Vulnerabilidades de los paquetes del sistema y de Python en la imagen |

### Caché de la base de datos

Trivy descarga una base de datos de vulnerabilidades. Si se guarda en un volumen de Docker, no la descarga en cada ejecución. Además, la línea base y el escaneo final pueden usar exactamente la misma base, y así la comparación es justa. Basta con agregar -v trivy-cache:/root/.cache a cada comando; Docker crea el volumen la primera vez.

Base de datos de vulnerabilidades actualizada el 2026-11-08 (`trivy version`). Los dos escaneos usaron la misma base de datos (`--skip-db-update` en el escaneo final).

### Carpeta para las imágenes exportadas

Se va a exportar cada imagen a un archivo .tar de unos 150 a 200 MB. Ponerlos en una carpeta que git ignore y nunca subirlos al repositorio.

Trivy no tiene acceso al daemon de Docker: escanea la imagen exportada con `docker save`.

### Tipos de análisis utilizados

- vuln (Vulnerabilidades - CVE): Es el motor principal. Busca fallos de seguridad conocidos públicamente en los paquetes instalados del sistema operativo (como Alpine o Debian) y en las dependencias de los lenguajes de programación (como las librerías listadas en un package.json, requirements.txt o go.mod).
- secret (Secretos y Credenciales): Inspecciona el contenido de los archivos en busca de información confidencial expuesta por error. Rastrea patrones de claves API, tokens de servicios (AWS, GitHub, GitLab), contraseñas en texto plano, certificados SSH y cadenas de conexión a bases de datos.
- misconfig (Malas Configuraciones): Evalúa archivos de Infraestructura como Código (IaC) para verificar que sigan las mejores prácticas de seguridad. Analiza tus Dockerfile, manifiestos de Kubernetes, planos de Terraform o Helm Charts buscando configuraciones riesgosas (por ejemplo, correr un contenedor con privilegios innecesarios o dejar puertos críticos expuestos al público).

### Resultados

| Informe | Versión de la app |
|---|---|
| [Línea base](./reports/baseline/trivyreport.txt) | v2.1.0 |
| [Final](./reports/final/trivyreport.txt) | v2.1.1 |

### ¿Cómo leer el informe?

El informe tiene dos secciones:

- Paquetes del sistema operativo: los paquetes de Debian que trae la imagen base python:3.12-slim.
- Paquetes Python: lo instalado en site-packages. Es normal que aquí aparezcan las mismas vulnerabilidades de pip 25.0.1 que encontró pip-audit.

Para decidir qué hacer con cada fila, la columna clave es Status:

- fixed: existe una versión corregida (columna “Fixed Version”), así que se resuelve actualizando.
- affected: todavía no hay corrección publicada.
- will_not_fix / fix_deferred: Debian decidió no corregirla o postergarla.

Con affected, will_not_fix o fix_deferred, actualizar no la resuelve: hay que documentarla.

### Vulnerabilidades CRITICAL y HIGH

- Baseline (v2.1.0)
    - Debian 13.7: 189 vulnerabilidades (UNKNOWN: 0, LOW: 65, MEDIUM: 75, HIGH: 49, CRITICAL: 0)
        - Todas las librerías del sistema operativo tienen vulnerabilidades con Status affected (todavía no hay corrección publicada), a excepción de una librería zlib1g.
        - zlib1g tiene 3 vulnerabilidades para las que se tiene corrección publicada:
            - HIGH: CVE-2026-76844 y CVE-2026-85091 son vulnerabilidades de desbordamiento de búfer en la región heap (Heap Buffer Overflow).
            - MEDIUM: CVE-2026-27171 es una vulnerabilidad de denegación de servicio (DoS).
            - La solución a estas vulnerabilidades es actualizar a la versión 1:1.3.dfsg+really1.3.1-1+deb13u1
    - Python (python-pkg): 6 vulnerabilidades (UNKNOWN: 0, LOW: 1, MEDIUM: 5, HIGH: 0, CRITICAL: 0)
        - Las vulnerabilidades son las mismas que las detectadas con pip-audit, se solucionan igual.

Luego, en v2.1.1 se aplicó:
- En Dockerfile, actualiza la librería zlib1g de Debian a la versión fixeada. Agregar después de la línea FROM: RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && rm -rf /var/lib/apt/lists/*
- pip actualizado a 26.2.0.

- Final (v2.1.1)
    - Debian 13.7: 186 vulnerabilidades (UNKNOWN: 0, LOW: 65, MEDIUM: 74, HIGH: 47, CRITICAL: 0)
        - Se fixearon las vulnerabilidades con Status fixed del reporte anterior.
    - Python (python-pkg): 9 vulnerabilidades (UNKNOWN: 0, LOW: 1, MEDIUM: 2, HIGH: 5, CRITICAL: 1).
        - Se introdujeron nuevas vulnerabilidades a otras librerías Python (no a pip) y de mayor gravedad al actualizar pip.
        - Pero son librerías internas de pip; pip solo se usa durante el build; la app no las importa.
        - El riesgo que queda: durante el build, pip descarga paquetes usando la librería certifi.
        - No se pueden actualizar por separado, porque no están instaladas como paquetes propios.

### Comandos para obtener los reportes

```bash
=== 0. Preparación ===

# Versión de Trivy
$TRIVY = "aquasec/trivy:0.76.2"
docker pull $TRIVY

# Agregar build/ a .gitignore

# Crear el directorio ./entregable3/build

=== 1. Línea base sobre v2.1.0

docker save -o entregable3/build/ci-validator-api-2.1.0.tar ci-validator-api:2.1.0

# Trivy escanea un archivo exportado de la imagen, en lugar de conectarse a Docker.
docker run --rm -v trivy-cache:/root/.cache -v "${PWD}:/repo" -w /repo $TRIVY image --input entregable3/build/ci-validator-api-2.1.0.tar --scanners vuln,secret,misconfig --format table --output entregable3/reports/baseline/trivyreport.txt

# Versión de Trivy y fecha de la base de datos, para el README.
docker run --rm -v trivy-cache:/root/.cache $TRIVY version

=== 3. Correcciones en v2.1.1 ===

# Corregir Dockerfile.

=== 4. Escaneo final sobre v2.1.1 ===

docker build -t ci-validator-api:2.1.1 ./ci-validator-api/v2.1.1

docker save -o entregable3/build/ci-validator-api-2.1.1.tar ci-validator-api:2.1.1

docker run --rm -v trivy-cache:/root/.cache -v "${PWD}:/repo" -w /repo $TRIVY image --input entregable3/build/ci-validator-api-2.1.1.tar --scanners vuln,secret,misconfig --skip-db-update --format table --output entregable3/reports/final/trivyreport.txt
```

## Seguridad en Kubernetes

KubeLinter es una herramienta de análisis estático (un linter) que identifica errores de configuración y vulnerabilidades antes de que los recursos se desplieguen en el clúster.

Kyverno es un motor de políticas dinámico diseñado específicamente para Kubernetes que valida, muta y genera recursos directamente dentro del clúster.

Helm es un gestor de paquetes para Kubernetes. Funciona de manera similar a gestores de paquetes como apt o yum en Linux, o pip en Python: en lugar de instalar librerías, Helm instala y administra aplicaciones completas dentro de un clúster de Kubernetes.

https://kyverno.io/docs/installation/installation/

Importante, para instalar kyverno en minikube hay que: ir a Docker Desktop Abre Settings → Docker Engine y agrega "dns": ["1.1.1.1", "8.8.8.8"] al JSON.

### Hallazgos con Kubelinter

| Hallazgo en la línea base - [app deployment.yaml del entregable 2](../entregable2/k8s/app/deployment.yaml) | Corrección en deployment.yaml - [app deployment.yaml del entregable 3](./k8s/app/deployment.yaml) |
| --- | --- |
| run-as-non-root | runAsNonRoot: true + runAsUser/runAsGroup numéricos |
| unset-cpu-requirements, unset-cpu-limit | CPU: request 50m, limit 500m |
| unset-memory-request, unset-memory-requirements | Memoria: request 64Mi, limit 128Mi |
| no-read-only-root-fs | readOnlyRootFilesystem: true |
| no-anti-affinity | podAntiAffinity de tipo preferred por nodo |

Los valores de los recursos salen de los paneles de Grafana del entregable 2.

La anti-afinidad preferred no tiene efecto en minikube, que tiene un solo nodo, pero tampoco cuesta nada y es correcta en un clúster real.

### Manifiestos no conformes rechazados por las políticas Kyverno

| Manifiesto | Lo rechaza |
| --- | --- |
| 01-latest-tag (Deployment) | disallow-latest-tag |
| 02-no-tag (Pod, sin etiqueta = latest implícito) | disallow-latest-tag |
| 03-no-limits (Deployment, requests sin limits) | require-requests-limits |
| 04-root (Deployment, imagen v2.1.0 sin USER) | disallow-root-containers |
| 05-run-as-user-0 (Pod, UID 0 explícito) | disallow-root-containers |
| entregable2/k8s/app/deployment.yaml | require-requests-limits y disallow-root-containers |
| kubectl run --image=nginx | las tres |

### Comandos para obtene

```bash
=== 0. Preparación ===

$KUBELINTER      = "stackrox/kube-linter:v0.8.3"

# UID y GID reales de appuser
docker build -t ci-validator-api:2.1.1 ./ci-validator-api/v2.1.1
docker run --rm ci-validator-api:2.1.1 id
# Esperado: uid=100(appuser) gid=101(appgroup) groups=101(appgroup)

=== 1. KubeLinter: línea base ===

# Igual que con Trivy y Semgrep, la línea base son los manifiestos de la app del entregable 2 (v2.1.0):
docker pull $KUBELINTER
docker run --rm -v "${PWD}:/repo" -w /repo $KUBELINTER lint --config entregable3/.kube-linter.yaml --format plain --output entregable3/reports/baseline/kubelinter.txt entregable2/k8s/app

=== 2. KubeLinter: final ===

docker run --rm -v "${PWD}:/repo" -w /repo $KUBELINTER lint --config entregable3/.kube-linter.yaml --format plain --output entregable3/reports/final/kubelinter.txt entregable3/k8s/app

=== 3. minikube limpio con la versión fijada

# Primero en Docker Desktop, Abre Settings → Docker Engine y agrega "dns": ["1.1.1.1", "8.8.8.8"] al JSON.

minikube version
minikube delete --all --purge
minikube start --driver=docker
minikube image load ci-validator-api:2.1.1

=== 4. Instalar Kyverno con Helm ===

winget install Helm.Helm # si no lo tienes; luego abre una terminal nueva y ejecuta: helm version

helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno --namespace kyverno kyverno/kyverno --create-namespace
kubectl get pods -n kyverno

=== 5. Aplicar las políticas

kubectl apply -f entregable3/k8s/policies/
kubectl get vpol                                # las 3 deben mostrar READY = true
kubectl get vpol disallow-latest-tag -o yaml    # revisa status.autogen

=== 6. Validar con manifiestos no conformes y guardar la evidencia ===

$OUT = "entregable3/reports/final/kyverno-validation.txt"
Remove-Item $OUT -ErrorAction Ignore

$TESTS = @(
  "entregable3/k8s/non-compliant/01-latest-tag.yaml",
  "entregable3/k8s/non-compliant/02-no-tag.yaml",
  "entregable3/k8s/non-compliant/03-no-limits.yaml",
  "entregable3/k8s/non-compliant/04-root.yaml",
  "entregable3/k8s/non-compliant/05-run-as-user-0.yaml",
  "entregable2/k8s/app/deployment.yaml"
)

foreach ($t in $TESTS) {
  "`n=== kubectl apply -f $t ===" | Tee-Object -FilePath $OUT -Append
  kubectl apply -f $t 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $OUT -Append
}

"`n=== kubectl run nc-kubectl-run --image=nginx ===" | Tee-Object -FilePath $OUT -Append

kubectl run nc-kubectl-run --image=nginx 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $OUT -Append

kubectl get deploy,pods    # no debe existir ningún recurso nc-* ni el ci-validator-api del entregable 2

=== 7. Desplegar la app conforme y comprobar el endurecimiento ===

kubectl apply -f entregable3/k8s/app/
kubectl rollout status deployment/ci-validator-api
kubectl get pods -l app=ci-validator-api        # 3 pods Running, READY 1/1

$POD = kubectl get pods -l app=ci-validator-api -o jsonpath='{.items[0].metadata.name}'
kubectl exec $POD -- id                                               # uid=100(appuser) gid=101(appgroup)
kubectl exec $POD -- touch /tmp/prueba                                # Read-only file system
kubectl exec $POD -- grep -E "NoNewPrivs|CapEff" /proc/1/status       # NoNewPrivs: 1 / CapEff: 0000000000000000
kubectl exec $POD -- ls /var/run/secrets/kubernetes.io/serviceaccount # No such file or directory
```

## Seguridad en Tiempo de Ejecución

Falco es una herramienta de código abierto de seguridad en tiempo de ejecución (runtime security) nativa de la nube, diseñada para detectar comportamientos anómalos, amenazas y accesos no autorizados en hosts, contenedores y clústeres de Kubernetes en tiempo real

En el contexto de Falco, una sonda (probe) es el componente de software encargado de captar las llamadas al sistema del kernel de Linux y enviarlas al espacio de usuario donde Falco las procesa. Es el "ojo" de Falco dentro del sistema operativo.

### Alerta de Falco

time      : 2026-11-08T11:40:26.535436666Z
rule      : Terminal shell in container
priority  : Notice
pod       : ci-validator-api-57b864cdf9-8dgps
namespace : default
uid       : 100
proceso   : sh
padre     : 
terminal  : 34816


### Comandos

```bash
=== 0. Punto de partida ===

# Retoma desde el paso 7 de la sección anterior
kubectl get vpol                           # 3 políticas, READY = true
kubectl get pods -l app=ci-validator-api   # 3 pods Running 1/1

=== 1. Verificar que el kernel soporta la sonda moderna ===

minikube ssh -- uname -r
minikube ssh -- ls -l /sys/kernel/btf/vmlinux
kubectl get nodes -o wide

# uname -r debería mostrar algo como 6.x-microsoft-standard-WSL2, o -linuxkit si Docker Desktop usa Hyper-V. Es el kernel de la VM de Docker Desktop, no uno propio de minikube.
# /sys/kernel/btf/vmlinux tiene que existir.
# La columna CONTAINER-RUNTIME debería decir docker://.... Falco consulta ese runtime para saber a qué pod y namespace pertenece cada evento.

=== 2: confirmar la exclusión del namespace. ===

kubectl get vpol -o custom-columns='POLITICA:.metadata.name,ACCION:.spec.validationActions,NS_EXCLUIDOS:.spec.matchConstraints.namespaceSelector.matchExpressions[0].values'
# Las tres políticas deben mostrar [Deny] y [kube-system kyverno falco].

=== 4. instalar Falco con la versión fijada. ===

helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm show chart falcosecurity/falco

helm install falco falcosecurity/falco --namespace falco --create-namespace -f entregable3/k8s/falco/falco-values.yaml

kubectl rollout status daemonset/falco -n falco --timeout=5m
kubectl get pods -n falco

=== Paso 5: comprobar que Falco está capturando. ===

kubectl logs -n falco daemonset/falco -c falco | Select-String "Falco version|falco_rules.yaml|Enabled event sources|modern BPF|ring buffer|iterators"

# Deberías ver Falco version: 0.45.2, la carga de /etc/falco/falco_rules.yaml, Enabled event sources: syscall y Opening 'syscall' source with modern BPF probe.
# Una línea con disabled BPF iterators (not running in the root PID namespace...) es informativa y normal: Falco corre en el namespace de PIDs de su propio pod.
# Uso daemonset/falco y no -l app.kubernetes.io/name=falco a propósito: con selector, kubectl logs muestra solo 10 líneas por defecto.

=== Paso 6: ejecutar la acción sospechosa. ===

# En la terminal A, deja los logs en vivo:
kubectl logs -n falco daemonset/falco -c falco -f --tail=0

# En la terminal B, abre la shell:
(Get-Date).ToUniversalTime().ToString("o")   # Falco registra la hora en UTC
$POD = kubectl get pods -l app=ci-validator-api -o jsonpath='{.items[0].metadata.name}'
kubectl exec -it $POD -- sh

# Dentro del contenedor:
id               # uid=100(appuser) gid=101(appgroup)
cat /etc/shadow  # Permission denied
touch /tmp/x     # Read-only file system
exit

# La alerta aparece en la terminal A al abrirse la shell, no al salir.

=== Paso 7: guardar la evidencia. ===

$OUT = "entregable3/reports/final/falco-event.txt"

kubectl logs -n falco daemonset/falco -c falco --since=30m |
  Where-Object { $_ -match '"rule":\s*"Terminal shell in container"' } |
  ForEach-Object { $_.TrimEnd("`r") } |
  Set-Content -Path $OUT -Encoding utf8NoBOM

(Get-Content $OUT).Count

Get-Content $OUT | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object time, rule, priority,
  @{n='pod'; e={ $_.output_fields.'k8s.pod.name' }},
  @{n='namespace'; e={ $_.output_fields.'k8s.ns.name' }},
  @{n='uid'; e={ $_.output_fields.'user.uid' }},
  @{n='proceso'; e={ $_.output_fields.'proc.name' }},
  @{n='padre'; e={ $_.output_fields.'proc.pname' }},
  @{n='terminal'; e={ $_.output_fields.'proc.tty' }} | Format-List
```