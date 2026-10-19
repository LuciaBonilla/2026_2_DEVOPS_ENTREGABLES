"""
Validador de Cédula de Identidad Uruguaya (v2.1.0).

Cambio v2.1.0: Métricas para Prometheus.
  - Endpoint GET /metrics con el formato de exposición de Prometheus.
  - Métrica de negocio:
    ci_validator_validations_total{result}.
  - Métricas HTTP: 
    ci_validator_http_requests_total{method, route, status},
    ci_validator_http_request_duration_seconds{method, route} y
    ci_validator_http_requests_in_progress{method, route}.

Cambio v2.0.0: Nuevo campo de respuesta "formatted_ci",
representando la cédula en la formade presentación xxx.xxx-x/x.xxx.xxx-x.
"""

# --- DEPENDENCIAS ---

import re
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (  # NUEVO v2.1.0
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    disable_created_metrics,
    generate_latest,
)
from pydantic import BaseModel
from starlette.routing import Match  # NUEVO v2.1.0



# --- METADATA DEL DEPLOYMENT ---

VERSION = "2.1.0"



# --- REGLAS DEL NEGOCIO ---

# Pesos utilizados por el DNIC uruguayo para calcular el dígito verificador a partir de la base.
CHECK_DIGIT_WEIGHTS = (2, 9, 8, 7, 6, 3, 4)
NON_DIGITS = re.compile(r"\D", re.ASCII)

# Forma de presentación de cédula con 7 dígitos: xxx.xxx-x
# Forma canónica de cédula con 7 dígitos: 0xxxxxxx (-> 8 números, el primero 0)
MIN_DIGITS = 7

# Forma de presentación de cédula con 8 dígitos: x.xxx.xxx-x
# Forma canónica de cédula con 8 dígitos: xxxxxxxx (-> 8 números, el primero distinto de 0)
MAX_DIGITS = 8 


app = FastAPI(title="Validador de Cédula de Identidad Uruguaya", version=VERSION)


class ValidationResult(BaseModel):
    input: str                                  
    normalized_ci: str | None = None            # Forma canónica de la cédula (xxxxxxxx).
    formatted_ci: str | None = None             # NUEVO v2.0.0. Forma de presentación de cédula (xxx.xxx-x o x.xxx.xxx-x).
    valid: bool                                 # Indica si la cédula es válida.
    expected_check_digit: int | None = None     # Dígito verificador esperado dada la base.
    message: str                                # Mensaje.
    api_version: str = VERSION                  # Versión de la API.


def calculate_check_digit(base: str) -> int:
    """
    Calcula el dígito verificador de la cédula a partir de la base de 7 dígitos.
    """
    total = 0
    for i in range(7):
        digit = int(base[i])
        weight = CHECK_DIGIT_WEIGHTS[i]
        total += digit * weight
    return (10 - (total % 10)) % 10


def format_ci(ci: str) -> str:  # NUEVO v2.0.0
    """
    Renderiza la forma canónica (xxxxxxxx) a la forma de presentación (xxx.xxx-x o x.xxx.xxx-x),
    convención utilizada en Uruguay.
    """
    base, check_digit = ci[:-1], ci[-1]
    return f"{int(base):,}".replace(",", ".") + f"-{check_digit}"



# --- MÉTRICAS ---  NUEVO v2.1.0

# Para no exponer las series auxiliares *_created (timestaps que indican la fecha de nacimiento de una métrica).
# Las series auxiliares *_created solo inflan el volumen, así que las desactivamos.
disable_created_metrics()

 
# Métricas del negocio:

# Contador de validaciones de cédula por resultado.
# Validar es la "operación" sobre la que se define la alerta "más de X operaciones en Y minutos".
# Se expone como ci_validator_validations_total (la librería agrega el sufijo _total).
CI_VALIDATIONS = Counter(
    name="ci_validator_validations",
    documentation="Cantidad de validaciones de cédula procesadas, por resultado.",
    labelnames=["result"],
)
 
# Una serie por cada resultado posible de una validación.
# labels() crea la serie con valor 0 (Prometheus la ve desde el primer scrape) y devuelve el
# objeto que la representa. Usar estos objetos en lugar de escribir el texto del resultado en
# cada .inc() evita que un error de tipeo cree una serie nueva.
VALIDATIONS_VALID = CI_VALIDATIONS.labels(result="valid")
VALIDATIONS_INVALID_CHECK_DIGIT = CI_VALIDATIONS.labels(result="invalid_check_digit")
VALIDATIONS_INVALID_FORMAT = CI_VALIDATIONS.labels(result="invalid_format")

 
# Métricas HTTP (tráfico, errores, latencia y saturación):

# Tráfico y errores: Contador de peticiones HTTP atendidas, por método, ruta y status.
HTTP_REQUESTS = Counter(
    name="ci_validator_http_requests",
    documentation="Cantidad de peticiones HTTP atendidas, por método, ruta y código de estado.",
    labelnames=["method", "route", "status"],
)
 
# Latencia: Duración de las peticiones HTTP, por método y ruta.
# Los buckets son los límites superiores (en milisegundos) de cada rango;
# están concentrados entre 0ms y 20ms, donde se espera la latencia de esta API simple.
HTTP_REQUEST_DURATION = Histogram(
    name="ci_validator_http_request_duration_seconds",
    documentation="Duración del procesamiento de las peticiones HTTP, en milisegundos.",
    labelnames=["method", "route"],
    buckets=(2.5, 5.0, 7.5, 10, 12.5, 15.0, 17.5, 20.0),
)
 
# Saturación: Cantidad de peticiones que se están procesando en este instante, por método y ruta.
# Gauge es como un contador, pero que puede además puede decrecer o cambiarse arbitrariamente su valor.
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    name="ci_validator_http_requests_in_progress",
    documentation="Peticiones HTTP que se están procesando en este momento.",
    labelnames=["method", "route"],
)


METRICS_PATH = "/metrics"
HEALTH_PATH = "/health"

# Rutas excluidas de las métricas HTTP. Ninguna es tráfico de usuarios:
#   - /metrics: lo consulta Prometheus periódicamente.
#   - /health: lo consultan las sondas de Kubernetes (readiness/liveness) cada pocos segundos.
# Incluirlas inflaría el tráfico medido y diluiría la tasa de errores y la latencia agregadas.
# Las fallas de /health igual quedan registradas: Kubernetes las reporta como eventos del pod.

EXCLUDED_PATHS = frozenset({METRICS_PATH, HEALTH_PATH})

# Métodos HTTP aceptados como valor de etiqueta; cualquier otro se registra como "OTHER".
# La API solo expone endpoints GET, así que todo otro método es tráfico inválido (405).
# Si se agrega un endpoint con otro método (por ejemplo, POST), hay que sumarlo aquí.
KNOWN_METHODS = frozenset({"GET"})
 
 
def get_route_template(request: Request) -> str:
    """
    Devuelve la plantilla de la ruta que atiende la petición ("/ci/{number}"), no la URL
    real (ej. "/ci/12345672"): con la URL real cada cédula crearía una serie nueva.
    Recorre las rutas de la app y pregunta a cada una si coincide.
    Si ninguna ruta coincide (404 o 405) devuelve "unmatched".
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL: # Coincidencia de URL y método HTTP.
            return route.path
    return "unmatched"


# --- MIDDLEWARE DE MÉTRICAS HTTP ---  NUEVO v2.1.0

# Un middleware envuelve todas las peticiones, así que hay que tocar muy poco cada endpoint.
 
@app.middleware("http")
async def prometheus_http_metrics(request: Request, call_next) -> Response:
    # Las rutas excluidas se atienden normalmente, pero sin medirlas.
    if request.url.path in EXCLUDED_PATHS:
        return await call_next(request)
 
    method = request.method if request.method in KNOWN_METHODS else "OTHER"
    route = get_route_template(request)
 
    in_progress = HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route)
    in_progress.inc()
    start = time.perf_counter()

    status_code = 500  # Si el endpoint lanza una excepción no controlada, la respuesta será 500 (error del servidor).
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        # Se ejecuta siempre, también si hubo una excepción.
        duration = time.perf_counter() - start
        HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(duration)
        HTTP_REQUESTS.labels(method=method, route=route, status=str(status_code)).inc()
        in_progress.dec()



# --- ENDPOINTS ---

@app.get(HEALTH_PATH)
def health() -> dict:
    return {
        "title":"Validador de Cédula de Identidad Uruguaya",
        "version": VERSION,
        "status": "ok"
    }


@app.get(METRICS_PATH, include_in_schema=False)  # NUEVO v2.1.0
def metrics() -> Response:
    # include_in_schema=False lo saca de /docs, ya que es un endpoint de infraestructura que no debería ir ahí.
    # generate_latest() serializa el registro global de la librería.
    # Ahí se registran automáticamente las métricas que creamos y también las por defecto.
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/ci/{number}", response_model=ValidationResult)
def validate_ci(number: str) -> ValidationResult:
    digits = NON_DIGITS.sub("", number)     # Elimina todo carácter que no sea un dígito.

    # VALIDACIÓN 1: Tiene dígitos.
    if not digits:
        VALIDATIONS_INVALID_FORMAT.inc()  # NUEVO v2.1.0
        return ValidationResult(
            input=number,
            valid=False,
            message="La entrada no contiene dígitos.",
        )

    # VALIDACIÓN 2: Cantidad de dígitos dentro del rango.
    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
        VALIDATIONS_INVALID_FORMAT.inc()  # NUEVO v2.1.0
        return ValidationResult(
            input=number,
            valid=False,
            message=(
                f"Cantidad de dígitos inválida: ({len(digits)}); "
                f"se espera entre {MIN_DIGITS} y {MAX_DIGITS} dígitos."
            ),
        )

    ci = digits.zfill(8)    # Relleno para cédula de 7 dígitos (queda 0xxxxxxx)
    base, provided_check_digit = ci[:7], int(ci[7])
    expected_check_digit = calculate_check_digit(base)
    valid = provided_check_digit == expected_check_digit

    if valid:  # NUEVO v2.1.0
        VALIDATIONS_VALID.inc()
    else:
        VALIDATIONS_INVALID_CHECK_DIGIT.inc()

    return ValidationResult(
        input=number,
        normalized_ci=ci,
        formatted_ci=format_ci(ci),  # NUEVO v2.0.0
        valid=valid,
        expected_check_digit=expected_check_digit,
        message=(
            "Cédula válida."
            if valid
            else f"Dígito verificador inválido: se esperaba {expected_check_digit}, "
            f"pero se ingresó {provided_check_digit}"
        ),
    )