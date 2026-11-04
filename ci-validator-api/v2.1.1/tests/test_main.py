from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cedula_valida_8_digitos():
    body = client.get("/ci/1.234.567-2").json()
    assert body["valid"] is True
    assert body["normalized_ci"] == "12345672"
    assert body["formatted_ci"] == "1.234.567-2"


def test_cedula_valida_7_digitos():
    body = client.get("/ci/123.456-1").json()
    assert body["valid"] is True
    assert body["normalized_ci"] == "01234561"


def test_digito_verificador_invalido():
    body = client.get("/ci/12345671").json()
    assert body["valid"] is False
    assert body["expected_check_digit"] == 2


def test_formato_invalido():
    for entrada in ("abc", "123"):
        body = client.get(f"/ci/{entrada}").json()
        assert body["valid"] is False
        assert body["normalized_ci"] is None


def test_metrics_expone_metrica_de_negocio():
    client.get("/ci/12345672")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'ci_validator_validations_total{result="valid"}' in response.text
    assert "ci_validator_http_requests_total" in response.text
