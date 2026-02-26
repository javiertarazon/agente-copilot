# OpenClaw Runbook

## Checklist Operativo

1. Validar policy:
   - `python skills_manager.py policy-validate`
2. Confirmar modo rollout:
   - `python skills_manager.py rollout-mode`
3. Diagnóstico estricto:
   - `python skills_manager.py doctor --strict`
4. Resolver skills para la tarea:
   - `python skills_manager.py skill-resolve --query "<objetivo>" --top 3`
5. Ejecutar run:
   - `python skills_manager.py task-run --goal "<objetivo>" --commands "..."`
6. Revisar evidencia:
   - `copilot-agent/runs/<run_id>.json`
   - `copilot-agent/runs/<run_id>.events.jsonl`

## Modo Canary

- `shadow`: simula steps sin ejecutar comandos.
- `assist`: ejecuta con guardrails y reporta sugerencias.
- `autonomous`: ejecuta pipeline completo con quality gate.

## Gestión de Incidentes

### Falla de policy
1. Ejecutar `policy-validate`.
2. Corregir `.github/openclaw-policy.yaml`.
3. Reintentar en `shadow` antes de volver a `autonomous`.

### Falla de quality gate
1. Revisar `events.jsonl` del run.
2. Corregir step fallido y reintentar `task-step`.
3. Cerrar run de nuevo con `task-close`.

### Bloqueo por riesgo/destructivo
1. Confirmar si el comando es realmente necesario.
2. Reejecutar con `--approve-high-risk` o `--allow-destructive` solo si aplica.
3. Registrar motivo en resumen final del run.
