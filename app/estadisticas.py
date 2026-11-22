"""
Reporte de estadísticas de las predicciones realizadas.

Cada predicción queda exportada como una línea JSON en un archivo de texto
(por defecto registros/predicciones.jsonl; en el contenedor,
/app/registros/predicciones.jsonl). Este módulo lee ese archivo y calcula lo
que piden los médicos:

    * Número total de predicciones por cada categoría.
    * Últimas 5 predicciones realizadas (la más reciente primero).
    * Fecha de la última predicción.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from app.modelo import ESTADOS

NUMERO_ULTIMAS = 5


def calcular_estadisticas(ruta_registro: str | Path, numero_ultimas: int = NUMERO_ULTIMAS) -> dict[str, Any]:
    """Lee el registro de predicciones y retorna el reporte de estadísticas.

    Si el archivo todavía no existe (no se ha hecho ninguna predicción), retorna
    los valores por defecto: conteos en 0, lista vacía y fecha None. Las líneas
    dañadas se ignoran y se cuentan en "lineas_invalidas".
    """
    conteo: dict[str, int] = {estado: 0 for estado in ESTADOS}
    ultimas: deque[dict[str, Any]] = deque(maxlen=numero_ultimas)
    total = 0
    lineas_invalidas = 0

    ruta = Path(ruta_registro)
    if ruta.is_file():
        with ruta.open(encoding="utf-8") as archivo:
            for linea in archivo:
                if not linea.strip():
                    continue
                try:
                    registro = json.loads(linea)
                    estado = registro["estado"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    lineas_invalidas += 1
                    continue
                conteo[estado] = conteo.get(estado, 0) + 1
                total += 1
                ultimas.append(registro)

    # El archivo se escribe en orden cronológico: la última línea es la predicción más reciente.
    ultimas_predicciones = list(reversed(ultimas))
    return {
        "total_predicciones": total,
        "predicciones_por_categoria": conteo,
        "ultimas_predicciones": ultimas_predicciones,
        "fecha_ultima_prediccion": ultimas_predicciones[0].get("fecha_utc") if ultimas_predicciones else None,
        "lineas_invalidas": lineas_invalidas,
    }
