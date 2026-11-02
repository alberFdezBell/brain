# Schema Changelog - Project Brain

Este documento registra los cambios de versión del esquema de Project Brain y las instrucciones para migrar entre versiones.

## [v1] - 2026-11-01

### Esquema Inicial
- Estructura base de bóvedas (`<slug>/` y `_global/`).
- Tipos de notas: `index`, `context`, `todo`, `decision`, `session`, `learning`, `reference`, `concept`.
- Frontmatter YAML canónico:
  - `date`: Timestamp ISO-8601 con zona horaria (`YYYY-MM-DDTHH:mm:ssZ` o con offset).
  - `project`: Slug del proyecto o `_global`.
  - `type`: Tipo de nota (`session` | `decision` | `learning` | `reference` | `index` | `concept`).
  - `status`: Estado del contenido (`active` | `obsolete` | `superseded`).
  - `tags`: Lista de etiquetas jerárquicas controladas (`#tema/subtema`).
  - `evidence`: Lista de evidencias concretas (rutas de archivo, commits, comandos, URLs, errores).
  - `needs_review`: Booleano (`true` | `false`).
  - `answers_questions`: Lista de preguntas que esta nota puede responder con evidencia propia.
- Metadatos por bóveda en `.brain.yml`:
  - `schema_version`: Número entero (`1`).
  - `slug`: Identificador único de la bóveda.
  - `created`: Fecha ISO.
  - `repo_path`: Ruta absoluta al repositorio git del proyecto.
  - `aliases`: Nombres alternativos o sinónimos del proyecto.
- Herramientas CLI en Python 3 stdlib con wrappers multiplataforma.
