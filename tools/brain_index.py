#!/usr/bin/env python3
"""
brain-index - Construye un índice invertido BM25 con pesos para Project Brain.
Genera .cache/bm25-index.json (100% Python stdlib).
Uso: python brain-index.py [--force]
"""

import sys
import re
import math
import json
import argparse
from pathlib import Path
from brain_common import (
    get_brain_home,
    read_note,
    get_all_vaults
)

TOKEN_RE = re.compile(r"\b\w{2,}\b")


STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero",
    "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "tambien", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra",
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "the",
    "and", "in", "of", "to", "is", "for", "on", "with", "as", "by", "at",
    "cómo", "como", "cuándo", "cuando", "dónde", "donde", "cuál", "cual",
    "cuáles", "cuales", "quién", "quien", "qué", "hicimos", "hizo", "hace"
}


def tokenize(text: str) -> list[str]:
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    return [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]


def build_index(force: bool = False) -> int:
    brain_home = get_brain_home()
    cache_dir = brain_home / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_file = cache_dir / "bm25-index.json"

    documents = []
    doc_id = 0

    print("[INFO] Indexando bóvedas en Project Brain...")

    for vault in get_all_vaults(brain_home):
        slug = vault.name
        for md_file in vault.rglob("*.md"):
            # Excluir archive/raw si existe
            if "archive/raw" in md_file.as_posix() or "archive\\raw" in md_file.as_posix():
                continue

            metadata, body = read_note(md_file)
            title = md_file.stem
            tags = metadata.get("tags", [])
            questions = metadata.get("answers_questions", [])
            evidence = metadata.get("evidence", [])
            date_val = metadata.get("date", "")
            note_type = metadata.get("type", "note")

            rel_path = str(md_file.relative_to(brain_home)).replace("\\", "/")

            # Ponderación de términos
            weighted_tokens = []

            # Título (x3)
            title_tokens = tokenize(title.replace("-", " "))
            weighted_tokens.extend(title_tokens * 3)

            # answers_questions (x2.5 -> aprox x3)
            q_text = " ".join([str(q) for q in questions]) if isinstance(questions, list) else str(questions)
            q_tokens = tokenize(q_text)
            weighted_tokens.extend(q_tokens * 3)

            # tags (x2)
            tags_text = " ".join([str(t) for t in tags]) if isinstance(tags, list) else str(tags)
            tags_tokens = tokenize(tags_text)
            weighted_tokens.extend(tags_tokens * 2)

            # evidence (x1.5 -> aprox x2)
            ev_text = " ".join([str(e) for e in evidence]) if isinstance(evidence, list) else str(evidence)
            ev_tokens = tokenize(ev_text)
            weighted_tokens.extend(ev_tokens * 2)

            # Body (x1)
            body_tokens = tokenize(body)
            weighted_tokens.extend(body_tokens)

            # Frecuencia de términos en doc
            term_freq = {}
            for t in weighted_tokens:
                term_freq[t] = term_freq.get(t, 0) + 1

            doc_len = len(weighted_tokens)

            documents.append({
                "id": doc_id,
                "path": rel_path,
                "project": slug,
                "type": note_type,
                "title": title,
                "date": date_val,
                "questions": questions,
                "evidence": evidence,
                "doc_len": doc_len,
                "term_freq": term_freq,
                "snippet": body[:400]
            })
            doc_id += 1

    total_docs = len(documents)
    if total_docs == 0:
        index_data = {"total_docs": 0, "avg_dl": 0, "idf": {}, "documents": []}
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False)
        print("[AVISO] No se encontraron documentos para indexar. Índice vacío creado.")
        return 0

    avg_dl = sum(d["doc_len"] for d in documents) / total_docs

    # Inverted index con Document Frequency (df)
    df = {}
    for doc in documents:
        for term in doc["term_freq"]:
            df[term] = df.get(term, 0) + 1

    # Calcular IDF para cada término: log(1 + (N - df + 0.5) / (df + 0.5))
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log(1.0 + (total_docs - freq + 0.5) / (freq + 0.5))

    index_data = {
        "total_docs": total_docs,
        "avg_dl": avg_dl,
        "idf": idf,
        "documents": documents
    }

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False)

    print(f"[EXITO] Índice generado: {total_docs} documentos indexados ({len(df)} términos únicos).")
    print(f"        Guardado en: {index_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Construye el índice de búsqueda BM25 para Project Brain.")
    parser.add_argument("--force", action="store_true", help="Fuerza la reindexación completa")
    args = parser.parse_args()

    sys.exit(build_index(args.force))


if __name__ == "__main__":
    main()
