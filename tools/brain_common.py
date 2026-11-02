#!/usr/bin/env python3
"""
brain_common.py - Utilidades compartidas para las herramientas de Project Brain.
100% Python 3 estándar (sin dependencias externas).
"""

import os
import sys
import re
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def get_brain_home() -> Path:
    """Devuelve la ruta absoluta a la raíz de Project Brain."""
    env_home = os.environ.get("BRAIN_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    # Por defecto ~/Brain
    return (Path.home() / "Brain").resolve()


def get_current_iso_time() -> str:
    """Devuelve timestamp ISO 8601 con zona horaria local."""
    return datetime.now().astimezone().isoformat()


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parsea el frontmatter YAML y el cuerpo de una nota markdown.
    Implementación nativa sin dependencias externas.
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    yaml_text = parts[1]
    body = parts[2]

    metadata = {}
    current_key = None
    in_list = False

    for raw_line in yaml_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Elemento de lista
        if line.startswith("- "):
            val = line[2:].strip().strip('"\'')
            if current_key and in_list:
                metadata[current_key].append(val)
            continue

        # Par clave: valor
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            if val == "":
                # Posible inicio de lista o diccionario
                metadata[key] = []
                current_key = key
                in_list = True
            else:
                in_list = False
                current_key = key
                # Normalización de tipos básicos
                if val.lower() == "true":
                    metadata[key] = True
                elif val.lower() == "false":
                    metadata[key] = False
                elif val.isdigit():
                    metadata[key] = int(val)
                else:
                    # Remover comillas envolventes
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    metadata[key] = val

    return metadata, body


def serialize_frontmatter(metadata: dict) -> str:
    """Serializa un diccionario a frontmatter YAML estándar."""
    lines = ["---"]
    for k, v in metadata.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
        else:
            val_str = str(v)
            if any(c in val_str for c in [":", "#", "[", "]", "{", "}", ",", "\n"]):
                lines.append(f"{k}: {json.dumps(val_str, ensure_ascii=False)}")
            else:
                lines.append(f"{k}: {val_str}")
    lines.append("---")
    return "\n".join(lines)


def read_note(path: Path) -> tuple[dict, str]:
    """Lee un archivo de nota y devuelve (metadata, body)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return parse_frontmatter(content)


def write_note(path: Path, metadata: dict, body: str) -> None:
    """Escribe una nota con frontmatter y cuerpo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = serialize_frontmatter(metadata)
    full_content = f"{fm}\n{body.lstrip()}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(full_content)


def extract_wikilinks(text: str) -> list[str]:
    """Extrae todos los enlaces [[nota]] o [[nota|alias]] del texto, excluyendo bloques de código."""
    # Eliminar bloques de código cercados
    no_fenced = re.sub(r"```[\s\S]*?```", "", text)
    # Eliminar código inline
    no_code = re.sub(r"`[^`\n]+`", "", no_fenced)
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    matches = re.findall(pattern, no_code)
    return [m.strip() for m in matches]


def load_vault_config(vault_dir: Path) -> dict:
    """Lee el archivo .brain.yml de una bóveda."""
    cfg_file = vault_dir / ".brain.yml"
    if not cfg_file.exists():
        return {}
    with open(cfg_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Parseo simple de yaml
    config = {}
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and ":" in line:
            k, v = line.split(":", 1)
            config[k.strip()] = v.strip().strip('"\'')
    return config


def save_vault_config(vault_dir: Path, config: dict) -> None:
    """Guarda configuración en .brain.yml."""
    cfg_file = vault_dir / ".brain.yml"
    lines = [f"{k}: {v}" for k, v in config.items()]
    with open(cfg_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def get_all_vaults(brain_home: Path) -> list[Path]:
    """Lista todos los directorios que son bóvedas válidas (tienen .brain.yml o son _global)."""
    vaults = []
    for item in brain_home.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if item.name in ["schema", "templates", "tools", "adapters"]:
                continue
            if (item / ".brain.yml").exists() or item.name == "_global":
                vaults.append(item)
    return sorted(vaults)


def run_git_cmd(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Ejecuta un comando git y devuelve (returncode, stdout, stderr) sin abrir ventanas emergentes de consola."""
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)
