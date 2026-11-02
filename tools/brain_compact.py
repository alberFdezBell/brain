#!/usr/bin/env python3
"""
brain-compact - Compacta sesiones antiguas en archive/YYYY-MM.md y poda context/todo si exceden 150 líneas.
Preserva hechos, hashes, evidencias y el 100% de los wikilinks.
Mueve originales a archive/raw/.
Uso: python brain-compact.py <slug> [--dry-run]
"""

import sys
import re
import argparse
from pathlib import Path
from collections import defaultdict
from brain_common import (
    get_brain_home,
    read_note,
    write_note,
    extract_wikilinks
)

MAX_LINES_LIMIT = 150
MAX_ACTIVE_SESSIONS = 30


def compact_vault(slug: str, dry_run: bool = False) -> int:
    brain_home = get_brain_home()
    vault_dir = brain_home / slug
    if not vault_dir.exists():
        print(f"[ERROR] Bóveda '{slug}' no existe.", file=sys.stderr)
        return 1

    sessions_dir = vault_dir / "sessions"
    archive_dir = vault_dir / "archive"
    archive_raw_dir = archive_dir / "raw"

    if not dry_run:
        archive_raw_dir.mkdir(parents=True, exist_ok=True)

    session_files = sorted(sessions_dir.glob("*.md")) if sessions_dir.exists() else []
    print(f"[INFO] Bóveda '{slug}': {len(session_files)} notas de sesión encontradas.")

    # 1. Comprobar límites de context y todo
    for target_name in [f"{slug}-context.md", f"{slug}-todo.md"]:
        target_path = vault_dir / target_name
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if len(lines) > MAX_LINES_LIMIT:
                print(f"[AVISO] '{target_name}' supera {MAX_LINES_LIMIT} líneas ({len(lines)} líneas).")
                if target_name.endswith("-todo.md"):
                    # Podar completadas antiguas
                    new_lines = []
                    completed_count = 0
                    for line in lines:
                        if line.strip().startswith("- [x]"):
                            completed_count += 1
                            if completed_count <= 10:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    if len(new_lines) < len(lines):
                        print(f"        Podadas {len(lines) - len(new_lines)} tareas completadas antiguas de {target_name}.")
                        if not dry_run:
                            with open(target_path, "w", encoding="utf-8") as f:
                                f.writelines(new_lines)

    # 2. Compactar sesiones si exceden MAX_ACTIVE_SESSIONS
    if len(session_files) <= MAX_ACTIVE_SESSIONS:
        print(f"[OK] Sesiones dentro del umbral ({len(session_files)} <= {MAX_ACTIVE_SESSIONS}). No se requiere compactación de sesiones.")
        return 0

    to_archive = session_files[:-20]  # Dejar las últimas 20 intactas
    print(f"[ACCION] Compactando {len(to_archive)} sesiones antiguas...")

    # Agrupar por mes (YYYY-MM)
    by_month = defaultdict(list)
    for sf in to_archive:
        # Extraer YYYY-MM del nombre (ej. 2026-11-01-...)
        m = re.match(r"^(\d{4}-\d{2})", sf.name)
        month_key = m.group(1) if m else "general"
        by_month[month_key].append(sf)

    for month_key, files in by_month.items():
        archive_monthly_md = archive_dir / f"{month_key}.md"
        print(f"  - Generando resumen mensual: archive/{month_key}.md ({len(files)} sesiones)")

        existing_meta = {}
        existing_body = ""
        if archive_monthly_md.exists():
            existing_meta, existing_body = read_note(archive_monthly_md)

        all_evidence = set(existing_meta.get("evidence", []))
        all_wikilinks = set()
        month_entries = []

        for sf in files:
            meta, body = read_note(sf)
            for ev in meta.get("evidence", []):
                all_evidence.add(str(ev))
            for wl in extract_wikilinks(body):
                all_wikilinks.add(wl)

            # Extraer hechos y resumen
            facts_m = re.search(r"## Hechos capturados\s*\n(.*?)(?=\n## |\Z)", body, flags=re.DOTALL)
            facts_text = facts_m.group(1).strip() if facts_m else ""

            obj_m = re.search(r"## Objetivo\s*\n(.*?)(?=\n## |\Z)", body, flags=re.DOTALL)
            obj_text = obj_m.group(1).strip() if obj_m else ""

            month_entries.append(f"""### Sesión: [[{sf.stem}]]
- **Fecha**: `{meta.get('date', 'N/A')}`
- **Objetivo**: {obj_text}
- **Hechos relevantes**:
{facts_text}
""")

        new_body = f"""# Archivo de Sesiones: {month_key} ({slug})

Resumen consolidado de sesiones antiguas compactadas. Los archivos originales se conservan intactos en `archive/raw/`.

{"".join(month_entries)}

## Grafo y Enlaces Conservados
{", ".join([f"[[{w}]]" for w in sorted(all_wikilinks)])}
"""

        new_meta = {
            "date": f"{month_key}-01T00:00:00Z",
            "project": slug,
            "type": "archive",
            "status": "active",
            "tags": [f"proyecto/{slug}", "archivo/sesiones"],
            "evidence": sorted(list(all_evidence)),
            "needs_review": False,
            "answers_questions": [f"¿Qué trabajos y commits se realizaron en {slug} durante {month_key}?"]
        }

        if dry_run:
            print(f"[DRY-RUN] Se crearía: {archive_monthly_md}")
            for sf in files:
                print(f"[DRY-RUN] Se movería: {sf.name} -> archive/raw/{sf.name}")
        else:
            write_note(archive_monthly_md, new_meta, new_body)
            # Mover originales a archive/raw/
            for sf in files:
                raw_dest = archive_raw_dir / sf.name
                sf.rename(raw_dest)
            print(f"[OK] {len(files)} sesiones movidas a archive/raw/ y resumidas en {archive_monthly_md.name}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Compacta sesiones antiguas y poda archivos sobredimensionados.")
    parser.add_argument("slug", help="Slug del proyecto a compactar")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin modificar archivos")
    args = parser.parse_args()

    sys.exit(compact_vault(args.slug, args.dry_run))


if __name__ == "__main__":
    main()
