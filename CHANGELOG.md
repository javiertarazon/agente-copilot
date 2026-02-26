# Changelog — Agente Free JT7

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v3.0] - 2026-02-26

### Summary
Rebranding a **Agente Free JT7** + compatibilidad multi-IDE ampliada (VS Code, Cursor, Kiro, Antigravity, Codex, Claude Code y Gemini CLI).

### Added
- Integración de workspace para `claude-code` (`.claude/openclaw-agent.md` + bridge en `CLAUDE.md`).
- Integración de workspace para `gemini-cli` (`.gemini/openclaw-agent.md` + bridge en `GEMINI.md`).
- Detección `auto` ampliada para `codex`, `claude-code` y `gemini-cli`.

### Changed
- Nombre operativo del agente actualizado a **Free JT7** en documentación y prompts.
- Scripts de instalación ajustados al branding Free JT7.
- `skills_manager.py` actualizado para exponer branding Free JT7 manteniendo compatibilidad legacy.


## [v2.0] - 2026-02-26

### Summary
OpenClaw autonomous runtime with policy, run telemetry, canary rollout, and strict quality gate.

### Added
- Declarative policy at `.github/openclaw-policy.yaml`.
- Task runtime commands: `task-start/task-step/task-close/task-run`.
- Ephemeral skill resolution with `skill-resolve`.
- Canary rollout modes via `rollout-mode` (`shadow|assist|autonomous`).
- Run telemetry at `copilot-agent/runs/<run_id>.json` and `events.jsonl` with sanitization.
- Operational runbook at `copilot-agent/RUNBOOK.md`.

### Changed
- `doctor` now supports `--strict`.
- `skills_manager.py` hardened for autonomous execution and quality gates.

## [v1.1] — 2026-07-15

### Summary
963 expert skills — autonomous AI coding agent for VS Code GitHub Copilot.

### Added
- **5 new autonomous-agent SKILL.md files**:
  - `agent-orchestration` — Multi-agent Gem/RUG Orchestrator orchestration patterns
  - `polyglot-testing-pipeline` — Multi-language TDD pipeline (Python/TS/Go/Rust/Java/C#)
  - `tdd-full-cycle` — Full Red→Green→Refactor TDD cycle with autonomous agents
  - `context-multi-file` — Context Architect for coordinated multi-file changes
  - `agent-safety-governance` — Safety & governance framework for autonomous agents
- **`skills/.skills_index.json`** updated to 963 entries (was 958)
- **`CLAUDE.md`** updated — 963 skills, date 2026-07-15
- **`.github/copilot-instructions.md`** updated — all category counts current
- **`copilot-agent/RESUME.md`** updated — reflects v1.1 milestone
- **PowerShell ExecutionPolicy** fix documented (RemoteSigned scope CurrentUser)

### Category Distribution (963 total)
| Category | Count |
|---|---|
| architecture | 83 |
| business | 130 |
| data-ai | 93 |
| development | 186 |
| general | 249 |
| infrastructure | 71 |
| security | 38 |
| testing | 34 |
| workflow | 78 |
| documentation | 1 |

---

## [v1.0] — 2026-07-14

### Summary
Initial release — 958 expert skills system built on top of:
- 908 base skills from [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) v5.7
- 50 additional skills from [github/awesome-copilot](https://github.com/github/awesome-copilot)

### Included
- `skills_manager.py` CLI with 12 commands
- Full `.github/skills/<id>/SKILL.md` library
- `skills/.skills_index.json` with 958 entries
- `CLAUDE.md` and `.github/copilot-instructions.md` with system prompt for Copilot
- `copilot-agent/` task tracking (tasks.yaml, audit-log, RESUME.md)
- OpenClaw source in `OPEN CLAW/`

## [v1.3] — 2026-02-26

### Summary
Release sync automático: 962 skills y consistencia de metadatos.

