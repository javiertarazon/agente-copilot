# Proyecto: Agente Trader Codex

Este directorio contiene el agente de trading automatico para MetaTrader5
(Expert Advisor TM_VOLATILITY_75) y el sistema de gestion de skills.

## Comandos del proyecto
- Agente: `powershell -File descarga_datos/scripts/run_expert_tm_v75_agent.ps1`
- Supervisor: `powershell -File descarga_datos/scripts/run_expert_tm_v75_supervisor.ps1`

<!-- SKILLS_LIBRARY_START -->
## Skills Library â€” Contexto Experto

Directorio: `.github/skills/` â€” **964 skills** en el indice.
Actualizacion: 2026-02-27 00:20 UTC

### Comandos de gestion
```
python skills_manager.py list              # listar todas
python skills_manager.py list --active     # ver activas
python skills_manager.py search QUERY      # buscar
python skills_manager.py activate   ID     # activar
python skills_manager.py deactivate ID     # desactivar
python skills_manager.py fetch             # importar skills
python skills_manager.py github-search Q   # buscar repos
```

### Skills Activas (1 de 964)

Lee los archivos SKILL.md listados abajo al responder preguntas
en ese dominio. Aplica su metodologia y mejores practicas.

| Skill | Archivo | Descripcion |
|-------|---------|-------------|
| free-jt7-global-runtime-audit | .github/skills/free-jt7-global-runtime-audit/SKILL.md | Audit and enforce Free JT7 global runtime behavior across IDEs (C |

> **Instruccion para Claude**: Al inicio de cada sesion, lee los
> archivos SKILL.md de la tabla anterior. Cuando el usuario haga
> una solicitud relacionada con esa area, aplica el contexto experto
> de la skill correspondiente.
<!-- SKILLS_LIBRARY_END -->

<!-- FREE_JT7_CLAUDE_CODE_START -->
## Free JT7 Claude Code Bridge
Use these files as source of truth:
- `.github/copilot-instructions.md`
- `.github/agents/free-jt7.agent.md`
- `.github/skills/.skills_index.json`
- `.github/free-jt7-policy.yaml`
Prefer `python skills_manager.py task-run` for full execution flow.
<!-- FREE_JT7_CLAUDE_CODE_END -->
