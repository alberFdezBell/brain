<#
.SYNOPSIS
    Lanzador directo del instalador de Project Brain para Windows.
#>
param(
    [string]$BrainHome = "",
    [switch]$DownloadModel,
    [switch]$SkipModel
)

$scriptPath = Join-Path $PSScriptRoot "scripts\install.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "No se encontró scripts\install.ps1 en $PSScriptRoot"
}

& $scriptPath -BrainHome $BrainHome -DownloadModel:$DownloadModel -SkipModel:$SkipModel
