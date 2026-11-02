<#
.SYNOPSIS
    Instalador y configurador automatizado de Project Brain para Windows.
.DESCRIPTION
    Configura el entorno, variables del sistema ($BRAIN_HOME), dependencias,
    integraciones para Antigravity, Claude Code y OpenAI Codex, e inicializa los índices.
.PARAMETER BrainHome
    Ruta raíz donde reside Project Brain. Por defecto, la carpeta contenedora de este script.
.PARAMETER DownloadModel
    Descarga automáticamente el modelo Qwen2.5-1.5B (GGUF) y el binario de llama.cpp.
.PARAMETER SkipModel
    Omite la descarga de modelos pesados para una instalación ultraligera.
#>

[CmdletBinding()]
param(
    [string]$BrainHome = "",
    [switch]$DownloadModel,
    [switch]$SkipModel
)

$ErrorActionPreference = "Stop"

function Write-Header ($text) {
    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host "   $text" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
}

function Write-Step ($step, $text) {
    Write-Host "`n[$step] $text" -ForegroundColor Yellow
}

function Write-Success ($text) {
    Write-Host "    [OK] $text" -ForegroundColor Green
}

function Write-Notice ($text) {
    Write-Host "    [INFO] $text" -ForegroundColor Gray
}

function Write-Warn ($text) {
    Write-Host "    [AVISO] $text" -ForegroundColor DarkYellow
}

Write-Header "INSTALADOR AUTOMATIZADO - PROJECT BRAIN (WINDOWS)"

# 1. Determinar ruta de BRAIN_HOME
if ([string]::IsNullOrWhiteSpace($BrainHome)) {
    if (Test-Path "$PSScriptRoot\..\PROTOCOL.md") {
        $BrainHome = (Resolve-Path "$PSScriptRoot\..").Path
    } elseif (Test-Path "$PSScriptRoot\PROTOCOL.md") {
        $BrainHome = (Resolve-Path "$PSScriptRoot").Path
    } else {
        $BrainHome = "$HOME\Brain"
    }
}
$BrainHome = [System.IO.Path]::GetFullPath($BrainHome)

Write-Step "1/7" "Verificando ruta del repositorio..."
Write-Notice "Ubicacion detectada: $BrainHome"
if (-not (Test-Path "$BrainHome\PROTOCOL.md")) {
    throw "No se encontro PROTOCOL.md en '$BrainHome'. Asegurate de ejecutar este instalador dentro del repositorio de Project Brain."
}
Write-Success "Estructura del repositorio confirmada."

# 2. Configurar variable de entorno persistente BRAIN_HOME
Write-Step "2/7" "Configurando variable de entorno BRAIN_HOME..."
$env:BRAIN_HOME = $BrainHome
[Environment]::SetEnvironmentVariable("BRAIN_HOME", $BrainHome, "User")
Write-Success "Variable de usuario BRAIN_HOME establecida en: $BrainHome"

# 3. Validar Python y Git
Write-Step "3/7" "Verificando dependencias del sistema..."
try {
    $pythonVersion = & python --version 2>&1
    Write-Success "Python detectado: $pythonVersion"
} catch {
    throw "Python no esta instalado o no se encuentra en el PATH. Instala Python 3.10+ para continuar."
}

try {
    $gitVersion = & git --version 2>&1
    Write-Success "Git detectado: $gitVersion"
} catch {
    throw "Git no esta instalado o no se encuentra en el PATH. Instala Git para continuar."
}

# 4. Crear estructura de carpetas necesarias
Write-Step "4/7" "Asegurando estructura interna de directorios..."
$requiredDirs = @(
    "$BrainHome\tools\bin",
    "$BrainHome\.cache",
    "$BrainHome\assets",
    "$BrainHome\templates",
    "$BrainHome\schema",
    "$BrainHome\adapters",
    "$BrainHome\_global"
)

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Notice "Creado directorio: $dir"
    }
}
Write-Success "Directorios base operativos."

# 5. Descarga opcional de modelo local y llama.cpp para Brain Chat
Write-Step "5/7" "Comprobando motor de inferencia local (Brain Chat)..."
$serverExe = "$BrainHome\tools\bin\llama-server.exe"
$modelFile = "$BrainHome\tools\bin\qwen2.5-1.5b-instruct-q4_k_m.gguf"

if ((Test-Path $serverExe) -and (Test-Path $modelFile)) {
    Write-Success "Motor local ya disponible: llama-server.exe y Qwen2.5-1.5B (GGUF)."
} elseif ($SkipModel.IsPresent) {
    Write-Notice "Descarga de modelo omitida (-SkipModel especificado)."
} else {
    $shouldDownload = $DownloadModel.IsPresent
    if ((-not $shouldDownload) -and (-not [Console]::IsInputRedirected)) {
        $answer = Read-Host "Deseas descargar el motor local de chat (llama-server.exe + Qwen2.5-1.5B ~986 MB)? [S/N]"
        if ($answer -match "^[sSyY]") {
            $shouldDownload = $true
        }
    }

    if ($shouldDownload) {
        if (-not (Test-Path $serverExe)) {
            Write-Notice "Descargando llama-server.exe..."
            $serverUrl = "https://github.com/ggerganov/llama.cpp/releases/download/b4400/llama-b4400-bin-win-avx2-x64.zip"
            $zipPath = "$BrainHome\.cache\llama-bin.zip"
            try {
                Invoke-WebRequest -Uri $serverUrl -OutFile $zipPath -UseBasicParsing
                Expand-Archive -Path $zipPath -DestinationPath "$BrainHome\.cache\llama-temp" -Force
                $extractedExe = Get-ChildItem "$BrainHome\.cache\llama-temp" -Filter "llama-server.exe" -Recurse | Select-Object -First 1
                if ($extractedExe) {
                    Move-Item -Path $extractedExe.FullName -Destination $serverExe -Force
                    Write-Success "llama-server.exe instalado en tools\bin\"
                }
                Remove-Item -Path "$BrainHome\.cache\llama-temp" -Recurse -Force -ErrorAction SilentlyContinue
                Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Warn "No se pudo descargar automaticamente llama-server.exe. Puedes colocarlo manualmente en '$BrainHome\tools\bin\'."
            }
        }

        if (-not (Test-Path $modelFile)) {
            Write-Notice "Descargando modelo Qwen2.5-1.5B-Instruct-Q4_K_M.gguf (~986 MB)..."
            $modelUrl = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
            try {
                Invoke-WebRequest -Uri $modelUrl -OutFile $modelFile -UseBasicParsing
                Write-Success "Modelo Qwen2.5-1.5B instalado en tools\bin\"
            } catch {
                Write-Warn "No se pudo descargar automaticamente el modelo. Puedes colocar 'qwen2.5-1.5b-instruct-q4_k_m.gguf' manualmente en '$BrainHome\tools\bin\'."
            }
        }
    } else {
        Write-Notice "Motor local no descargado. Podras usar la CLI y herramientas de indexacion sin restricciones."
    }
}

# 6. Integracion con Antigravity, Claude Code y Codex
Write-Step "6/7" "Configurando integraciones para asistentes de IA..."

# A) Google Antigravity
$geminiDir = "$HOME\.gemini"
if (-not (Test-Path $geminiDir)) {
    New-Item -ItemType Directory -Path $geminiDir -Force | Out-Null
}

$agentsRuleFile = "$geminiDir\AGENTS.md"
$ruleBlock = @'

# Project Brain - Memoria Persistente Obligatoria
En cada sesion, chat y proyecto, debes leer y seguir obligatoriamente `$BRAIN_HOME/PROTOCOL.md` (por defecto `~/Brain/PROTOCOL.md`) antes de actuar y antes de dar nada por terminado:
1. **Inicio de sesion**: Leer capa caliente del proyecto (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`) y las 3 ultimas sesiones. Ejecutar `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
2. **Durante la sesion**: Registrar decisiones en `decisions/` y aprendizajes en `learnings/` con hechos reales y reproducibles.
3. **Cierre de sesion / finalizacion de tarea**: La tarea NO esta completa hasta que se ejecute `python ~/Brain/tools/brain-session.py --slug <slug>`, se completen las secciones narrativas obligatorias sin expresiones vagas, y pasen con exito tanto `python ~/Brain/tools/brain-quality.py --strict --slug <slug>` como `python ~/Brain/tools/brain-commit.py --slug <slug>`.
'@

if (Test-Path $agentsRuleFile) {
    $existing = Get-Content $agentsRuleFile -Raw -Encoding UTF8
    if ($existing -notmatch "Project Brain - Memoria Persistente") {
        Add-Content -Path $agentsRuleFile -Value "`n$ruleBlock" -Encoding UTF8
        Write-Success "Regla de Project Brain inyectada en ~/.gemini/AGENTS.md"
    } else {
        Write-Notice "Regla de Project Brain ya presente en ~/.gemini/AGENTS.md"
    }
} else {
    Set-Content -Path $agentsRuleFile -Value $ruleBlock -Encoding UTF8
    Write-Success "Archivo ~/.gemini/AGENTS.md creado con regla obligatoria."
}

# Copiar skills para Antigravity si existe carpeta ~/.gemini/config/skills
$skillsDir = "$HOME\.gemini\config\skills"
if (Test-Path $skillsDir) {
    $skillNames = @("project-brain", "brain-ask", "brain-search", "brain-save", "brain-audit", "brain-compact", "brain-init")
    foreach ($sk in $skillNames) {
        $skTarget = "$skillsDir\$sk"
        if (-not (Test-Path $skTarget)) {
            New-Item -ItemType Directory -Path $skTarget -Force | Out-Null
        }
        $skillDoc = @"
---
name: $sk
description: Interaccion con el sistema de memoria persistente Project Brain ($sk).
---
# Skill $sk
Consulta '$BrainHome/PROTOCOL.md' y ejecuta las herramientas CLI correspondientes en '$BrainHome/tools/'.
"@
        Set-Content -Path "$skTarget\SKILL.md" -Value $skillDoc -Encoding UTF8
    }
    Write-Success "Skills de Antigravity registradas en ~/.gemini/config/skills/"
}

# B) Claude Code
$claudeDir = "$HOME\.claude"
if (-not (Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
}
$claudeFile = "$claudeDir\CLAUDE.md"
if (Test-Path "$BrainHome\adapters\claude-code.md") {
    $claudeContent = Get-Content "$BrainHome\adapters\claude-code.md" -Raw -Encoding UTF8
    if (Test-Path $claudeFile) {
        $existingClaude = Get-Content $claudeFile -Raw -Encoding UTF8
        if ($existingClaude -notmatch "Memoria Persistente \(Project Brain\)") {
            Add-Content -Path $claudeFile -Value "`n`n$claudeContent" -Encoding UTF8
            Write-Success "Instrucciones inyectadas en ~/.claude/CLAUDE.md"
        } else {
            Write-Notice "Instrucciones ya presentes en ~/.claude/CLAUDE.md"
        }
    } else {
        Set-Content -Path $claudeFile -Value $claudeContent -Encoding UTF8
        Write-Success "Archivo ~/.claude/CLAUDE.md creado para Claude Code."
    }
}

# C) OpenAI Codex / Copilot / Cursor
$codexDir = "$HOME\.codex"
if (-not (Test-Path $codexDir)) {
    New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
}
$codexFile = "$codexDir\instructions.md"
if (Test-Path "$BrainHome\adapters\codex.md") {
    Copy-Item -Path "$BrainHome\adapters\codex.md" -Destination $codexFile -Force
    Write-Success "Instrucciones de Codex guardadas en ~/.codex/instructions.md"
}

# 7. Construir indice BM25 y ejecutar diagnostico de salud
Write-Step "7/7" "Generando indice BM25 y ejecutando brain-doctor..."
try {
    & python "$BrainHome\tools\brain-index.py"
    Write-Success "Indice BM25 generado con exito."
} catch {
    Write-Warn "Error al generar indice BM25: $_"
}

Write-Host ""
& python "$BrainHome\tools\brain-doctor.py"

Write-Header "INSTALACION COMPLETADA CON EXITO"
Write-Host "Project Brain esta listo para usarse.`n" -ForegroundColor Green
Write-Host "Comandos utiles para empezar:" -ForegroundColor White
Write-Host "  1. Abrir la interfaz de chat local:    python tools/brain_chat.py" -ForegroundColor Cyan
Write-Host "  2. Inicializar una nueva boveda:       python tools/brain-init.py <nombre> --repo-path <ruta>" -ForegroundColor Cyan
Write-Host "  3. Preguntar por historial/decisiones: python tools/brain-ask.py '<consulta>'" -ForegroundColor Cyan
Write-Host "  4. Verificar calidad de notas:         python tools/brain-quality.py --strict --slug <nombre>" -ForegroundColor Cyan
Write-Host "`nPara mas detalles sobre migracion y uso, consulta INSTALACION.md" -ForegroundColor Gray
