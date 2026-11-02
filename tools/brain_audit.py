#!/usr/bin/env python3
"""
brain-audit - Auditoría periódica profunda de salud, calidad y enlaces de toda la bóveda.
Genera un informe consolidado en _global/audit-YYYY-MM.md.
Uso: python brain-audit.py [--save]
"""

import sys
import re
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from brain_common import (
    get_brain_home,
    get_all_vaults,
    read_note,
    extract_wikilinks,
    write_note
)
from brain_quality import evaluate_note, load_vault_config
from brain_lint import load_controlled_tags


def run_audit(save_report: bool = False) -> int:
    brain_home = get_brain_home()
    all_vaults = get_all_vaults(brain_home)
    controlled_tags = load_controlled_tags(brain_home)

    now = datetime.now()
    month_slug = now.strftime("%Y-%m")
    audit_date_str = now.strftime("%Y-%m-%d %H:%M:%S")

    print("==================================================")
    print(f"      AUDITORÍA DE SALUD PROJECT BRAIN ({month_slug})    ")
    print("==================================================")

    all_notes = {}
    links_incoming = defaultdict(set)
    links_outgoing = defaultdict(set)
    broken_links = []
    orphan_notes = []
    obsolete_without_successor = []
    tags_unknown = []
    quality_scores = []
    low_quality_notes = []

    # 1. Recolección de notas
    for vault in all_vaults:
        slug = vault.name
        cfg = load_vault_config(vault)
        repo_path = Path(cfg["repo_path"]) if "repo_path" in cfg else None

        for md in vault.rglob("*.md"):
            if "archive/raw" in md.as_posix() or "archive\\raw" in md.as_posix():
                continue
            stem = md.stem
            all_notes[stem] = (md, vault, repo_path)

    # 2. Análisis exhaustivo
    for stem, (md, vault, repo_path) in all_notes.items():
        meta, body = read_note(md)
        note_type = meta.get("type", "unknown")
        status = meta.get("status", "active")
        rel_path = md.relative_to(brain_home)

        # Enlaces
        wikilinks = extract_wikilinks(body)
        for target in wikilinks:
            links_outgoing[stem].add(target)
            links_incoming[target].add(stem)
            if target not in all_notes:
                broken_links.append((str(rel_path), target))

        # Obsoletas sin sucesora
        if status in ["obsolete", "superseded"]:
            if "superseded_by" not in meta or not meta["superseded_by"]:
                obsolete_without_successor.append(str(rel_path))

        # Tags fuera de vocabulario
        tags = meta.get("tags", [])
        if isinstance(tags, list):
            for t in tags:
                clean_t = str(t).lstrip("#").lower()
                if controlled_tags and clean_t not in controlled_tags:
                    tags_unknown.append((str(rel_path), clean_t))

        # Calidad
        if note_type in ["session", "decision", "learning", "concept"]:
            score, blocking, _ = evaluate_note(md, repo_path)
            quality_scores.append(score)
            if score < 85 or len(blocking) > 0:
                low_quality_notes.append((str(rel_path), score, blocking))

    # Huérfanas
    for stem, (md, _, _) in all_notes.items():
        if stem in ["_global-index", "tags"] or stem.endswith("-index"):
            continue
        if len(links_incoming[stem]) == 0:
            orphan_notes.append(str(md.relative_to(brain_home)))

    avg_score = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 100.0

    print(f"\n- Total notas analizadas: {len(all_notes)}")
    print(f"- Puntuación media de calidad: {avg_score}/100")
    print(f"- Notas bajo el umbral de calidad (<85): {len(low_quality_notes)}")
    print(f"- Enlaces rotos: {len(broken_links)}")
    print(f"- Notas huérfanas: {len(orphan_notes)}")
    print(f"- Notas obsoletas sin sucesora: {len(obsolete_without_successor)}")
    print(f"- Tags fuera de vocabulario: {len(tags_unknown)}")

    # Generar Markdown del reporte
    report_body = f"""# Auditoría de Salud: {month_slug}

- **Fecha de ejecución**: `{audit_date_str}`
- **Total de notas**: {len(all_notes)}
- **Puntuación media de calidad**: {avg_score} / 100

## Métricas Globales
| Métrica | Valor | Estado |
| :--- | :--- | :--- |
| Puntuación Media | {avg_score} / 100 | {"[OPTIMO]" if avg_score >= 90 else "[REVISAR]"} |
| Notas Bajo Umbral | {len(low_quality_notes)} | {"[OK]" if len(low_quality_notes) == 0 else "[ACCION]"} |
| Enlaces Rotos | {len(broken_links)} | {"[OK]" if len(broken_links) == 0 else "[ACCION]"} |
| Notas Huérfanas | {len(orphan_notes)} | {"[OK]" if len(orphan_notes) == 0 else "[ACCION]"} |
| Obsoletas sin Sucesora | {len(obsolete_without_successor)} | {"[OK]" if len(obsolete_without_successor) == 0 else "[AVISO]"} |

## Detalle de Hallazgos

### 1. Notas con Calidad Insuficiente (<85)
"""
    if low_quality_notes:
        for p, sc, bl in low_quality_notes:
            report_body += f"\n- **{p}** ({sc}/100):\n"
            for b in bl:
                report_body += f"  - {b}\n"
    else:
        report_body += "\nTodas las notas evaluadas superan el umbral mínimo de calidad.\n"

    report_body += "\n### 2. Enlaces Rotos\n"
    if broken_links:
        for src, tgt in broken_links:
            report_body += f"- `{src}` -> enlace a `[[{tgt}]]` inexistente.\n"
    else:
        report_body += "\nCero enlaces rotos detectados en toda la bóveda.\n"

    report_body += "\n### 3. Notas Huérfanas\n"
    if orphan_notes:
        for o in orphan_notes:
            report_body += f"- `{o}` no recibe enlaces entrantes.\n"
    else:
        report_body += "\nCero notas huérfanas: topología del grafo completamente conectada.\n"

    report_meta = {
        "date": now.astimezone().isoformat(),
        "project": "_global",
        "type": "audit",
        "status": "active",
        "tags": ["auditoria/salud", "moc/indice"],
        "evidence": ["tools/brain-audit.py"],
        "needs_review": len(broken_links) > 0 or len(low_quality_notes) > 0,
        "answers_questions": [f"¿Cuál fue el estado y puntuación de salud de Project Brain en {month_slug}?"]
    }

    if save_report:
        report_file = brain_home / "_global" / f"audit-{month_slug}.md"
        write_note(report_file, report_meta, report_body)
        print(f"\n[OK] Informe de auditoría guardado en: {report_file.relative_to(brain_home)}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Audita la salud, calidad y enlaces de Project Brain.")
    parser.add_argument("--save", action="store_true", default=False, help="Guarda el reporte en _global/audit-YYYY-MM.md")
    args = parser.parse_args()

    sys.exit(run_audit(save_report=args.save))


if __name__ == "__main__":
    main()
