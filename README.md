# Predicción de enfermedades en pacientes · MLOps (Unidad 2)

* **Integrantes:** Edgar Mauricio Sanchez Duran y Juan Camilo Cortes Jaramillo
* **Curso:** MLOps · Maestría en Inteligencia Artificial Aplicada · Universidad Icesi

## El problema

En medicina hay mucha información de los pacientes, pero en las enfermedades poco comunes (llamadas **huérfanas**) los datos escasean. Se necesita un modelo que, a partir de los síntomas y signos de un paciente, estime si es posible que sufra una enfermedad y en qué estado se encuentra. Debe funcionar tanto para enfermedades comunes (muchos datos) como para enfermedades huérfanas (pocos datos).

En la Unidad 1 se construyó una **solución local para el médico**: una función que simula el modelo de predicción, expuesta como servicio web y API REST dentro de una imagen de Docker.

## Propósito del repositorio

Este repositorio mantiene el **control de versiones** de esa solución y su evolución:

1. Versionar el código del modelo simulado, el servicio y la imagen de Docker.
2. Incorporar nuevos requerimientos de los médicos mediante **ramas y pull requests** hacia `main`.
3. Automatizar las pruebas, la construcción de la imagen y su publicación en GitHub Packages con un pipeline de **CI/CD en GitHub Actions**.

## Flujo de trabajo

* `main` es la rama principal y contiene siempre la versión estable de la solución.
* Cada cambio se desarrolla en su propia rama y entra a `main` mediante un pull request:
    * `solución-inicial`: archivos de la Unidad 1.
    * Una rama por cada nuevo requerimiento de los médicos.
    * `añadir-github-actions`: pipeline de CI/CD.

> ⚠️ Proyecto académico: el modelo es una **simulación** (no es un modelo entrenado) y **no sirve como diagnóstico médico**.

---

# Servicio de predicción del estado de salud del paciente (Docker)

Imagen de Docker con un **modelo simulado**. A partir de 5 datos clínicos del paciente, el servicio retorna uno de estos 5 estados:

| Estado | Significado |
|---|---|
| `NO ENFERMO` | Sin hallazgos anormales |
| `ENFERMEDAD LEVE` | Hallazgos leves, de corta duración |
| `ENFERMEDAD AGUDA` | Hallazgos severos o signos de alarma, de corta duración |
| `ENFERMEDAD CRÓNICA` | Síntomas persistentes durante 90 días o más |
| `ENFERMEDAD TERMINAL` | Síntomas persistentes (90 días o más) con compromiso severo de varios signos a la vez *(nueva categoría, modelo v1.1.0)* |

## 1. Finalidad de la solución

Es un prototipo del componente **«Servicio de predicción»** del pipeline de MLOps propuesto en la Unidad 1. Su objetivo es que un médico pueda **lanzar el modelo en su propio equipo con Docker** y consultarlo de dos maneras:

* **Página web** (`http://localhost:5000`): un formulario donde el médico ingresa los datos y ve el estado, la recomendación y la explicación del resultado.
* **API REST** (`POST /predecir`): para integrarlo con otros sistemas, como una historia clínica electrónica. Tiene documentación interactiva Swagger en `/apidocs`.

Cada predicción se registra con un identificador único (trazabilidad). Esos registros son los datos que alimentarían el monitoreo y el re-entrenamiento del pipeline de MLOps.

## 2. Estructura del repositorio

```text
.
├── README.md               # Este archivo
├── Dockerfile              # Instrucciones para construir la imagen
├── .dockerignore           # Archivos que no entran a la imagen
├── .gitignore              # Archivos que no se versionan
├── docker-compose.yml      # (Extra) Construir y correr con un solo comando
├── requirements.txt        # Dependencias de ejecución (Flask, flasgger, gunicorn)
├── requirements-dev.txt    # Dependencias de pruebas (pytest)
├── pytest.ini              # Configuración de las pruebas
├── app/
│   ├── __init__.py
│   ├── modelo.py           # ★ Función del modelo simulado (predecir_estado / evaluar_paciente)
│   ├── servidor.py         # Servicio Flask: web, API REST, Swagger y health check
│   ├── templates/
│   │   └── index.html      # Formulario web para el médico
│   └── static/
│       └── estilos.css     # Estilos de la página
├── ejemplos/
│   ├── 1_no_enfermo.json           # Un ejemplo de entrada por cada estado
│   ├── 2_enfermedad_leve.json
│   ├── 3_enfermedad_aguda.json
│   ├── 4_enfermedad_cronica.json
│   ├── 5_enfermedad_terminal.json
│   ├── probar_api.sh               # Prueba los ejemplos (Linux / macOS / Git Bash)
│   └── probar_api.ps1              # Prueba los ejemplos (Windows PowerShell)
└── tests/
    ├── test_modelo.py      # Pruebas de la función (estados, límites y validaciones)
    └── test_api.py         # Pruebas de integración de la web y la API
```

## 3. El modelo simulado

### 3.1 Datos de entrada (5 valores)

| Campo (JSON) | Descripción | Unidad | Rango válido |
|---|---|---|---|
| `temperatura` | Temperatura corporal | °C | 30 a 45 (admite decimales) |
| `frecuencia_cardiaca` | Frecuencia cardiaca en reposo | latidos por minuto | 20 a 250 (entero) |
| `saturacion_oxigeno` | Saturación de oxígeno (SpO₂) | % | 50 a 100 (entero) |
| `intensidad_dolor` | Intensidad del dolor o malestar | escala 0-10 | 0 a 10 (entero) |
| `dias_sintomas` | Días con síntomas | días | 0 a 3650 (entero) |

Los 5 campos son obligatorios. Si alguno falta o está fuera de rango, el servicio responde con **HTTP 400** y la lista de errores.

### 3.2 Lógica de decisión

**Paso 1.** Cada signo recibe un puntaje de 0 (normal) a 3 (alarma):

| Puntaje | Temperatura (°C) | Frecuencia cardiaca (lpm) | SpO₂ (%) | Dolor (0-10) |
|:---:|---|---|---|---|
| **0** | 36,0 a 37,4 | 60 a 100 | 95 o más | 0 |
| **1** | 37,5 a 38,4, o 35,0 a 35,9 | 101 a 120, o 50 a 59 | 92 a 94 | 1 a 3 |
| **2** | 38,5 a 39,4 | 121 a 140, o 40 a 49 | 88 a 91 | 4 a 6 |
| **3** (alarma) | 39,5 o más, o menos de 35,0 | más de 140, o menos de 40 | menos de 88 | 7 a 10 |

**Paso 2.** Con el puntaje total (de 0 a 12) y los días con síntomas, se aplican estas reglas en orden:

1. Si el puntaje total es **0**, el estado es **`NO ENFERMO`**.
2. Si hay síntomas desde hace **90 días o más** y el puntaje total es **8 o más**, el estado es **`ENFERMEDAD TERMINAL`**: es un cuadro persistente con compromiso severo de varios signos a la vez.
3. Si hay síntomas desde hace **90 días o más** (con puntaje menor a 8), el estado es **`ENFERMEDAD CRÓNICA`**. Si además hay signos de alarma, la recomendación lo advierte.
4. Si el puntaje total es **5 o más**, o algún signo tiene puntaje **3**, el estado es **`ENFERMEDAD AGUDA`**.
5. En cualquier otro caso, el estado es **`ENFERMEDAD LEVE`**.

> En una solución real, agregar la categoría `ENFERMEDAD TERMINAL` implicaría re-entrenar el modelo con datos etiquetados de esa clase. En esta simulación basta con la nueva regla 2 de la función.

### 3.3 Ejemplos que producen cada estado

| Ejemplo | Temp. | FC | SpO₂ | Dolor | Días | Puntaje | **Estado** |
|---|---|---|---|---|---|---|---|
| `1_no_enfermo.json` | 36,8 | 72 | 98 | 0 | 0 | 0 | **NO ENFERMO** |
| `2_enfermedad_leve.json` | 37,9 | 92 | 97 | 3 | 2 | 2 | **ENFERMEDAD LEVE** |
| `3_enfermedad_aguda.json` | 39,8 | 128 | 89 | 8 | 3 | 10 | **ENFERMEDAD AGUDA** |
| `4_enfermedad_cronica.json` | 37,0 | 84 | 95 | 5 | 180 | 2 | **ENFERMEDAD CRÓNICA** |
| `5_enfermedad_terminal.json` | 38,9 | 132 | 84 | 9 | 240 | 10 | **ENFERMEDAD TERMINAL** |

### 3.4 Uso directo de la función (Python)

```python
from app.modelo import predecir_estado, evaluar_paciente

predecir_estado(temperatura=39.8, frecuencia_cardiaca=128, saturacion_oxigeno=89,
                intensidad_dolor=8, dias_sintomas=3)
# 'ENFERMEDAD AGUDA'

evaluar_paciente({"temperatura": 37.0, "frecuencia_cardiaca": 84, "saturacion_oxigeno": 95,
                  "intensidad_dolor": 5, "dias_sintomas": 180})["estado"]
# 'ENFERMEDAD CRÓNICA'
```

## 4. Requisitos previos

* **Docker** instalado y en ejecución:
    * Windows o macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop/).
    * Linux: Docker Engine.
* Comprobar la instalación:

    ```bash
    docker --version
    ```

* Clonar este repositorio y abrir una terminal **en su raíz**, que es donde está el `Dockerfile`:

    ```bash
    git clone https://github.com/emauro80sd/sanchez-y-cortes-prediccion-de-enfermedades-mlops-U2.git
    cd sanchez-y-cortes-prediccion-de-enfermedades-mlops-U2
    ```

No hace falta instalar Python: todo corre dentro del contenedor.

## 5. Construir la imagen (`docker build`)

```bash
docker build -t prediccion-enfermedades:1.1.0 .
```

* `-t prediccion-enfermedades:1.1.0` le da a la imagen un nombre y una versión.
* El `.` final indica que el contexto de construcción es la carpeta actual.

Para verificar que la imagen existe:

```bash
docker images prediccion-enfermedades
```

**¿Qué hace el Dockerfile?**

1. Parte de la imagen oficial `python:3.12-slim`.
2. Define variables de entorno: sin archivos `.pyc` y con logs inmediatos.
3. Instala las dependencias de `requirements.txt`. Se copia primero ese archivo para aprovechar la caché de capas.
4. Copia el código de `app/`.
5. Crea un usuario sin privilegios (`appuser`) y ejecuta el servicio con él.
6. Expone el puerto `5000`.
7. Define un `HEALTHCHECK` contra `/salud`.
8. Arranca el servicio con **gunicorn**, un servidor WSGI de producción, con 2 workers.

## 6. Correr el contenedor (`docker run`)

```bash
docker run -d --name prediccion-enfermedades -p 5000:5000 prediccion-enfermedades:1.1.0
```

* `-d` corre el contenedor en segundo plano.
* `--name` le asigna un nombre fácil de recordar.
* `-p 5000:5000` mapea el puerto 5000 del equipo al puerto 5000 del contenedor.

Para comprobar que el servicio está arriba, ejecute el siguiente comando. Tras unos segundos, la columna `STATUS` debe mostrar `(healthy)`:

```bash
docker ps --filter name=prediccion-enfermedades
```

Para ver los logs del servicio y de cada predicción:

```bash
docker logs -f prediccion-enfermedades
```

**Opciones útiles:**

* **El puerto 5000 está ocupado** (en macOS suele usarlo AirPlay). Use otro puerto del equipo, por ejemplo 8080, y abra `http://localhost:8080`:

    ```bash
    docker run -d --name prediccion-enfermedades -p 8080:5000 prediccion-enfermedades:1.1.0
    ```

* **Conservar el registro de predicciones** aunque se elimine el contenedor (volumen de Docker):

    ```bash
    docker run -d --name prediccion-enfermedades -p 5000:5000 -v registros_prediccion:/app/registros prediccion-enfermedades:1.1.0
    ```

### Alternativa: Docker Compose (construye y corre en un solo paso)

```bash
docker compose up --build -d
```

Para detenerlo:

```bash
docker compose down
```

## 7. Obtener predicciones del modelo

### 7.1 Página web (recomendado para el médico)

1. Abra **http://localhost:5000** en el navegador.
2. Escriba los 5 valores, o use los botones **«Cargar ejemplo»** para llenar los datos de cada estado.
3. Haga clic en **«Obtener predicción»**.

La página muestra el estado, la recomendación, el puntaje de severidad y el puntaje de cada variable.

### 7.2 API REST: `POST /predecir` con JSON

**Linux / macOS / Git Bash:**

```bash
curl -X POST http://localhost:5000/predecir \
     -H "Content-Type: application/json" \
     -d '{"temperatura": 39.8, "frecuencia_cardiaca": 128, "saturacion_oxigeno": 89, "intensidad_dolor": 8, "dias_sintomas": 3}'
```

**Windows PowerShell:**

```powershell
$paciente = @{ temperatura = 39.8; frecuencia_cardiaca = 128; saturacion_oxigeno = 89; intensidad_dolor = 8; dias_sintomas = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:5000/predecir -ContentType "application/json" -Body $paciente
```

**Con un archivo de ejemplo** (en PowerShell escriba `curl.exe` en lugar de `curl`):

```bash
curl -X POST http://localhost:5000/predecir -H "Content-Type: application/json" --data @ejemplos/3_enfermedad_aguda.json
```

**Respuesta (HTTP 200):**

```json
{
  "estado": "ENFERMEDAD AGUDA",
  "puntaje_severidad": 10,
  "puntaje_maximo": 12,
  "puntajes_por_variable": {"temperatura": 3, "frecuencia_cardiaca": 2, "saturacion_oxigeno": 2, "intensidad_dolor": 3},
  "signos_de_alarma": ["temperatura", "intensidad_dolor"],
  "recomendacion": "Cuadro agudo con signos de severidad. Requiere valoración médica prioritaria y considerar atención de urgencias.",
  "entrada": {"temperatura": 39.8, "frecuencia_cardiaca": 128, "saturacion_oxigeno": 89, "intensidad_dolor": 8, "dias_sintomas": 3},
  "version_modelo": "1.1.0",
  "id_prediccion": "cfd8952e-7bad-4e83-bd7d-1ed8cdb5b042"
}
```

**Respuesta con datos inválidos (HTTP 400):**

```json
{
  "error": "Datos de entrada inválidos",
  "detalles": [
    "'temperatura' debe estar entre 30.0 y 45.0 °C (se recibió 50)",
    "'saturacion_oxigeno' es obligatorio (Saturación de oxígeno (SpO2), %)"
  ]
}
```

### 7.3 API REST: `GET /predecir` (desde el navegador)

Abra esta dirección en el navegador o con `curl`. Retorna `ENFERMEDAD CRÓNICA`:

```text
http://localhost:5000/predecir?temperatura=37&frecuencia_cardiaca=84&saturacion_oxigeno=95&intensidad_dolor=5&dias_sintomas=180
```

### 7.4 Documentación interactiva (Swagger)

Abra **http://localhost:5000/apidocs**. Allí puede ver el esquema de entrada y salida y probar cada endpoint con el botón *Try it out*.

### 7.5 Probar todos los estados de una vez

**Linux / macOS / Git Bash:**

```bash
bash ejemplos/probar_api.sh
```

**Windows PowerShell:**

```powershell
powershell -ExecutionPolicy Bypass -File .\ejemplos\probar_api.ps1
```

Salida esperada (PowerShell):

```text
1_no_enfermo.json            -> NO ENFERMO           (puntaje 0/12)
2_enfermedad_leve.json       -> ENFERMEDAD LEVE      (puntaje 2/12)
3_enfermedad_aguda.json      -> ENFERMEDAD AGUDA     (puntaje 10/12)
4_enfermedad_cronica.json    -> ENFERMEDAD CRÓNICA   (puntaje 2/12)
5_enfermedad_terminal.json   -> ENFERMEDAD TERMINAL  (puntaje 10/12)
```

### 7.6 Resumen de endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Formulario web para el médico |
| `POST` | `/` | Envía el formulario y muestra el resultado |
| `POST` | `/predecir` | Predicción con un cuerpo JSON (también acepta datos de formulario) |
| `GET` | `/predecir?...` | Predicción con parámetros en la URL |
| `GET` | `/ejemplos` | Un ejemplo de entrada por cada estado |
| `GET` | `/salud` | Health check, que usa el `HEALTHCHECK` de Docker |
| `GET` | `/apidocs` | Documentación Swagger UI |

## 8. Registro de predicciones (trazabilidad)

Cada predicción se escribe como una línea JSON en los logs del contenedor y en `/app/registros/predicciones.jsonl`. Cada línea incluye el id, la fecha, el canal (web o API), la versión del modelo, la entrada y el estado.

Para consultar el archivo:

```bash
docker exec prediccion-enfermedades cat /app/registros/predicciones.jsonl
```

## 9. Pruebas automáticas (opcional, sin Docker)

Requiere Python 3.10 o superior. Desde la raíz del repositorio:

```bash
python -m pip install -r requirements-dev.txt
```

```bash
python -m pytest -v
```

Las 47 pruebas verifican lo siguiente:

* Que la función retorne **cada uno de los 5 estados**.
* Los casos límite: 89 frente a 90 días, puntaje 4 frente a 5 (aguda) y puntaje 7 frente a 8 (terminal).
* La validación de las entradas.
* Las respuestas de la web, la API, el registro y Swagger.

Para correr el servicio sin Docker (solo en desarrollo):

```bash
python -m app.servidor
```

## 10. Detener y limpiar

Detener el contenedor:

```bash
docker stop prediccion-enfermedades
```

Eliminar el contenedor:

```bash
docker rm prediccion-enfermedades
```

Eliminar la imagen (opcional):

```bash
docker rmi prediccion-enfermedades:1.1.0
```

## 11. Solución de problemas

| Problema | Solución |
|---|---|
| `Cannot connect to the Docker daemon` / `error during connect` | Docker Desktop no está abierto. Ábralo y espere a que diga *Engine running*. |
| `port is already allocated` | El puerto 5000 está ocupado. Use `-p 8080:5000` y abra `http://localhost:8080`. |
| `Conflict. The container name ... is already in use` | Ya existe un contenedor con ese nombre. Ejecute `docker rm -f prediccion-enfermedades` y vuelva a correrlo. |
| La página no carga recién iniciado el contenedor | Espere unos segundos y revise `docker logs prediccion-enfermedades`. |
| En PowerShell, `curl` no acepta `-X` o `-H` | En PowerShell `curl` es un alias de `Invoke-WebRequest`. Use `curl.exe` o el ejemplo con `Invoke-RestMethod`. |
