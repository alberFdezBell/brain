#!/usr/bin/env python3
"""
brain-ask - Construye un paquete de evidencia y línea de tiempo unificada para responder preguntas futuras.
Uso: python brain-ask.py "<pregunta>" [--project <slug>] [--since <YYYY-MM-DD>] [--json]
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from brain_common import (
    get_brain_home,
    read_note,
    load_vault_config,
    run_git_cmd
)
from brain_search import search_bm25


def extract_citable_snippets(body: str, query_terms: list[str]) -> list[str]:
    """Extrae bloques de texto y comandos ejecutables relevantes a la consulta."""
    snippets = []
    # 1. Extraer bloques de código bash o configuración
    code_blocks = re.findall(r"```(?:bash|sh|text|json|yaml)?\n(.*?)```", body, flags=re.DOTALL)
    for cb in code_blocks:
        cb_clean = cb.strip()
        if cb_clean:
            snippets.append(f"```bash\n{cb_clean}\n```")

    # 2. Extraer oraciones que contengan términos de la consulta
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip() and not p.startswith("#")]
    for p in paragraphs:
        p_lower = p.lower()
        if any(term in p_lower for term in query_terms if len(term) > 3):
            clean_p = re.sub(r"<!--.*?-->", "", p, flags=re.DOTALL).strip()
            if len(clean_p) > 20:
                snippets.append(clean_p)

    return snippets[:4]


def get_git_history_for_evidence(repo_path: Path, evidence_items: list[str], since_date: str | None = None) -> list[dict]:
    """Consulta git log para archivos o hashes mencionados en la evidencia."""
    git_events = []
    if not repo_path or not repo_path.exists():
        return git_events

    # Recorrer items de evidencia que sean archivos o commits
    for item in evidence_items:
        item_str = str(item).strip()
        if "commit:" in item_str.lower():
            m = re.search(r"([0-9a-f]{7,40})", item_str, re.IGNORECASE)
            if m:
                c_hash = m.group(1)
                ret, out, _ = run_git_cmd(["log", "-1", "--pretty=format:%h|%ad|%an|%s", "--date=iso", c_hash], cwd=repo_path)
                if ret == 0 and out:
                    parts = out.split("|", 3)
                    if len(parts) == 4:
                        git_events.append({
                            "type": "commit",
                            "hash": parts[0],
                            "date": parts[1],
                            "author": parts[2],
                            "message": parts[3],
                            "source_file": item_str
                        })
        elif "/" in item_str or "." in item_str:
            # Es una ruta de archivo
            file_path = repo_path / item_str
            if file_path.exists():
                git_args = ["log", "-5", "--pretty=format:%h|%ad|%an|%s", "--date=iso"]
                if since_date:
                    git_args.append(f"--since={since_date}")
                git_args.extend(["--", item_str])
                ret, out, _ = run_git_cmd(git_args, cwd=repo_path)
                if ret == 0 and out:
                    for line in out.splitlines():
                        parts = line.split("|", 3)
                        if len(parts) == 4:
                            git_events.append({
                                "type": "commit",
                                "hash": parts[0],
                                "date": parts[1],
                                "author": parts[2],
                                "message": parts[3],
                                "source_file": item_str
                            })

    # Deduplicar por hash
    seen_hashes = set()
    deduped = []
    for ev in git_events:
        if ev["hash"] not in seen_hashes:
            seen_hashes.add(ev["hash"])
            deduped.append(ev)

    return deduped


def build_evidence_package(question: str, project: str | None = None, since: str | None = None) -> dict:
    brain_home = get_brain_home()

    # Detección inteligente de proyectos mencionados en la consulta (incluyendo menciones @slug)
    from brain_common import get_all_vaults
    known_vaults = [v.name for v in get_all_vaults(brain_home) if v.name != "_global"]
    matched_project = project
    if not matched_project:
        # Prioridad a menciones explícitas con @proyecto
        m_mention = re.search(r"@([a-zA-Z0-9_-]+)", question)
        if m_mention:
            cand = m_mention.group(1).lower()
            for v_name in known_vaults:
                if v_name.lower() == cand:
                    matched_project = v_name
                    break

        if not matched_project:
            q_lower = question.lower()
            for v_name in known_vaults:
                if re.search(r"\b" + re.escape(v_name.lower()) + r"\b", q_lower):
                    matched_project = v_name
                    break

    results = search_bm25(question, project=matched_project, limit=5)

    # Si se mencionó un proyecto conocido y context/index no aparecieron en el top, incorporarlos
    if matched_project and (brain_home / matched_project).exists():
        v_dir = brain_home / matched_project
        ctx_file = v_dir / f"{matched_project}-context.md"
        if ctx_file.exists():
            rel_ctx = str(ctx_file.relative_to(brain_home)).replace("\\", "/")
            if not any(r["path"] == rel_ctx for r in results):
                meta_ctx, body_ctx = read_note(ctx_file)
                results.insert(0, {
                    "score": 10.0,
                    "matched_terms": 1,
                    "title": ctx_file.stem,
                    "path": rel_ctx,
                    "project": matched_project,
                    "type": "context",
                    "date": meta_ctx.get("date", ""),
                    "questions": meta_ctx.get("answers_questions", []),
                    "evidence": meta_ctx.get("evidence", []),
                    "snippet": body_ctx[:400].replace("\n", " ")
                })

        # Incorporar las sesiones más recientes del proyecto para responder con precisión sobre últimos cambios
        sessions_dir = v_dir / "sessions"
        if sessions_dir.exists():
            sess_files = sorted(sessions_dir.glob("*.md"), reverse=True)
            for sf in reversed(sess_files[:2]):
                rel_sf = str(sf.relative_to(brain_home)).replace("\\", "/")
                results = [r for r in results if r["path"] != rel_sf]
                meta_s, body_s = read_note(sf)
                results.insert(1, {
                    "score": 9.5,
                    "matched_terms": 1,
                    "title": sf.stem,
                    "path": rel_sf,
                    "project": matched_project,
                    "type": "session",
                    "date": meta_s.get("date", ""),
                    "questions": meta_s.get("answers_questions", []),
                    "evidence": meta_s.get("evidence", []),
                    "snippet": body_s[:400].replace("\n", " ")
                })

    if not results or results[0]["score"] < 0.5:
        return {
            "question": question,
            "status": "insufficient_evidence",
            "message": "No se encontró evidencia suficiente ni notas relevantes en Project Brain para responder a esta pregunta con certeza.",
            "notes": [],
            "timeline": [],
            "gaps": []
        }

    query_terms = [t for t in re.findall(r"\w+", question.lower()) if len(t) >= 2]
    relevant_notes = []
    all_evidence = []
    gaps_collected = []
    timeline_events = []

    repo_path = None
    if project:
        vault_cfg = load_vault_config(brain_home / project)
        if "repo_path" in vault_cfg:
            repo_path = Path(vault_cfg["repo_path"])

    for r in results:
        note_file = brain_home / r["path"]
        if not note_file.exists():
            continue
        meta, body = read_note(note_file)

        # Si aún no tenemos repo_path, inferirlo
        if not repo_path:
            v_dir = brain_home / r["project"]
            v_cfg = load_vault_config(v_dir)
            if "repo_path" in v_cfg:
                repo_path = Path(v_cfg["repo_path"])

        snippets = extract_citable_snippets(body, query_terms)
        note_evidence = meta.get("evidence", [])
        if isinstance(note_evidence, list):
            all_evidence.extend(note_evidence)

        # Buscar lagunas en la nota
        lagunas_m = re.search(r"## Lagunas\s*\n(.*?)(?=\n## |\Z)", body, flags=re.DOTALL)
        if lagunas_m:
            l_text = lagunas_m.group(1).strip()
            clean_l = re.sub(r"<!--.*?-->", "", l_text).strip()
            if clean_l and "ninguna" not in clean_l.lower():
                gaps_collected.append(f"[{r['title']}] {clean_l}")

        note_date = meta.get("date", r["date"])
        relevant_notes.append({
            "title": r["title"],
            "path": r["path"],
            "project": r["project"],
            "type": r["type"],
            "date": note_date,
            "score": r["score"],
            "answers_questions": meta.get("answers_questions", []),
            "evidence": note_evidence,
            "snippets": snippets
        })

        # Añadir nota a la línea de tiempo
        timeline_events.append({
            "timestamp": note_date,
            "type": f"note_{r['type']}",
            "title": r["title"],
            "detail": f"Nota: [[{r['title']}]] ({r['path']})"
        })

    # Consultar Git para asociar commits
    git_commits = []
    if repo_path and repo_path.exists():
        git_commits = get_git_history_for_evidence(repo_path, all_evidence, since_date=since)
        for c in git_commits:
            timeline_events.append({
                "timestamp": c["date"],
                "type": "git_commit",
                "title": f"Commit {c['hash']}: {c['message']}",
                "detail": f"Hash: {c['hash']} | Autor: {c['author']} | Archivo: {c.get('source_file', '')}"
            })

    # Ordenar línea de tiempo (lo más reciente primero)
    timeline_events.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)

    return {
        "question": question,
        "status": "success",
        "project": project or "multi-project",
        "notes": relevant_notes,
        "timeline": timeline_events,
        "git_commits": git_commits,
        "gaps": gaps_collected
    }


def main():
    parser = argparse.ArgumentParser(description="Responde preguntas consultando evidencia y línea de tiempo.")
    parser.add_argument("question", help="Pregunta en lenguaje natural")
    parser.add_argument("--project", help="Filtrar por proyecto específico", default=None)
    parser.add_argument("--since", help="Filtrar por fecha mínima (YYYY-MM-DD)", default=None)
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado")
    args = parser.parse_args()

    pkg = build_evidence_package(args.question, args.project, args.since)

    if args.json:
        print(json.dumps(pkg, indent=2, ensure_ascii=False))
        return 0

    print("==================================================================")
    print("                PAQUETE DE EVIDENCIA PROJECT BRAIN                ")
    print("==================================================================")
    print(f"Pregunta: {pkg['question']}")
    print(f"Estado:   {pkg['status']}")
    print("-" * 66)

    if pkg["status"] == "insufficient_evidence":
        print(f"\n[AVISO] {pkg['message']}")
        return 0

    print("\n1. NOTAS PRINCIPALES Y EVIDENCIA DISPONIBLE:")
    for i, n in enumerate(pkg["notes"], 1):
        print(f"\n[{i}] {n['title']} (Proyecto: {n['project']} | Tipo: {n['type']})")
        print(f"    Fecha: {n['date']}")
        print(f"    Ruta:  {n['path']}")
        if n["evidence"]:
            print(f"    Evidencia registrada: {', '.join([str(e) for e in n['evidence']])}")
        if n["snippets"]:
            print("    Fragmentos citables:")
            for sn in n["snippets"]:
                indented = "\n      ".join(sn.splitlines())
                print(f"      - {indented}")

    if pkg["timeline"]:
        print("\n2. LÍNEA DE TIEMPO UNIFICADA (NOTAS Y COMMITS):")
        for ev in pkg["timeline"]:
            ts = ev.get("timestamp", "N/A")
            print(f"  [{ts}] [{ev['type'].upper()}] {ev['title']}")
            if ev.get("detail"):
                print(f"       -> {ev['detail']}")

    if pkg["gaps"]:
        print("\n3. LAGUNAS O DUDAS CONOCIDAS REGISTRADAS:")
        for g in pkg["gaps"]:
            print(f"  - {g}")
    else:
        print("\n3. LAGUNAS: Ninguna registrada en las notas relevantes.")

    print("\n==================================================================")
    return 0


if __name__ == "__main__":
    main()
