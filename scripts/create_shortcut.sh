#!/usr/bin/env bash
# ==============================================================================
# Project Brain - Creador de Acceso Directo (.desktop) para Linux
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$BRAIN_HOME" ]; then
    if [ -f "$SCRIPT_DIR/../PROTOCOL.md" ]; then
        BRAIN_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
    else
        BRAIN_HOME="$HOME/Brain"
    fi
fi

APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

mkdir -p "$APPS_DIR"

DESKTOP_ENTRY="[Desktop Entry]
Version=1.0
Type=Application
Name=Project Brain
Comment=Asistente Local con Memoria Persistente
Exec=python3 $BRAIN_HOME/tools/brain_chat.py
Icon=$BRAIN_HOME/assets/cerebro.ico
Path=$BRAIN_HOME
Terminal=false
Categories=Development;Utility;
"

echo "$DESKTOP_ENTRY" > "$APPS_DIR/project-brain.desktop"
chmod +x "$APPS_DIR/project-brain.desktop"

if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_ENTRY" > "$DESKTOP_DIR/Project Brain.desktop"
    chmod +x "$DESKTOP_DIR/Project Brain.desktop"
fi

echo "Lanzador de escritorio creado con éxito."
