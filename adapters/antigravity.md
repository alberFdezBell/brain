# Adapter: Google Antigravity
# Añade este bloque a tus reglas globales (~/.gemini/AGENTS.md) o como regla de espacio de trabajo (.gemini/rules/project-brain.md):

## Memoria Persistente Obligatoria (Project Brain)
En cada sesión, chat y proyecto, debes leer y seguir obligatoriamente `$BRAIN_HOME/PROTOCOL.md` (por defecto `~/Brain/PROTOCOL.md` o `C:\Users\alber\Brain\PROTOCOL.md`) antes de actuar y antes de dar nada por terminado:

1. **Inicio de sesión**:
   - Leer capa caliente del proyecto (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`) y las 3 últimas sesiones.
   - Ejecutar `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
2. **Durante la sesión**:
   - Registrar decisiones técnicas en `<slug>/decisions/` con hechos reales y reproducibles.
   - Registrar resolución de errores y aprendizajes en `<slug>/learnings/`.
3. **Cierre de sesión / finalización de tarea**:
   - La tarea NO está completa hasta que se ejecute `python ~/Brain/tools/brain-session.py --slug <slug>`, se completen las secciones narrativas obligatorias sin expresiones vagas, y pasen con éxito tanto `python ~/Brain/tools/brain-quality.py --strict --slug <slug>` como `python ~/Brain/tools/brain-commit.py --slug <slug>`.
4. **Consultas retrospectivas**:
   - Responder preguntas con evidencia cruzada ejecutando `python ~/Brain/tools/brain-ask.py "<pregunta>" --project <slug>`.
