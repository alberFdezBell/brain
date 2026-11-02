#!/usr/bin/env python3
"""
brain-commit - Puerta de persistencia blindada para Project Brain.
Ejecuta brain-lint --secrets y brain-quality --strict antes de realizar git commit.
Uso: python brain-commit.py [--slug <slug>] [-m "Resumen de cambios"]
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from brain_common import (
    get_brain_home,
    run_git_cmd
)
from brain_lint import run_linter
from brain_quality import evaluate_note, load_vault_config


def execute_commit(slug: str | None = None, message: str | None = None) -> int:
    brain_home = get_brain_home()

    print("==================================================")
    print("        PUERTA DE COMMIT PROJECT BRAIN            ")
    print("==================================================")

    # 1. Ejecutar escáner de integridad y secretos
    print("\n[PASO 1/3] Ejecutando brain-lint con escáner de secretos...")
    lint_ret = run_linter(check_secrets=True)
    if lint_ret != 0:
        print("\n\033[91m[COMMIT RECHAZADO] Errores de integridad o secretos detectados por el linter.\033[0m", file=sys.stderr)
        return 1

    # 2. Inicializar git si es necesario
    if not (brain_home / ".git").exists():
        print("\n[INFO] Inicializando repositorio Git en $BRAIN_HOME...")
        ret, _, err = run_git_cmd(["init"], cwd=brain_home)
        if ret != 0:
            print(f"[ERROR] No se pudo inicializar git: {err}", file=sys.stderr)
            return 1

    # 3. Identificar archivos modificados en Brain para pasar brain-quality --strict
    print("\n[PASO 2/3] Verificando calidad estricta sobre notas modificadas y estado de bóvedas...")

    # Comprobación de blindaje: verificar que ninguna bóveda activa tenga inicialización pendiente
    from brain_common import get_all_vaults
    target_slugs = [slug] if slug and slug != "_global" else ([] if slug == "_global" else [v.name for v in get_all_vaults(brain_home) if v.name != "_global"])
    for s in target_slugs:
        v_dir = brain_home / s
        if not v_dir.exists():
            continue
        cfg = load_vault_config(v_dir)
        r_path = Path(cfg["repo_path"]) if "repo_path" in cfg else None

        for required_file in [f"{s}-context.md", f"{s}-index.md"]:
            rf_path = v_dir / required_file
            if not rf_path.exists():
                print(f"\n\033[91m[COMMIT RECHAZADO] La bóveda '{s}' está incompleta: falta {required_file}.\033[0m", file=sys.stderr)
                return 1
            sc, bl, _ = evaluate_note(rf_path, r_path)
            if sc < 85 or len(bl) > 0:
                print(f"\n\033[91m[COMMIT RECHAZADO] La bóveda '{s}' tiene inicialización pendiente o incompleta en {required_file} (Score: {sc}/100).\033[0m", file=sys.stderr)
                for b in bl:
                    print(f"  - {b}")
                return 1

    ret_st, out_st, _ = run_git_cmd(["status", "--porcelain"], cwd=brain_home)
    modified_files = []
    if ret_st == 0 and out_st:
        for line in out_st.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                status_code, fpath = parts[0], parts[1]
                if fpath.endswith(".md"):
                    full_p = brain_home / fpath
                    # Excluir README, PROTOCOL, QUALITY, schema, templates, adapters
                    if not any(fpath.startswith(prefix) for prefix in ["README", "PROTOCOL", "QUALITY", "schema", "templates", "adapters", "tools"]):
                        if full_p.exists():
                            modified_files.append(full_p)

    failed_quality = False
    for mf in modified_files:
        # Inferir repo_path
        repo_path = None
        for p in [mf.parent, mf.parent.parent]:
            if (p / ".brain.yml").exists():
                cfg = load_vault_config(p)
                if "repo_path" in cfg:
                    repo_path = Path(cfg["repo_path"])
                break

        score, blocking, _ = evaluate_note(mf, repo_path)
        if score < 85 or len(blocking) > 0:
            failed_quality = True
            print(f"\n\033[91m[FALLO DE CALIDAD] {mf.relative_to(brain_home)} (Score: {score}/100)\033[0m")
            for b in blocking:
                print(f"  - {b}")

    if failed_quality:
        print("\n\033[91m[COMMIT RECHAZADO] Las notas modificadas no superan el contrato de calidad estricto.\033[0m", file=sys.stderr)
        return 1

    # 4. Git add & commit
    print("\n[PASO 3/3] Registrando cambios en Git local...")
    run_git_cmd(["add", "-A"], cwd=brain_home)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")
    clean_slug = slug or "workspace"
    summary_text = message or "actualizacion de memoria persistente"

    commit_msg = f"brain: {clean_slug} {date_str} - {summary_text}"

    ret_c, out_c, err_c = run_git_cmd(["commit", "-m", commit_msg], cwd=brain_home)
    if ret_c != 0:
        if "nothing to commit" in out_c or "nothing to commit" in err_c:
            print("[INFO] No hay cambios pendientes por commitear en $BRAIN_HOME.")
            return 0
        print(f"[ERROR] Error al hacer commit: {err_c}", file=sys.stderr)
        return 1

    print(f"\033[92m[EXITO] Cambios guardados en Git: '{commit_msg}'\033[0m")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Realiza commit seguro y verificado en Project Brain.")
    parser.add_argument("--slug", help="Slug del proyecto asociado", default=None)
    parser.add_argument("-m", "--message", help="Mensaje o resumen de los cambios", default=None)
    args = parser.parse_args()

    sys.exit(execute_commit(args.slug, args.message))


if __name__ == "__main__":
    main()
