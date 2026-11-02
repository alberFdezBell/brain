# Adapter: Claude Code
# Añade este bloque a tu CLAUDE.md en la raíz de tu proyecto o en tu configuración global (~/.claude/CLAUDE.md):

## Memoria Persistente (Project Brain)
- En cada sesión y proyecto, lee y sigue `$BRAIN_HOME/PROTOCOL.md` (por defecto `~/Brain/PROTOCOL.md`) antes de actuar y antes de dar nada por terminado.
- **Al iniciar**: Lee capa caliente (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`) y ejecuta `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
- **Durante**: Documenta decisiones y aprendizajes técnicos reales en `decisions/` y `learnings/`.
- **Al cerrar**: La tarea NO está completa hasta que `python ~/Brain/tools/brain-session.py --slug <slug>` genere la sesión, `python ~/Brain/tools/brain-quality.py --strict --slug <slug>` pase con score >= 85 sin expresiones vagas, y `python ~/Brain/tools/brain-commit.py --slug <slug>` guarde los cambios en git.
- **Consultas**: Responde preguntas retrospectivas usando `python ~/Brain/tools/brain-ask.py "<pregunta>" --project <slug>`.
