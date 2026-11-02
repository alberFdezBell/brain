#!/usr/bin/env python3
"""
brain-init - Inicializa una nueva bóveda de proyecto en Project Brain.
Uso: python brain-init.py <slug> [--repo-path <ruta>] [--dry-run]
"""

import sys
import re
import argparse
from pathlib import Path
from brain_common import (
    get_brain_home,
    get_current_iso_time,
    save_vault_config,
    read_note,
    write_note
)

VALID_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def init_vault(slug: str, repo_path: str | None = None, dry_run: bool = False) -> int:
    slug = slug.lower().strip()
    if not VALID_SLUG_PATTERN.match(slug):
        print(f"[ERROR] Slug inválido: '{slug}'. Use solo minúsculas, números y guiones.", file=sys.stderr)
        return 1

    brain_home = get_brain_home()
    vault_dir = brain_home / slug

    if vault_dir.exists():
        print(f"[INFO] La bóveda '{slug}' ya existe en: {vault_dir}. No se modifica nada.")
        return 0

    target_repo = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
    print(f"[ACCION] Inicializando bóveda '{slug}'...")
    print(f"         Destino: {vault_dir}")
    print(f"         Repo path: {target_repo}")

    if dry_run:
        print("[DRY-RUN] Operación simulada completada exitosamente.")
        return 0

    # Crear subcarpetas
    subdirs = ["decisions", "sessions", "learnings", "references", "archive", "archive/raw"]
    for sub in subdirs:
        (vault_dir / sub).mkdir(parents=True, exist_ok=True)

    # Crear .brain.yml
    now_iso = get_current_iso_time()
    vault_cfg = {
        "schema_version": "1",
        "slug": slug,
        "created": now_iso,
        "repo_path": str(target_repo),
        "aliases": slug
    }
    save_vault_config(vault_dir, vault_cfg)

    # Copiar y personalizar plantillas base
    templates_dir = brain_home / "templates"

    def apply_tpl(tpl_name: str, target_file: Path, extra_vars: dict, pending_init: bool = False):
        tpl_path = templates_dir / tpl_name
        if not tpl_path.exists():
            print(f"[AVISO] Plantilla no encontrada: {tpl_path}")
            return
        meta, body = read_note(tpl_path)
        # Reemplazar variables en body y metadata
        body_str = body
        for k, v in extra_vars.items():
            body_str = body_str.replace(f"{{{{{k}}}}}", str(v))
        meta_replaced = {}
        for mk, mv in meta.items():
            if isinstance(mv, str):
                for k, v in extra_vars.items():
                    mv = mv.replace(f"{{{{{k}}}}}", str(v))
            meta_replaced[mk] = mv
        meta_replaced["project"] = slug
        meta_replaced["date"] = now_iso

        if pending_init:
            meta_replaced["needs_review"] = True
            body_str = f"> [!WARNING] INICIALIZACIÓN PENDIENTE: Complete los campos obligatorios y la evidencia antes de comenzar la sesión.\n\n" + body_str.lstrip()

        write_note(target_file, meta_replaced, body_str)

    subs = {
        "PROJECT": slug,
        "DATE": now_iso,
        "REPO_PATH": str(target_repo)
    }

    apply_tpl("index.md", vault_dir / f"{slug}-index.md", subs, pending_init=True)
    apply_tpl("context.md", vault_dir / f"{slug}-context.md", subs, pending_init=True)
    apply_tpl("todo.md", vault_dir / f"{slug}-todo.md", subs, pending_init=False)

    # Enlazar en _global-index.md
    global_index = brain_home / "_global" / "_global-index.md"
    if global_index.exists():
        with open(global_index, "r", encoding="utf-8", errors="replace") as f:
            g_content = f.read()
        wikilink = f"[[{slug}-index|{slug}]]"
        if wikilink not in g_content and f"[[{slug}-index]]" not in g_content:
            section_marker = "## Proyectos Activos"
            if section_marker in g_content:
                parts = g_content.split(section_marker, 1)
                new_g = f"{parts[0]}{section_marker}\n- {wikilink}{parts[1]}"
            else:
                new_g = f"{g_content}\n\n## Proyectos Activos\n- {wikilink}\n"
            with open(global_index, "w", encoding="utf-8") as f:
                f.write(new_g)
            print(f"[OK] Bóveda '{slug}' enlazada en _global-index.md")

    print(f"[EXITO] Bóveda '{slug}' creada y lista.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Inicializa una bóveda de proyecto en Project Brain.")
    parser.add_argument("slug", help="Identificador único del proyecto (minúsculas, números, guiones)")
    parser.add_argument("--repo-path", help="Ruta local al repositorio Git del proyecto", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simula la creación sin escribir archivos")
    args = parser.parse_args()

    sys.exit(init_vault(args.slug, args.repo_path, args.dry_run))


if __name__ == "__main__":
    main()
