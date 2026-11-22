"""Pruebas de la función del modelo simulado."""

import itertools

import pytest

from app.modelo import (
    EJEMPLOS,
    ENFERMEDAD_AGUDA,
    ENFERMEDAD_CRONICA,
    ENFERMEDAD_LEVE,
    ENFERMEDAD_TERMINAL,
    ESTADOS,
    NO_ENFERMO,
    ErrorValidacion,
    evaluar_paciente,
    predecir_estado,
)


def paciente(**cambios):
    """Paciente sano de referencia, al que se le cambian algunos valores."""
    base = dict(EJEMPLOS[NO_ENFERMO])
    base.update(cambios)
    return base


# --- La función puede retornar cada uno de los 5 estados ---------------------
@pytest.mark.parametrize("estado_esperado", ESTADOS)
def test_cada_estado_tiene_un_ejemplo_que_lo_produce(estado_esperado):
    assert predecir_estado(**EJEMPLOS[estado_esperado]) == estado_esperado


def test_los_cinco_estados_son_alcanzables():
    obtenidos = {predecir_estado(**datos) for datos in EJEMPLOS.values()}
    assert len(ESTADOS) == 5
    assert obtenidos == set(ESTADOS)


# --- Nueva categoría: ENFERMEDAD TERMINAL -----------------------------------
def test_paciente_cronico_con_compromiso_severo_es_terminal():
    # 240 días con síntomas; temperatura 38.9 (2), FC 132 (2), SpO2 84 (3), dolor 9 (3) => total 10
    resultado = evaluar_paciente(EJEMPLOS[ENFERMEDAD_TERMINAL])
    assert resultado["estado"] == ENFERMEDAD_TERMINAL
    assert resultado["puntaje_severidad"] == 10
    assert "paliativos" in resultado["recomendacion"]


def test_limite_terminal_puntaje_7_es_cronica_y_8_es_terminal():
    # temperatura 39.6 (3) + SpO2 86 (3) + FC 105 (1) => total 7
    cronica = evaluar_paciente(paciente(temperatura=39.6, saturacion_oxigeno=86, frecuencia_cardiaca=105, dias_sintomas=120))
    assert (cronica["puntaje_severidad"], cronica["estado"]) == (7, ENFERMEDAD_CRONICA)
    # + dolor 2 (1) => total 8
    terminal = evaluar_paciente(paciente(temperatura=39.6, saturacion_oxigeno=86, frecuencia_cardiaca=105,
                                         intensidad_dolor=2, dias_sintomas=120))
    assert (terminal["puntaje_severidad"], terminal["estado"]) == (8, ENFERMEDAD_TERMINAL)


def test_compromiso_severo_sin_cronicidad_es_aguda_no_terminal():
    # Mismos signos que el ejemplo terminal, pero solo 10 días de evolución.
    resultado = evaluar_paciente({**EJEMPLOS[ENFERMEDAD_TERMINAL], "dias_sintomas": 10})
    assert resultado["estado"] == ENFERMEDAD_AGUDA


# --- Reglas de decisión y casos límite ------------------------------------
def test_sin_hallazgos_es_no_enfermo_aunque_reporte_dias():
    assert evaluar_paciente(paciente(dias_sintomas=200))["estado"] == NO_ENFERMO


def test_limite_de_cronicidad_en_90_dias():
    assert evaluar_paciente(paciente(intensidad_dolor=2, dias_sintomas=89))["estado"] == ENFERMEDAD_LEVE
    assert evaluar_paciente(paciente(intensidad_dolor=2, dias_sintomas=90))["estado"] == ENFERMEDAD_CRONICA


def test_puntaje_4_es_leve_y_puntaje_5_es_aguda():
    # temperatura 38.6 -> 2, dolor 5 -> 2  => total 4
    leve = evaluar_paciente(paciente(temperatura=38.6, intensidad_dolor=5, dias_sintomas=2))
    assert (leve["puntaje_severidad"], leve["estado"]) == (4, ENFERMEDAD_LEVE)
    # + frecuencia cardiaca 105 -> 1  => total 5
    aguda = evaluar_paciente(paciente(temperatura=38.6, intensidad_dolor=5, frecuencia_cardiaca=105, dias_sintomas=2))
    assert (aguda["puntaje_severidad"], aguda["estado"]) == (5, ENFERMEDAD_AGUDA)


def test_un_solo_signo_de_alarma_es_aguda():
    resultado = evaluar_paciente(paciente(saturacion_oxigeno=85, dias_sintomas=1))
    assert resultado["estado"] == ENFERMEDAD_AGUDA
    assert resultado["signos_de_alarma"] == ["saturacion_oxigeno"]


def test_cronica_con_signos_de_alarma_lo_advierte():
    resultado = evaluar_paciente(paciente(temperatura=39.9, dias_sintomas=120))
    assert resultado["estado"] == ENFERMEDAD_CRONICA
    assert "signos de alarma" in resultado["recomendacion"]


def test_hipotermia_y_bradicardia_puntuan_como_alarma():
    assert evaluar_paciente(paciente(temperatura=34.5))["puntajes_por_variable"]["temperatura"] == 3
    assert evaluar_paciente(paciente(frecuencia_cardiaca=35))["puntajes_por_variable"]["frecuencia_cardiaca"] == 3


def test_siempre_retorna_un_estado_valido():
    combinaciones = itertools.product(
        [34.0, 36.5, 37.8, 38.8, 40.0],  # temperatura
        [35, 55, 80, 110, 150],          # frecuencia cardiaca
        [85, 90, 93, 98],                # saturación
        [0, 2, 5, 9],                    # dolor
        [0, 10, 90, 400],                # días
    )
    for t, fc, spo2, dolor, dias in combinaciones:
        assert predecir_estado(t, fc, spo2, dolor, dias) in ESTADOS


def test_estructura_de_la_respuesta():
    resultado = evaluar_paciente(EJEMPLOS[ENFERMEDAD_AGUDA])
    assert set(resultado) >= {
        "estado", "puntaje_severidad", "puntaje_maximo", "puntajes_por_variable",
        "signos_de_alarma", "recomendacion", "entrada", "version_modelo",
    }
    assert resultado["puntaje_maximo"] == 12
    assert 0 <= resultado["puntaje_severidad"] <= resultado["puntaje_maximo"]


# --- Validación de la entrada ---------------------------------------------
def test_acepta_texto_y_coma_decimal():
    datos = {k: str(v) for k, v in EJEMPLOS[ENFERMEDAD_LEVE].items()}
    datos["temperatura"] = "37,9"
    assert evaluar_paciente(datos)["estado"] == ENFERMEDAD_LEVE


@pytest.mark.parametrize(
    "cambio, fragmento",
    [
        ({"temperatura": None}, "'temperatura' es obligatorio"),
        ({"temperatura": 50}, "'temperatura' debe estar entre"),
        ({"saturacion_oxigeno": 101}, "'saturacion_oxigeno' debe estar entre"),
        ({"intensidad_dolor": 11}, "'intensidad_dolor' debe estar entre"),
        ({"intensidad_dolor": 4.5}, "'intensidad_dolor' debe ser un número entero"),
        ({"dias_sintomas": -1}, "'dias_sintomas' debe estar entre"),
        ({"frecuencia_cardiaca": "rápida"}, "'frecuencia_cardiaca' debe ser un número"),
        ({"frecuencia_cardiaca": True}, "no booleano"),
        ({"temperatura": float("nan")}, "número finito"),
    ],
)
def test_rechaza_entradas_invalidas(cambio, fragmento):
    with pytest.raises(ErrorValidacion) as error:
        evaluar_paciente(paciente(**cambio))
    assert any(fragmento in e for e in error.value.errores)


def test_reporta_todos_los_campos_faltantes_a_la_vez():
    with pytest.raises(ErrorValidacion) as error:
        evaluar_paciente({})
    assert len(error.value.errores) == 5


def test_rechaza_cuerpo_que_no_es_objeto():
    with pytest.raises(ErrorValidacion):
        evaluar_paciente([36.5, 70, 98, 0, 0])
