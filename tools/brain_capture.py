#!/usr/bin/env python3
"""
brain-capture - Captura hechos objetivos del sistema y del repo git para una sesión.
Uso:
  python brain-capture.py --start --slug <slug>
  python brain-capture.py --end --slug <slug> [--json]
"""

import sys
import json
import argparse
from pathlib import Path
from brain_common import (
    get_brain_home,
    get_current_iso_time,
    load_vault_config,
    run_git_cmd
)


def detect_tool_versions(repo_path: Path) -> dict:
    """Detecta versiones de herramientas y lenguajes en el entorno y manifiestos."""
    versions = {}
    # Python
    ret, out, _ = run_git_cmd(["--version"])
    if ret == 0:
        versions["git"] = out

    import platform
    versions["python"] = platform.python_version()

    # Si hay package.json
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                d = json.load(f)
                versions["node_package"] = f"{d.get('name', 'app')}@{d.get('version', '0.0.0')}"
        except Exception:
            pass

    return versions


def start_capture(slug: str, dry_run: bool = False) -> int:
    brain_home = get_brain_home()
    vault_dir = brain_home / slug
    if not vault_dir.exists():
        print(f"[ERROR] Bóveda '{slug}' no existe en {vault_dir}.", file=sys.stderr)
        return 1

    cfg = load_vault_config(vault_dir)
    repo_path = Path(cfg.get("repo_path", Path.cwd())).resolve()

    now_iso = get_current_iso_time()
    git_head = None
    git_branch = None

    if repo_path.exists():
        ret, out, _ = run_git_cmd(["rev-parse", "HEAD"], cwd=repo_path)
        if ret == 0 and out:
            git_head = out
        ret_b, out_b, _ = run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if ret_b == 0 and out_b:
            git_branch = out_b

    state = {
        "slug": slug,
        "repo_path": str(repo_path),
        "start_time": now_iso,
        "start_commit": git_head,
        "branch": git_branch
    }

    cache_dir = brain_home / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{slug}-session-start.json"

    if dry_run:
        print("[DRY-RUN] Estado de inicio que se guardaría:")
        print(json.dumps(state, indent=2))
        return 0

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"[OK] Sesión iniciada para '{slug}'.")
    print(f"     Inicio: {now_iso}")
    print(f"     Commit base: {git_head or 'Sin repo git'}")
    print(f"     Rama: {git_branch or 'N/A'}")
    return 0


def end_capture(slug: str, output_json: bool = False, dry_run: bool = False) -> int:
    brain_home = get_brain_home()
    vault_dir = brain_home / slug
    if not vault_dir.exists():
        print(f"[ERROR] Bóveda '{slug}' no existe.", file=sys.stderr)
        return 1

    cfg = load_vault_config(vault_dir)
    repo_path = Path(cfg.get("repo_path", Path.cwd())).resolve()

    cache_file = brain_home / ".cache" / f"{slug}-session-start.json"
    start_state = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                start_state = json.load(f)
        except Exception:
            pass

    start_commit = start_state.get("start_commit")
    start_time = start_state.get("start_time", get_current_iso_time())
    end_time = get_current_iso_time()

    current_commit = None
    current_branch = None
    commits_list = []
    files_changed = []
    diffstat = ""

    if repo_path.exists():
        ret, out, _ = run_git_cmd(["rev-parse", "HEAD"], cwd=repo_path)
        if ret == 0 and out:
            current_commit = out
        ret_b, out_b, _ = run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if ret_b == 0 and out_b:
            current_branch = out_b

        if start_commit and current_commit and start_commit != current_commit:
            # Commits entre inicio y fin
            ret_log, out_log, _ = run_git_cmd([
                "log", "--pretty=format:%h|%an|%ad|%s", "--date=iso", f"{start_commit}..{current_commit}"
            ], cwd=repo_path)
            if ret_log == 0 and out_log:
                for line in out_log.splitlines():
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commits_list.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })

            # Archivos modificados
            ret_f, out_f, _ = run_git_cmd(["diff", "--name-status", f"{start_commit}..{current_commit}"], cwd=repo_path)
            if ret_f == 0 and out_f:
                files_changed = [line.strip() for line in out_f.splitlines() if line.strip()]

            # Diffstat
            ret_s, out_s, _ = run_git_cmd(["diff", "--stat", f"{start_commit}..{current_commit}"], cwd=repo_path)
            if ret_s == 0 and out_s:
                diffstat = out_s
        elif current_commit:
            # Si no hubo commits nuevos, capturar status de archivos no commiteados o commit actual
            ret_st, out_st, _ = run_git_cmd(["status", "--short"], cwd=repo_path)
            if ret_st == 0 and out_st:
                files_changed = [line.strip() for line in out_st.splitlines() if line.strip()]
            # Último commit disponible
            ret_last, out_last, _ = run_git_cmd(["log", "-1", "--pretty=format:%h|%an|%ad|%s", "--date=iso"], cwd=repo_path)
            if ret_last == 0 and out_last:
                parts = out_last.split("|", 3)
                if len(parts) == 4:
                    commits_list.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    })

    tools_detected = detect_tool_versions(repo_path)

    result = {
        "slug": slug,
        "start_time": start_time,
        "end_time": end_time,
        "branch": current_branch or "N/A",
        "current_commit": current_commit,
        "start_commit": start_commit,
        "commits": commits_list,
        "files_changed": files_changed,
        "diffstat": diffstat,
        "tool_versions": tools_detected
    }

    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"=== HECHOS CAPTURADOS ({slug}) ===")
    print(f"- Intervalo: {start_time} -> {end_time}")
    print(f"- Rama git: {current_branch or 'N/A'}")
    print(f"- Commit actual: {current_commit or 'Sin repo git'}")
    print(f"- Commits nuevos: {len(commits_list)}")
    for c in commits_list:
        print(f"  * [{c['hash']}] {c['message']} ({c['date']})")
    print(f"- Archivos tocados: {len(files_changed)}")
    for f in files_changed[:10]:
        print(f"  * {f}")
    if len(files_changed) > 10:
        print(f"  * ... y {len(files_changed) - 10} más")
    if diffstat:
        print("\nDiffstat:")
        print(diffstat)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Captura hechos del sistema y Git para una sesión.")
    parser.add_argument("--slug", required=True, help="Slug del proyecto")
    parser.add_argument("--start", action="store_true", help="Fija la marca de inicio de sesión")
    parser.add_argument("--end", action="store_true", help="Captura los cambios producidos durante la sesión")
    parser.add_argument("--json", action="store_true", help="Devuelve el resultado en formato JSON")
    parser.add_argument("--dry-run", action="store_true", help="Modo simulación sin escribir estado")
    args = parser.parse_args()

    if args.start:
        sys.exit(start_capture(args.slug, args.dry_run))
    elif args.end:
        sys.exit(end_capture(args.slug, args.json, args.dry_run))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
