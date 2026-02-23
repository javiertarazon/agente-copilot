<#
.SYNOPSIS
    Instala el agente OpenClaw (963 skills) en un proyecto VS Code.

.DESCRIPTION
    Configura GitHub Copilot para usar los 963 skills de OpenClaw en el proyecto
    actual o en la ruta especificada. Crea symlinks en .github/ y opcionalmente
    actualiza los settings de VS Code del usuario.

.PARAMETER ProjectPath
    Ruta del proyecto donde instalar. Por defecto: directorio actual.

.PARAMETER AgentPath
    Ruta del repositorio agente-copilot. Por defecto: detecta automáticamente.

.PARAMETER UpdateUserSettings
    Si se especifica, actualiza settings.json de VS Code del usuario para
    que TODOS los proyectos usen OpenClaw automáticamente.

.EXAMPLE
    # Instalar en el proyecto actual
    .\setup-project.ps1

.EXAMPLE
    # Instalar en un proyecto específico
    .\setup-project.ps1 -ProjectPath "D:\mis-proyectos\mi-app"

.EXAMPLE
    # Configurar VS Code globalmente (una sola vez)
    .\setup-project.ps1 -UpdateUserSettings
#>

param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$AgentPath   = "",
    [switch]$UpdateUserSettings
)

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/javiertarazon/agente-copilot.git"

# ─── Funciones helper ────────────────────────────────────────────────────────

function Write-Step($msg) { Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-WARN($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-ERR($msg)  { Write-Host "  ❌ $msg" -ForegroundColor Red }

function Create-SymlinkOrCopy($src, $dst, $isDir = $false) {
    if (Test-Path $dst) {
        Write-WARN "Ya existe: $dst (omitido)"
        return
    }
    try {
        if ($isDir) {
            New-Item -ItemType SymbolicLink -Path $dst -Target $src -Force | Out-Null
        } else {
            New-Item -ItemType SymbolicLink -Path $dst -Target $src -Force | Out-Null
        }
        Write-OK "Symlink: $dst → $src"
    } catch {
        # Fallback: copiar si no hay permisos para symlinks
        if ($isDir) {
            Copy-Item -Recurse -Path $src -Destination $dst
        } else {
            Copy-Item -Path $src -Destination $dst
        }
        Write-WARN "Copiado (sin symlink): $dst"
    }
}

# ─── Detectar ruta del agente ─────────────────────────────────────────────────

Write-Step "Detectando repositorio OpenClaw..."

if (-not $AgentPath) {
    # Intentar detectar por ubicación común del script
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (Test-Path "$scriptDir\.github\copilot-instructions.md") {
        $AgentPath = $scriptDir
    }
}

if (-not $AgentPath -or -not (Test-Path "$AgentPath\.github\copilot-instructions.md")) {
    # Buscar en ubicaciones comunes
    $candidates = @(
        "D:\agente-copilot",
        "D:\javie\agente coplit tipo open claw con skill",
        "$env:USERPROFILE\agente-copilot",
        "$env:USERPROFILE\Documents\agente-copilot"
    )
    foreach ($c in $candidates) {
        if (Test-Path "$c\.github\copilot-instructions.md") {
            $AgentPath = $c
            break
        }
    }
}

if (-not $AgentPath -or -not (Test-Path "$AgentPath\.github\copilot-instructions.md")) {
    Write-WARN "No se encontró el repositorio localmente."
    $clone = Read-Host "  ¿Clonar desde GitHub? (Esto puede tardar) [S/n]"
    if ($clone -ne "n") {
        $AgentPath = "$env:USERPROFILE\agente-copilot"
        Write-Step "Clonando en $AgentPath ..."
        git clone $REPO_URL $AgentPath
    } else {
        Write-ERR "Necesitas el repositorio para continuar. Clona manualmente:"
        Write-Host "  git clone $REPO_URL" -ForegroundColor Yellow
        exit 1
    }
}

Write-OK "Agente encontrado en: $AgentPath"

# ─── Verificar proyecto destino ───────────────────────────────────────────────

Write-Step "Configurando proyecto: $ProjectPath"

if (-not (Test-Path $ProjectPath)) {
    Write-ERR "El directorio no existe: $ProjectPath"
    exit 1
}

$githubDir = Join-Path $ProjectPath ".github"
if (-not (Test-Path $githubDir)) {
    New-Item -ItemType Directory -Path $githubDir | Out-Null
    Write-OK "Creado: .github/"
}

# ─── Crear symlinks en el proyecto ───────────────────────────────────────────

Write-Step "Enlazando instrucciones y skills..."

# copilot-instructions.md
Create-SymlinkOrCopy `
    (Join-Path $AgentPath ".github\copilot-instructions.md") `
    (Join-Path $githubDir "copilot-instructions.md")

# agents/
$agentsDir = Join-Path $githubDir "agents"
Create-SymlinkOrCopy `
    (Join-Path $AgentPath ".github\agents") `
    $agentsDir `
    $true

# instructions/ (opcional)
$instrDir = Join-Path $githubDir "instructions"
if (-not (Test-Path $instrDir)) {
    $link = Read-Host "  ¿Enlazar también instrucciones por categoría? [S/n]"
    if ($link -ne "n") {
        Create-SymlinkOrCopy `
            (Join-Path $AgentPath ".github\instructions") `
            $instrDir `
            $true
    }
}

# ─── Actualizar settings de VS Code del usuario ───────────────────────────────

if ($UpdateUserSettings) {
    Write-Step "Actualizando settings globales de VS Code..."

    $settingsPath = "$env:APPDATA\Code\User\settings.json"
    if (-not (Test-Path $settingsPath)) {
        Write-WARN "No se encontró settings.json en: $settingsPath"
    } else {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json

        # Asegurar que la clave existe
        if (-not $settings.PSObject.Properties["github.copilot.chat.codeGeneration.instructions"]) {
            $settings | Add-Member -NotePropertyName "github.copilot.chat.codeGeneration.instructions" -NotePropertyValue @()
        }

        $instructionFile = ($AgentPath -replace "\\", "/") + "/.github/copilot-instructions.md"
        $alreadyAdded = $settings."github.copilot.chat.codeGeneration.instructions" | Where-Object { $_.file -eq $instructionFile }

        if (-not $alreadyAdded) {
            $newEntry = [PSCustomObject]@{ file = $instructionFile }
            $settings."github.copilot.chat.codeGeneration.instructions" += $newEntry
            $settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath
            Write-OK "Instrucciones globales añadidas a settings.json"
        } else {
            Write-OK "Las instrucciones globales ya estaban configuradas"
        }

        # chat.agentFilesLocations
        $agentPath_fwd = ($AgentPath -replace "\\", "/") + "/.github/agents"
        if (-not $settings.PSObject.Properties["chat.agentFilesLocations"]) {
            $settings | Add-Member -NotePropertyName "chat.agentFilesLocations" -NotePropertyValue @()
        }
        $alreadyAgent = $settings."chat.agentFilesLocations" | Where-Object { $_ -eq $agentPath_fwd }
        if (-not $alreadyAgent) {
            $settings."chat.agentFilesLocations" += $agentPath_fwd
            $settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath
            Write-OK "AgentFilesLocations añadido en settings.json"
        }

        # Flags básicos
        $flags = @{
            "github.copilot.chat.codeGeneration.useInstructionFiles" = $true
            "github.copilot.chat.customInstructionsInSystemMessage"   = $true
            "chat.agent.enabled"                                       = $true
        }
        foreach ($key in $flags.Keys) {
            if (-not $settings.PSObject.Properties[$key]) {
                $settings | Add-Member -NotePropertyName $key -NotePropertyValue $flags[$key]
            }
        }
        $settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath
        Write-OK "Flags de Copilot activados"
    }
}

# ─── Resumen final ────────────────────────────────────────────────────────────

Write-Host "`n─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "✅ OpenClaw instalado en: $ProjectPath" -ForegroundColor Green
Write-Host ""
Write-Host "  Próximos pasos:" -ForegroundColor White
Write-Host "  1. Abre el proyecto en VS Code" -ForegroundColor Gray
Write-Host "  2. Copilot usará automáticamente los 963 skills" -ForegroundColor Gray
Write-Host "  3. En Copilot Chat, usa el agente '@openclaw' para acceso directo" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para configurar VS Code globalmente (todos los proyectos):" -ForegroundColor Yellow
Write-Host "  .\setup-project.ps1 -UpdateUserSettings" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────`n" -ForegroundColor DarkGray
