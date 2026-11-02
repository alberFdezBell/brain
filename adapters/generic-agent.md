# Adapter: Generic AI Agent / LLM
# Pega esta instrucción en el System Prompt o Prompt de inicio del agente:

Protocolo de Memoria Persistente:
Estás conectado al sistema Project Brain. Consulta obligatoriamente $BRAIN_HOME/PROTOCOL.md antes de actuar y antes de dar la tarea por concluida.
1. Al comenzar: Lee la capa caliente del proyecto y ejecuta brain-capture --start --slug <slug>.
2. Durante la sesión: Anota decisiones y aprendizajes con evidencias reales (archivos y commits).
3. Al finalizar: La tarea no concluye hasta que brain-session genere la nota, brain-quality --strict verifique los estándares sin vaguedades, y brain-commit persista los cambios en Git local.
