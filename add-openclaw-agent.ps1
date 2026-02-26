# Instala Copilot-OpenClaw en un proyecto existente
#
# Uso:
#   .\add-openclaw-agent.ps1 [-Path <ruta>] [-Force]
#
# Si no se especifica Path, se toma el directorio de trabajo actual.
# El script invoca el gestor de skills (skills_manager.py) y crea
# los enlaces/copias necesarios para que el workspace use el agente.

param(
    [string]$Path = ".",
    [switch]$Force
)

# Resolver rutas (crear destino si no existe)
if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$targetDir = (Resolve-Path -Path $Path -ErrorAction Stop).Path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manager = Join-Path $scriptDir "skills_manager.py"

if (-not (Test-Path $manager)) {
    Write-Error "No se puede encontrar skills_manager.py en $scriptDir"
    exit 1
}

Write-Host "[add-openclaw-agent] instalando en: $targetDir"

# Construir comando
$python = "python"
# si existe venv local, preferirla
$venvPy = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $python = $venvPy }

if ($Force) {
    Write-Host "ejecutando: $python `"$manager`" install `"$targetDir`" --force"
    & $python $manager install $targetDir --force
} else {
    Write-Host "ejecutando: $python `"$manager`" install `"$targetDir`""
    & $python $manager install $targetDir
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "[add-openclaw-agent] OK agente ligado correctamente."
} else {
    Write-Error "[add-openclaw-agent] ERROR durante la instalacion (codigo $LASTEXITCODE)."
}
