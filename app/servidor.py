"""
Servicio web que expone el modelo simulado al médico.

Rutas:
    GET  /            Formulario web para ingresar los datos del paciente
    POST /            Procesa el formulario y muestra el resultado
    POST /predecir    API REST: recibe JSON y retorna el estado del paciente
    GET  /predecir    API REST: igual que POST, con parámetros en la URL
    GET  /ejemplos    Datos de ejemplo que producen cada uno de los 4 estados
    GET  /salud       Health check (lo usa el HEALTHCHECK del Dockerfile)
    GET  /apidocs     Documentación interactiva (Swagger UI)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from flasgger import Swagger
from flask import Flask, jsonify, render_template, request

from app.modelo import (
    ESTADOS,
    EJEMPLOS,
    VARIABLES,
    VERSION_MODELO,
    ErrorValidacion,
    evaluar_paciente,
)

app = Flask(__name__)
app.json.ensure_ascii = False  # muestra "CRÓNICA" y no "CRÓNICA"
app.json.sort_keys = False

app.config["SWAGGER"] = {
    "title": "API · Predicción del estado de salud del paciente",
    "uiversion": 3,
    "description": (
        "Servicio que simula un modelo de ML: recibe 5 valores clínicos y retorna "
        "NO ENFERMO, ENFERMEDAD LEVE, ENFERMEDAD AGUDA o ENFERMEDAD CRÓNICA. "
        "Simulación académica, no apta para uso clínico real."
    ),
    "version": VERSION_MODELO,
}
Swagger(app)

# --------------------------------------------------------------------------
# Registro de predicciones (trazabilidad y datos para monitoreo / re-entrenamiento)
# --------------------------------------------------------------------------
log_predicciones = logging.getLogger("predicciones")
log_predicciones.setLevel(logging.INFO)
log_predicciones.propagate = False
if not log_predicciones.handlers:
    _consola = logging.StreamHandler(sys.stdout)
    _consola.setFormatter(logging.Formatter("%(message)s"))
    log_predicciones.addHandler(_consola)


def registrar_prediccion(resultado: dict[str, Any], canal: str) -> str:
    """Escribe la predicción en stdout (y en un archivo JSONL si está configurado). Retorna su id."""
    id_prediccion = str(uuid.uuid4())
    registro = {
        "id_prediccion": id_prediccion,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canal": canal,
        "version_modelo": resultado["version_modelo"],
        "entrada": resultado["entrada"],
        "estado": resultado["estado"],
        "puntaje_severidad": resultado["puntaje_severidad"],
    }
    linea = json.dumps(registro, ensure_ascii=False)
    log_predicciones.info(linea)

    ruta = os.environ.get("RUTA_REGISTRO_PREDICCIONES")
    if ruta:
        try:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            with open(ruta, "a", encoding="utf-8") as archivo:
                archivo.write(linea + "\n")
        except OSError as error:  # el registro nunca debe impedir la predicción
            app.logger.warning("No se pudo escribir el registro de predicciones: %s", error)
    return id_prediccion


def _predecir(datos: Mapping[str, Any], canal: str) -> dict[str, Any]:
    resultado = evaluar_paciente(datos)
    resultado["id_prediccion"] = registrar_prediccion(resultado, canal)
    return resultado


def _error_validacion(error: ErrorValidacion):
    return jsonify({"error": "Datos de entrada inválidos", "detalles": error.errores}), 400


# --------------------------------------------------------------------------
# Interfaz web para el médico
# --------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def inicio():
    resultado, errores = None, []
    valores = request.form.to_dict() if request.method == "POST" else {}
    if request.method == "POST":
        try:
            resultado = _predecir(valores, canal="web")
        except ErrorValidacion as error:
            errores = error.errores
    return render_template(
        "index.html",
        variables=VARIABLES,
        valores=valores,
        resultado=resultado,
        errores=errores,
        ejemplos=EJEMPLOS,
        version=VERSION_MODELO,
    )


# --------------------------------------------------------------------------
# API REST
# --------------------------------------------------------------------------
@app.post("/predecir")
def predecir_post():
    """Predice el estado de salud del paciente (datos en JSON)
    ---
    tags:
      - Predicción
    consumes:
      - application/json
    parameters:
      - in: body
        name: paciente
        required: true
        schema:
          $ref: '#/definitions/Paciente'
    responses:
      200:
        description: Estado predicho y su explicación
        schema:
          $ref: '#/definitions/Resultado'
      400:
        description: Datos de entrada faltantes o fuera de rango
    definitions:
      Paciente:
        type: object
        required: [temperatura, frecuencia_cardiaca, saturacion_oxigeno, intensidad_dolor, dias_sintomas]
        properties:
          temperatura:
            type: number
            description: Temperatura corporal en °C (30 a 45)
            example: 39.8
          frecuencia_cardiaca:
            type: integer
            description: Latidos por minuto en reposo (20 a 250)
            example: 128
          saturacion_oxigeno:
            type: integer
            description: Saturación de oxígeno SpO2 en % (50 a 100)
            example: 89
          intensidad_dolor:
            type: integer
            description: Intensidad del dolor o malestar (0 a 10)
            example: 8
          dias_sintomas:
            type: integer
            description: Días con síntomas (0 a 3650)
            example: 3
      Resultado:
        type: object
        properties:
          estado:
            type: string
            enum: [NO ENFERMO, ENFERMEDAD LEVE, ENFERMEDAD AGUDA, ENFERMEDAD CRÓNICA]
          puntaje_severidad:
            type: integer
          puntaje_maximo:
            type: integer
          puntajes_por_variable:
            type: object
          signos_de_alarma:
            type: array
            items:
              type: string
          recomendacion:
            type: string
          entrada:
            type: object
          version_modelo:
            type: string
          id_prediccion:
            type: string
    """
    datos = request.get_json(silent=True)
    if datos is None and request.form:
        datos = request.form.to_dict()
    try:
        return jsonify(_predecir(datos, canal="api"))
    except ErrorValidacion as error:
        return _error_validacion(error)


@app.get("/predecir")
def predecir_get():
    """Predice el estado de salud del paciente (parámetros en la URL)
    ---
    tags:
      - Predicción
    parameters:
      - {name: temperatura, in: query, type: number, required: true, description: "°C (30 a 45)", default: 37.9}
      - {name: frecuencia_cardiaca, in: query, type: integer, required: true, description: "lpm (20 a 250)", default: 92}
      - {name: saturacion_oxigeno, in: query, type: integer, required: true, description: "% (50 a 100)", default: 97}
      - {name: intensidad_dolor, in: query, type: integer, required: true, description: "0 a 10", default: 3}
      - {name: dias_sintomas, in: query, type: integer, required: true, description: "días (0 a 3650)", default: 2}
    responses:
      200:
        description: Estado predicho y su explicación
        schema:
          $ref: '#/definitions/Resultado'
      400:
        description: Datos de entrada faltantes o fuera de rango
    """
    try:
        return jsonify(_predecir(request.args.to_dict(), canal="api"))
    except ErrorValidacion as error:
        return _error_validacion(error)


@app.get("/ejemplos")
def ejemplos():
    """Datos de ejemplo que producen cada uno de los 4 estados
    ---
    tags:
      - Utilidades
    responses:
      200:
        description: Un ejemplo de entrada por cada estado
    """
    return jsonify(EJEMPLOS)


@app.get("/salud")
def salud():
    """Health check del servicio
    ---
    tags:
      - Utilidades
    responses:
      200:
        description: El servicio está funcionando
    """
    return jsonify({"estado": "ok", "version_modelo": VERSION_MODELO, "estados_posibles": list(ESTADOS)})


@app.errorhandler(404)
def no_encontrado(_error):
    return jsonify({"error": "Ruta no encontrada", "rutas_disponibles": ["/", "/predecir", "/ejemplos", "/salud", "/apidocs"]}), 404


@app.errorhandler(405)
def metodo_no_permitido(_error):
    return jsonify({"error": "Método HTTP no permitido para esta ruta"}), 405


if __name__ == "__main__":
    # Solo para desarrollo local. En el contenedor se usa gunicorn (ver Dockerfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PUERTO", "5000")), debug=False)
