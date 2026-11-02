# QUALITY.md - Contrato de Calidad de Project Brain

Este documento define las reglas de calidad mecánicas de Project Brain. Es evaluado e interpretado por `tools/brain-quality`. Toda nota nueva o modificada debe someterse a esta verificación; en modo estricto (`--strict`), cualquier violación bloquea el commit.

---

## 1. PRINCIPIO FUNDAMENTAL

> **Cero invención, cero vaguedad.** Si una nota no proporciona evidencia reproducible de qué, cómo, cuándo y por qué se hizo un cambio, no se guarda. Si faltan datos, se registran formalmente en la sección "Lagunas" con `needs_review: true`.

---

## 2. SECCIONES OBLIGATORIAS POR TIPO DE NOTA

Las notas no pueden tener secciones vacías ni con texto de plantilla/placeholders.

### 2.1 Nota de Sesión (`type: session`)
- `## Objetivo`: Qué se solicitó y por qué (mínimo 2 frases y 20 palabras).
- `## Qué se hizo`: Lista concreta de hitos completados y alcance real.
- `## Cómo se hizo`: Procedimiento reproducible paso a paso con comandos ejecutables o bloques de código, nombres exactos de archivos y versiones.
- `## Resultado verificado`: Métricas, logs o comprobaciones manuales/automatizadas que demuestran que el cambio funciona.
- `## Hechos capturados`: Bloque estructurado generado por herramientas (commits, ramas, hashes, diffstats, archivos modificados).
- `## Problemas y soluciones`: Obstáculos encontrados y cómo se resolvieron (o "Ninguno detectado en esta sesión").
- `## Pendientes`: Tareas que quedan abiertas para próximas sesiones.
- `## Lagunas`: Incertidumbres, supuestos no validados o datos pendientes de confirmación. Si no hay lagunas, declarar explícitamente "Ninguna laguna identificada".
- `## Relacionado`: Wikilinks al índice del proyecto, decisiones, aprendizajes y notas globales vinculadas.

### 2.2 Nota de Decisión (`type: decision` / ADR)
- `## Contexto`: Situación técnica o de arquitectura que motivó la decisión.
- `## Opciones consideradas`: Mínimo 2 opciones analizadas, con pros y contras explícitos.
- `## Decisión`: La opción elegida de forma inequívoca.
- `## Motivo`: Justificación técnica y de negocio de por qué se eligió dicha opción.
- `## Consecuencias`: Impacto positivo y negativo (compromisos técnicos asumidos).
- `## Cómo revertirla`: Pasos necesarios para desmantelar o cambiar la decisión si fuera necesario.
- `## Relacionado`: Enlace de vuelta a la sesión que la originó y notas técnicas asociadas.

### 2.3 Nota de Aprendizaje (`type: learning`)
- `## Problema`: Síntoma exacto y mensaje de error literal si existió.
- `## Causa raíz`: Explicación técnica precisa de por qué ocurrió la falla.
- `## Solución`: Pasos y comandos exactos ejecutados para resolver el incidente.
- `## Cómo verificar que está resuelto`: Comando o prueba reproducible de comprobación.
- `## Cómo evitarlo`: Medida preventiva para que no vuelva a suceder en el futuro.
- `## Relacionado`: Enlace a la sesión de origen y documentación o conceptos relevantes.

### 2.4 Nota de Concepto (`type: concept`)
- `## Qué es`: Definición concisa y técnica de la tecnología o patrón.
- `## Para qué lo usamos en mis proyectos`: Propósito específico dentro de nuestros sistemas.
- `## Dónde se usa`: Lista de wikilinks a proyectos y componentes que lo implementan.
- `## Gotchas`: Trampas conocidas, peculiaridades y advertencias prácticas.

---

## 3. REGLAS DE ESPECIFICIDAD Y EVALUACIÓN MECÁNICA

### 3.1 Lista Negra de Expresiones Vagas (Blacklist)
El escáner rechaza frases que contengan expresiones ambiguas a menos que vengan acompañadas de un dato concreto (ruta, hash, versión o número) en la misma cláusula.

Términos prohibidos si están aislados:
- `se arregló`
- `se solucionó`
- `varios cambios`
- `algunas mejoras`
- `se mejoró`
- `se optimizó`
- `se actualizó` (sin especificar a qué versión exacta)
- `etc.`
- `y demás`
- `entre otros`
- `como siempre`
- `lo de antes`
- `ya sabes`
- `stuff`
- `various`
- `fixed bugs`
- `some changes`
- `misc`
- `WIP`
- `TODO` (en cuerpo de sesión sin estar en sección Pendientes)
- `TBD`
- `pendiente de completar`
- `lorem`

### 3.2 Densidad de Contenido
- Cada sección narrativa debe contener al menos **2 oraciones completas** y un mínimo de **20 palabras útiles** (excluyendo encabezados, wikilinks y líneas en blanco).

### 3.3 Evidencia Requerida (`evidence`)
- **Sesiones**: Mínimo 2 elementos de evidencia concreta (rutas de archivo existentes, hashes git reales, comandos ejecutados con output o URLs de referencia).
- **Aprendizajes**: Mínimo 2 elementos de evidencia concreta (error literal, archivo corregido, comando de fix o test verificado).
- **Decisiones**: Mínimo 1 elemento de evidencia concreta (documento de referencia, benchmark, commit o archivo afectado).
- Toda evidencia debe figurar tanto en el frontmatter (`evidence: [...]`) como en el cuerpo de la nota.

### 3.4 Verificación de Hashes Git
- Si una nota menciona un commit hash de 7 a 40 caracteres hexadecimales, la herramienta comprueba su existencia en el repositorio local del proyecto (`repo_path`). La invención o alteración de hashes provoca rechazo inmediato.

### 3.5 Títulos Descriptivos
- Los títulos de notas de sesión y decisiones deben describir la acción con un sustantivo o verbo concreto:
  - **Inválido**: `2026-11-01-sesion.md`, `2026-11-01-cambios.md`, `2026-11-01-base-de-datos.md`
  - **Válido**: `2026-11-01-1630-crear-esquema-postgres-pedidos-con-alembic.md`

### 3.6 Test de la Pregunta Futura (`answers_questions`)
- En el frontmatter, el campo `answers_questions` debe contener al menos una pregunta en lenguaje natural que la nota responde fehacientemente (por ejemplo: `¿Cómo configuramos las migraciones iniciales de Postgres en pedidos?`).
- La nota debe contener todos los datos requeridos para responder a esa pregunta sin requerir contexto externo ni suposiciones.
