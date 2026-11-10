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
    - Instalar Falco en el clúster (o usar una instalación existente). 
    - Ejecutar dentro de un pod una acción sospechosa (por ejemplo, abrir una shell interactiva). 
    - Verificar que Falco registre el evento y guardar el log o la alerta en /reports/falco-event.log 

# Documentación

## Seguridad en el Código

### Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| Semgrep | 1.184.0 | Análisis estático del código y del Dockerfile |
| pip-audit | 2.10.1 | Vulnerabilidades conocidas en las dependencias Python |

- [Semgrep](https://semgrep.dev/) es una herramienta de análisis estático de código (SAST, por sus siglas en inglés) ligera y de código abierto que permite examinar el código fuente en busca de errores, vulnerabilidades de seguridad y problemas de calidad.
- [pip-audit](https://pypi.org/project/pip-audit/) es una herramienta de software desarrollada por Trail of Bits con el apoyo de Google y mantenida por la Python Packaging Authority (PyPA). Su función principal es escanear entornos y dependencias de Python en busca de vulnerabilidades de seguridad conocidas

### ¿Por qué pip-audit en lugar de npm-audit?

`npm audit` analiza dependencias del ecosistema npm a partir de un `package-lock.json`. La aplicación está escrita en Python y no tiene dependencias de Node, así que `npm audit` no tiene nada que analizar. La herramienta equivalente para Python es `pip-audit`, de la Python Packaging Authority (PyPA), que compara cada dependencia con las vulnerabilidades publicadas.

Se audita la lista de paquetes instalados en la imagen (`pip freeze --all`) y no el `requirements.txt`, porque en v2.1.0 las dependencias transitivas no estaban fijadas: auditar el archivo habría resuelto versiones distintas de las que contiene la imagen.

### Resultados

| Informe | Versión de la app |
|---|---|
| [Semgrep, línea base](./reports/baseline/semgrep.txt) | v2.1.0 |
| [Semgrep, final](./reports/final/semgrep.txt) | v2.1.1 |
| [pip-audit, línea base](./reports/baseline/pip-audit.txt) | v2.1.0 |
| [pip-audit, final](./reports/final/pip-audit.txt) | v2.1.1 |

### Hallazgos y Decisiones

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

### Comandos para Obtener los Reportes

Ejecutados en PowerShell (>v6.0), desde la raíz del repositorio:

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

# 1. Construir la imagen v2.1.0 (si no se tiene).
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

=== 2. Analizar y decidir en base a los resultados ===

=== 3. Crear v2.1.1 con las correcciones ===

# Corregir.

# Luego, construir y verificar
docker build -t ci-validator-api:2.1.1 ./ci-validator-api/v2.1.1

# No debe mostrar uid=0(root).
docker run --rm ci-validator-api:2.1.1 id

# La app sigue funcionando a pesar de las correcciones.
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

- Trivy es un escáner de seguridad de código abierto desarrollado y mantenido por Aqua Security, diseñado para entornos nativos de la nube y DevOps.
    Trivy se utiliza para analizar diferentes elementos en busca de problemas de seguridad mediante un solo comando de terminal:
    - Vulnerabilidades de software: Detecta fallos conocidos (CVE) en paquetes de sistemas operativos (Alpine, Ubuntu, Debian, Red Hat, etc.) y dependencias de lenguajes de programación (npm, Pip, Go, Cargo, etc.).
    - Errores de configuración (IaC): Analiza archivos de infraestructura como código (Terraform, Kubernetes, Dockerfiles) para detectar malas prácticas de seguridad.
    - Secretos y credenciales expuestas: Encuentra contraseñas, tokens y claves privadas filtradas en el código, variables de entorno o repositorios.
    - Licencias de software: Identifica las licencias de los componentes utilizados en el proyecto.

### Caché de la Base de Datos

Trivy descarga una base de datos de vulnerabilidades. Si se guarda en un volumen de Docker, no la descarga en cada ejecución. Además, la línea base y el escaneo final pueden usar exactamente la misma base, y así la comparación es justa. Basta con agregar `-v trivy-cache:/root/.cache` a cada comando; Docker crea el volumen la primera vez.

Base de datos de vulnerabilidades actualizada el 2026-11-08 (`trivy version`). Los dos escaneos usaron la misma base de datos (`--skip-db-update` en el escaneo final).

### Carpeta para las Imágenes Exportadas

Se va a exportar cada imagen a un archivo .tar de unos 150 a 200 MB. Ponerlos en una carpeta que git ignore y nunca subirlos al repositorio. Esto porque Trivy no tiene acceso al daemon de Docker: escanea la imagen exportada con `docker save`.

### Tipos de Análisis Utilizados

- **vuln (Vulnerabilidades - CVE):** Es el motor principal. Busca fallos de seguridad conocidos públicamente en los paquetes instalados del sistema operativo (como Debian) y en las dependencias de los lenguajes de programación (como las librerías listadas en un requirements.txt).
- **secret (Secretos y Credenciales):** Inspecciona el contenido de los archivos en busca de información confidencial expuesta por error. Rastrea patrones de claves API, tokens de servicios (AWS, GitHub, GitLab), contraseñas en texto plano, certificados SSH y cadenas de conexión a bases de datos.
- **misconfig (Malas Configuraciones):** Evalúa archivos de Infraestructura como Código (IaC) para verificar que sigan las mejores prácticas de seguridad. Analiza los Dockerfile, manifiestos de Kubernetes, planos de Terraform o Helm Charts buscando configuraciones riesgosas (por ejemplo, correr un contenedor con privilegios innecesarios o dejar puertos críticos expuestos al público).

### Resultados

| Informe | Versión de la app |
|---|---|
| [Línea base](./reports/baseline/trivyreport.txt) | v2.1.0 |
| [Final](./reports/final/trivyreport.txt) | v2.1.1 |

### ¿Cómo leer el informe?

El informe tiene dos secciones:

- **Paquetes del sistema operativo:** los paquetes de Debian que trae la imagen base python:3.12-slim.
- **Paquetes Python:** lo instalado en site-packages (ubicación estándar donde Python almacena las bibliotecas y paquetes de terceros que instalas (por ejemplo, a través de herramientas como pip)). Es normal que aquí aparezcan las mismas vulnerabilidades de pip v25.0.1 que encontró pip-audit antes.

Para decidir qué hacer con cada fila, la columna clave es Status:

- `fixed`: existe una versión corregida (columna “Fixed Version”), así que se resuelve actualizando.
- `affected`: todavía no hay corrección publicada.
- `will_not_fix` / `fix_deferred`: Debian decidió no corregirla o postergarla.

Con `affected`, `will_not_fix` o `fix_deferred`, actualizar no resuelve la vulnerabilidad: hay que documentarla.

### Vulnerabilidades CRITICAL y HIGH

#### Línea base (v2.1.0)

- **Paquetes del sistema operativo (Debian 13.7):** 189 vulnerabilidades (UNKNOWN: 0, LOW: 65, MEDIUM: 75, HIGH: 49, CRITICAL: 0).
    - Casi todas tienen Status `affected` (todavía no hay corrección publicada), `will_not_fix` (Debian decidió no corregirlas) o `fix_deferred` (Debian postergó la corrección). En esos casos actualizar no sirve: no existe una versión corregida a la cual actualizar.
    - La única excepción es la librería de compresión `zlib1g`, con 3 vulnerabilidades en Status `fixed`, es decir, con versión corregida publicada:
        - HIGH: CVE-2026-76844 y CVE-2026-85091, desbordamientos de búfer en el heap (heap buffer overflow). Un dato comprimido manipulado puede escribir fuera de la memoria reservada.
        - MEDIUM: CVE-2026-27171, denegación de servicio (DoS).
        - Se corrigen actualizando `zlib1g` a la versión `1:1.3.dfsg+really1.3.1-1+deb13u1`.
- **Paquetes Python (python-pkg):** 6 vulnerabilidades (UNKNOWN: 0, LOW: 1, MEDIUM: 5, HIGH: 0, CRITICAL: 0).
    - Son las mismas que detectó pip-audit: todas están en pip v25.0.1, el que trae la imagen base. Las dependencias de la app no tienen vulnerabilidades.

#### Correcciones aplicadas en v2.1.1

- En el Dockerfile, inmediatamente después de `FROM`, se actualiza `zlib1g` a la versión corregida:
  `RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && rm -rf /var/lib/apt/lists/*`
- pip se actualiza a la versión 26.2.0.

#### Final (v2.1.1)

- **Paquetes del sistema operativo (Debian 13.7):** 186 vulnerabilidades (UNKNOWN: 0, LOW: 65, MEDIUM: 74, HIGH: 47, CRITICAL: 0).
    - Bajaron de 189 a 186 porque se corrigieron las 3 de `zlib1g`: HIGH pasó de 49 a 47 y MEDIUM de 75 a 74.
    - Las 186 restantes no tienen versión corregida publicada y quedan documentadas.
- **Paquetes Python (python-pkg):** 9 vulnerabilidades (UNKNOWN: 0, LOW: 1, MEDIUM: 2, HIGH: 5, CRITICAL: 1).
    - Las 6 de la línea base desaparecieron al actualizar pip.
    - Las 9 nuevas no están en pip en sí ni en las dependencias de la app. Están en librerías que pip trae copiadas dentro de su propia carpeta (`pip/_vendor`), como `certifi`. Esta práctica se llama *vendoring*: pip incluye sus dependencias para seguir funcionando aunque el entorno de Python esté dañado.
    - No se pueden actualizar por separado, porque no están instaladas como paquetes independientes sino como parte de pip. Solo se corrigen con una versión de pip que traiga copias más nuevas.
    - Impacto en la app: ninguna de estas librerías se importa en tiempo de ejecución. La app usa sus propias dependencias (FastAPI, Uvicorn y prometheus-client).
    - Riesgo residual:
        - **Durante el build:** pip descarga los paquetes de PyPI usando estas librerías. Por ejemplo, `certifi` aporta los certificados con los que se verifica la conexión TLS. Una vulnerabilidad ahí podría afectar la integridad de lo que se descarga.
        - **En la imagen final:** pip sigue instalado, aunque la app no lo use. Alguien que obtuviera una shell en el contenedor podría usarlo. El endurecimiento del Deployment reduce ese riesgo: usuario no-root, sistema de archivos de solo lectura y sin capabilities.
    - Mejora posible: quitar pip de la imagen final, desinstalándolo después de instalar las dependencias. Así estas vulnerabilidades dejan de existir en la imagen en lugar de quedar documentadas.

#### Resumen

| Categoría | Línea base (v2.1.0) | Final (v2.1.1) | ¿Qué cambió? |
|---|---|---|---|
| Debian: total | 189 | 186 | Se corrigió `zlib1g` |
| Debian: HIGH | 49 | 47 | Las 2 HIGH de `zlib1g` |
| Debian: CRITICAL | 0 | 0 | — |
| Python: total | 6 | 9 | Se corrigió pip; aparecieron las de sus librerías internas |
| Python: HIGH + CRITICAL | 0 | 6 | Librerías incluidas en pip 26.2.0, no usadas por la app |

### Comandos para Obtener los Reportes

Ejecutados en PowerShell (>v6.0), desde la raíz del repositorio:

```bash
=== 0. Preparación ===

# Versión de Trivy
$TRIVY = "aquasec/trivy:0.76.2"
docker pull $TRIVY

# Agregar build/ a .gitignore

# Crear el directorio ./entregable3/build

=== 1. Línea base sobre v2.1.0 ===

docker save -o entregable3/build/ci-validator-api-2.1.0.tar ci-validator-api:2.1.0

# Trivy escanea un archivo exportado de la imagen, en lugar de conectarse a Docker.
docker run --rm -v trivy-cache:/root/.cache -v "${PWD}:/repo" -w /repo $TRIVY image --input entregable3/build/ci-validator-api-2.1.0.tar --scanners vuln,secret,misconfig --format table --output entregable3/reports/baseline/trivyreport.txt
# Además, descarga la base de datos de vulnerabilidades.

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

### Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| KubeLinter | v0.8.3 | Análisis estático de los manifiestos antes de desplegarlos |
| Kyverno | la última (porque fijar la versión dio errores) | Controlador de admisión: rechaza en el clúster los recursos que violan las políticas |
| Helm | la última (porque fijar la versión dio errores) | Instalación de Kyverno en el clúster |

- [KubeLinter](https://docs.kubelinter.io/#/) es una herramienta de análisis estático (un linter) que identifica errores de configuración y vulnerabilidades antes de que los recursos se desplieguen en el clúster. 
- [Kyverno](https://kyverno.io/) es un motor de políticas dinámico diseñado específicamente para Kubernetes que valida, muta y genera recursos directamente dentro del clúster. Cada vez que alguien crea o modifica un recurso, el API server se lo consulta a Kyverno y, si viola una política en modo `Deny`, rechaza el pedido. Actúa en el momento del despliegue. Las políticas de este entregable usan el tipo `ValidatingPolicy` (`policies.kyverno.io/v1`), basado en expresiones CEL (al igual que los manifiestos k8s); el tipo anterior, `ClusterPolicy`, está deprecado.
- [Helm](https://helm.sh/es/) es un gestor de paquetes para Kubernetes. Funciona de manera similar a gestores de paquetes como apt o yum en Linux, o pip en Python: en lugar de instalar librerías, Helm instala y administra aplicaciones completas dentro de un clúster de Kubernetes.

> **__Nota__** Importante, para instalar kyverno en minikube hay que: ir a Docker Desktop, abrir Settings → Docker Engine, agregar "dns": ["1.1.1.1", "8.8.8.8"] al JSON (Daemon configuration file) y aplicar.

### Hallazgos con Kubelinter

La línea base es el Deployment de la app del entregable 2 (v2.1.0).

| Hallazgo en la línea base ([deployment.yaml del entregable 2](../entregable2/k8s/app/deployment.yaml)) | Corrección ([deployment.yaml del entregable 3](./k8s/app/deployment.yaml)) |
| --- | --- |
| run-as-non-root | `runAsNonRoot: true`, con `runAsUser: 100` y `runAsGroup: 101` numéricos |
| no-read-only-root-fs | `readOnlyRootFilesystem: true` |
| no-anti-affinity | `podAntiAffinity` de tipo `preferred` por nodo |

- **UID numérico:** la imagen declara `USER appuser`, un nombre. Con un nombre, el kubelet no puede comprobar que el usuario no sea root y el pod falla con `CreateContainerConfigError`. Por eso se declaran los números reales, obtenidos con `docker run --rm ci-validator-api:2.1.1 id`.
- **Anti-afinidad:** no tiene efecto en minikube, que tiene un solo nodo. En un clúster de varios nodos evita que la caída de un nodo se lleve todas las réplicas. Al ser `preferred`, nunca impide ubicar un pod.

### Endurecimiento Adicional (no lo pidió KubeLinter)

| Control | ¿Qué evita? |
| --- | --- |
| `allowPrivilegeEscalation: false` | Que un proceso no-root se convierta en root ejecutando un binario setuid (activa `no_new_privs` en el kernel) |
| `capabilities.drop: ["ALL"]` | Que el proceso conserve privilegios del kernel que no necesita |
| `seccompProfile: RuntimeDefault` | Llamadas al sistema peligrosas, filtradas por el perfil por defecto del runtime |
| `automountServiceAccountToken: false` | Que alguien con una shell en el pod obtenga credenciales para hablar con la API de Kubernetes |
| `readinessProbe` y `livenessProbe` sobre `/health` | Que un pod que no responde reciba tráfico o siga corriendo sin reiniciarse |

### Manifiestos No Conformes Rechazados por las Políticas de Kyverno

Las tres políticas están en modo `Deny`: Kyverno rechaza el recurso en la admisión. Excluyen los namespaces `kube-system`, `kyverno` y `falco`, cuyos componentes necesitan privilegios que violarían las políticas.

| Manifiesto | Lo rechaza |
| --- | --- |
| 01-latest-tag (Deployment) | disallow-latest-tag |
| 02-no-tag (Pod sin etiqueta: equivale a latest) | disallow-latest-tag |
| 03-no-limits (Deployment con requests y sin limits) | require-requests-limits |
| 04-root (Deployment con la imagen v2.1.0, que no tiene USER) | disallow-root-containers |
| 05-run-as-user-0 (Pod con UID 0 explícito) | disallow-root-containers |
| entregable2/k8s/app/deployment.yaml | disallow-root-containers |
| kubectl run --image=nginx | las tres |

Como las políticas se escriben sobre Pods, Kyverno genera automáticamente reglas equivalentes para Deployments y otros controladores (autogen). Por eso se rechaza el Deployment completo, en lugar de aceptarlo y que fallen después los pods que crea.

### Comandos para Obtener los Reportes

Ejecutados en PowerShell (>v6.0), desde la raíz del repositorio:

```bash
=== 0. Preparación ===

$KUBELINTER      = "stackrox/kube-linter:v0.8.3"

# UID y GID reales de appuser
docker build -t ci-validator-api:2.1.1 ./ci-validator-api/v2.1.1
docker run --rm ci-validator-api:2.1.1 id
# Esperado: uid=100(appuser) gid=101(appgroup) groups=101(appgroup)

===  1. KubeLinter: línea base (manifiestos del entregable 2) ===

docker pull $KUBELINTER
docker run --rm -v "${PWD}:/repo" -w /repo $KUBELINTER lint --config entregable3/.kube-linter.yaml --format plain --output entregable3/reports/baseline/kubelinter.txt entregable2/k8s/app

=== 2. KubeLinter: final (manifiestos del entregable 3) ===

docker run --rm -v "${PWD}:/repo" -w /repo $KUBELINTER lint --config entregable3/.kube-linter.yaml --format plain --output entregable3/reports/final/kubelinter.txt entregable3/k8s/app

=== 3. minikube limpio ===

# Importante, para instalar kyverno en minikube hay que: ir a Docker Desktop, abrir Settings → Docker Engine, agregar "dns": ["1.1.1.1", "8.8.8.8"] al JSON (Daemon configuration file) y aplicar.

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
# Esperar a que los pods estén creados.

=== 5. Aplicar las políticas ===

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

### Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| Falco | la última (porque fijar la versión dio errores) | Detección de comportamiento sospechoso en contenedores en ejecución |

- [Falco](https://falco.org/docs/getting-started/falco-kubernetes-quickstart/) es una herramienta de seguridad en tiempo de ejecución (runtime security). Mientras que Trivy, KubeLinter y Kyverno revisan imágenes y manifiestos antes de que algo corra, Falco observa lo que los procesos hacen una vez en marcha. Compara cada evento con un conjunto de reglas y emite una alerta cuando alguna se cumple.

    Para ver esos eventos, Falco usa una **sonda** (probe): el componente que capta las llamadas al sistema (syscalls) en el kernel de Linux y se las entrega a Falco en el espacio de usuario. En este entregable se usa la **sonda eBPF moderna** (`modern_ebpf`). Viene compilada dentro del binario de Falco, así que no hay que compilar ni cargar un módulo del kernel. A cambio, necesita un kernel que exponga BTF (`/sys/kernel/btf/vmlinux`), que se verifica en el paso 1.

    Por eso Falco corre como un DaemonSet privilegiado: un pod por nodo, con acceso al kernel del nodo. Ese privilegio violaría las tres políticas de Kyverno, y por eso el namespace `falco` está excluido de ellas.

### Alerta de Falco

Al abrir una shell interactiva dentro de un pod de la app, Falco disparó la regla **Terminal shell in container**. Esa regla detecta un intérprete de comandos con una terminal asociada dentro de un contenedor: en producción casi nunca es legítimo y suele ser el primer paso de un atacante.

```bash
time      : 2026-11-10T17:51:11.754347136Z
rule      : Terminal shell in container
priority  : Notice
pod       : ci-validator-api-57b864cdf9-6vwqd
namespace : default
uid       : 100
proceso   : sh
padre     : containerd-shim
terminal  : 34816
```

### Comandos para Obtener los Reportes

Ejecutados en PowerShell (>v6.0), desde la raíz del repositorio:

```bash
=== 0. Punto de partida ===

# Retoma desde el paso 7 de la sección anterior
kubectl get vpol                           # 3 políticas, READY = true
kubectl get pods -l app=ci-validator-api   # 3 pods Running 1/1

=== 1. Verificar que el kernel soporta la sonda moderna ===

minikube ssh -- uname -r
minikube ssh -- ls -l /sys/kernel/btf/vmlinux
kubectl get nodes -o wide

# uname -r muestra el kernel de la VM de Docker Desktop (por ejemplo x-microsoft-standard-WSL2), no uno propio de minikube.
# /sys/kernel/btf/vmlinux tiene que existir: la sonda moderna lo necesita.
# La columna CONTAINER-RUNTIME debe decir docker://...: Falco consulta ese runtime para saber a qué pod y namespace pertenece cada evento.

=== 2. Confirmar que las políticas de Kyverno excluyen el namespace falco ===

kubectl get vpol -o custom-columns='POLITICA:.metadata.name,ACCION:.spec.validationActions,NS_EXCLUIDOS:.spec.matchConstraints.namespaceSelector.matchExpressions[0].values'
# Las tres políticas deben mostrar [Deny] y [kube-system kyverno falco]. Si no, Kyverno rechaza el DaemonSet de Falco.

=== 3. Instalar Falco ===

helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm show chart falcosecurity/falco

helm install falco falcosecurity/falco --namespace falco --create-namespace -f entregable3/k8s/falco/falco-values.yaml

kubectl rollout status daemonset/falco -n falco
kubectl get pods -n falco

=== 4. Comprobar que Falco está capturando ===

kubectl logs -n falco daemonset/falco -c falco | Select-String "Falco version|falco_rules.yaml|Enabled event sources|modern BPF|ring buffer|iterators"

# Para ver Falco version, la carga de /etc/falco/falco_rules.yaml, Enabled event sources: syscall y Opening 'syscall' source with modern BPF probe.
# Una línea con disabled BPF iterators (not running in the root PID namespace...) es informativa y normal: Falco corre en el namespace de PIDs de su propio pod.
# Usa daemonset/falco y no -l app.kubernetes.io/name=falco a propósito: con selector, kubectl logs muestra solo 10 líneas por defecto.

=== 5. Ejecutar la acción sospechosa ===

# En la terminal A, dejar los logs en vivo:
kubectl logs -n falco daemonset/falco -c falco -f --tail=0

# En la terminal B, abrir la shell:
(Get-Date).ToUniversalTime().ToString("o")   # Falco registra la hora en UTC
$POD = kubectl get pods -l app=ci-validator-api -o jsonpath='{.items[0].metadata.name}'
kubectl exec -it $POD -- sh

# Dentro del contenedor (de paso se comprueba el endurecimiento):
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

# Vista legible de la alerta (la tabla de arriba sale de acá).
Get-Content $OUT | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object time, rule, priority,
  @{n='pod'; e={ $_.output_fields.'k8s.pod.name' }},
  @{n='namespace'; e={ $_.output_fields.'k8s.ns.name' }},
  @{n='uid'; e={ $_.output_fields.'user.uid' }},
  @{n='proceso'; e={ $_.output_fields.'proc.name' }},
  @{n='padre'; e={ $_.output_fields.'proc.pname' }},
  @{n='terminal'; e={ $_.output_fields.'proc.tty' }} | Format-List
```