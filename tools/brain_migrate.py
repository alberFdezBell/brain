#!/usr/bin/env python3
"""
brain-migrate - Aplica migraciones incrementales de esquema en Project Brain.
Comprueba schema/VERSION y actualiza cada bóveda.
Uso: python brain-migrate.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path
from brain_common import (
    get_brain_home,
    get_all_vaults,
    load_vault_config,
    save_vault_config
)


def get_current_schema_version(brain_home: Path) -> int:
    ver_file = brain_home / "schema" / "VERSION"
    if ver_file.exists():
        try:
            return int(ver_file.read_text(encoding="utf-8").strip())
        except Exception:
            return 1
    return 1


def run_migrations(dry_run: bool = False) -> int:
    brain_home = get_brain_home()
    target_version = get_current_schema_version(brain_home)
    vaults = get_all_vaults(brain_home)

    print("==================================================")
    print(f"      MIGRACIONES DE ESQUEMA PROJECT BRAIN (v{target_version})")
    print("==================================================")

    pending_count = 0
    for v in vaults:
        cfg = load_vault_config(v)
        vault_ver = int(cfg.get("schema_version", 1))

        if vault_ver < target_version:
            pending_count += 1
            print(f"[ACCION] Migrando bóveda '{v.name}' de v{vault_ver} a v{target_version}...")

            # Aquí se ejecutarían los pasos de migración según versión
            # Por ahora el esquema base es v1
            if not dry_run:
                cfg["schema_version"] = str(target_version)
                save_vault_config(v, cfg)
                print(f"[OK] Bóveda '{v.name}' actualizada a v{target_version}.")
        else:
            print(f"[OK] Bóveda '{v.name}' al día (v{vault_ver}).")

    if pending_count == 0:
        print("\n[INFO] Todas las bóvedas se encuentran en la versión más reciente del esquema.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Aplica migraciones de versión de esquema en Project Brain.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin modificar .brain.yml")
    args = parser.parse_args()

    sys.exit(run_migrations(args.dry_run))


if __name__ == "__main__":
    main()
