# Envía los 4 ejemplos (uno por estado) a la API y muestra el estado retornado.
# Uso:  .\ejemplos\probar_api.ps1                         (usa http://localhost:5000)
#       .\ejemplos\probar_api.ps1 -Url http://localhost:8080
# Funciona en Windows PowerShell 5.1 y en PowerShell 7+.
param([string]$Url = "http://localhost:5000")

Get-ChildItem -Path $PSScriptRoot -Filter *.json | Sort-Object Name | ForEach-Object {
    $cuerpo = [System.IO.File]::ReadAllBytes($_.FullName)
    $respuesta = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$Url/predecir" `
        -ContentType "application/json" -Body $cuerpo
    # Se decodifica como UTF-8 para que las tildes (CRÓNICA) se vean bien en cualquier versión.
    $resultado = [System.Text.Encoding]::UTF8.GetString($respuesta.RawContentStream.ToArray()) | ConvertFrom-Json
    "{0,-28} -> {1,-20} (puntaje {2}/{3})" -f $_.Name, $resultado.estado, $resultado.puntaje_severidad, $resultado.puntaje_maximo
}
