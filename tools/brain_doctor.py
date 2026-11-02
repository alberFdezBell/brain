#!/usr/bin/env python3
"""
brain-doctor - Diagnóstico integral del entorno, herramientas, bóvedas e integraciones.
Uso: python brain-doctor.py
"""

import os
import sys
import platform
from pathlib import Path
from brain_common import (
    get_brain_home,
    get_all_vaults,
    load_vault_config,
    run_git_cmd
)


def run_diagnostics() -> int:
    all_ok = True
    print("==================================================")
    print("           DIAGNÓSTICO PROJECT BRAIN              ")
    print("==================================================")

    # 1. Sistema Operativo y Python
    py_ver = platform.python_version()
    print(f"\n[1] Entorno de Ejecución:")
    print(f"    - SO: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"    - Python: {py_ver} ({sys.executable})")
    if sys.version_info < (3, 10):
        print("      \033[93m[AVISO] Se recomienda Python 3.10 o superior.\033[0m")
    else:
        print("      \033[92m[OK] Versión de Python compatible.\033[0m")

    # 2. Git
    ret_git, out_git, _ = run_git_cmd(["--version"])
    print(f"\n[2] Control de Versiones Git:")
    if ret_git == 0:
        print(f"    - Git: {out_git}")
        print("      \033[92m[OK] Git detectado y operativo.\033[0m")
    else:
        print("      \033[91m[FALLO] Git no está disponible en el PATH.\033[0m")
        all_ok = False

    # 3. Variable BRAIN_HOME
    brain_home = get_brain_home()
    env_brain = os.environ.get("BRAIN_HOME")
    print(f"\n[3] Ubicación de Project Brain:")
    print(f"    - Ruta efectiva: {brain_home}")
    if env_brain:
        print(f"    - Variable $BRAIN_HOME: {env_brain}")
        print("      \033[92m[OK] Variable de entorno configurada.\033[0m")
    else:
        print("      \033[93m[AVISO] Variable $BRAIN_HOME no definida explícitamente (usando ~/Brain por defecto).\033[0m")

    # 4. Estructura interna de Brain
    print(f"\n[4] Estructura del Almacén Central:")
    required_dirs = ["schema", "templates", "tools", "adapters", "_global", ".obsidian"]
    for d in required_dirs:
        p = brain_home / d
        if p.exists():
            print(f"    - Directoria '{d}': \033[92m[PRESENTE]\033[0m")
        else:
            print(f"    - Directorio '{d}': \033[91m[FALTANTE]\033[0m")
            all_ok = False

    # Archivos fundamentales
    required_files = ["PROTOCOL.md", "QUALITY.md", "schema/VERSION", ".obsidian/graph.json"]
    for f in required_files:
        p = brain_home / f
        if p.exists():
            print(f"    - Archivo '{f}': \033[92m[PRESENTE]\033[0m")
        else:
            print(f"    - Archivo '{f}': \033[91m[FALTANTE]\033[0m")
            all_ok = False

    # 5. Diagnóstico de Bóvedas
    vaults = get_all_vaults(brain_home)
    print(f"\n[5] Bóvedas Registradas ({len(vaults)}):")
    for v in vaults:
        slug = v.name
        cfg = load_vault_config(v)
        repo_path_str = cfg.get("repo_path")
        repo_ok = False
        if repo_path_str:
            repo_p = Path(repo_path_str)
            if repo_p.exists():
                repo_ok = True

        # Comprobar estado de inicialización (context e index)
        vault_issues = []
        if slug != "_global":
            ctx_file = v / f"{slug}-context.md"
            idx_file = v / f"{slug}-index.md"
            for f_check, f_label in [(ctx_file, "context"), (idx_file, "index")]:
                if not f_check.exists():
                    vault_issues.append(f"falta {f_label}")
                    all_ok = False
                else:
                    try:
                        from brain_common import read_note
                        m, b = read_note(f_check)
                        if m.get("needs_review") is True:
                            vault_issues.append(f"{f_label} con needs_review=true")
                            all_ok = False
                        if "INICIALIZACIÓN PENDIENTE" in b or "INICIALIZACION PENDIENTE" in b:
                            vault_issues.append(f"{f_label} con INICIALIZACIÓN PENDIENTE")
                            all_ok = False
                        if "{{" in b or "}}" in b:
                            vault_issues.append(f"{f_label} con placeholders")
                            all_ok = False
                    except Exception as e:
                        vault_issues.append(f"error leyendo {f_label}: {e}")
                        all_ok = False

        if vault_issues:
            status_str = f"\033[91m[INCOMPLETO: {', '.join(vault_issues)}]\033[0m"
        elif repo_ok or slug == "_global":
            status_str = "\033[92m[OK - Inicializado y verificado]\033[0m"
        else:
            status_str = "\033[93m[REPO NO ENCONTRADO]\033[0m"

        print(f"    - {slug} (repo: {repo_path_str or 'N/A'}) -> {status_str}")

    # 6. Integración Antigravity
    print(f"\n[6] Integraciones de Asistente IA:")
    user_home = Path.home()
    agents_rule = user_home / ".gemini" / "AGENTS.md"
    skill_dir = user_home / ".gemini" / "config" / "skills" / "project-brain" / "SKILL.md"

    if agents_rule.exists():
        with open(agents_rule, "r", encoding="utf-8", errors="replace") as f:
            c = f.read()
        if "Project Brain" in c or "PROTOCOL.md" in c:
            print("    - Regla global Antigravity (~/.gemini/AGENTS.md): \033[92m[INSTALADA Y ACTIVA]\033[0m")
        else:
            print("    - Regla global Antigravity (~/.gemini/AGENTS.md): \033[93m[ARCHIVO EXISTE PERO FALTA PROTOCOLO]\033[0m")
    else:
        print("    - Regla global Antigravity: \033[93m[PENDIENTE DE INSTALACIÓN]\033[0m")

    if skill_dir.exists():
        print("    - Skill Antigravity (project-brain): \033[92m[INSTALADA]\033[0m")
    else:
        print("    - Skill Antigravity (project-brain): \033[93m[PENDIENTE DE INSTALACIÓN]\033[0m")

    print("\n--------------------------------------------------")
    if all_ok:
        print("\033[92m[RESULTADO] Todos los componentes esenciales están en verde y listos.\033[0m")
        return 0
    else:
        print("\033[91m[RESULTADO] Se detectaron elementos pendientes de corrección.\033[0m")
        return 1


def main():
    sys.exit(run_diagnostics())


if __name__ == "__main__":
    main()
