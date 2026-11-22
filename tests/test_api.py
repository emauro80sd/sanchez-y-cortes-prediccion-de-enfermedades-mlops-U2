"""Pruebas de integración del servicio web / API (cliente de pruebas de Flask)."""

import json

import pytest

from app.modelo import EJEMPLOS, ENFERMEDAD_AGUDA, ENFERMEDAD_LEVE, ESTADOS
from app.servidor import app


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_REGISTRO_PREDICCIONES", str(tmp_path / "predicciones.jsonl"))
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_salud(cliente):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.get_json()["estado"] == "ok"


@pytest.mark.parametrize("estado", ESTADOS)
def test_post_json_retorna_cada_estado(cliente, estado):
    respuesta = cliente.post("/predecir", json=EJEMPLOS[estado])
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["estado"] == estado
    assert cuerpo["id_prediccion"]


def test_respuesta_json_conserva_tildes(cliente):
    respuesta = cliente.post("/predecir", json=EJEMPLOS["ENFERMEDAD CRÓNICA"])
    assert "CRÓNICA" in respuesta.get_data(as_text=True)


def test_get_con_parametros_en_la_url(cliente):
    respuesta = cliente.get("/predecir", query_string=EJEMPLOS[ENFERMEDAD_LEVE])
    assert respuesta.status_code == 200
    assert respuesta.get_json()["estado"] == ENFERMEDAD_LEVE


def test_post_formulario_urlencoded_en_la_api(cliente):
    respuesta = cliente.post("/predecir", data=EJEMPLOS[ENFERMEDAD_AGUDA])
    assert respuesta.get_json()["estado"] == ENFERMEDAD_AGUDA


def test_datos_invalidos_retornan_400_con_detalles(cliente):
    respuesta = cliente.post("/predecir", json={"temperatura": 80})
    assert respuesta.status_code == 400
    cuerpo = respuesta.get_json()
    assert cuerpo["error"] == "Datos de entrada inválidos"
    assert len(cuerpo["detalles"]) == 5


def test_cuerpo_vacio_o_json_malformado_retorna_400(cliente):
    assert cliente.post("/predecir").status_code == 400
    assert cliente.post("/predecir", data="{no es json", content_type="application/json").status_code == 400


def test_registra_cada_prediccion_en_archivo(cliente, tmp_path):
    cliente.post("/predecir", json=EJEMPLOS[ENFERMEDAD_AGUDA])
    lineas = (tmp_path / "predicciones.jsonl").read_text(encoding="utf-8").splitlines()
    registro = json.loads(lineas[-1])
    assert registro["estado"] == ENFERMEDAD_AGUDA
    assert registro["canal"] == "api"


def test_pagina_web_muestra_formulario(cliente):
    respuesta = cliente.get("/")
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "<form" in html and 'name="temperatura"' in html


def test_formulario_web_muestra_resultado(cliente):
    datos = {k: str(v) for k, v in EJEMPLOS[ENFERMEDAD_AGUDA].items()}
    html = cliente.post("/", data=datos).get_data(as_text=True)
    assert "ENFERMEDAD AGUDA" in html
    assert "estado-aguda" in html


def test_formulario_web_muestra_errores(cliente):
    html = cliente.post("/", data={"temperatura": "99"}).get_data(as_text=True)
    assert "Revise los datos ingresados" in html


def test_ejemplos(cliente):
    assert set(cliente.get("/ejemplos").get_json()) == set(ESTADOS)


def test_documentacion_swagger(cliente):
    assert cliente.get("/apidocs/").status_code == 200
    especificacion = cliente.get("/apispec_1.json").get_json()
    assert "/predecir" in especificacion["paths"]


def test_ruta_inexistente_retorna_404_json(cliente):
    respuesta = cliente.get("/no-existe")
    assert respuesta.status_code == 404
    assert "rutas_disponibles" in respuesta.get_json()
