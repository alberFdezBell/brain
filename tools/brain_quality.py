#!/usr/bin/env python3
"""
brain-quality - Evaluador y verificador estricto de calidad de notas en Project Brain.
Aplica mecánicamente el contrato de calidad definido en QUALITY.md.
Uso:
  python brain-quality.py [--slug <slug>] [--file <path>] [--strict] [--fix-hints] [--all]
"""

import sys
import re
import argparse
from pathlib import Path
from brain_common import (
    get_brain_home,
    read_note,
    load_vault_config,
    get_all_vaults,
    run_git_cmd
)

VAGUE_TERMS = [
    "se arregló", "se solucionó", "varios cambios", "algunas mejoras",
    "se mejoró", "se optimizó", "se actualizó", "etc.", "y demás",
    "entre otros", "como siempre", "lo de antes", "ya sabes",
    "stuff", "various", "fixed bugs", "some changes", "misc",
    "pendiente de completar", "lorem"
]
ACRONYM_VAGUE_TERMS = ["TODO", "WIP", "TBD"]

REQUIRED_SECTIONS = {
    "session": [
        "Objetivo", "Qué se hizo", "Cómo se hizo", "Resultado verificado",
        "Hechos capturados", "Problemas y soluciones", "Pendientes", "Lagunas", "Relacionado"
    ],
    "decision": [
        "Contexto", "Opciones consideradas", "Decisión", "Motivo",
        "Consecuencias", "Cómo revertirla", "Relacionado"
    ],
    "learning": [
        "Problema", "Causa raíz", "Solución", "Cómo verificar que está resuelto",
        "Cómo evitarlo", "Relacionado"
    ],
    "concept": [
        "Qué es", "Para qué lo usamos en mis proyectos", "Dónde se usa", "Gotchas"
    ]
}

GENERIC_TITLES = {"sesion", "session", "cambios", "fix", "bugs", "base de datos", "notas", "update", "wip"}


def clean_markdown_section_content(raw_text: str) -> str:
    """Elimina comentarios HTML, encabezados y espacios sobrantes."""
    no_comments = re.sub(r"<!--.*?-->", "", raw_text, flags=re.DOTALL)
    # Quitar wikilinks tipo [[...]] para conteo de palabras útiles
    clean_text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", no_comments)
    return clean_text.strip()


def extract_sections(body: str) -> dict[str, str]:
    """Extrae secciones delimitadas por ## Encabezado."""
    sections = {}
    current_sec = "intro"
    lines = body.splitlines()
    buffer = []

    for line in lines:
        if line.startswith("## "):
            if current_sec:
                sections[current_sec] = "\n".join(buffer).strip()
            current_sec = line[3:].strip()
            buffer = []
        else:
            buffer.append(line)

    if current_sec:
        sections[current_sec] = "\n".join(buffer).strip()

    return sections


def verify_commit_hash(repo_path: Path, commit_hash: str) -> bool:
    """Verifica si un commit hash existe realmente en el repositorio git."""
    if not repo_path or not repo_path.exists():
        return True  # No se puede verificar sin repo
    ret, _, _ = run_git_cmd(["cat-file", "-e", f"{commit_hash}^{{commit}}"], cwd=repo_path)
    return ret == 0


def evaluate_note(file_path: Path, repo_path: Path | None = None) -> tuple[int, list[str], list[str]]:
    """
    Evalúa una nota contra QUALITY.md.
    Devuelve (score: 0-100, blocking_errors: list, warnings: list).
    """
    blocking = []
    warnings = []
    score = 100

    if not file_path.exists():
        return 0, [f"El archivo no existe: {file_path}"], []

    metadata, body = read_note(file_path)
    note_type = metadata.get("type", "unknown")

    # Si es todo o reference, aplicar reglas ligeras
    if note_type in ["todo", "reference"]:
        if "type" not in metadata or "project" not in metadata:
            blocking.append("Falta 'type' o 'project' en frontmatter.")
            score -= 30
        line_count = len(body.splitlines())
        if note_type == "todo" and line_count > 150:
            blocking.append(f"Nota todo excede el límite estricto de 150 líneas (tiene {line_count}).")
            score -= 25
        return max(score, 0), blocking, warnings

    # Comprobación reforzada para context e index (garantizar inicialización completa y sin placeholders)
    if note_type in ["context", "index"]:
        if "type" not in metadata or "project" not in metadata:
            blocking.append("Falta 'type' o 'project' en frontmatter.")
            score -= 30

        # 1. needs_review
        if metadata.get("needs_review") is True:
            blocking.append("Nota marcada con 'needs_review: true': inicialización o revisión pendiente.")
            score -= 30

        # 2. Marca INICIALIZACIÓN PENDIENTE
        if "INICIALIZACIÓN PENDIENTE" in body or "INICIALIZACION PENDIENTE" in body:
            blocking.append("Contiene la marca 'INICIALIZACIÓN PENDIENTE'. Debe completar el contenido y retirar la advertencia.")
            score -= 40

        # 3. Placeholders y comentarios de plantilla
        if "{{" in body or "}}" in body:
            blocking.append("Contiene variables de plantilla sin reemplazar ('{{...}}').")
            score -= 30
        if "<!--" in body:
            blocking.append("Contiene comentarios de plantilla HTML ('<!-- ... -->') sin completar con contenido real.")
            score -= 20

        # 4. Evidencia concreta obligatoria
        ev_list = metadata.get("evidence", [])
        if not isinstance(ev_list, list):
            ev_list = [ev_list] if ev_list else []
        clean_ev = [str(e).strip() for e in ev_list if str(e).strip()]

        has_real_evidence = False
        brain_home = get_brain_home()
        for ev in clean_ev:
            if any(p in ev.lower() for p in ["ruta exacta", "ruta del repositorio local:", "{{", "ejemplo"]):
                continue
            if "commit:" in ev.lower() or re.search(r"\b[0-9a-f]{7,40}\b", ev):
                has_real_evidence = True
                break
            if re.search(r"v?\d+\.\d+", ev):
                has_real_evidence = True
                break
            p_ev = Path(ev)
            if p_ev.exists() or (brain_home / ev).exists() or (repo_path and (repo_path / ev).exists()):
                has_real_evidence = True
                break
            if "." in ev and "/" not in ev and "\\" not in ev:
                if (file_path.parent / ev).exists():
                    has_real_evidence = True
                    break

        if not has_real_evidence:
            blocking.append("Evidencia requerida: debe incluir al menos una ruta de archivo real existente, versión o hash de commit.")
            score -= 30

        # 5. Comprobación de contenido sustantivo por tipo
        if note_type == "context" and file_path.name != "_global-context.md":
            secs = extract_sections(body)
            required_context_secs = ["Objetivo", "Stack Tecnológico", "Rutas Clave", "Convenciones y Estándares", "Estado Actual"]
            for csec in required_context_secs:
                found_k = None
                for k in secs:
                    if k.lower() == csec.lower():
                        found_k = k
                        break
                if not found_k:
                    blocking.append(f"Falta sección obligatoria en context: '## {csec}'.")
                    score -= 15
                else:
                    c_clean = clean_markdown_section_content(secs[found_k])
                    if not c_clean or len(c_clean) < 15:
                        blocking.append(f"La sección '## {csec}' en context está vacía o incompleta.")
                        score -= 15
                    if csec == "Stack Tecnológico":
                        lines_stack = [l.strip() for l in secs[found_k].splitlines() if l.strip().startswith("- ")]
                        empty_keys = [l for l in lines_stack if l.endswith(":") or l in ["- Lenguaje:", "- Framework:", "- Base de datos:", "- Infraestructura / Despliegue:"]]
                        if len(empty_keys) >= 2:
                            blocking.append("La sección '## Stack Tecnológico' contiene campos vacíos de plantilla sin especificar valores.")
                            score -= 20

            line_count = len(body.splitlines())
            if line_count > 150:
                blocking.append(f"Nota context excede el límite estricto de 150 líneas (tiene {line_count}).")
                score -= 25

        elif note_type == "index":
            proj_slug = metadata.get("project", "")
            if proj_slug and proj_slug != "_global":
                if f"[[{proj_slug}-context" not in body:
                    blocking.append(f"El índice debe enlazar a [[{proj_slug}-context]].")
                    score -= 15
                if f"[[{proj_slug}-todo" not in body:
                    blocking.append(f"El índice debe enlazar a [[{proj_slug}-todo]].")
                    score -= 15

        return max(score, 0), blocking, warnings

    if note_type not in REQUIRED_SECTIONS:
        warnings.append(f"Tipo de nota '{note_type}' no requiere evaluación estricta.")
        return 90, [], warnings

    # 1. Frontmatter obligatorio
    required_keys = ["date", "project", "type", "status", "tags", "evidence", "needs_review", "answers_questions"]
    for k in required_keys:
        if k not in metadata:
            blocking.append(f"Frontmatter: Falta campo obligatorio '{k}'.")
            score -= 10
        elif metadata[k] is None or metadata[k] == "":
            blocking.append(f"Frontmatter: Campo obligatorio '{k}' está vacío.")
            score -= 10

    # Evidencia mínima
    evidence_list = metadata.get("evidence", [])
    if not isinstance(evidence_list, list):
        evidence_list = [evidence_list] if evidence_list else []

    min_evidence = 2 if note_type in ["session", "learning"] else 1
    if len(evidence_list) < min_evidence:
        blocking.append(f"Evidencia: Se requieren al menos {min_evidence} elementos en 'evidence', encontrados {len(evidence_list)}.")
        score -= 20

    # answers_questions
    questions = metadata.get("answers_questions", [])
    if not questions or (isinstance(questions, list) and len(questions) == 0):
        blocking.append("Falta al menos una pregunta en 'answers_questions' para responder futuras consultas.")
        score -= 15

    # 2. Título no genérico
    title_raw = file_path.stem.lower()
    for gen in GENERIC_TITLES:
        if title_raw == gen or title_raw.endswith(f"-{gen}"):
            blocking.append(f"Título genérico detectado ('{file_path.name}'). Debe describir el contenido con sustantivos y verbos concretos.")
            score -= 15

    # 3. Secciones obligatorias y densidad
    sections = extract_sections(body)
    req_secs = REQUIRED_SECTIONS[note_type]

    for sec in req_secs:
        # Match case insensitive
        found_key = None
        for k in sections:
            if k.lower() == sec.lower():
                found_key = k
                break

        if not found_key:
            blocking.append(f"Falta sección obligatoria: '## {sec}'.")
            score -= 15
            continue

        raw_content = sections[found_key]
        clean_content = clean_markdown_section_content(raw_content)

        if not clean_content:
            blocking.append(f"La sección '## {sec}' está vacía o solo contiene comentarios de plantilla.")
            score -= 20
            continue

        # Densidad para secciones narrativas
        if sec in ["Objetivo", "Contexto", "Problema", "Causa raíz", "Motivo", "Qué es"]:
            words = [w for w in re.split(r"\s+", clean_content) if len(w) > 1]
            sentences = [s for s in re.split(r"[.!?]+", clean_content) if len(s.strip()) > 5]
            if len(words) < 18 or len(sentences) < 2:
                blocking.append(f"Densidad insuficiente en '## {sec}': requiere al menos 2 oraciones y 20 palabras útiles (tiene {len(words)} palabras, {len(sentences)} oraciones).")
                score -= 15

    # 4. Reproducibilidad: Bloque de código o pasos ejecutables
    if note_type == "session":
        como_content = sections.get("Cómo se hizo", "")
        if "```" not in como_content and not re.search(r"^\s*1\.\s+", como_content, re.MULTILINE):
            blocking.append("Reproducibilidad: '## Cómo se hizo' debe incluir comandos ejecutables en bloque de código (```) o lista numerada de pasos.")
            score -= 15
    elif note_type == "learning":
        sol_content = sections.get("Solución", "")
        if "```" not in sol_content and not re.search(r"^\s*1\.\s+", sol_content, re.MULTILINE):
            blocking.append("Reproducibilidad: '## Solución' debe incluir comandos o código explícito.")
            score -= 15

    # 5. Lista negra de vaguedades
    body_lower = body.lower()
    for term in VAGUE_TERMS:
        if term in body_lower:
            sentences = re.split(r"[.\n]+", body)
            for s in sentences:
                s_lower = s.lower()
                if term in s_lower:
                    has_concrete = re.search(r"(\d+|/|\\|[a-f0-9]{7,40}|`[^`]+`)", s)
                    if not has_concrete:
                        blocking.append(f"Expresión vaga detectada: '{term}' en la frase: '{s.strip()}'. Debe aportar un dato concreto (versión, ruta, número o commit).")
                        score -= 15

    for acr in ACRONYM_VAGUE_TERMS:
        # Buscar acrónimo exacto en mayúsculas como palabra completa
        if re.search(r"\b" + acr + r"\b", body):
            sentences = re.split(r"[.\n]+", body)
            for s in sentences:
                if re.search(r"\b" + acr + r"\b", s):
                    # Permitir TODO en la sección de pendientes o si menciona archivos
                    if acr == "TODO" and "todo.md" in s.lower():
                        continue
                    has_concrete = re.search(r"(\d+|/|\\|[a-f0-9]{7,40}|`[^`]+`)", s)
                    if not has_concrete:
                        blocking.append(f"Acrónimo de vaguedad detectado: '{acr}' en la frase: '{s.strip()}'. Debe especificar el elemento concreto o moverlo a Pendientes.")
                        score -= 15

    # 6. Verificación de commits hashes
    if repo_path and repo_path.exists():
        # Buscar palabras de 7 a 40 caracteres hexadecimales
        potential_hashes = re.findall(r"\b([0-9a-f]{7,40})\b", body)
        # Excluir palabras normales que contengan solo a-f y números si son muy cortas, o filtrar por prefijo commit
        commit_evidences = [e for e in evidence_list if "commit:" in str(e).lower()]
        for ce in commit_evidences:
            m = re.search(r"([0-9a-f]{7,40})", str(ce), re.IGNORECASE)
            if m:
                c_hash = m.group(1)
                if not verify_commit_hash(repo_path, c_hash):
                    blocking.append(f"Hash de commit falso o inexistente en el repo: '{c_hash}'.")
                    score -= 30

    return max(score, 0), blocking, warnings


def main():
    parser = argparse.ArgumentParser(description="Evalúa la calidad de notas en Project Brain.")
    parser.add_argument("--slug", help="Evalúa notas del proyecto indicado")
    parser.add_argument("--file", help="Evalúa una nota específica por su ruta")
    parser.add_argument("--strict", action="store_true", help="Falla (exit 1) si el score < 85 o hay errores bloqueantes")
    parser.add_argument("--fix-hints", action="store_true", help="Muestra sugerencias de corrección")
    parser.add_argument("--all", action="store_true", help="Evalúa todas las notas de todas las bóvedas")
    args = parser.parse_args()

    brain_home = get_brain_home()
    files_to_check = []
    repo_path = None

    if args.file:
        p = Path(args.file).resolve()
        files_to_check.append(p)
        # Intentar inferir repo_path buscando .brain.yml en ancestros
        for parent in [p.parent, p.parent.parent]:
            if (parent / ".brain.yml").exists():
                cfg = load_vault_config(parent)
                if "repo_path" in cfg:
                    repo_path = Path(cfg["repo_path"])
                break
    elif args.slug:
        vault = brain_home / args.slug
        if not vault.exists():
            print(f"[ERROR] Bóveda '{args.slug}' no existe.", file=sys.stderr)
            sys.exit(1)
        cfg = load_vault_config(vault)
        if "repo_path" in cfg:
            repo_path = Path(cfg["repo_path"])
        for sub in ["sessions", "decisions", "learnings", "references"]:
            d = vault / sub
            if d.exists():
                files_to_check.extend(sorted(d.glob("*.md")))
        # También context, index, todo
        for main_file in [f"{args.slug}-context.md", f"{args.slug}-todo.md"]:
            mf = vault / main_file
            if mf.exists():
                files_to_check.append(mf)
    elif args.all:
        for v in get_all_vaults(brain_home):
            for sub in ["sessions", "decisions", "learnings", "references", "concepts"]:
                d = v / sub
                if d.exists():
                    files_to_check.extend(sorted(d.glob("*.md")))
    else:
        # Por defecto evaluar últimas notas modificadas en la bóveda actual o sesiones
        cwd = Path.cwd()
        # Ver si estamos en una bóveda o repo
        for parent in [cwd, cwd.parent]:
            if (parent / ".brain.yml").exists():
                args.slug = parent.name
                return main()
        # Si no se especificó nada, evaluar todas
        args.all = True
        return main()

    total_evaluated = 0
    failed_count = 0

    print("==================================================")
    print("      EVALUADOR DE CALIDAD PROJECT BRAIN          ")
    print("==================================================")

    for f in files_to_check:
        score, block, warn = evaluate_note(f, repo_path)
        total_evaluated += 1
        is_fail = score < 85 or len(block) > 0

        status_label = "[FAIL]" if is_fail else "[PASS]"
        color_prefix = "\033[91m" if is_fail else "\033[92m"
        color_reset = "\033[0m"

        print(f"\n{status_label} ({score}/100) -> {f.relative_to(brain_home) if f.is_relative_to(brain_home) else f.name}")

        if block:
            failed_count += 1
            print("  Errores Bloqueantes:")
            for b in block:
                print(f"    - {b}")

        if warn:
            print("  Avisos:")
            for w in warn:
                print(f"    - {w}")

        if is_fail and args.fix_hints:
            print("  Sugerencias de corrección:")
            print("    1. Agregue evidencia verificada (rutas de archivos, commits reales de git).")
            print("    2. Reemplace adjetivos vagos por datos cuantificables y pasos ejecutables.")
            print("    3. Complete todas las secciones obligatorias del contrato de calidad.")

    print("\n--------------------------------------------------")
    print(f"Total evaluadas: {total_evaluated} | Fallidas: {failed_count}")
    print("--------------------------------------------------")

    if args.strict and failed_count > 0:
        print("[BLOQUEO STRICT] Calidad insuficiente. Corrija los errores bloqueantes antes de continuar.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
