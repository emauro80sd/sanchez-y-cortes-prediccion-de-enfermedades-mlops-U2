"""Pruebas del reporte de estadísticas de las predicciones."""

import json

import pytest

from app.estadisticas import calcular_estadisticas
from app.modelo import (
    EJEMPLOS,
    ENFERMEDAD_AGUDA,
    ENFERMEDAD_CRONICA,
    ENFERMEDAD_LEVE,
    ENFERMEDAD_TERMINAL,
    ESTADOS,
    NO_ENFERMO,
)
from app.servidor import app


@pytest.fixture()
def registro(tmp_path, monkeypatch):
    """Cada prueba usa un archivo de registro nuevo y vacío."""
    ruta = tmp_path / "registros" / "predicciones.jsonl"
    monkeypatch.setenv("RUTA_REGISTRO_PREDICCIONES", str(ruta))
    return ruta


@pytest.fixture()
def cliente(registro):
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def predecir(cliente, estado):
    respuesta = cliente.post("/predecir", json=EJEMPLOS[estado])
    assert respuesta.status_code == 200
    return respuesta.get_json()


# --- Antes de cualquier predicción: valores por defecto ---------------------
def test_estadisticas_vacias_antes_de_cualquier_prediccion(cliente, registro):
    assert not registro.exists()
    reporte = cliente.get("/estadisticas").get_json()
    assert reporte["total_predicciones"] == 0
    assert reporte["predicciones_por_categoria"] == {estado: 0 for estado in ESTADOS}
    assert reporte["ultimas_predicciones"] == []
    assert reporte["fecha_ultima_prediccion"] is None


# --- Después de predecir: la última predicción es la esperada ---------------
def test_la_ultima_prediccion_del_reporte_es_la_esperada(cliente):
    resultado = predecir(cliente, ENFERMEDAD_TERMINAL)
    reporte = cliente.get("/estadisticas").get_json()
    ultima = reporte["ultimas_predicciones"][0]
    assert ultima["estado"] == ENFERMEDAD_TERMINAL
    assert ultima["id_prediccion"] == resultado["id_prediccion"]
    assert ultima["entrada"] == EJEMPLOS[ENFERMEDAD_TERMINAL]
    assert reporte["fecha_ultima_prediccion"] == ultima["fecha_utc"]


def test_cuenta_las_predicciones_por_categoria(cliente):
    for estado in [NO_ENFERMO, ENFERMEDAD_LEVE, ENFERMEDAD_AGUDA, ENFERMEDAD_AGUDA, ENFERMEDAD_CRONICA, ENFERMEDAD_TERMINAL]:
        predecir(cliente, estado)
    reporte = cliente.get("/estadisticas").get_json()
    assert reporte["total_predicciones"] == 6
    assert reporte["predicciones_por_categoria"] == {
        NO_ENFERMO: 1,
        ENFERMEDAD_LEVE: 1,
        ENFERMEDAD_AGUDA: 2,
        ENFERMEDAD_CRONICA: 1,
        ENFERMEDAD_TERMINAL: 1,
    }


def test_retorna_solo_las_ultimas_5_la_mas_reciente_primero(cliente):
    orden = [NO_ENFERMO, ENFERMEDAD_LEVE, ENFERMEDAD_AGUDA, ENFERMEDAD_CRONICA, ENFERMEDAD_TERMINAL, NO_ENFERMO, ENFERMEDAD_LEVE]
    ids = [predecir(cliente, estado)["id_prediccion"] for estado in orden]
    ultimas = cliente.get("/estadisticas").get_json()["ultimas_predicciones"]
    assert len(ultimas) == 5
    assert [p["id_prediccion"] for p in ultimas] == list(reversed(ids[-5:]))
    assert [p["estado"] for p in ultimas] == list(reversed(orden[-5:]))


def test_las_predicciones_desde_la_web_tambien_cuentan(cliente):
    datos = {k: str(v) for k, v in EJEMPLOS[ENFERMEDAD_CRONICA].items()}
    cliente.post("/", data=datos)
    reporte = cliente.get("/estadisticas").get_json()
    assert reporte["predicciones_por_categoria"][ENFERMEDAD_CRONICA] == 1
    assert reporte["ultimas_predicciones"][0]["canal"] == "web"


def test_las_solicitudes_invalidas_no_se_registran(cliente):
    cliente.post("/predecir", json={"temperatura": 80})
    assert cliente.get("/estadisticas").get_json()["total_predicciones"] == 0


# --- Lectura del archivo de texto -----------------------------------------
def test_ignora_lineas_danadas_del_registro(registro):
    registro.parent.mkdir(parents=True)
    valida = {"id_prediccion": "a1", "fecha_utc": "2026-11-20T10:00:00+00:00", "estado": ENFERMEDAD_LEVE}
    registro.write_text("no es json\n" + json.dumps(valida) + "\n\n{\"sin_estado\": 1}\n", encoding="utf-8")
    reporte = calcular_estadisticas(registro)
    assert reporte["total_predicciones"] == 1
    assert reporte["lineas_invalidas"] == 2
    assert reporte["fecha_ultima_prediccion"] == "2026-11-20T10:00:00+00:00"


# --- Página web del reporte -------------------------------------------------
def test_pagina_de_reporte_sin_predicciones(cliente):
    html = cliente.get("/reporte").get_data(as_text=True)
    assert "Reporte de predicciones" in html
    assert "Aún no se han realizado predicciones" in html


def test_pagina_de_reporte_muestra_las_estadisticas(cliente):
    predecir(cliente, ENFERMEDAD_AGUDA)
    predecir(cliente, ENFERMEDAD_TERMINAL)
    html = cliente.get("/reporte").get_data(as_text=True)
    assert "Total de predicciones" in html
    assert "ENFERMEDAD TERMINAL" in html
    assert "Últimas 5 predicciones" in html
    assert " UTC" in html  # fecha de la última predicción
