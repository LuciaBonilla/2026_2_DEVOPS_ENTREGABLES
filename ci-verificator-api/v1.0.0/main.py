"""
Validador de Cédula de Identidad Uruguaya (v1.0.0).
"""

# --- DEPENDENCIAS ---

import re

from fastapi import FastAPI
from pydantic import BaseModel


# --- METADATA DEL DEPLOYMENT ---

VERSION = "1.0.0"


# --- REGLAS DEL NEGOCIO ---

# Pesos utilizados por el DNIC uruguayo para calcular el dígito verificador a partir de la base.
CHECK_DIGIT_WEIGHTS = (2, 9, 8, 7, 6, 3, 4)
NON_DIGITS = re.compile(r"\D", re.ASCII)

MIN_DIGITS = 7 # Forma de presentación de cédula con 7 dígitos: xxx.xxx-x
MAX_DIGITS = 8 # Forma de presentación de cédula con 8 dígitos: x.xxx.xxx-x


app = FastAPI(title="Validador de Cédula de Identidad Uruguaya", version=VERSION)


class ValidationResult(BaseModel):
    input: str
    normalized_ci: str | None = None    # Forma canónica de la cédula (xxxxxxxx).
    valid: bool
    expected_check_digit: int | None = None
    message: str
    api_version: str = VERSION


def calculate_check_digit(base: str) -> int:
    """
    Calcula el dígito verificador a partir de la base de 7 dígitos.
    """
    total = 0
    for i in range(7):
        digit = int(base[i])
        weight = CHECK_DIGIT_WEIGHTS[i]
        total += digit * weight
    return (10 - (total % 10)) % 10


# --- ENDPOINTS ---

@app.get("/health")
def health() -> dict:
    return {
        "title":"Validador de Cédula de Identidad Uruguaya",
        "version": VERSION,
        "status": "ok"
    }


@app.get("/ci/{number}", response_model=ValidationResult)
def validate_ci(number: str) -> ValidationResult:
    digits = NON_DIGITS.sub("", number)     # Elimina todo carácter que no sea un dígito.

    # VALIDACIÓN 1: Sin dígitos.
    if not digits:
        return ValidationResult(
            input=number,
            valid=False,
            message="La entrada no contiene dígitos.",
        )

    # VALIDACIÓN 2: Número de dígitos fuera del rango.
    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
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

    return ValidationResult(
        input=number,
        normalized_ci=ci,
        valid=valid,
        expected_check_digit=expected_check_digit,
        message=(
            "Cédula válida."
            if valid
            else f"Dígito verificador inválido: se esperaba {expected_check_digit}, pero se ingresó {provided_check_digit}"
        ),
    )