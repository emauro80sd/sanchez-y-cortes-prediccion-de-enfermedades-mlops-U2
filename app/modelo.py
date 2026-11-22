"""
Modelo simulado para predecir el estado de salud de un paciente.

No es un modelo de ML entrenado: es una función basada en reglas que imita
la salida del modelo real descrito en el pipeline de la Parte 1. Recibe 5
valores clínicos y retorna uno de 4 estados:

    NO ENFERMO | ENFERMEDAD LEVE | ENFERMEDAD AGUDA | ENFERMEDAD CRÓNICA

Lógica de decisión:
    1. Cada signo o síntoma recibe un puntaje de 0 (normal) a 3 (alarma).
    2. Puntaje total = 0             -> NO ENFERMO
    3. Síntomas por >= 90 días       -> ENFERMEDAD CRÓNICA
    4. Total >= 5 o algún puntaje 3  -> ENFERMEDAD AGUDA
    5. En otro caso                  -> ENFERMEDAD LEVE

AVISO: es una simulación con fines académicos. No sirve como diagnóstico médico.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

VERSION_MODELO = "1.0.0"

NO_ENFERMO = "NO ENFERMO"
ENFERMEDAD_LEVE = "ENFERMEDAD LEVE"
ENFERMEDAD_AGUDA = "ENFERMEDAD AGUDA"
ENFERMEDAD_CRONICA = "ENFERMEDAD CRÓNICA"

ESTADOS = (NO_ENFERMO, ENFERMEDAD_LEVE, ENFERMEDAD_AGUDA, ENFERMEDAD_CRONICA)

# Desde cuántos días con síntomas se considera crónica la enfermedad (3 meses).
DIAS_CRONICIDAD = 90
# Puntaje total desde el cual el cuadro se considera agudo.
UMBRAL_AGUDA = 5
# Puntaje de una variable que se considera signo de alarma.
PUNTAJE_ALARMA = 3

# Definición de las variables de entrada: rango válido, unidad y si debe ser entera.
VARIABLES: dict[str, dict[str, Any]] = {
    "temperatura": {
        "descripcion": "Temperatura corporal",
        "unidad": "°C",
        "minimo": 30.0,
        "maximo": 45.0,
        "entero": False,
    },
    "frecuencia_cardiaca": {
        "descripcion": "Frecuencia cardiaca en reposo",
        "unidad": "latidos por minuto",
        "minimo": 20,
        "maximo": 250,
        "entero": True,
    },
    "saturacion_oxigeno": {
        "descripcion": "Saturación de oxígeno (SpO2)",
        "unidad": "%",
        "minimo": 50,
        "maximo": 100,
        "entero": True,
    },
    "intensidad_dolor": {
        "descripcion": "Intensidad del dolor o malestar",
        "unidad": "escala 0-10",
        "minimo": 0,
        "maximo": 10,
        "entero": True,
    },
    "dias_sintomas": {
        "descripcion": "Días con síntomas",
        "unidad": "días",
        "minimo": 0,
        "maximo": 3650,
        "entero": True,
    },
}

RECOMENDACIONES = {
    NO_ENFERMO: "Sin hallazgos de enfermedad. Continuar con controles de rutina.",
    ENFERMEDAD_LEVE: (
        "Cuadro leve. Manejo ambulatorio y sintomático; volver a evaluar "
        "si los síntomas empeoran o no mejoran en 48-72 horas."
    ),
    ENFERMEDAD_AGUDA: (
        "Cuadro agudo con signos de severidad. Requiere valoración médica "
        "prioritaria y considerar atención de urgencias."
    ),
    ENFERMEDAD_CRONICA: (
        "Síntomas persistentes (90 días o más). Estudiar una posible enfermedad "
        "crónica o huérfana y considerar remitir al especialista."
    ),
}


class ErrorValidacion(ValueError):
    """Se lanza cuando los datos de entrada del médico no son válidos."""

    def __init__(self, errores: list[str]):
        super().__init__("; ".join(errores))
        self.errores = errores


# --------------------------------------------------------------------------
# Puntajes por variable: 0 = normal, 1 = leve, 2 = moderado, 3 = alarma
# --------------------------------------------------------------------------
def puntaje_temperatura(t: float) -> int:
    if t >= 39.5 or t < 35.0:
        return 3
    if t >= 38.5:
        return 2
    if t >= 37.5 or t < 36.0:
        return 1
    return 0


def puntaje_frecuencia_cardiaca(fc: float) -> int:
    if fc > 140 or fc < 40:
        return 3
    if fc > 120 or fc < 50:
        return 2
    if fc > 100 or fc < 60:
        return 1
    return 0


def puntaje_saturacion(spo2: float) -> int:
    if spo2 < 88:
        return 3
    if spo2 < 92:
        return 2
    if spo2 < 95:
        return 1
    return 0


def puntaje_dolor(dolor: float) -> int:
    if dolor >= 7:
        return 3
    if dolor >= 4:
        return 2
    if dolor >= 1:
        return 1
    return 0


# --------------------------------------------------------------------------
# Validación de la entrada
# --------------------------------------------------------------------------
def _a_numero(nombre: str, valor: Any) -> float:
    """Convierte el valor a número. Acepta coma decimal (p. ej. "38,5")."""
    if isinstance(valor, bool):
        raise ValueError(f"'{nombre}' debe ser numérico, no booleano")
    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str) and valor.strip():
        try:
            numero = float(valor.strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"'{nombre}' debe ser un número (se recibió '{valor}')") from None
    else:
        raise ValueError(f"'{nombre}' es obligatorio")
    if math.isnan(numero) or math.isinf(numero):
        raise ValueError(f"'{nombre}' debe ser un número finito")
    return numero


def validar_entrada(datos: Mapping[str, Any] | None) -> dict[str, float]:
    """Valida y convierte los 5 valores de entrada. Lanza ErrorValidacion con todos los errores."""
    if not isinstance(datos, Mapping):
        raise ErrorValidacion(["El cuerpo de la solicitud debe ser un objeto JSON con los datos del paciente"])

    errores: list[str] = []
    limpios: dict[str, float] = {}
    for nombre, regla in VARIABLES.items():
        if nombre not in datos or datos[nombre] is None or datos[nombre] == "":
            errores.append(f"'{nombre}' es obligatorio ({regla['descripcion']}, {regla['unidad']})")
            continue
        try:
            numero = _a_numero(nombre, datos[nombre])
        except ValueError as e:
            errores.append(str(e))
            continue
        if regla["entero"] and not numero.is_integer():
            errores.append(f"'{nombre}' debe ser un número entero")
            continue
        if not regla["minimo"] <= numero <= regla["maximo"]:
            errores.append(
                f"'{nombre}' debe estar entre {regla['minimo']} y {regla['maximo']} {regla['unidad']} "
                f"(se recibió {datos[nombre]})"
            )
            continue
        limpios[nombre] = int(numero) if regla["entero"] else numero

    if errores:
        raise ErrorValidacion(errores)
    return limpios


# --------------------------------------------------------------------------
# Función del modelo
# --------------------------------------------------------------------------
def predecir_estado(
    temperatura: float,
    frecuencia_cardiaca: float,
    saturacion_oxigeno: float,
    intensidad_dolor: float,
    dias_sintomas: float,
) -> str:
    """Retorna el estado del paciente: NO ENFERMO, ENFERMEDAD LEVE, AGUDA o CRÓNICA.

    Ejemplo:
        >>> predecir_estado(36.8, 72, 98, 0, 0)
        'NO ENFERMO'
        >>> predecir_estado(39.8, 128, 89, 8, 3)
        'ENFERMEDAD AGUDA'
    """
    return evaluar_paciente(
        {
            "temperatura": temperatura,
            "frecuencia_cardiaca": frecuencia_cardiaca,
            "saturacion_oxigeno": saturacion_oxigeno,
            "intensidad_dolor": intensidad_dolor,
            "dias_sintomas": dias_sintomas,
        }
    )["estado"]


def evaluar_paciente(datos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida los datos, calcula los puntajes y retorna el estado con su explicación."""
    x = validar_entrada(datos)

    puntajes = {
        "temperatura": puntaje_temperatura(x["temperatura"]),
        "frecuencia_cardiaca": puntaje_frecuencia_cardiaca(x["frecuencia_cardiaca"]),
        "saturacion_oxigeno": puntaje_saturacion(x["saturacion_oxigeno"]),
        "intensidad_dolor": puntaje_dolor(x["intensidad_dolor"]),
    }
    total = sum(puntajes.values())
    signos_alarma = [nombre for nombre, p in puntajes.items() if p >= PUNTAJE_ALARMA]

    if total == 0:
        estado = NO_ENFERMO
    elif x["dias_sintomas"] >= DIAS_CRONICIDAD:
        estado = ENFERMEDAD_CRONICA
    elif total >= UMBRAL_AGUDA or signos_alarma:
        estado = ENFERMEDAD_AGUDA
    else:
        estado = ENFERMEDAD_LEVE

    recomendacion = RECOMENDACIONES[estado]
    if estado == ENFERMEDAD_CRONICA and signos_alarma:
        recomendacion += " Hay signos de alarma: descartar una descompensación aguda."

    return {
        "estado": estado,
        "puntaje_severidad": total,
        "puntaje_maximo": 3 * len(puntajes),
        "puntajes_por_variable": puntajes,
        "signos_de_alarma": signos_alarma,
        "recomendacion": recomendacion,
        "entrada": x,
        "version_modelo": VERSION_MODELO,
    }


# Ejemplos de entrada que producen cada uno de los 4 estados (los usan la web, la API y las pruebas).
EJEMPLOS: dict[str, dict[str, float]] = {
    NO_ENFERMO: {
        "temperatura": 36.8,
        "frecuencia_cardiaca": 72,
        "saturacion_oxigeno": 98,
        "intensidad_dolor": 0,
        "dias_sintomas": 0,
    },
    ENFERMEDAD_LEVE: {
        "temperatura": 37.9,
        "frecuencia_cardiaca": 92,
        "saturacion_oxigeno": 97,
        "intensidad_dolor": 3,
        "dias_sintomas": 2,
    },
    ENFERMEDAD_AGUDA: {
        "temperatura": 39.8,
        "frecuencia_cardiaca": 128,
        "saturacion_oxigeno": 89,
        "intensidad_dolor": 8,
        "dias_sintomas": 3,
    },
    ENFERMEDAD_CRONICA: {
        "temperatura": 37.0,
        "frecuencia_cardiaca": 84,
        "saturacion_oxigeno": 95,
        "intensidad_dolor": 5,
        "dias_sintomas": 180,
    },
}
