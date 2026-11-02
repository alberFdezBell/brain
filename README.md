# Project Brain: Sistema de Memoria Persistente de Segunda Generación

**Project Brain** es una infraestructura de memoria persistente para proyectos asistidos por Inteligencia Artificial. Diseñado como una bóveda unificada de Obsidian compuesta por sub-bóvedas por proyecto y una transversal (`_global`), garantiza que cualquier asistente IA (Antigravity, Claude Code, Gemini CLI, Cursor o modelos locales) comience cada sesión conociendo el historial técnico anterior, y que puedas responder dentro de meses o años a la pregunta:
> *"¿Cómo hicimos X en el proyecto Y, con qué fecha, comandos y commits?"*

---

## 1. Principios de Diseño Fundamentales

1. **Solo Markdown plano + YAML frontmatter**: Formato abierto, portable, sin dependencias propietarias ni bases de datos binarias. Durabilidad garantizada por décadas.
2. **Agnóstico de herramienta**: La fuente canónica de verdad son los archivos en `$BRAIN_HOME` (`~/Brain`). Antigravity, Claude Code o Gemini son clientes intercambiables.
3. **Divulgación Progresiva y Eficiencia de Tokens**:
   - **Capa Caliente**: `<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md` (≤150 líneas cada uno). Se cargan siempre al inicio.
   - **Capa Templada**: Últimas 3 a 5 sesiones y notas enlazadas relevantes.
   - **Capa Fría**: Historial archivado en `archive/`, consultado bajo demanda.
4. **Calidad Blindada por Código**: Contrato estricto (`QUALITY.md`) validado mecánicamente por `brain-quality`. Se rechazan expresiones vagas, omisión de evidencias o secciones vacías.
5. **Hechos por Herramienta, Narrativa por la IA**: Commits, hashes, fechas con zona horaria, ramas y diffstats se capturan automáticamente de Git; la IA redacta la síntesis conceptual y los motivos.
6. **Cero Invención**: Si un dato no se conoce con total seguridad, se declara formalmente en "Lagunas" con `needs_review: true`.
7. **Grafo Conectado**: Cada nota enlaza a su índice y a notas relacionadas; conceptos compartidos en `_global/concepts/` actúan como nodos puente entre proyectos.
8. **Seguridad Proactiva**: Escaneo automatizado de credenciales, tokens y claves privadas antes de cualquier commit (`brain-lint --secrets`).

---

## 2. Estructura de Directorios

```
~/Brain/
├── README.md                 # Documentación general y guía de uso
├── PROTOCOL.md               # Protocolo canónico obligatorio para todas las IAs
├── QUALITY.md                # Contrato mecánico de calidad
├── schema/
│   ├── VERSION               # Versión activa del esquema (v1)
│   └── CHANGELOG.md          # Registro de cambios y guía de migraciones
├── templates/                # Plantillas normalizadas de notas
├── tools/                    # Herramientas en Python 3 stdlib + wrappers (.ps1 / .sh)
├── adapters/                 # Snippets de configuración para cada asistente IA
├── .cache/                   # Índice BM25 y marcas de tiempo (en .gitignore)
├── _global/                  # Bóveda transversal + tags.md + concepts/
├── <slug-proyecto>/          # Una sub-bóveda por proyecto
├── .obsidian/                # Configuración de grafo y filtros de Obsidian
└── .gitignore
```

---

## 3. Comandos Esenciales (Guía Rápida)

Todos los comandos residen en `tools/` y cuentan con wrappers `.ps1` (PowerShell en Windows) y `.sh` (Bash en Linux/macOS).

| Comando | Función Principal | Ejemplo de Uso |
| :--- | :--- | :--- |
| **`brain-chat`** | Interfaz nativa local estilo ChatGPT (Qwen 1.5B) para consultar la documentación | `brain-chat` |
| **`brain-ask`** | Responde preguntas futuras con paquete de evidencia, commits y línea de tiempo | `brain-ask "¿Cómo configuramos Alembic?" --project mi-api` |
| **`brain-search`** | Búsqueda semántica/léxica con algoritmo BM25 ponderado | `brain-search "migraciones postgres"` |
| **`brain-audit`** | Auditoría periódica de salud, huérfanas, enlaces rotos y calidad | `brain-audit` |
| **`brain-lint`** | Verificación estricta de sintaxis, límites y escáner de secretos | `brain-lint --secrets` |
| **`brain-doctor`** | Diagnóstico del entorno, herramientas y estado de las bóvedas | `brain-doctor` |
| **`brain-compact`** | Archiva sesiones antiguas (>30 días) y poda archivos sobrepasados | `brain-compact mi-api` |
| **`brain-init`** | Crea e inicializa una nueva sub-bóveda para un proyecto | `brain-init mi-app --repo-path /ruta/al/repo` |
| **`brain-session`** | Crea el borrador de la sesión con los hechos Git volcados | `brain-session --slug mi-app --title "configurar-docker"` |
| **`brain-quality`** | Evalúa las notas contra el contrato de calidad (score 0-100) | `brain-quality --strict --slug mi-app` |
| **`brain-commit`** | Persiste los cambios en Git previa verificación de calidad y secretos | `brain-commit -m "Cierre de sesión: Docker implementado"` |

---

## 4. Cómo Añadir un Nuevo Adaptador de IA en 2 Minutos

Project Brain es totalmente agnóstico de la herramienta de IA utilizada. Para integrar un nuevo asistente:

1. Localiza el archivo de configuración o system prompt del asistente (ejemplo: `.cursorrules`, `CLAUDE.md`, `.windsurfrules`, `.copilot-instructions.md`).
2. Copia el siguiente snippet minimalista:
   ```markdown
   ## Memoria Persistente (Project Brain)
   En cada sesión y proyecto, consulta y sigue obligatoriamente `$BRAIN_HOME/PROTOCOL.md`.
   - Al iniciar: Lee la capa caliente del proyecto y ejecuta `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
   - Durante: Registra decisiones y aprendizajes con evidencias reales (archivos y commits).
   - Al cerrar: La tarea no concluye hasta que `brain-session` genere la nota, `brain-quality --strict` apruebe con >= 85, y `brain-commit` guarde los cambios en Git local.
   - Preguntas retrospectivas: Utiliza `python ~/Brain/tools/brain-ask.py "<pregunta>" --project <slug>`.
   ```
3. Guarda el archivo en la raíz del proyecto o en la carpeta `adapters/` de Brain para reutilización.

---

## 5. Visualización del Grafo en Obsidian

Para abrir y navegar el grafo de Project Brain:
1. Abre Obsidian y selecciona **"Open folder as vault"**.
2. Elige el directorio `~/Brain` (o `C:\Users\alber\Brain`).
3. Abre la vista de grafo (**Graph View** o `Ctrl + G`).
4. La configuración precargada en `.obsidian/graph.json` colorea automáticamente los nodos por su tipo:
   - **Verde**: Mapas de contenido e índices (`-index.md`).
   - **Azul**: Sesiones interactivas (`sessions/`).
   - **Naranja**: Decisiones arquitectónicas ADRs (`decisions/`).
   - **Violeta**: Aprendizajes y gotchas resueltos (`learnings/`).
   - **Cyan**: Conceptos transversales compartidos (`concepts/`).
