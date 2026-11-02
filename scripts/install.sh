#!/usr/bin/env bash
# ==============================================================================
# Project Brain - Instalador Automatizado para Linux y macOS
# ==============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
NC='\033[0m'

echo -e "\n${CYAN}=================================================="
echo -e "   INSTALADOR AUTOMATIZADO - PROJECT BRAIN (UNIX) "
echo -e "==================================================${NC}"

# 1. Determinar ruta de BRAIN_HOME
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../PROTOCOL.md" ]; then
    BRAIN_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/PROTOCOL.md" ]; then
    BRAIN_HOME="$SCRIPT_DIR"
else
    BRAIN_HOME="$HOME/Brain"
fi

echo -e "\n${YELLOW}[1/7] Verificando ruta del repositorio...${NC}"
echo -e "    ${GRAY}Ubicación detectada: $BRAIN_HOME${NC}"
if [ ! -f "$BRAIN_HOME/PROTOCOL.md" ]; then
    echo "Error: No se encontró PROTOCOL.md en $BRAIN_HOME" >&2
    exit 1
fi
echo -e "    ${GREEN}[OK] Repositorio verificado.${NC}"

# 2. Configurar variable de entorno persistente BRAIN_HOME
echo -e "\n${YELLOW}[2/7] Configurando variable de entorno BRAIN_HOME...${NC}"
export BRAIN_HOME="$BRAIN_HOME"

add_env_to_rc() {
    local rc_file="$1"
    if [ -f "$rc_file" ]; then
        if ! grep -q "export BRAIN_HOME=" "$rc_file"; then
            echo -e "\n# Project Brain Environment" >> "$rc_file"
            echo "export BRAIN_HOME=\"$BRAIN_HOME\"" >> "$rc_file"
            echo -e "    ${GREEN}[OK] Agregado BRAIN_HOME a $rc_file${NC}"
        else
            echo -e "    ${GRAY}[INFO] BRAIN_HOME ya configurado en $rc_file${NC}"
        fi
    fi
}

add_env_to_rc "$HOME/.bashrc"
add_env_to_rc "$HOME/.zshrc"
add_env_to_rc "$HOME/.profile"

# 3. Validar Python y Git
echo -e "\n${YELLOW}[3/7] Verificando dependencias del sistema...${NC}"
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3 no está instalado. Instala Python 3.10+ para continuar." >&2
    exit 1
fi
echo -e "    ${GREEN}[OK] Python detectado: $($PYTHON_BIN --version)${NC}"

if ! command -v git &>/dev/null; then
    echo "Error: Git no está instalado. Instala git para continuar." >&2
    exit 1
fi
echo -e "    ${GREEN}[OK] Git detectado: $(git --version)${NC}"

# 4. Crear estructura de carpetas y permisos
echo -e "\n${YELLOW}[4/7] Asegurando estructura interna y permisos...${NC}"
mkdir -p "$BRAIN_HOME/tools/bin"
mkdir -p "$BRAIN_HOME/.cache"
mkdir -p "$BRAIN_HOME/assets"
mkdir -p "$BRAIN_HOME/templates"
mkdir -p "$BRAIN_HOME/schema"
mkdir -p "$BRAIN_HOME/adapters"
mkdir -p "$BRAIN_HOME/_global"

chmod +x "$BRAIN_HOME"/tools/*.sh 2>/dev/null || true
chmod +x "$BRAIN_HOME"/tools/*.py 2>/dev/null || true
chmod +x "$BRAIN_HOME"/scripts/*.sh 2>/dev/null || true
echo -e "    ${GREEN}[OK] Carpetas y permisos verificados.${NC}"

# 5. Descarga opcional de modelo local y binario llama.cpp
echo -e "\n${YELLOW}[5/7] Comprobando motor de inferencia local (Brain Chat)...${NC}"
SERVER_BIN="$BRAIN_HOME/tools/bin/llama-server"
MODEL_FILE="$BRAIN_HOME/tools/bin/qwen2.5-1.5b-instruct-q4_k_m.gguf"

DOWNLOAD_MODEL=false
for arg in "$@"; do
    case "$arg" in
        --download-model) DOWNLOAD_MODEL=true ;;
        --skip-model) DOWNLOAD_MODEL=false ;;
    esac
done

if [ -f "$SERVER_BIN" ] && [ -f "$MODEL_FILE" ]; then
    echo -e "    ${GREEN}[OK] Motor local ya instalado (llama-server y Qwen2.5-1.5B).${NC}"
else
    if [ "$DOWNLOAD_MODEL" = false ] && [ -t 0 ]; then
        read -p "¿Deseas descargar el motor local de chat (llama-server + Qwen2.5-1.5B ~986 MB)? [s/N]: " resp
        case "$resp" in
            [sSyY]*) DOWNLOAD_MODEL=true ;;
        esac
    fi

    if [ "$DOWNLOAD_MODEL" = true ]; then
        if [ ! -f "$SERVER_BIN" ]; then
            echo -e "    ${GRAY}[INFO] Descargando binario llama-server para Linux x86_64...${NC}"
            LLAMA_URL="https://github.com/ggerganov/llama.cpp/releases/download/b4400/llama-b4400-bin-ubuntu-x64.zip"
            TMP_ZIP="$BRAIN_HOME/.cache/llama-bin.zip"
            curl -L -o "$TMP_ZIP" "$LLAMA_URL"
            unzip -q -o "$TMP_ZIP" -d "$BRAIN_HOME/.cache/llama-temp"
            find "$BRAIN_HOME/.cache/llama-temp" -type f -name "llama-server" -exec mv {} "$SERVER_BIN" \;
            chmod +x "$SERVER_BIN"
            rm -rf "$BRAIN_HOME/.cache/llama-temp" "$TMP_ZIP"
            echo -e "    ${GREEN}[OK] llama-server instalado en tools/bin/${NC}"
        fi

        if [ ! -f "$MODEL_FILE" ]; then
            echo -e "    ${GRAY}[INFO] Descargando modelo Qwen2.5-1.5B-Instruct-Q4_K_M.gguf (~986 MB)...${NC}"
            MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
            curl -L -o "$MODEL_FILE" "$MODEL_URL"
            echo -e "    ${GREEN}[OK] Modelo instalado en tools/bin/${NC}"
        fi
    else
        echo -e "    ${GRAY}[INFO] Motor local no descargado. Puedes usar la CLI y herramientas de indexación.${NC}"
    fi
fi

# 6. Integración con Antigravity, Claude Code y Codex
echo -e "\n${YELLOW}[6/7] Configurando integraciones para asistentes de IA...${NC}"

# A) Antigravity
GEMINI_DIR="$HOME/.gemini"
mkdir -p "$GEMINI_DIR"
AGENTS_FILE="$GEMINI_DIR/AGENTS.md"
RULE_TEXT=$(cat <<EOF

# Project Brain - Memoria Persistente Obligatoria
En cada sesión, chat y proyecto, debes leer y seguir obligatoriamente \$BRAIN_HOME/PROTOCOL.md (por defecto ~/Brain/PROTOCOL.md) antes de actuar y antes de dar nada por terminado:
1. **Inicio de sesión**: Leer capa caliente del proyecto (<slug>-index.md, <slug>-context.md, <slug>-todo.md) y las 3 últimas sesiones. Ejecutar python ~/Brain/tools/brain-capture.py --start --slug <slug>.
2. **Durante la sesión**: Registrar decisiones en decisions/ y aprendizajes en learnings/ con hechos reales y reproducibles.
3. **Cierre de sesión / finalización de tarea**: La tarea NO está completa hasta que se ejecute python ~/Brain/tools/brain-session.py --slug <slug>, se completen las secciones narrativas obligatorias sin expresiones vagas, y pasen con éxito tanto python ~/Brain/tools/brain-quality.py --strict --slug <slug> como python ~/Brain/tools/brain-commit.py --slug <slug>.
EOF
)

if [ -f "$AGENTS_FILE" ]; then
    if ! grep -q "Project Brain - Memoria Persistente" "$AGENTS_FILE"; then
        echo -e "\n$RULE_TEXT" >> "$AGENTS_FILE"
        echo -e "    ${GREEN}[OK] Regla de Project Brain inyectada en ~/.gemini/AGENTS.md${NC}"
    else
        echo -e "    ${GRAY}[INFO] Regla de Project Brain ya presente en ~/.gemini/AGENTS.md${NC}"
    fi
else
    echo -e "$RULE_TEXT" > "$AGENTS_FILE"
    echo -e "    ${GREEN}[OK] Archivo ~/.gemini/AGENTS.md creado con regla obligatoria.${NC}"
fi

# Copiar skills para Antigravity si existe ~/.gemini/config/skills
SKILLS_DIR="$HOME/.gemini/config/skills"
if [ -d "$SKILLS_DIR" ]; then
    for sk in project-brain brain-ask brain-search brain-save brain-audit brain-compact brain-init; do
        mkdir -p "$SKILLS_DIR/$sk"
        cat <<EOF > "$SKILLS_DIR/$sk/SKILL.md"
---
name: $sk
description: Interacción con el sistema de memoria persistente Project Brain ($sk).
---
# Skill $sk
Consulta \$BRAIN_HOME/PROTOCOL.md y ejecuta las herramientas CLI correspondientes en \$BRAIN_HOME/tools/.
EOF
    done
    echo -e "    ${GREEN}[OK] Skills registradas en ~/.gemini/config/skills/${NC}"
fi

# B) Claude Code
CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
CLAUDE_FILE="$CLAUDE_DIR/CLAUDE.md"
if [ -f "$BRAIN_HOME/adapters/claude-code.md" ]; then
    CLAUDE_CONTENT=$(cat "$BRAIN_HOME/adapters/claude-code.md")
    if [ -f "$CLAUDE_FILE" ]; then
        if ! grep -q "Memoria Persistente (Project Brain)" "$CLAUDE_FILE"; then
            echo -e "\n\n$CLAUDE_CONTENT" >> "$CLAUDE_FILE"
            echo -e "    ${GREEN}[OK] Instrucciones inyectadas en ~/.claude/CLAUDE.md${NC}"
        else
            echo -e "    ${GRAY}[INFO] Instrucciones ya presentes en ~/.claude/CLAUDE.md${NC}"
        fi
    else
        echo "$CLAUDE_CONTENT" > "$CLAUDE_FILE"
        echo -e "    ${GREEN}[OK] Archivo ~/.claude/CLAUDE.md creado.${NC}"
    fi
fi

# C) OpenAI Codex / Copilot
CODEX_DIR="$HOME/.codex"
mkdir -p "$CODEX_DIR"
if [ -f "$BRAIN_HOME/adapters/codex.md" ]; then
    cp "$BRAIN_HOME/adapters/codex.md" "$CODEX_DIR/instructions.md"
    echo -e "    ${GREEN}[OK] Instrucciones guardadas en ~/.codex/instructions.md${NC}"
fi

# 7. Construir índice BM25 y diagnóstico
echo -e "\n${YELLOW}[7/7] Generando índice BM25 y ejecutando brain-doctor...${NC}"
$PYTHON_BIN "$BRAIN_HOME/tools/brain-index.py" || true
echo ""
$PYTHON_BIN "$BRAIN_HOME/tools/brain-doctor.py" || true

echo -e "\n${CYAN}=================================================="
echo -e "   INSTALACIÓN COMPLETADA CON ÉXITO               "
echo -e "==================================================${NC}"
echo -e "${GREEN}Project Brain está listo para usarse.${NC}\n"
echo -e "Comandos útiles para empezar:"
echo -e "  1. Abrir chat local:                   ${CYAN}$PYTHON_BIN tools/brain_chat.py${NC}"
echo -e "  2. Inicializar nueva bóveda:           ${CYAN}$PYTHON_BIN tools/brain-init.py <nombre> --repo-path <ruta>${NC}"
echo -e "  3. Preguntar por historial/decisiones: ${CYAN}$PYTHON_BIN tools/brain-ask.py '<consulta>'${NC}"
echo -e "  4. Verificar calidad estricta:         ${CYAN}$PYTHON_BIN tools/brain-quality.py --strict --slug <nombre>${NC}"
echo -e "\nPara detalles sobre migración de bóvedas y arquitectura, lee ${GRAY}INSTALACION.md${NC}"
EOF
