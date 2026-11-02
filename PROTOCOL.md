# PROTOCOL.md - Protocolo Operativo Universal de Project Brain

Este documento es la **fuente de verdad canónica** para cualquier sistema de inteligencia artificial (Antigravity, Claude Code, Gemini CLI, Cursor, agentes autónomos o scripts) que interactúe con proyectos del usuario. Debe seguirse de forma estricta e incondicional.

---

## 1. PRINCIPIOS Y ARQUITECTURA

1. **Persistencia Autónoma**: La memoria vive en el sistema de archivos local (`$BRAIN_HOME`, por defecto `~/Brain`), estructurada como una bóveda unificada de Obsidian con sub-bóvedas por proyecto y una transversal (`_global`).
2. **Independencia Tecnológica**: Formato 100% Markdown plano con frontmatter YAML estándar. Sin bases de datos binarias ni plugins obligatorios.
3. **Divulgación Progresiva de Tokens**:
   - **Capa Caliente (Hot)**: Siempre se carga al inicio (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`; ≤150 líneas cada uno).
   - **Capa Templada (Warm)**: Las últimas 3 a 5 sesiones y notas directamente enlazadas relevantes a la tarea actual.
   - **Capa Fría (Cold)**: Historial archivado en `archive/`, consultado únicamente bajo demanda mediante `brain-search` o `brain-ask`.
4. **Unicidad Global de Nombres**: Obsidian resuelve wikilinks a nivel global por nombre de archivo. Por tanto, los archivos clave de cada proyecto incluyen el prefijo del slug: `<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`. Jamás crear dos notas con el mismo nombre en toda la raíz de `~/Brain`.
5. **Hechos Verificados vs. Narrativa**: Fechas, ramas, commits, hashes, archivos y diffstats son capturados automáticamente por herramientas desde el repositorio git. La IA se encarga de la síntesis narrativa, justificación y conexiones contextuales. Queda terminantemente prohibido inventar o aproximar datos técnicos.

---

## 2. IDENTIFICACIÓN DEL PROYECTO

1. **Resolución del Slug**:
   - Si en el directorio de trabajo del proyecto existe un archivo `.brain.yml`, se toma el slug indicado allí.
   - En su defecto, se toma el nombre de la carpeta raíz del repositorio Git o del espacio de trabajo en minúsculas, sin caracteres especiales y con guiones (ejemplo: `mi-servicio-web`).
   - Si no hay un proyecto activo (conversación general o transversal), se opera directamente sobre la bóveda `_global`.
2. **Ruta del Repositorio (`repo_path`)**:
   - Cada bóveda de proyecto almacena en su `.brain.yml` la ruta absoluta al repositorio git local (`repo_path`), permitiendo a las herramientas consultar `git log`, `diff` y verificar hashes.

---

## 3. CICLO DE VIDA DE LA SESIÓN

### A. Al Iniciar Sesión (Obligatorio)
1. Resolver `$BRAIN_HOME` (si no está definida en el entorno, usar `~/Brain`).
2. Identificar el `slug` del proyecto y su `repo_path`.
3. Comprobar si existe la bóveda `$BRAIN_HOME/<slug>/`:
   - Si **no existe**: Ejecutar `python tools/brain-init.py <slug> --repo-path <ruta>`. La herramienta generará `<slug>-context.md` y `<slug>-index.md` marcados con `needs_review: true` y la advertencia `INICIALIZACIÓN PENDIENTE`. La IA debe explorar inmediatamente el repositorio (README, manifiestos como `package.json`, `pyproject.toml`, estructura y rutas clave) y rellenar de forma exhaustiva `<slug>-context.md` y `<slug>-index.md`, eliminando todos los placeholders, registrando la evidencia real y fijando `needs_review: false`. **La inicialización NO está completa hasta que `python tools/brain-quality.py --strict --slug <slug>` pase con éxito sobre context e index; queda terminantemente prohibido comenzar la tarea del usuario sin haber superado este paso.**
4. Si **ya existe**:
   - Leer únicamente la **capa caliente**: `<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`.
   - Leer las **3 sesiones más recientes** en `<slug>/sessions/`.
   - Leer `_global/_global-index.md` y `_global/_global-context.md`.
5. Ejecutar la captura de inicio:
   ```bash
   python tools/brain-capture.py --start --slug <slug>
   ```
   Esto guarda el timestamp exacto y el hash del commit actual en `.cache/<slug>-session-start.json`.

### B. Durante la Sesión
- **Decisiones Técnicas Significativas**: Si se toma una decisión de arquitectura, diseño de base de datos, librería o protocolo, redactar inmediatamente una nota en `<slug>/decisions/YYYY-MM-DD-<titulo-descriptivo>.md` usando la plantilla de decisión.
- **Aprendizajes y Resolución de Errores**: Si se resuelve un bug no trivial, una incompatibilidad de dependencias o un procedimiento complejo de despliegue/configuración, redactar una nota en `<slug>/learnings/YYYY-MM-DD-<titulo-descriptivo>.md`.
- **Registro Silencioso**: Toda nota se crea y actualiza sin interrumpir al usuario y sin pedir confirmaciones superfluas.
- **Detalle Reproducible**: Registrar comandos exactos, flags, versiones reales y orden secuencial.

### C. Al Completar la Tarea o Cerrar Sesión (Puerta de Calidad Obligatoria)
1. Ejecutar la captura y generación de sesión:
   ```bash
   python tools/brain-session.py --slug <slug>
   ```
   Esto genera una nueva nota en `<slug>/sessions/YYYY-MM-DD-HHmm-<titulo>.md` con el bloque `## Hechos capturados` ya rellenado con commits, archivos tocados, diffstat y ramas.
2. Completar las secciones narrativas obligatorias exigidas por `QUALITY.md`:
   - `## Objetivo`
   - `## Qué se hizo`
   - `## Cómo se hizo` (con bloques de código y comandos reproducibles)
   - `## Resultado verificado`
   - `## Problemas y soluciones`
   - `## Pendientes`
   - `## Lagunas` (si no hay, "Ninguna laguna identificada")
   - `## Relacionado` (wikilinks a decisiones, aprendizajes, índice)
   - Completar en el frontmatter `answers_questions: ["¿Pregunta realista sobre lo hecho?"]`.
3. Actualizar `<slug>-todo.md` (marcar lo hecho, añadir nuevos ítems).
4. Actualizar `<slug>-context.md` si hubo cambios estructurales en el proyecto (mantener siempre ≤ 150 líneas mediante síntesis).
5. Enlazar las nuevas notas en `<slug>-index.md`.
6. **Ejecutar la verificación estricta de calidad**:
   ```bash
   python tools/brain-quality.py --strict --slug <slug>
   ```
   - Si la puntuación es < 85 o hay fallos bloqueantes (expresiones vagas, falta de evidencia, hashes inexistentes, secciones vacías), **la IA debe corregir la nota y reintentar**. Máximo 5 iteraciones.
   - Si algún dato no se conoce con certeza, se declara en "Lagunas" con `needs_review: true`. Queda prohibido inventar datos para pasar la prueba.
7. **Persistir en Git**:
   ```bash
   python tools/brain-commit.py --slug <slug> -m "Resumen claro de la sesión"
   ```
   El commit se abortará si `brain-lint --secrets` o `brain-quality --strict` detectan fallos o secretos expuestos.
8. Informar al usuario en **una sola línea concisa** qué se ha registrado (y alertar si alguna nota quedó con `needs_review: true`).

---

## 4. REGLAS DE REDACCIÓN Y METADATOS

- **Idioma**: Español neutro y conciso, conservando en inglés los nombres técnicos, código y comandos.
- **Frontmatter Obligatorio**:
  ```yaml
  ---
  date: 2026-11-01T16:30:00+01:00
  project: mi-proyecto
  type: session # session | decision | learning | reference | index | concept
  status: active # active | obsolete | superseded
  tags:
    - tecnologia/docker
    - arquitectura/base-de-datos
  evidence:
    - src/config/database.py
    - "commit: 4a7c81b"
    - "alembic upgrade head"
  needs_review: false
  answers_questions:
    - "¿Cómo se crearon las migraciones iniciales de Postgres?"
  ---
  ```
- **Inmutabilidad y Obsolescencia**: Jamás borrar una nota que represente una decisión previa o un aprendizaje. Si queda desfasada, marcar `status: superseded` y agregar `superseded_by: [[nueva-nota]]`.
- **Referencias de Código**: No pegar archivos completos. Referenciar la ruta del archivo y como máximo fragmentos de 10-15 líneas relevantes al cambio.

---

## 5. REGLAS DE ENLAZADO Y CRECIMIENTO DEL GRAFO

1. **Topología Libre de Huérfanos**: Cada nota creada debe figurar en el `<slug>-index.md` correspondiente.
2. **Bidireccionalidad Contextual**:
   - Una nota de sesión enlaza a todas las decisiones y aprendizajes creados en ella.
   - Toda decisión y aprendizaje enlaza de vuelta a la nota de sesión que la vio nacer: `Origen: [[YYYY-MM-DD-HHmm-sesion]]`.
3. **Hubs Globales**: Tecnologías o patrones transversales (`Docker`, `FastAPI`, `Tailwind`, `Supabase`) deben tener una nota en `_global/concepts/[[nombre]]`. Cuando dos proyectos usan la misma tecnología, ambos enlazan a la misma nota conceptual de `_global`, creando puentes automáticos en el grafo.
4. **Vocabulario Controlado de Tags**: Los tags siguen el estándar `#categoria/subcategoria` y deben registrarse en `_global/tags.md`. Antes de inventar un tag, consultar `tags.md`.

---

## 6. SEGURIDAD Y PRIVACIDAD

1. **Cero Secretos**: Jamás escribir contraseñas, tokens JWT, claves privadas SSH/PGP o API keys (`sk-...`, `ghp-...`, `bearer ...`).
2. **Sanitización de Comandos**: En cualquier salida de consola o comando reproducido, reemplazar credenciales reales por variables o placeholders explícitos: `<DB_PASSWORD>`, `<API_KEY>`.
3. **Escáner Preventivo**: El script `brain-lint --secrets` analiza heurísticamente cada archivo antes del commit.

---

## 7. RECUPERACIÓN Y CONSULTA (`brain-ask`)

Cuando el usuario pregunte en el futuro "¿cómo hicimos X en el proyecto Y?":
1. Ejecutar:
   ```bash
   python tools/brain-ask.py "<pregunta>" --project <slug>
   ```
2. La herramienta devolverá un paquete estructurado de evidencia:
   - Notas relevantes encontradas mediante BM25 ponderado.
   - Fragmentos citables con fecha y ruta.
   - Commits del repositorio git asociados temporalmente o por archivos modificados.
   - Línea temporal cronológica unificada.
   - Lagunas conocidas.
3. Responder citando siempre:
   - Fecha exacta.
   - Nota fuente (`[[ruta]]`).
   - Hash del commit y mensaje.
   - Comandos exactos ejecutados.
4. Si la información no existe o la evidencia es insuficiente, afirmarlo con total transparencia sin inferencias ficticias.
