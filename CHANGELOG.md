# Changelog — OpenClaw Copilot Agent

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

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
