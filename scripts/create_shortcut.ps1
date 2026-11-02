<#
.SYNOPSIS
    Crea un acceso directo en el Escritorio para Brain Chat con icono cerebro.ico.
#>
param(
    [string]$BrainHome = ""
)

if ([string]::IsNullOrWhiteSpace($BrainHome)) {
    if ($env:BRAIN_HOME) {
        $BrainHome = $env:BRAIN_HOME
    } elseif (Test-Path "$PSScriptRoot\..\PROTOCOL.md") {
        $BrainHome = (Resolve-Path "$PSScriptRoot\..").Path
    } else {
        $BrainHome = "$HOME\Brain"
    }
}
$BrainHome = [System.IO.Path]::GetFullPath($BrainHome)

$WshShell = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$shortcutPath = Join-Path $desktop "Project Brain.lnk"

# Buscar pythonw.exe para ejecucion silenciosa sin ventana negra de consola
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonCmd = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($pythonCmd) {
        $pythonDir = Split-Path -Parent $pythonCmd
        $candidate = Join-Path $pythonDir "pythonw.exe"
        if (Test-Path $candidate) {
            $pythonw = $candidate
        } else {
            $pythonw = $pythonCmd
        }
    } else {
        $pythonw = "pythonw.exe"
    }
}

$chatScript = Join-Path $BrainHome "tools\brain_chat.py"
$icoPath = Join-Path $BrainHome "assets\cerebro.ico"

$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$chatScript`""
$shortcut.WorkingDirectory = $BrainHome
if (Test-Path $icoPath) {
    $shortcut.IconLocation = "$icoPath,0"
}
$shortcut.Description = "Project Brain - Asistente Local con Memoria Persistente"
$shortcut.Save()

Write-Host "Acceso directo creado con exito en el Escritorio:" -ForegroundColor Green
Write-Host "  $shortcutPath" -ForegroundColor Cyan
