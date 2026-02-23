# Proyecto: Agente Trader Codex

Este directorio contiene el agente de trading automatico para MetaTrader5
(Expert Advisor TM_VOLATILITY_75) y el sistema de gestion de skills.

## Comandos del proyecto
- Agente: `powershell -File descarga_datos/scripts/run_expert_tm_v75_agent.ps1`
- Supervisor: `powershell -File descarga_datos/scripts/run_expert_tm_v75_supervisor.ps1`

<!-- SKILLS_LIBRARY_START -->
## Skills Library — Contexto Experto

Directorio: `skills/` — **963 skills** en el indice.
Actualizacion: 2026-07-15 UTC

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

### Skills Activas (0)

No hay skills activas. Activa las que necesites:
```
python skills_manager.py activate python-pro
python skills_manager.py activate docker-expert fastapi
```
<!-- SKILLS_LIBRARY_END -->
