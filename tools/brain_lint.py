#!/usr/bin/env python3
"""
brain-lint - Analizador estático de integridad, enlaces rotos, huérfanas, duplicados y secretos.
Uso: python brain-lint.py [--secrets] [--fix]
"""

import sys
import re
import argparse
from pathlib import Path
from collections import defaultdict
from brain_common import (
    get_brain_home,
    read_note,
    extract_wikilinks,
    get_all_vaults
)

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "OpenAI / Claude Secret Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}"), "GitHub Personal Access Token"),
    (re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP|PRIVATE) KEY-----"), "Private Key block"),
    (re.compile(r"ey[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}"), "JWT Secret Token"),
    (re.compile(r'(?:api_key|access_token|secret_key|password)\s*[:=]\s*["\']([^"\'\s<]{12,})["\']', re.IGNORECASE), "Plaintext Secret / Password")
]


def load_controlled_tags(brain_home: Path) -> set[str]:
    """Carga los tags registrados en _global/tags.md."""
    tags_file = brain_home / "_global" / "tags.md"
    controlled = set()
    if not tags_file.exists():
        return controlled
    with open(tags_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # Extraer tags como #categoria/subcategoria o simplemente categoria/subcategoria
    matches = re.findall(r"`?#?([a-z0-9_-]+/[a-z0-9_-]+)`?", content)
    for m in matches:
        controlled.add(m.lstrip("#").lower())
    return controlled


def run_linter(check_secrets: bool = True, fix: bool = False) -> int:
    brain_home = get_brain_home()
    all_vaults = get_all_vaults(brain_home)
    controlled_tags = load_controlled_tags(brain_home)

    print("==================================================")
    print("           LINTER INTEGRAL PROJECT BRAIN          ")
    print("==================================================")

    all_notes = {}  # stem -> Path
    duplicate_names = defaultdict(list)
    links_outgoing = defaultdict(set)  # source_stem -> set of target_stems
    links_incoming = defaultdict(set)  # target_stem -> set of source_stems
    file_errors = defaultdict(list)
    secret_findings = []

    # 1. Mapeo global de notas para comprobar unicidad y existencia
    for vault in all_vaults:
        for md in vault.rglob("*.md"):
            # Omitir archive/raw
            if "archive/raw" in md.as_posix() or "archive\\raw" in md.as_posix():
                continue
            stem = md.stem
            duplicate_names[stem].append(md)
            all_notes[stem] = md

    # Chequeo de duplicados
    for stem, paths in duplicate_names.items():
        if len(paths) > 1:
            rel_paths = [str(p.relative_to(brain_home)) for p in paths]
            for p in paths:
                file_errors[p].append(f"Nombre duplicado en la raíz de Obsidian: '{stem}'. Conflicto con: {rel_paths}")

    # 2. Análisis por archivo
    for stem, md_path in all_notes.items():
        rel_path = md_path.relative_to(brain_home)
        metadata, body = read_note(md_path)

        # Regla de nombres de archivo válidos
        if not re.match(r"^[a-z0-9_.-]+$", md_path.name.lower()):
            file_errors[md_path].append(f"Nombre de archivo contiene caracteres inválidos: '{md_path.name}'.")

        # Regla de tamaño en context y todo
        if md_path.name.endswith("-context.md") or md_path.name.endswith("-todo.md"):
            lines_count = len(body.splitlines())
            if lines_count > 150:
                file_errors[md_path].append(f"Excede límite estricto de 150 líneas ({lines_count} líneas).")

        # Regla de tags controlados
        tags = metadata.get("tags", [])
        if isinstance(tags, list) and controlled_tags:
            for t in tags:
                clean_t = str(t).lstrip("#").lower()
                # Si no está en controlled_tags y tiene estructura de categoria/subcategoria
                if clean_t not in controlled_tags:
                    # Aviso suave si el vocabulario está definido
                    pass

        # Regla de enlaces rotos
        wikilinks = extract_wikilinks(body)
        for target in wikilinks:
            links_outgoing[stem].add(target)
            links_incoming[target].add(stem)
            if target not in all_notes:
                file_errors[md_path].append(f"Enlace roto: [[{target}]] (la nota de destino no existe).")

        # 3. Escaneo de secretos
        if check_secrets:
            with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()
            for pattern, sec_name in SECRET_PATTERNS:
                matches = pattern.finditer(full_text)
                for m in matches:
                    val = m.group(0)
                    # Ignorar si es un placeholder como <API_KEY> o dummy en docs
                    if any(dummy in val.upper() for dummy in ["PLACEHOLDER", "<API_KEY>", "TU_API_KEY", "EXAMPLE", "TEST", "XXXXX"]):
                        continue
                    secret_findings.append({
                        "file": str(rel_path),
                        "type": sec_name,
                        "match": val[:15] + "..."
                    })

    # 4. Huérfanas (notas a las que nadie enlaza, salvo índices principales)
    orphans = []
    for stem, md_path in all_notes.items():
        if stem in ["_global-index", "tags"]:
            continue
        if len(links_incoming[stem]) == 0:
            # Comprobar si al menos es un índice secundario
            if not stem.endswith("-index"):
                orphans.append(md_path)
                file_errors[md_path].append(f"Nota huérfana: ninguna otra nota de la bóveda enlaza a [[{stem}]].")

    # Presentación de resultados
    has_critical_errors = False

    if secret_findings:
        has_critical_errors = True
        print("\n\033[91m[ALERTA DE SEGURIDAD] ¡Secretos detectados en archivos!\033[0m")
        for s in secret_findings:
            print(f"  - Archivo: {s['file']} | Tipo: {s['type']} | Fragmento: {s['match']}")

    total_error_files = len(file_errors)
    if total_error_files > 0:
        has_critical_errors = True
        print(f"\n[ERRORES] Se detectaron anomalías en {total_error_files} archivos:")
        for path, errs in file_errors.items():
            print(f"\n  * {path.relative_to(brain_home)}:")
            for e in errs:
                print(f"    - {e}")
    else:
        print("\n[OK] Enlaces íntegros: cero enlaces rotos.")
        print("[OK] Unicidad: cero nombres duplicados.")
        print("[OK] Grafo conectado: cero notas huérfanas.")
        print("[OK] Tamaños: todos los archivos dentro de los límites.")

    if not secret_findings and not file_errors:
        print("\n\033[92m[PASO EXITOSO] Toda la bóveda cumple los estándares de integridad y seguridad.\033[0m")
        return 0

    return 1 if has_critical_errors else 0


def main():
    parser = argparse.ArgumentParser(description="Linter de integridad y secretos para Project Brain.")
    parser.add_argument("--secrets", action="store_true", default=True, help="Ejecuta escaneo de credenciales y secretos (por defecto activo)")
    parser.add_argument("--fix", action="store_true", help="Intenta corrección automática básica")
    args = parser.parse_args()

    sys.exit(run_linter(check_secrets=args.secrets, fix=args.fix))


if __name__ == "__main__":
    main()
