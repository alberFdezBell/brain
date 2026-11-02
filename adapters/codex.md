# Adapter: OpenAI Codex / Copilot / AGENTS.md
# Añade este bloque a tu archivo de instrucciones de agente (~/.codex/instructions.md, AGENTS.md o .cursorrules):

## Memoria Persistente (Project Brain)
Eres un asistente guiado por el sistema de memoria persistente de **Project Brain**.
En cada sesión de trabajo sobre cualquier repositorio o proyecto, debes consultar y sincronizar con `$BRAIN_HOME` (por defecto `~/Brain`):

1. **Lectura inicial obligatoria**:
   - Antes de modificar código, consulta `$BRAIN_HOME/<slug>/<slug>-context.md`, `<slug>-index.md` y `<slug>-todo.md` para conocer la arquitectura, dependencias y estado actual.
   - Ejecuta `python $BRAIN_HOME/tools/brain-capture.py --start --slug <slug>`.
2. **Durante el desarrollo**:
   - Cada decisión relevante de arquitectura debe quedar registrada en `$BRAIN_HOME/<slug>/decisions/YYYY-MM-DD-<slug>.md`.
   - Cada solución de error o incompatibilidad debe quedar en `$BRAIN_HOME/<slug>/learnings/YYYY-MM-DD-<slug>.md`.
3. **Validación de cierre**:
   - Ejecuta `python $BRAIN_HOME/tools/brain-session.py --slug <slug>` para redactar la nota de sesión.
   - Valida la calidad con `python $BRAIN_HOME/tools/brain-quality.py --strict --slug <slug>`. No des la tarea por finalizada si no alcanza el puntaje requerido (mínimo 85/100 o 100/100).
   - Guarda los cambios en el repositorio de memoria con `python $BRAIN_HOME/tools/brain-commit.py --slug <slug>`.
