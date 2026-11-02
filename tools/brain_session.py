#!/usr/bin/env python3
"""
brain-session - Genera el esqueleto de una nota de sesión con hechos capturados de Git.
Uso: python brain-session.py --slug <slug> [--title <titulo>] [--dry-run]
"""

import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from brain_common import (
    get_brain_home,
    get_current_iso_time,
    load_vault_config,
    read_note,
    write_note,
    run_git_cmd
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def create_session_note(slug: str, title: str | None = None, dry_run: bool = False) -> int:
    brain_home = get_brain_home()
    vault_dir = brain_home / slug
    if not vault_dir.exists():
        print(f"[ERROR] Bóveda '{slug}' no existe en {vault_dir}.", file=sys.stderr)
        return 1

    cfg = load_vault_config(vault_dir)
    repo_path = Path(cfg.get("repo_path", Path.cwd())).resolve()

    now = datetime.now().astimezone()
    now_iso = now.isoformat()
    timestamp_prefix = now.strftime("%Y-%m-%d-%H%M")

    # Leer estado de inicio si existe
    cache_file = brain_home / ".cache" / f"{slug}-session-start.json"
    start_state = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                start_state = json.load(f)
        except Exception:
            pass

    start_commit = start_state.get("start_commit")
    start_time = start_state.get("start_time", now_iso)

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
            ret_log, out_log, _ = run_git_cmd([
                "log", "--pretty=format:%h|%an|%ad|%s", "--date=iso", f"{start_commit}..{current_commit}"
            ], cwd=repo_path)
            if ret_log == 0 and out_log:
                for line in out_log.splitlines():
                    p = line.split("|", 3)
                    if len(p) == 4:
                        commits_list.append({"hash": p[0], "author": p[1], "date": p[2], "message": p[3]})

            ret_f, out_f, _ = run_git_cmd(["diff", "--name-status", f"{start_commit}..{current_commit}"], cwd=repo_path)
            if ret_f == 0 and out_f:
                files_changed = [line.strip() for line in out_f.splitlines() if line.strip()]

            ret_s, out_s, _ = run_git_cmd(["diff", "--stat", f"{start_commit}..{current_commit}"], cwd=repo_path)
            if ret_s == 0 and out_s:
                diffstat = out_s
        elif current_commit:
            ret_last, out_last, _ = run_git_cmd(["log", "-1", "--pretty=format:%h|%an|%ad|%s", "--date=iso"], cwd=repo_path)
            if ret_last == 0 and out_last:
                p = out_last.split("|", 3)
                if len(p) == 4:
                    commits_list.append({"hash": p[0], "author": p[1], "date": p[2], "message": p[3]})
            ret_st, out_st, _ = run_git_cmd(["status", "--short"], cwd=repo_path)
            if ret_st == 0 and out_st:
                files_changed = [line.strip() for line in out_st.splitlines() if line.strip()]

    # Título por defecto
    clean_title = title if title else "avance-de-sesion"
    title_slug = slugify(clean_title)
    filename = f"{timestamp_prefix}-{title_slug}.md"
    target_path = vault_dir / "sessions" / filename

    # Bloque de hechos capturados
    facts_lines = [
        f"- **Intervalo**: `{start_time}` a `{now_iso}`",
        f"- **Rama Git**: `{current_branch or 'N/A'}`",
        f"- **HEAD Commit**: `{current_commit or 'Sin repo git'}`"
    ]
    if commits_list:
        facts_lines.append("- **Commits registrados**:")
        for c in commits_list:
            facts_lines.append(f"  - `{c['hash']}`: {c['message']} ({c['date']})")
    if files_changed:
        facts_lines.append("- **Archivos tocados**:")
        for f in files_changed[:15]:
            facts_lines.append(f"  - `{f}`")
        if len(files_changed) > 15:
            facts_lines.append(f"  - *... y {len(files_changed) - 15} archivos adicionales*")
    if diffstat:
        facts_lines.append("```text\n" + diffstat + "\n```")

    captured_facts_block = "\n".join(facts_lines)

    # Evidencia inicial
    evidence = []
    if current_commit:
        evidence.append(f"commit: {current_commit[:7]}")
    for c in commits_list[:3]:
        evidence.append(f"commit: {c['hash']}")
    for f in files_changed[:3]:
        parts = f.split(None, 1)
        path_name = parts[1] if len(parts) > 1 else parts[0]
        evidence.append(path_name)

    if not evidence:
        evidence = [f"{slug}-context.md"]

    metadata = {
        "date": now_iso,
        "project": slug,
        "type": "session",
        "status": "active",
        "tags": [f"proyecto/{slug}", "sesion/desarrollo"],
        "evidence": evidence,
        "needs_review": False,
        "answers_questions": [f"¿Qué cambios técnicos se realizaron en {slug} el {now.strftime('%Y-%m-%d')}?"]
    }

    body = f"""# {clean_title}

## Objetivo
<!-- Detalla en al menos 2 oraciones el objetivo técnico, requerimiento o motivo de esta sesión. -->

## Qué se hizo
<!-- Enumera las tareas completadas y modificaciones realizadas. -->

## Cómo se hizo
<!-- Pasos reproducibles, comandos exactos ejecutados y orden de aplicación. -->

```bash
# Comandos ejecutados
```

## Resultado verificado
<!-- Cómo se comprobó el funcionamiento: logs, tests, comprobación en navegador o consola. -->

## Hechos capturados
{captured_facts_block}

## Problemas y soluciones
<!-- Obstáculos encontrados y resolución aplicada. Si no hubo: Ninguno detectado en esta sesión. -->

## Pendientes
<!-- Tareas que quedan para sesiones posteriores. -->

## Lagunas
<!-- Aspectos pendientes de aclaración o datos supuestos. Si todo está claro: Ninguna laguna identificada. -->

## Relacionado
- Índice: [[{slug}-index]]
"""

    if dry_run:
        print(f"[DRY-RUN] Se crearía la nota: {target_path}")
        print(body[:300] + "\n...")
        return 0

    write_note(target_path, metadata, body)
    print(f"[EXITO] Nota de sesión creada en: {target_path}")

    # Enlazar en <slug>-index.md
    index_file = vault_dir / f"{slug}-index.md"
    if index_file.exists():
        note_name = target_path.stem
        with open(index_file, "r", encoding="utf-8", errors="replace") as f:
            idx_content = f.read()
        if f"[[{note_name}]]" not in idx_content:
            marker = "## Sesiones Recientes"
            link_entry = f"- [[{note_name}|{clean_title}]] ({now.strftime('%Y-%m-%d %H:%M')})"
            if marker in idx_content:
                parts = idx_content.split(marker, 1)
                new_idx = f"{parts[0]}{marker}\n{link_entry}{parts[1]}"
            else:
                new_idx = f"{idx_content}\n\n{marker}\n{link_entry}\n"
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(new_idx)
            print(f"[OK] Sesión enlazada en {index_file.name}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Genera la nota de sesión para Project Brain.")
    parser.add_argument("--slug", required=True, help="Slug del proyecto")
    parser.add_argument("--title", help="Título descriptivo de la sesión", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir")
    args = parser.parse_args()

    sys.exit(create_session_note(args.slug, args.title, args.dry_run))


if __name__ == "__main__":
    main()
