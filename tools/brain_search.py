#!/usr/bin/env python3
"""
brain-search - Búsqueda semántica/léxica con BM25 ponderado en Project Brain.
Uso: python brain-search.py "<consulta>" [--project <slug>] [--limit <N>] [--json]
"""

import sys
import json
import argparse
from pathlib import Path
from brain_common import get_brain_home
from brain_index import tokenize, build_index

K1 = 1.5
B = 0.75


def load_or_rebuild_index() -> dict:
    brain_home = get_brain_home()
    index_file = brain_home / ".cache" / "bm25-index.json"
    if not index_file.exists():
        build_index()
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        build_index()
        with open(index_file, "r", encoding="utf-8") as f:
            return json.load(f)


def search_bm25(query: str, project: str | None = None, limit: int = 5) -> list[dict]:
    index_data = load_or_rebuild_index()
    documents = index_data.get("documents", [])
    idf_map = index_data.get("idf", {})
    avg_dl = index_data.get("avg_dl", 100)

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    results = []

    for doc in documents:
        if project and doc.get("project") != project and doc.get("project") != "_global":
            continue

        score = 0.0
        doc_len = doc.get("doc_len", 1)
        term_freq = doc.get("term_freq", {})

        matched_terms = 0
        for token in query_tokens:
            if token in term_freq:
                matched_terms += 1
                tf = term_freq[token]
                idf = idf_map.get(token, 0.5)
                # BM25 formula
                numerator = tf * (K1 + 1.0)
                denominator = tf + K1 * (1.0 - B + B * (doc_len / avg_dl))
                score += idf * (numerator / denominator)

        if score >= 1.0 and matched_terms > 0:
            results.append({
                "score": round(score, 3),
                "matched_terms": matched_terms,
                "title": doc["title"],
                "path": doc["path"],
                "project": doc["project"],
                "type": doc["type"],
                "date": doc["date"],
                "questions": doc.get("questions", []),
                "evidence": doc.get("evidence", []),
                "snippet": doc.get("snippet", "").replace("\n", " ")[:200]
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Busca notas en Project Brain usando BM25 ponderado.")
    parser.add_argument("query", help="Texto o términos de búsqueda")
    parser.add_argument("--project", help="Filtrar por slug de proyecto", default=None)
    parser.add_argument("--limit", type=int, default=5, help="Número máximo de resultados")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado")
    args = parser.parse_args()

    results = search_bm25(args.query, args.project, args.limit)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print(f"[INFO] No se encontraron notas relevantes para: '{args.query}'")
        return 0

    print(f"\nResultados para: '{args.query}' (Top {len(results)})")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['score']}] {r['title']} ({r['project']})")
        print(f"   Ruta: {r['path']}")
        print(f"   Fecha: {r['date']} | Tipo: {r['type']}")
        if r.get("evidence"):
            print(f"   Evidencia: {', '.join([str(e) for e in r['evidence'][:2]])}")
        if r.get("questions"):
            print(f"   Responde: {r['questions'][0] if isinstance(r['questions'], list) else r['questions']}")
        print(f"   Extracto: {r['snippet']}...")
        print("-" * 60)

    return 0


if __name__ == "__main__":
    main()
