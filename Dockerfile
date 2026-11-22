# =============================================================================
# Imagen Docker: servicio de predicción del estado de salud del paciente
#
# Construir:  docker build -t prediccion-enfermedades:1.1.0 .
# Ejecutar:   docker run -d --name prediccion-enfermedades -p 5000:5000 prediccion-enfermedades:1.1.0
# Usar:       http://localhost:5000  (web)   ·   POST http://localhost:5000/predecir  (API)
# =============================================================================

# 1. Imagen base oficial y liviana de Python
FROM python:3.12-slim

# 2. Metadatos de la imagen
LABEL org.opencontainers.image.title="prediccion-enfermedades" \
      org.opencontainers.image.description="Modelo simulado que predice NO ENFERMO o ENFERMEDAD LEVE, AGUDA, CRÓNICA o TERMINAL" \
      org.opencontainers.image.version="1.1.0"

# 3. Variables de entorno
#    - PYTHONDONTWRITEBYTECODE: no genera archivos .pyc
#    - PYTHONUNBUFFERED: los logs salen de inmediato (docker logs)
#    - PIP_*: no guarda caché de pip y omite la verificación de versión
#    - RUTA_REGISTRO_PREDICCIONES: archivo donde se guarda cada predicción (trazabilidad)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RUTA_REGISTRO_PREDICCIONES=/app/registros/predicciones.jsonl

# 4. Directorio de trabajo dentro del contenedor
WORKDIR /app

# 5. Instalar dependencias. Se copia primero solo requirements.txt para aprovechar
#    la caché de capas: si el código cambia pero las dependencias no, esta capa se reutiliza.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 6. Copiar el código fuente del servicio (modelo + servidor web + plantillas)
COPY app/ ./app/

# 7. Crear un usuario sin privilegios (buena práctica de seguridad) y la carpeta de registros
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/registros \
    && chown -R appuser:appuser /app/registros
USER appuser

# 8. Puerto en el que escucha el servicio
EXPOSE 5000

# 9. Verificación de salud: Docker marca el contenedor como "healthy" si /salud responde
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/salud', timeout=4)" || exit 1

# 10. Comando de arranque: gunicorn (servidor WSGI de producción) con 2 workers
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app.servidor:app"]
