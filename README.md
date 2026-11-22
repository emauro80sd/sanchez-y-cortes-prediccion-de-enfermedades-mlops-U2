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

## Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `README.md` | Este documento: problema, propósito, estructura e instrucciones de uso |
| `app/` | Función del modelo simulado y servicio web / API (Flask) |
| `tests/` | Pruebas unitarias y de integración (pytest) |
| `ejemplos/` | Entradas de ejemplo y scripts para probar la API |
| `Dockerfile`, `docker-compose.yml` | Construcción y ejecución de la imagen de Docker |
| `.github/workflows/` | Pipeline de CI/CD con GitHub Actions |

## Flujo de trabajo

* `main` es la rama principal y contiene siempre la versión estable de la solución.
* Cada cambio se desarrolla en su propia rama y entra a `main` mediante un pull request:
    * `solución-inicial`: archivos de la Unidad 1.
    * Una rama por cada nuevo requerimiento de los médicos.
    * `añadir-github-actions`: pipeline de CI/CD.

> Proyecto académico: el modelo es una simulación y no debe usarse para diagnóstico médico real.
