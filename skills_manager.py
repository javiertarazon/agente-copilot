#!/usr/bin/env python3
"""
Skills Library Manager for Claude Code.
Gestiona una libreria local de skills (habilidades de experto) que se
inyectan en CLAUDE.md para que Claude las use automaticamente.

Uso:
    python skills_manager.py <comando> [opciones]

Comandos:
    list       Listar skills disponibles
    search     Buscar skills por nombre/descripcion/tags
    activate   Activar una o mas skills
    deactivate Desactivar skills
    fetch      Importar skills desde un repo GitHub
    add        Agregar una skill nueva o desde archivo
    github-search  Buscar repos de skills en GitHub
    sync-claude    Actualizar CLAUDE.md con skills activas
    policy-validate  Validar policy de ejecución
    rollout-mode     Ver/cambiar modo canary
    skill-resolve    Resolver skills efímeras
    task-run/task-*  Orquestar runs de tarea con evidencia
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# Evita caidas por UnicodeEncodeError en consolas Windows con cp1252.
for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

ROOT          = Path(__file__).resolve().parent
# por defecto el catálogo residente se ubica en .github/skills
SKILLS_DIR    = ROOT / ".github" / "skills"
INDEX_FILE    = SKILLS_DIR / ".skills_index.json"
ACTIVE_FILE   = SKILLS_DIR / ".active_skills.json"
SOURCES_FILE  = SKILLS_DIR / ".sources.json"
LEGACY_SKILLS_DIR = ROOT / "skills"
LEGACY_INDEX_FILE = LEGACY_SKILLS_DIR / ".skills_index.json"
CLAUDE_MD     = ROOT / "CLAUDE.md"
COPILOT_AGENT = ROOT / "copilot-agent"
GH_SKILLS_DIR = ROOT / ".github" / "skills"
GH_INSTR_DIR  = ROOT / ".github" / "instructions"
COPILOT_INSTR = ROOT / ".github" / "copilot-instructions.md"
VERSION_FILE  = ROOT / "VERSION"
README_MD     = ROOT / "README.md"
CHANGELOG_MD  = ROOT / "CHANGELOG.md"
AGENT_FILE    = ROOT / ".github" / "agents" / "openclaw.agent.md"
POLICY_FILE   = ROOT / ".github" / "openclaw-policy.yaml"
ROLLOUT_FILE  = COPILOT_AGENT / "rollout-mode.json"

GITHUB_RAW  = "https://raw.githubusercontent.com"
GITHUB_API  = "https://api.github.com"
DEFAULT_REPO   = "javiertarazon/antigravity-awesome-skills"
DEFAULT_BRANCH = "main"

SKILLS_START = "<!-- SKILLS_LIBRARY_START -->"
SKILLS_END   = "<!-- SKILLS_LIBRARY_END -->"

DEFAULT_POLICY: dict[str, Any] = {
    "autonomy": {"mode": "autonomous"},
    "risk": {
        "thresholds": {
            "low_keywords": ["list", "search", "read", "inspect", "analyze"],
            "medium_keywords": ["install", "update", "configure", "build", "test"],
            "high_keywords": ["delete", "drop", "format", "reset", "remove", "shutdown"],
        },
        "destructive_patterns": ["rm ", "rmdir", "del ", "drop ", "truncate ", "git reset --hard"],
    },
    "execution": {"retry": {"max_attempts": 3}},
    "quality_gate": {"required": True},
    "skills": {"activation": "ephemeral", "max_composed": 3},
    "shell": {"strategy": "cross-shell", "default": "powershell"},
    "telemetry": {"level": "full_sanitized"},
    "report": {"style": "executive_technical"},
}

# Palabras clave para auto-categorizar skills
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "architecture": ["architect", "c4-", "cqrs", "event-sourcing", "adr", "brainstorm",
                     "refactor", "monorepo", "nestjs", "elixir", "haskell", "inngest"],
    "business":     ["seo", "crm", "growth", "pricing", "marketing", "sales", "content",
                     "copy", "hr", "competitor", "market", "startup", "notion-", "defi",
                     "contract", "conductor"],
    "data-ai":      ["llm", "rag", "agent-", "langchain", "langgraph", "crewai", "embedding",
                     "hugging", "fal-", "dbt", "feature-eng", "hybrid-search", "mlops",
                     "data-sci", "data-eng", "data-qual", "graphql", "analytics", "faiss"],
    "development":  ["python", "typescript", "javascript", "golang", "rust", "java", "php",
                     "ruby", "swift", "flutter", "django", "fastapi", "react", "vue",
                     "nextjs", "laravel", "shopify", "expo", "bun", "prisma", "clickhouse",
                     "discord-bot", "slack-bot", "mobile", "ios-dev", "android"],
    "general":      ["git-", "github-issue", "planning", "docs-", "code-review", "debug",
                     "clean-code", "commit", "create-pr", "readme", "tutorial", "mermaid",
                     "prompt-lib", "context-", "finishing-"],
    "infrastructure":["docker", "kubernetes", "terraform", "aws", "azure-", "devops",
                     "helm", "cicd", "ci-", "gitlab-ci", "github-action", "prometheus",
                     "grafana", "istio", "nginx", "serverless", "gitops", "mlops"],
    "security":     ["security", "pentest", "xss", "sql-inject", "auth-", "oauth",
                     "gdpr", "vulnerab", "burp", "metasploit", "idor", "active-directory",
                     "threat-model", "stride", "malware", "firmware", "incident-resp",
                     "pci-", "sast", "csrf"],
    "testing":      ["test", "tdd", "playwright", "cypress", "jest", "pytest", "qa-",
                     "ab-test", "unit-test", "e2e-", "bats-", "screen-reader"],
    "workflow":     ["slack-", "jira", "notion-", "airtable", "hubspot", "trello",
                     "asana", "monday", "zapier", "stripe-", "sentry", "datadog",
                     "linear-", "zendesk", "github-workflow", "confluence", "make-",
                     "clickup", "todoist", "figma"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades I/O
# ─────────────────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def save_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def load_index() -> list[dict]:
    return load_json(INDEX_FILE, [])


def save_index(skills: list[dict]) -> None:
    save_json(INDEX_FILE, skills)


def load_active() -> dict:
    return load_json(ACTIVE_FILE, {"active": [], "auto_detect": True, "last_changed": ""})


def save_active(data: dict) -> None:
    save_json(ACTIVE_FILE, data)


def load_sources() -> dict:
    return load_json(SOURCES_FILE, {"sources": []})


def save_sources(data: dict) -> None:
    save_json(SOURCES_FILE, data)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _parse_scalar(value: str) -> Any:
    val = value.strip()
    if val.lower() in {"true", "false"}:
        return val.lower() == "true"
    if re.fullmatch(r"-?\d+", val):
        try:
            return int(val)
        except Exception:
            return val
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        items = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        return [item.strip("'\"") for item in items]
    return val


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _parse_scalar(value)
    return root


def _to_yaml_lines(data: dict[str, Any], level: int = 0) -> list[str]:
    lines: list[str] = []
    prefix = " " * level
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_to_yaml_lines(value, level + 2))
        elif isinstance(value, list):
            rendered = ", ".join(
                f"'{x}'" if isinstance(x, str) and ("," in x or " " in x) else str(x)
                for x in value
            )
            lines.append(f"{prefix}{key}: [{rendered}]")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return lines


def _write_policy(policy: dict[str, Any]) -> None:
    lines = ["# OpenClaw policy file (autogenerated)", * _to_yaml_lines(policy), ""]
    _atomic_write_text(POLICY_FILE, "\n".join(lines))


def _load_policy() -> dict[str, Any]:
    if not POLICY_FILE.exists():
        _write_policy(DEFAULT_POLICY)
        return DEFAULT_POLICY
    try:
        parsed = _parse_simple_yaml(POLICY_FILE.read_text(encoding="utf-8"))
    except Exception:
        parsed = {}
    return _deep_merge(DEFAULT_POLICY, parsed if isinstance(parsed, dict) else {})


def _validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    mode = str(policy.get("autonomy", {}).get("mode", ""))
    if mode not in {"shadow", "assist", "autonomous"}:
        errors.append("autonomy.mode debe ser shadow|assist|autonomous")
    strategy = str(policy.get("shell", {}).get("strategy", ""))
    if strategy not in {"cross-shell", "powershell"}:
        errors.append("shell.strategy debe ser cross-shell|powershell")
    max_attempts = policy.get("execution", {}).get("retry", {}).get("max_attempts", 0)
    if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 5:
        errors.append("execution.retry.max_attempts debe ser entero entre 1 y 5")
    level = str(policy.get("telemetry", {}).get("level", ""))
    if level not in {"full_sanitized", "moderate", "minimal"}:
        errors.append("telemetry.level inválido")
    return errors


def _load_rollout_mode(policy: dict[str, Any]) -> str:
    if ROLLOUT_FILE.exists():
        data = load_json(ROLLOUT_FILE, {})
        mode = str(data.get("mode", ""))
        if mode in {"shadow", "assist", "autonomous"}:
            return mode
    return str(policy.get("autonomy", {}).get("mode", "autonomous"))


def _save_rollout_mode(mode: str) -> None:
    COPILOT_AGENT.mkdir(parents=True, exist_ok=True)
    save_json(ROLLOUT_FILE, {
        "mode": mode,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def _runs_dir() -> Path:
    return COPILOT_AGENT / "runs"


def _run_paths(run_id: str) -> tuple[Path, Path]:
    base = _runs_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{run_id}.json", base / f"{run_id}.events.jsonl"


def _redact_sensitive(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\"`]+)",
        r"\1=***REDACTED***",
        out,
    )
    out = re.sub(r"(?i)bearer\s+([a-z0-9\._\-]+)", "Bearer ***REDACTED***", out)
    out = re.sub(r"ghp_[A-Za-z0-9]{20,}", "***REDACTED***", out)
    out = re.sub(r"sk-[A-Za-z0-9]{20,}", "***REDACTED***", out)
    return out


def _append_run_event(run_id: str, payload: dict[str, Any]) -> None:
    _, events = _run_paths(run_id)
    safe_payload = {
        **payload,
        "command": _redact_sensitive(str(payload.get("command", ""))),
        "result": _redact_sensitive(str(payload.get("result", ""))),
        "redaction_applied": True,
    }
    with open(events, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_payload, ensure_ascii=False) + "\n")


def _classify_risk(text: str, policy: dict[str, Any]) -> str:
    probe = text.lower()
    thresholds = policy.get("risk", {}).get("thresholds", {})
    if any(k in probe for k in thresholds.get("high_keywords", [])):
        return "high"
    if any(k in probe for k in thresholds.get("medium_keywords", [])):
        return "medium"
    return "low"


def _is_destructive(command: str, policy: dict[str, Any]) -> bool:
    probe = command.lower()
    for pat in policy.get("risk", {}).get("destructive_patterns", []):
        if pat.lower() in probe:
            return True
    return False


def _normalize_shell_command(command: str, strategy: str) -> str:
    if strategy != "cross-shell":
        return command
    trimmed = command.strip()
    if trimmed == "ls":
        return "Get-ChildItem"
    if trimmed.startswith("cat "):
        arg = trimmed[4:].strip()
        return f"Get-Content -Path {arg}"
    if trimmed == "pwd":
        return "Get-Location"
    if trimmed.startswith("grep "):
        parts = shlex.split(trimmed)
        if len(parts) >= 3:
            pat = parts[1]
            target = parts[2]
            return f"Select-String -Path {target} -Pattern {pat}"
    return command


def _execute_powershell(command: str, timeout: int = 120000) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout / 1000,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output[:8000]
    except subprocess.TimeoutExpired:
        return 124, "command timed out"
    except Exception as exc:
        return 1, str(exc)


def _resolve_skills_for_query(query: str, top_n: int = 3) -> list[dict[str, Any]]:
    skills = load_index()
    scored = [(s, _relevance(s, query)) for s in skills]
    scored = [(s, score) for s, score in scored if score > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    picked = []
    for skill, score in scored[:top_n]:
        picked.append({
            "id": skill["id"],
            "category": skill.get("category", "general"),
            "score": round(score, 3),
            "gh_path": skill.get("gh_path", ""),
        })
    return picked
def _backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.bak.{stamp}")
    shutil.copy2(path, backup)
    return backup


def _mirror_legacy_index(skills: list[dict]) -> None:
    LEGACY_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    save_json(LEGACY_INDEX_FILE, skills)


def _ensure_active_consistency(skills: list[dict]) -> list[dict]:
    active_data = load_active()
    active_set = set(active_data.get("active", []))
    for skill in skills:
        skill["active"] = skill.get("id") in active_set
    return skills


def _load_skills_from_disk(skills_dir: Path) -> list[dict]:
    skills: list[dict] = []
    active_set = set(load_active().get("active", []))
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_id = skill_md.parent.name
        with open(skill_md, "r", encoding="utf-8", errors="replace") as handle:
            header_probe = handle.read(16384)
        if not header_probe.startswith("---"):
            header_probe = ""
        meta, _ = parse_frontmatter(header_probe)
        fm_meta = meta.get("metadata", {}) if isinstance(meta.get("metadata"), dict) else {}
        name = str(meta.get("name", skill_id))
        description = str(meta.get("description", "")).strip()
        category = str(fm_meta.get("category", "")) or auto_categorize(skill_id, description)
        skills.append({
            "id": skill_id,
            "name": name,
            "description": description[:120],
            "category": category,
            "path": str(skill_md.relative_to(ROOT)).replace("\\", "/"),
            "gh_path": str(skill_md.relative_to(ROOT)).replace("\\", "/"),
            "tags": [t for t in skill_id.replace("-", " ").split() if len(t) > 2],
            "risk": str(fm_meta.get("risk", "unknown")),
            "source": str(fm_meta.get("source", "local")),
            "active": skill_id in active_set,
        })
    return skills


def _rebuild_index_from_disk() -> list[dict]:
    if not SKILLS_DIR.exists():
        raise RuntimeError(f"No existe el catálogo de skills: {SKILLS_DIR}")
    skills = _load_skills_from_disk(SKILLS_DIR)
    if not skills:
        raise RuntimeError("No se encontraron SKILL.md en .github/skills")
    skills.sort(key=lambda s: s["id"])
    save_index(skills)
    _mirror_legacy_index(skills)
    return skills


def _migrate_legacy_state() -> list[str]:
    notes: list[str] = []
    if LEGACY_INDEX_FILE.exists() and not INDEX_FILE.exists():
        backup = _backup_file(LEGACY_INDEX_FILE)
        if backup:
            notes.append(f"backup legado creado: {backup.name}")
    if not INDEX_FILE.exists() and SKILLS_DIR.exists():
        skills = _load_skills_from_disk(SKILLS_DIR)
        if skills:
            save_index(skills)
            _mirror_legacy_index(skills)
            notes.append("índice reconstruido desde .github/skills")
    elif INDEX_FILE.exists():
        _mirror_legacy_index(load_index())
        notes.append("espejo legado actualizado")
    return notes


def _preflight(require_index: bool = False, strict_active_project: bool = False) -> None:
    if not SKILLS_DIR.exists():
        raise RuntimeError(f"Catálogo no encontrado: {SKILLS_DIR}")
    migrate_notes = _migrate_legacy_state()
    if migrate_notes:
        _log_audit("migrate", "; ".join(migrate_notes))
    if require_index and not INDEX_FILE.exists():
        _rebuild_index_from_disk()
    if strict_active_project:
        active_project = load_json(COPILOT_AGENT / "active-project.json", {})
        if not active_project.get("path"):
            raise RuntimeError(
                "Proyecto activo no configurado. Ejecuta: python skills_manager.py set-project <ruta>"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Frontmatter
# ─────────────────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parsea frontmatter YAML simple (solo primer nivel + metadata: bloque)."""
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    m = pattern.match(text)
    if not m:
        return {}, text
    meta: dict[str, Any] = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith('#'):
            i += 1
            continue
        if re.match(r'^[a-zA-Z0-9_-]+:\s*$', line):
            # bloque anidado
            key = line.split(':')[0].strip()
            sub: dict[str, Any] = {}
            i += 1
            while i < len(lines) and (lines[i].startswith('  ') or lines[i].startswith('\t')):
                sub_line = lines[i].strip()
                if ':' in sub_line:
                    sk, _, sv = sub_line.partition(':')
                    sv = sv.strip().strip('"')
                    # parse list
                    if sv.startswith('[') and sv.endswith(']'):
                        sv = [x.strip().strip('"') for x in sv[1:-1].split(',') if x.strip()]
                    sub[sk.strip()] = sv
                i += 1
            meta[key] = sub
        elif ':' in line:
            k, _, v = line.partition(':')
            v = v.strip().strip('"')
            if v.startswith('[') and v.endswith(']'):
                v = [x.strip().strip('"') for x in v[1:-1].split(',') if x.strip()]
            meta[k.strip()] = v
            i += 1
        else:
            i += 1
            continue
    return meta, text[m.end():]


def build_frontmatter(meta: dict, body: str) -> str:
    """Serializa frontmatter dict a YAML block + cuerpo."""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                if isinstance(sv, list):
                    lines.append(f"  {sk}: [{', '.join(sv)}]")
                else:
                    lines.append(f"  {sk}: {sv}")
        elif isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


# ─────────────────────────────────────────────────────────────────────────────
# Categorization automatica
# ─────────────────────────────────────────────────────────────────────────────

def auto_categorize(skill_id: str, description: str = "") -> str:
    text = (skill_id + " " + description).lower()
    best_cat  = "general"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_cat   = cat
    return best_cat


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"User-Agent": "skills-manager/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_url(url: str, timeout: int = 15) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def fetch_json(url: str) -> Any:
    data = fetch_url(url)
    if data is None:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


def print_progress(done: int, total: int, label: str = "", width: int = 36) -> None:
    pct   = done / total if total else 0
    filled = int(width * pct)
    bar   = "=" * filled + "-" * (width - filled)
    suffix = f" {label}" if label else ""
    sys.stdout.write(f"\r  [{bar}] {done}/{total}{suffix}   ")
    sys.stdout.flush()
    if done >= total:
        sys.stdout.write("\n")


# ─────────────────────────────────────────────────────────────────────────────
# cmd_fetch
# ─────────────────────────────────────────────────────────────────────────────

def cmd_fetch(args: argparse.Namespace) -> int:
    """Importa skills desde un repositorio GitHub."""
    try:
        _preflight(require_index=False)
    except RuntimeError as exc:
        print(f"[fetch] ERROR: {exc}")
        return 1

    repo   = args.repo   if hasattr(args, "repo")   and args.repo   else DEFAULT_REPO
    branch = args.branch if hasattr(args, "branch") and args.branch else DEFAULT_BRANCH
    force  = getattr(args, "update", False)
    dry    = getattr(args, "dry_run", False)

    raw_base = f"{GITHUB_RAW}/{repo}/{branch}"

    print(f"[fetch] Repo   : {repo} (branch: {branch})")
    print(f"[fetch] Destino: {SKILLS_DIR}")

    # 1. Obtener skills_index.json del repo
    print("[fetch] Descargando skills_index.json...")
    index_data = fetch_json(f"{raw_base}/skills_index.json")
    if not index_data or not isinstance(index_data, list):
        print("[fetch] ERROR: No se pudo obtener skills_index.json del repo.")
        return 1

    total = len(index_data)
    print(f"[fetch] Encontrados {total} skills.")

    if dry:
        print("[fetch] Modo --dry-run: no se descarga nada.")
        for s in index_data[:5]:
            print(f"  {s['id']:40s}  {s.get('description','')[:60]}")
        print(f"  ... y {total - 5} mas.")
        return 0

    # 2. Descargar cada SKILL.md
    ok = 0
    skip = 0
    errors: list[str] = []

    for i, entry in enumerate(index_data):
        skill_path  = entry.get("path", "")           # e.g. "skills/python-pro"
        skill_id    = entry.get("id", "")
        description = entry.get("description", "")
        category    = entry.get("category", "")

        if not skill_path or not skill_id:
            errors.append(f"[skip] entry sin path/id: {entry}")
            continue

        local_file = ROOT / skill_path / "SKILL.md"

        if local_file.exists() and not force:
            skip += 1
            print_progress(i + 1, total, f"(skip) {skill_id}")
            continue

        url = f"{raw_base}/{skill_path}/SKILL.md"
        content = fetch_url(url)

        if content is None:
            errors.append(f"[error] No se pudo descargar: {url}")
            print_progress(i + 1, total, f"(error) {skill_id}")
            continue

        # Inyectar metadata local
        try:
            text = content.decode("utf-8", errors="replace")
            meta, body = parse_frontmatter(text)
            if "metadata" not in meta:
                meta["metadata"] = {}
            if isinstance(meta["metadata"], dict):
                if not meta["metadata"].get("category"):
                    meta["metadata"]["category"] = (
                        category if category and category != "uncategorized"
                        else auto_categorize(skill_id, description)
                    )
                meta["metadata"]["source"] = repo
                meta["metadata"]["imported_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            text = build_frontmatter(meta, body)
        except Exception:
            text = content.decode("utf-8", errors="replace")

        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_text(text, encoding="utf-8")
        ok += 1

        print_progress(i + 1, total, skill_id[:30])
        time.sleep(0.04)

    sys.stdout.write("\n")

    # 3. Rebuild index
    print(f"[fetch] Descargados: {ok}  Saltados: {skip}  Errores: {len(errors)}")
    if errors:
        for e in errors[:5]:
            print(f"  {e}")
        if len(errors) > 5:
            print(f"  ... y {len(errors)-5} errores mas.")

    print("[fetch] Reconstruyendo indice local...")
    _rebuild_index(index_data, repo)

    # 4. Actualizar sources
    sources = load_sources()
    existing = [s for s in sources["sources"] if s["repo"] != repo]
    existing.append({
        "repo": repo,
        "description": f"Skills importados de {repo}",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "skill_count": ok + skip,
        "branch": branch,
    })
    sources["sources"] = existing
    save_sources(sources)

    print(f"[fetch] Listo. Indice con {len(load_index())} skills.")
    return 0


def _rebuild_index(remote_index: list[dict], repo: str) -> None:
    """Reconstruye .skills_index.json a partir de los archivos locales."""
    del remote_index, repo
    skills = _rebuild_index_from_disk()
    print(f"[index] {len(skills)} skills indexados.")


# ─────────────────────────────────────────────────────────────────────────────
# cmd_list
# ─────────────────────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[list] ERROR: {exc}")
        return 1
    skills = load_index()
    if not skills:
        print("No hay skills en el indice. Ejecuta: python skills_manager.py fetch")
        return 0

    cat_filter    = getattr(args, "category", None)
    only_active   = getattr(args, "active",   False)
    output_json   = getattr(args, "json",     False)

    if cat_filter:
        skills = [s for s in skills if s["category"] == cat_filter]
    if only_active:
        skills = [s for s in skills if s.get("active")]

    if output_json:
        print(json.dumps(skills, indent=2))
        return 0

    # Agrupar por categoria
    from collections import defaultdict
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for s in skills:
        by_cat[s["category"]].append(s)

    total_active = sum(1 for s in skills if s.get("active"))
    print(f"\n{'-'*68}")
    print(f"  Skills Library  -  {len(skills)} skills  |  {total_active} activas")
    print(f"{'-'*68}")

    for cat in sorted(by_cat.keys()):
        group = by_cat[cat]
        active_count = sum(1 for s in group if s.get("active"))
        print(f"\n  {cat.upper()} ({len(group)} skills, {active_count} activas)")
        for s in sorted(group, key=lambda x: x["id"]):
            flag = "[ON]" if s.get("active") else "    "
            desc = s.get("description", "")[:55]
            print(f"    {flag}  {s['id']:<38s}  {desc}")

    print()
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# cmd_search
# ─────────────────────────────────────────────────────────────────────────────

def _relevance(skill: dict, query: str) -> float:
    q = query.lower()
    tokens = q.split()
    text = (skill.get("id","") + " " + skill.get("description","") + " " +
            " ".join(skill.get("tags", []))).lower()

    # Puntuacion por tokens exactos
    score = sum(1.5 if t in skill.get("id","").lower() else
                1.0 if t in text else 0.0
                for t in tokens)

    # Similitud difusa con el ID
    fuzzy = SequenceMatcher(None, q, skill.get("id","").lower()).ratio()
    score += fuzzy * 0.8
    return score


def cmd_search(args: argparse.Namespace) -> int:
    query      = " ".join(args.query) if args.query else ""
    top_n      = getattr(args, "top",      15)
    cat_filter = getattr(args, "category", None)

    if not query:
        print("Uso: python skills_manager.py search QUERY [--top N] [--category CAT]")
        return 1

    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[search] ERROR: {exc}")
        return 1
    skills = load_index()
    if not skills:
        print("No hay skills. Ejecuta: python skills_manager.py fetch")
        return 1

    if cat_filter:
        skills = [s for s in skills if s["category"] == cat_filter]

    scored = [(s, _relevance(s, query)) for s in skills]
    scored = [(s, sc) for s, sc in scored if sc > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:top_n]

    if not scored:
        print(f'Sin resultados para: "{query}"')
        return 0

    print(f'\nResultados para: "{query}"  ({len(scored)} encontrados)\n')
    print(f"  {'Score':>5}  {'Categoria':<16}  {'Skill ID':<38}  Descripcion")
    print(f"  {'-'*5}  {'-'*16}  {'-'*38}  {'-'*40}")
    for s, sc in scored:
        flag = " [ON]" if s.get("active") else "     "
        desc = s.get("description","")[:42]
        print(f"  {sc:5.2f}  {s['category']:<16}  {s['id']:<38}  {desc}")

    print()
    if scored:
        best = scored[0][0]
        if not best.get("active"):
            print(f'  Sugerencia: python skills_manager.py activate {best["id"]}')
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# cmd_activate / cmd_deactivate
# ─────────────────────────────────────────────────────────────────────────────

def cmd_activate(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[activate] ERROR: {exc}")
        return 1
    skill_ids = args.skill_ids
    skills    = load_index()
    active    = load_active()

    index_map = {s["id"]: i for i, s in enumerate(skills)}
    activated = []
    not_found = []

    for sid in skill_ids:
        if sid in index_map:
            skills[index_map[sid]]["active"] = True
            if sid not in active["active"]:
                active["active"].append(sid)
            activated.append(sid)
        else:
            not_found.append(sid)

    if activated:
        active["last_changed"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_index(skills)
        save_active(active)
        _mirror_legacy_index(skills)
        print(f"[activate] Activadas: {', '.join(activated)}")
        cmd_sync_claude(args)
    if not_found:
        print(f"[activate] No encontradas: {', '.join(not_found)}")
        print("  Sugerencia: python skills_manager.py search <nombre>")
    return 0 if activated else 1


def cmd_deactivate(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[deactivate] ERROR: {exc}")
        return 1
    skill_ids = args.skill_ids
    skills    = load_index()
    active    = load_active()

    index_map = {s["id"]: i for i, s in enumerate(skills)}
    deactivated = []

    for sid in skill_ids:
        if sid in index_map:
            skills[index_map[sid]]["active"] = False
            deactivated.append(sid)
        if sid in active["active"]:
            active["active"].remove(sid)

    if deactivated:
        active["last_changed"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_index(skills)
        save_active(active)
        _mirror_legacy_index(skills)
        print(f"[deactivate] Desactivadas: {', '.join(deactivated)}")
        cmd_sync_claude(args)
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# cmd_add
# ─────────────────────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> int:
    """Agrega una skill nueva al indice."""
    try:
        _preflight(require_index=False)
    except RuntimeError as exc:
        print(f"[add] ERROR: {exc}")
        return 1
    name     = getattr(args, "name",      None)
    category = getattr(args, "category",  "general")
    desc     = getattr(args, "description", "")
    file_src = getattr(args, "file",      None)
    from_repo= getattr(args, "from_repo", None)

    local_file: Path | None = None
    if from_repo:
        # Formato: OWNER/REPO/path/to/SKILL.md
        parts = from_repo.split("/", 2)
        if len(parts) < 3:
            print("ERROR: --from-repo debe ser OWNER/REPO/path/al/SKILL.md")
            return 1
        owner, repo, path_in_repo = parts
        url = f"{GITHUB_RAW}/{owner}/{repo}/main/{path_in_repo}"
        print(f"[add] Descargando desde {url}...")
        content = fetch_url(url)
        if content is None:
            print(f"[add] ERROR: No se pudo descargar {url}")
            return 1
        # Derivar nombre del path
        if not name:
            name = Path(path_in_repo).parent.name or Path(path_in_repo).stem
        if not category:
            category = auto_categorize(name, desc)
        local_file = SKILLS_DIR / name / "SKILL.md"
        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_bytes(content)
        print(f"[add] Skill guardada en: {local_file}")
        file_src = str(local_file)

    elif file_src:
        src = Path(file_src)
        if not src.exists():
            print(f"ERROR: Archivo no encontrado: {file_src}")
            return 1
        if not name:
            name = src.stem
        if not category:
            category = auto_categorize(name, desc)
        local_file = SKILLS_DIR / name / "SKILL.md"
        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_bytes(src.read_bytes())
        print(f"[add] Skill importada en: {local_file}")
        file_src = str(local_file)

    else:
        # Crear plantilla
        if not name:
            print("ERROR: Especifica --name NOMBRE o usa --file / --from-repo")
            return 1
        if not category:
            category = auto_categorize(name, desc)
        local_file = SKILLS_DIR / name / "SKILL.md"
        local_file.parent.mkdir(parents=True, exist_ok=True)
        template = f"""---
name: {name}
description: {desc or 'Describe aqui el proposito de esta skill.'}
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
metadata:
  category: {category}
  tags: []
  source: local
  imported_at: "{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}"
  risk: safe
---

# {name.replace('-', ' ').title()}

> {desc or 'Agrega aqui las instrucciones de experto para esta skill.'}

---

## Cuando usar esta skill
-

## Instrucciones
-

## Patrones y mejores practicas
-
"""
        local_file.write_text(template, encoding="utf-8")

    if local_file is None:
        print("[add] ERROR interno: no se pudo resolver ruta de salida.")
        return 1

    if not local_file.exists():
        print(f"[add] ERROR: no se creó el archivo esperado: {local_file}")
        return 1

    try:
        skills = _rebuild_index_from_disk()
    except RuntimeError as exc:
        print(f"[add] ERROR al reconstruir índice: {exc}")
        return 1

    _log_audit("add", f"{name} ({category})")
    _update_resume("add", f"skill creada/importada: {name}")
    print(f"[add] '{name}' agregada. Índice total: {len(skills)}")
    return 0


def cmd_add_agent(args: argparse.Namespace) -> int:
    """Genera un esqueleto de agente en `.github/agents`."""
    name = getattr(args, "name", None)
    if not name:
        print("ERROR: especifica --name para el agente")
        return 1
    desc = getattr(args, "description", "")
    model = getattr(args, "model", "claude-sonnet-4-5")
    tools = getattr(args, "tools", [])

    agent_id = name.lower().replace(" ", "-")
    agents_dir = ROOT / ".github" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f"{agent_id}.agent.md"
    if agent_file.exists():
        print(f"ERROR: el agente ya existe: {agent_file}")
        return 1

    tools_yaml = "\n".join([f"  - {t}" for t in tools])
    template = f"""---
name: {name}
description: {desc or 'Descripción del agente.'}
model: {model}
tools:
{tools_yaml}
---

# {name} — Agente personalizado

Eres **{agent_id}**.
Define aquí el comportamiento y las reglas del agente.
"""
    agent_file.write_text(template, encoding="utf-8")
    print(f"[add-agent] Agente creado en {agent_file}")
    _log_audit("add-agent", agent_id)
    _update_resume("add-agent", f"agente creado: {agent_id}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# cmd_github_search
# ─────────────────────────────────────────────────────────────────────────────

def cmd_github_search(args: argparse.Namespace) -> int:
    query = " ".join(args.query) if args.query else "claude skills"
    top_n = getattr(args, "top", 10)

    search_terms = [
        urllib.parse.quote(query) + "+topic:claude-skills",
        urllib.parse.quote(query) + "+topic:awesome-skills",
        urllib.parse.quote(query) + "+topic:agent-skills",
        urllib.parse.quote(query) + "+topic:claude-code-skills",
        urllib.parse.quote(query) + "+SKILL.md+in:path",
    ]

    seen: set[str] = set()
    repos: list[dict] = []

    for term in search_terms:
        url = f"{GITHUB_API}/search/repositories?q={term}&sort=stars&order=desc&per_page=20"
        data = fetch_json(url)
        if not data or "items" not in data:
            continue
        for item in data["items"]:
            full_name = item.get("full_name","")
            if full_name in seen:
                continue
            seen.add(full_name)
            repos.append({
                "repo":        full_name,
                "stars":       item.get("stargazers_count", 0),
                "description": (item.get("description") or "")[:80],
                "updated":     (item.get("updated_at") or "")[:10],
                "topics":      item.get("topics", []),
            })

    repos.sort(key=lambda r: r["stars"], reverse=True)
    repos = repos[:top_n]

    if not repos:
        print(f'Sin resultados en GitHub para: "{query}"')
        print("  Tip: intenta sin GITHUB_TOKEN para busqueda publica.")
        return 0

    print(f'\nRepositorios GitHub - "{query}"\n')
    print(f"  {'Stars':>6}  {'Repositorio':<45}  Descripcion")
    print(f"  {'-'*6}  {'-'*45}  {'-'*40}")
    for r in repos:
        stars_str = f"{r['stars']:,}" if r['stars'] else "0"
        print(f"  {stars_str:>6}  {r['repo']:<45}  {r['description']}")

    print()
    if repos:
        best = repos[0]
        print(f'  Para importar el mejor resultado:')
        print(f'  python skills_manager.py fetch --repo {best["repo"]}')
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# cmd_sync_claude
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# cmd_adapt_copilot
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_APPLY_TO: dict[str, str] = {
    "architecture":   "**/*.{ts,js,py,go,rs,java,cs,md}",
    "business":       "**/*.{md,txt,json}",
    "data-ai":        "**/*.{py,ipynb,json,yaml,yml}",
    "development":    "**/*.{ts,tsx,js,jsx,py,go,rs,java,cs,rb,php,swift,kt}",
    "general":        "**/*",
    "infrastructure": "**/*.{yaml,yml,tf,dockerfile,sh,toml}",
    "security":       "**/*.{ts,js,py,go,rs,java,cs,rb,php}",
    "testing":        "**/*.{test.ts,test.js,test.py,spec.ts,spec.js,_test.go}",
    "workflow":       "**/*.{yaml,yml,json,md}",
}


def cmd_adapt_copilot(args: argparse.Namespace) -> int:
    """Regenera .github/instructions/ y actualiza copilot-instructions.md."""
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[adapt-copilot] ERROR: {exc}")
        return 1
    skills = load_index()
    if not skills:
        print("[adapt-copilot] No hay skills en el indice.")
        return 1

    from collections import defaultdict
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for s in skills:
        by_cat[s["category"]].append(s)

    GH_INSTR_DIR.mkdir(parents=True, exist_ok=True)

    for cat, entries in by_cat.items():
        if not entries:
            continue
        apply_to = CATEGORY_APPLY_TO.get(cat, "**/*")
        lines = [
            "---",
            f'applyTo: "{apply_to}"',
            "---",
            "",
            f"# Skills de experto — categoría: {cat}",
            "",
            f"Cuando el usuario haga una solicitud relacionada con **{cat}**, "
            f"consulta automáticamente el SKILL.md correspondiente en "
            f"`.github/skills/<nombre>/SKILL.md` antes de responder.",
            "",
            f"## Skills disponibles en esta categoría ({len(entries)})",
            "",
            "| ID | Descripción |",
            "|-----|-------------|" ,
        ]
        for e in sorted(entries, key=lambda x: x["id"]):
            desc = e.get("description", "")[:80].replace("|", "\\|")
            lines.append(f"| `{e['id']}` | {desc} |")
        lines += [
            "",
            "## Instrucción de uso",
            "",
            "1. **Identifica** qué skill es más relevante para la solicitud.",
            "2. **Lee** el archivo `.github/skills/<id>/SKILL.md` para obtener "
            "   contexto experto, metodología y mejores prácticas.",
            "3. **Aplica** ese conocimiento en tu respuesta.",
            "4. Si múltiples skills son relevantes, combínalas.",
        ]
        out = GH_INSTR_DIR / f"{cat}.instructions.md"
        out.write_text("\n".join(lines), encoding="utf-8")

    # Actualizar conteos en copilot-instructions.md
    if COPILOT_INSTR.exists():
        content = COPILOT_INSTR.read_text(encoding="utf-8")
        content = re.sub(r'\*\*(\d+) skills expertos\*\*',
                         f'**{len(skills)} skills expertos**', content)
        for cat, entries in by_cat.items():
            content = re.sub(
                rf'(\| `{cat}` \|) (\d+) (\|)',
                rf'\g<1> {len(entries)} \g<3>',
                content
            )
        content = re.sub(
            r'\*(\d+) skills — antigravity.*\*',
            f'*{len(skills)} skills — antigravity-awesome-skills v5.7 + OpenClaw behaviors*',
            content
        )
        COPILOT_INSTR.write_text(content, encoding="utf-8")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _log_audit("adapt-copilot", f"{len(skills)} skills, {len(by_cat)} categorias")
    print(f"[adapt-copilot] {len(skills)} skills | {len(by_cat)} categorias | {ts}")
    for cat in sorted(by_cat):
        print(f"  {cat:<20} {len(by_cat[cat]):>4} skills")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# copilot-agent helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log_audit(action: str, detail: str = "") -> None:
    """Registra una entrada en copilot-agent/audit-log.jsonl."""
    COPILOT_AGENT.mkdir(parents=True, exist_ok=True)
    audit = COPILOT_AGENT / "audit-log.jsonl"
    entry = json.dumps({
        "ts":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "detail": detail,
    }, ensure_ascii=False)
    with open(audit, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def _update_resume(action: str, detail: str = "") -> None:
    """Actualiza copilot-agent/RESUME.md con la última acción."""
    COPILOT_AGENT.mkdir(parents=True, exist_ok=True)
    resume = COPILOT_AGENT / "RESUME.md"
    skills = load_index()
    active = [s for s in skills if s.get("active")]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    active_lines = '\n'.join(f'- `{s["id"]}` ({s["category"]})' for s in active) or '- (ninguna)'
    content = f"""# copilot-agent — Estado del sistema

*Actualizado: {ts}*

## Última acción
- **{action}**: {detail}

## Estado del catálogo
- Total skills: **{len(skills)}**
- Skills activas: **{len(active)}**
- Categorías: 9
- Fuente: antigravity-awesome-skills v5.7

## Skills activas
{active_lines}

## Comandos útiles
```powershell
python skills_manager.py search <query>
python skills_manager.py activate <id>
python skills_manager.py adapt-copilot
python skills_manager.py sync-claude
```
"""
    resume.write_text(content, encoding="utf-8")


def cmd_sync_claude(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[sync-claude] ERROR: {exc}")
        return 1

    skills  = load_index()
    active_skills = [s for s in skills if s.get("active")]
    total   = len(skills)

    # Construir bloque de skills activas
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        SKILLS_START,
        "## Skills Library — Contexto Experto",
        "",
        f"Directorio: `.github/skills/` — **{total} skills** en el indice.",
        f"Actualizacion: {ts}",
        "",
        "### Comandos de gestion",
        "```",
        "python skills_manager.py list              # listar todas",
        "python skills_manager.py list --active     # ver activas",
        "python skills_manager.py search QUERY      # buscar",
        "python skills_manager.py activate   ID     # activar",
        "python skills_manager.py deactivate ID     # desactivar",
        "python skills_manager.py fetch             # importar skills",
        "python skills_manager.py github-search Q   # buscar repos",
        "```",
        "",
    ]

    if active_skills:
        active_block = "\n".join(
            f"| {s['id']} | {s.get('path', '')} | {s.get('description', '')[:65]} |"
            for s in active_skills
        )
        lines += [
            f"### Skills Activas ({len(active_skills)} de {total})",
            "",
            "Lee los archivos SKILL.md listados abajo al responder preguntas",
            "en ese dominio. Aplica su metodologia y mejores practicas.",
            "",
            "| Skill | Archivo | Descripcion |",
            "|-------|---------|-------------|",
            active_block,
            "",
            "> **Instruccion para Claude**: Al inicio de cada sesion, lee los",
            "> archivos SKILL.md de la tabla anterior. Cuando el usuario haga",
            "> una solicitud relacionada con esa area, aplica el contexto experto",
            "> de la skill correspondiente.",
        ]
    else:
        lines += [
            "",
            "No hay skills activas. Activa las que necesites:",
            "```",
            "python skills_manager.py activate python-pro",
            "python skills_manager.py activate docker-expert fastapi",
            "```",
        ]

    lines.append(SKILLS_END)
    block = "\n".join(lines)

    # Leer/crear CLAUDE.md
    if CLAUDE_MD.exists():
        content = CLAUDE_MD.read_text(encoding="utf-8")
        if SKILLS_START in content and SKILLS_END in content:
            # Reemplazar bloque existente
            start_idx = content.index(SKILLS_START)
            end_idx   = content.index(SKILLS_END) + len(SKILLS_END)
            new_content = content[:start_idx].rstrip() + "\n\n" + block + "\n"
        else:
            # Append al final
            new_content = content.rstrip() + "\n\n" + block + "\n"
    else:
        # Crear CLAUDE.md nuevo
        new_content = f"""# Proyecto: Agente Trader Codex

Este directorio contiene el agente de trading automatico para MetaTrader5
(Expert Advisor TM_VOLATILITY_75) y el sistema de gestion de skills.

## Comandos del proyecto
- Agente: `powershell -File descarga_datos/scripts/run_expert_tm_v75_agent.ps1`
- Supervisor: `powershell -File descarga_datos/scripts/run_expert_tm_v75_supervisor.ps1`

<!-- SKILLS_LIBRARY_START -->
{block}
<!-- SKILLS_LIBRARY_END -->
"""

    CLAUDE_MD.write_text(new_content, encoding="utf-8")
    print(f"[sync-claude] CLAUDE.md actualizado. Skills activas: {len(active_skills)}/{total}")
    _log_audit("sync-claude", f"{len(active_skills)} activas de {total}")
    _update_resume("sync-claude", f"{len(active_skills)} activas de {total}")
    return 0


def cmd_set_project(args: argparse.Namespace) -> int:
    """Establece el proyecto activo donde se aplican los cambios."""
    import json as _json
    ruta = Path(args.path).resolve()
    if not ruta.exists():
        print(f"[set-project] WARN La ruta no existe: {ruta}")
        resp = input("¿Crear directorio? [s/N] ").strip().lower()
        if resp == "s":
            ruta.mkdir(parents=True)
        else:
            return 1
    ap = COPILOT_AGENT / "active-project.json"
    COPILOT_AGENT.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if ap.exists():
        try:
            existing = _json.loads(ap.read_text(encoding="utf-8"))
        except Exception:
            pass
    history = existing.get("history", [])
    if existing.get("path"):
        history.insert(0, {"path": existing["path"], "set_at": existing.get("set_at", "")})
    history = history[:10]  # keep last 10
    config = {
        "_description": "Proyecto activo donde se aplican los cambios. Edita 'path' o usa: python skills_manager.py set-project <ruta>",
        "path": str(ruta),
        "name": ruta.name,
        "set_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": args.description or "",
        "history": history,
    }
    ap.write_text(_json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[set-project] OK Proyecto activo: {ruta}")
    _log_audit("set-project", str(ruta))
    _update_resume("set-project", f"proyecto activo → {ruta.name}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Instala/vincula skills de este agente en otro proyecto."""
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[install] ERROR: {exc}")
        return 1

    target = Path(args.path).resolve()
    gh_target = target / ".github"
    skills_target = gh_target / "skills"
    instr_target = gh_target / "instructions"
    ci_target = gh_target / "copilot-instructions.md"

    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    gh_target.mkdir(parents=True, exist_ok=True)

    # copilot-instructions.md
    if not ci_target.exists() or args.force:
        shutil.copy2(ROOT / ".github" / "copilot-instructions.md", ci_target)
        print(f"[install] OK copilot-instructions.md -> {ci_target}")
    else:
        print(f"[install] SKIP copilot-instructions.md ya existe (usa --force para sobreescribir)")

    # skills/ (symlink)
    if skills_target.exists() or skills_target.is_symlink():
        if args.force:
            if skills_target.is_symlink():
                skills_target.unlink()
            else:
                shutil.rmtree(skills_target)
        else:
            print(f"[install] SKIP .github/skills/ ya existe (usa --force)")
    if not skills_target.exists() and not skills_target.is_symlink():
        try:
            skills_target.symlink_to(GH_SKILLS_DIR, target_is_directory=True)
            print(f"[install] LINK .github/skills/ -> symlink a {GH_SKILLS_DIR}")
        except OSError:
            shutil.copytree(GH_SKILLS_DIR, skills_target)
            print(f"[install] COPY .github/skills/ -> copiado (sin privilegios de symlink)")

    # instructions/ (symlink)
    instr_src = ROOT / ".github" / "instructions"
    if instr_target.exists() or instr_target.is_symlink():
        if args.force:
            if instr_target.is_symlink():
                instr_target.unlink()
            else:
                shutil.rmtree(instr_target)
        else:
            print(f"[install] SKIP .github/instructions/ ya existe (usa --force)")
    if not instr_target.exists() and not instr_target.is_symlink():
        try:
            instr_target.symlink_to(instr_src, target_is_directory=True)
            print(f"[install] LINK .github/instructions/ -> symlink a {instr_src}")
        except OSError:
            shutil.copytree(instr_src, instr_target)
            print(f"[install] COPY .github/instructions/ -> copiado")

    _log_audit("install", str(target))
    _update_resume("install", f"skills instalados en {target.name}")
    print(f"[install] OK Skills vinculados en: {target}")
    return 0


def cmd_policy_validate(args: argparse.Namespace) -> int:
    del args
    policy = _load_policy()
    errors = _validate_policy(policy)
    if errors:
        print("[policy-validate] ERROR")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("[policy-validate] OK")
    print(json.dumps(policy, indent=2, ensure_ascii=False))
    return 0


def cmd_rollout_mode(args: argparse.Namespace) -> int:
    policy = _load_policy()
    mode = getattr(args, "mode", None)
    if not mode:
        current = _load_rollout_mode(policy)
        print(f"[rollout-mode] {current}")
        return 0
    if mode not in {"shadow", "assist", "autonomous"}:
        print("[rollout-mode] ERROR: modo inválido")
        return 1
    _save_rollout_mode(mode)
    _log_audit("rollout-mode", mode)
    print(f"[rollout-mode] OK -> {mode}")
    return 0


def _create_run_record(run_id: str, payload: dict[str, Any]) -> None:
    run_file, _ = _run_paths(run_id)
    save_json(run_file, payload)


def _load_run_record(run_id: str) -> dict[str, Any] | None:
    run_file, _ = _run_paths(run_id)
    if not run_file.exists():
        return None
    return load_json(run_file, {})


def cmd_task_start(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[task-start] ERROR: {exc}")
        return 1
    policy = _load_policy()
    policy_errors = _validate_policy(policy)
    if policy_errors:
        print("[task-start] ERROR: policy inválida")
        for err in policy_errors:
            print(f"  - {err}")
        return 1

    goal = str(getattr(args, "goal", "")).strip()
    if not goal:
        print("[task-start] ERROR: especifica --goal")
        return 1
    run_id = getattr(args, "run_id", None) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    scope = str(getattr(args, "scope", "workspace"))
    risk_level = _classify_risk(goal, policy)
    skills_selected = _resolve_skills_for_query(goal, int(policy.get("skills", {}).get("max_composed", 3)))

    run = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": "",
        "user_goal": goal,
        "scope": scope,
        "risk_level": risk_level,
        "status": "planned",
        "skills_selected": skills_selected,
        "quality_gate": {"required": bool(policy.get("quality_gate", {}).get("required", True)), "passed": False},
        "steps": [],
        "summary": "",
        "rollout_mode": _load_rollout_mode(policy),
    }
    _create_run_record(run_id, run)
    _append_run_event(run_id, {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step_id": "intake",
        "action": "task-start",
        "command": "",
        "result": f"goal={goal}",
        "exit_code": 0,
        "retry_index": 0,
        "evidence_ref": "",
    })
    print(f"[task-start] OK run_id={run_id} risk={risk_level} mode={run['rollout_mode']}")
    return 0


def cmd_skill_resolve(args: argparse.Namespace) -> int:
    try:
        _preflight(require_index=True)
    except RuntimeError as exc:
        print(f"[skill-resolve] ERROR: {exc}")
        return 1
    query = str(getattr(args, "query", "")).strip()
    if not query:
        print("[skill-resolve] ERROR: especifica --query")
        return 1
    top = int(getattr(args, "top", 3))
    items = _resolve_skills_for_query(query, top)
    if getattr(args, "json", False):
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return 0
    print(f"[skill-resolve] query='{query}' -> {len(items)} skills")
    for item in items:
        print(f"  - {item['id']} ({item['category']}) score={item['score']}")
    return 0


def cmd_task_step(args: argparse.Namespace) -> int:
    run_id = str(getattr(args, "run_id", "")).strip()
    if not run_id:
        print("[task-step] ERROR: especifica --run-id")
        return 1
    run = _load_run_record(run_id)
    if not run:
        print(f"[task-step] ERROR: run no encontrado: {run_id}")
        return 1
    command = str(getattr(args, "command", "")).strip()
    if not command:
        print("[task-step] ERROR: especifica --command")
        return 1

    policy = _load_policy()
    mode = run.get("rollout_mode", _load_rollout_mode(policy))
    strategy = str(policy.get("shell", {}).get("strategy", "cross-shell"))
    normalized = _normalize_shell_command(command, strategy)
    risk_level = _classify_risk(command, policy)
    destructive = _is_destructive(command, policy)

    if destructive and not getattr(args, "allow_destructive", False):
        step_result = {
            "step_id": f"step-{len(run.get('steps', [])) + 1}",
            "action": "blocked-destructive",
            "command": command,
            "normalized_command": normalized,
            "result": "Comando bloqueado por política destructiva",
            "exit_code": 2,
            "retry_index": 0,
            "risk_level": risk_level,
            "mode": mode,
        }
        run.setdefault("steps", []).append(step_result)
        run["status"] = "blocked"
        _create_run_record(run_id, run)
        _append_run_event(run_id, {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "step_id": step_result["step_id"],
            "action": step_result["action"],
            "command": command,
            "result": step_result["result"],
            "exit_code": 2,
            "retry_index": 0,
            "evidence_ref": "",
        })
        print("[task-step] BLOCKED destructive command")
        return 1

    if risk_level == "high" and not getattr(args, "approve_high_risk", False):
        print("[task-step] BLOCKED high-risk requires --approve-high-risk")
        return 1

    max_attempts = int(policy.get("execution", {}).get("retry", {}).get("max_attempts", 3))
    run["status"] = "running"
    attempts = [
        normalized,
        normalized + " 2>$null",
        f"cmd /c {command}",
    ]
    attempts = attempts[:max_attempts]

    if mode == "shadow":
        exit_code, result = 0, f"[shadow] command simulated: {normalized}"
        used_attempt = 0
    else:
        exit_code, result, used_attempt = 1, "", 0
        for retry_index, candidate in enumerate(attempts):
            code, out = _execute_powershell(candidate)
            exit_code, result, used_attempt = code, out, retry_index
            _append_run_event(run_id, {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "step_id": f"step-{len(run.get('steps', [])) + 1}",
                "action": "task-step-attempt",
                "command": candidate,
                "result": out[:1000],
                "exit_code": code,
                "retry_index": retry_index,
                "evidence_ref": "",
            })
            if code == 0:
                break

    step = {
        "step_id": f"step-{len(run.get('steps', [])) + 1}",
        "action": "task-step",
        "command": command,
        "normalized_command": normalized,
        "result": result[:4000],
        "exit_code": exit_code,
        "retry_index": used_attempt,
        "risk_level": risk_level,
        "mode": mode,
    }
    run.setdefault("steps", []).append(step)
    if exit_code != 0:
        run["status"] = "failed"
    _create_run_record(run_id, run)
    print(f"[task-step] run_id={run_id} exit={exit_code} retries={used_attempt}")
    return 0 if exit_code == 0 else 1


def cmd_task_close(args: argparse.Namespace) -> int:
    run_id = str(getattr(args, "run_id", "")).strip()
    if not run_id:
        print("[task-close] ERROR: especifica --run-id")
        return 1
    run = _load_run_record(run_id)
    if not run:
        print(f"[task-close] ERROR: run no encontrado: {run_id}")
        return 1
    steps = run.get("steps", [])
    required = bool(run.get("quality_gate", {}).get("required", True))
    passed = bool(steps) and all(int(s.get("exit_code", 1)) == 0 for s in steps)
    if required and not passed:
        run["status"] = "blocked"
        run["quality_gate"]["passed"] = False
        run["summary"] = "Bloqueado por quality gate: existen steps fallidos o sin evidencia."
        _create_run_record(run_id, run)
        print("[task-close] BLOCKED quality gate")
        return 1
    run["quality_gate"]["passed"] = passed
    run["status"] = "succeeded" if passed else "failed"
    run["ended_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run["summary"] = str(getattr(args, "summary", "")).strip() or f"Run finalizado con {len(steps)} steps"
    _create_run_record(run_id, run)
    _append_run_event(run_id, {
        "ts": run["ended_at"],
        "step_id": "close",
        "action": "task-close",
        "command": "",
        "result": run["summary"],
        "exit_code": 0 if run["status"] == "succeeded" else 1,
        "retry_index": 0,
        "evidence_ref": "",
    })
    _log_audit("task-close", f"{run_id}:{run['status']}")
    print(f"[task-close] OK run_id={run_id} status={run['status']}")
    return 0 if run["status"] == "succeeded" else 1


def cmd_task_run(args: argparse.Namespace) -> int:
    goal = str(getattr(args, "goal", "")).strip()
    commands = list(getattr(args, "commands", []) or [])
    if not goal:
        print("[task-run] ERROR: especifica --goal")
        return 1
    start_rc = cmd_task_start(argparse.Namespace(
        goal=goal,
        scope=getattr(args, "scope", "workspace"),
        run_id=getattr(args, "run_id", None),
    ))
    if start_rc != 0:
        return start_rc

    # Recuperar run_id más reciente si no fue explícito.
    run_id = getattr(args, "run_id", None)
    if not run_id:
        runs = sorted(_runs_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            print("[task-run] ERROR: no se pudo resolver run_id")
            return 1
        run_id = runs[0].stem

    rc = 0
    for command in commands:
        step_rc = cmd_task_step(argparse.Namespace(
            run_id=run_id,
            command=command,
            approve_high_risk=getattr(args, "approve_high_risk", False),
            allow_destructive=getattr(args, "allow_destructive", False),
        ))
        if step_rc != 0:
            rc = step_rc
            break

    close_rc = cmd_task_close(argparse.Namespace(run_id=run_id, summary=getattr(args, "summary", "")))
    return close_rc if rc == 0 else rc


def cmd_doctor(args: argparse.Namespace) -> int:
    strict = bool(getattr(args, "strict", False))
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    if not SKILLS_DIR.exists():
        errors.append(f"catálogo ausente: {SKILLS_DIR}")
    else:
        skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
        if not skill_files:
            errors.append("no se encontraron SKILL.md en .github/skills")
        else:
            info.append(f"SKILL.md detectados: {len(skill_files)}")

    if INDEX_FILE.exists():
        try:
            index = load_index()
            info.append(f"índice principal: {len(index)} entries")
        except Exception as exc:
            errors.append(f"índice principal corrupto: {exc}")
            index = []
    else:
        warnings.append("índice principal ausente; se requiere rebuild")
        index = []

    if LEGACY_INDEX_FILE.exists():
        info.append("índice legado presente (compatibilidad)")
    else:
        warnings.append("índice legado ausente (se regenerará en sync/rebuild)")

    if not COPILOT_INSTR.exists():
        errors.append("falta .github/copilot-instructions.md")
    if not AGENT_FILE.exists():
        errors.append("falta .github/agents/openclaw.agent.md")
    if not GH_INSTR_DIR.exists():
        errors.append("falta .github/instructions/")

    active_project = load_json(COPILOT_AGENT / "active-project.json", {})
    if not active_project.get("path"):
        warnings.append("active-project.json sin ruta (set-project recomendado)")

    policy = _load_policy()
    policy_errors = _validate_policy(policy)
    if policy_errors:
        errors.extend([f"policy inválida: {e}" for e in policy_errors])
    else:
        info.append(f"policy mode: {_load_rollout_mode(policy)}")

    if index:
        missing = [s["id"] for s in index if not (ROOT / s["gh_path"]).exists()]
        if missing:
            errors.append(f"{len(missing)} entries del índice apuntan a rutas inexistentes")

    print("[doctor] Diagnóstico del sistema")
    for line in info:
        print(f"  [INFO] {line}")
    for line in warnings:
        print(f"  [WARN] {line}")
    for line in errors:
        print(f"  [ERR ] {line}")

    _log_audit("doctor", f"errors={len(errors)} warnings={len(warnings)} strict={strict}")
    if errors:
        return 1
    return 1 if strict and warnings else 0


def _sync_counts_in_text(path: Path, replacements: list[tuple[str, str]]) -> None:
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    updated = content
    for pattern, repl in replacements:
        updated = re.sub(pattern, repl, updated, flags=re.MULTILINE)
    if updated != content:
        _atomic_write_text(path, updated)


def cmd_release_sync(args: argparse.Namespace) -> int:
    bump = getattr(args, "bump", "patch")
    try:
        skills = _rebuild_index_from_disk()
    except RuntimeError as exc:
        print(f"[release-sync] ERROR: {exc}")
        return 1

    by_cat: dict[str, int] = {}
    for skill in skills:
        by_cat[skill["category"]] = by_cat.get(skill["category"], 0) + 1
    total = len(skills)

    _sync_counts_in_text(
        COPILOT_INSTR,
        [
            (r"\*\*\d+ skills expertos\*\*", f"**{total} skills expertos**"),
            (r"- \*\*Catálogo completo\*\*: `skills/\.skills_index\.json` — \d+ entries",
             f"- **Catálogo completo**: `.github/skills/.skills_index.json` — {total} entries"),
            (r"\*\d+ skills — antigravity-awesome-skills v5\.7 \+ OpenClaw behaviors\*",
             f"*{total} skills — antigravity-awesome-skills v5.7 + OpenClaw behaviors*"),
        ],
    )

    for cat, count in by_cat.items():
        _sync_counts_in_text(
            COPILOT_INSTR,
            [(rf"(\| `{re.escape(cat)}` \|)\s+\d+\s+(\|)", rf"\g<1> {count} \g<2>")],
        )

    _sync_counts_in_text(
        AGENT_FILE,
        [
            (r"acceso a \d+ skills expertos", f"acceso a {total} skills expertos"),
            (r"catálogo de \d+ skills", f"catálogo de {total} skills"),
        ],
    )
    _sync_counts_in_text(
        README_MD,
        [
            (r"\b\d+\s+Skills\b", f"{total} Skills"),
            (r"\*\*\d+ skills\*\*", f"**{total} skills**"),
            (r"\*+\d+ skills — MIT License\*+", f"*{total} skills — MIT License*"),
        ],
    )

    version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0"
    parts = [int(p) for p in version.split(".") if p.isdigit()]
    while len(parts) < 2:
        parts.append(0)
    major, minor = parts[0], parts[1]
    if bump == "minor":
        minor += 1
    else:
        minor += 1
    new_version = f"{major}.{minor}"
    _atomic_write_text(VERSION_FILE, new_version + "\n")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if CHANGELOG_MD.exists():
        changelog = CHANGELOG_MD.read_text(encoding="utf-8")
        entry = (
            f"\n## [v{new_version}] — {ts}\n\n"
            "### Summary\n"
            f"Release sync automático: {total} skills y consistencia de metadatos.\n\n"
        )
        if entry not in changelog:
            _atomic_write_text(CHANGELOG_MD, changelog + entry)

    _mirror_legacy_index(skills)
    _update_resume("release-sync", f"{total} skills | versión {new_version}")
    _log_audit("release-sync", f"skills={total} version={new_version}")
    print(f"[release-sync] OK | skills={total} | version={new_version}")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    del args
    try:
        skills = _rebuild_index_from_disk()
    except RuntimeError as exc:
        print(f"[rebuild] ERROR: {exc}")
        return 1
    print(f"[rebuild] indice reconstruido: {len(skills)}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="skills_manager",
        description="Skills Library Manager para Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMANDO")

    # list
    p_list = sub.add_parser("list", help="Listar skills")
    p_list.add_argument("--category", "-c", help="Filtrar por categoria")
    p_list.add_argument("--active",   "-a", action="store_true", help="Solo activas")
    p_list.add_argument("--json",     "-j", action="store_true", help="Salida JSON")

    # search
    p_search = sub.add_parser("search", help="Buscar skills")
    p_search.add_argument("query", nargs="*", help="Terminos de busqueda")
    p_search.add_argument("--top",      "-n", type=int, default=15, help="Max resultados")
    p_search.add_argument("--category", "-c", help="Filtrar por categoria")

    # activate
    p_act = sub.add_parser("activate", help="Activar skills")
    p_act.add_argument("skill_ids", nargs="+", help="IDs de skills a activar")

    # deactivate
    p_dea = sub.add_parser("deactivate", help="Desactivar skills")
    p_dea.add_argument("skill_ids", nargs="+", help="IDs de skills a desactivar")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Importar skills desde GitHub")
    p_fetch.add_argument("--repo",    default=DEFAULT_REPO,   help="Owner/repo")
    p_fetch.add_argument("--branch",  default=DEFAULT_BRANCH, help="Branch")
    p_fetch.add_argument("--update",  "-u", action="store_true", help="Forzar actualizacion")
    p_fetch.add_argument("--dry-run", "-d", action="store_true", help="Sin descargar")

    # add
    p_add = sub.add_parser("add", help="Agregar skill nueva")
    p_add.add_argument("--name",        "-n", help="Nombre/ID de la skill")
    p_add.add_argument("--description", "-d", default="", help="Descripcion")
    p_add.add_argument("--category",    "-c", help="Categoria")
    p_add.add_argument("--file",        "-f", help="Importar desde archivo local")
    p_add.add_argument("--from-repo",   help="OWNER/REPO/path/SKILL.md en GitHub")

    # github-search
    p_gs = sub.add_parser("github-search", help="Buscar repos de skills en GitHub")
    p_gs.add_argument("query", nargs="*", help="Terminos")
    p_gs.add_argument("--top", "-n", type=int, default=10, help="Max resultados")

    # sync-claude
    sub.add_parser("sync-claude", help="Actualizar CLAUDE.md con skills activas")

    # adapt-copilot
    sub.add_parser("adapt-copilot", help="Regenerar .github/instructions/ para Copilot")

    # rebuild (util interna)
    sub.add_parser("rebuild", help="Reconstruir indice desde archivos locales")
    p_doc = sub.add_parser("doctor", help="Diagnosticar integridad del sistema")
    p_doc.add_argument("--strict", action="store_true", help="Tratar warnings como fallo")
    p_rs = sub.add_parser("release-sync", help="Sincronizar conteos/versionado y metadatos")
    p_rs.add_argument("--bump", choices=["patch", "minor"], default="patch", help="Tipo de bump de versión")

    # policy/runtime
    sub.add_parser("policy-validate", help="Validar política operativa OpenClaw")
    p_rm = sub.add_parser("rollout-mode", help="Ver o establecer modo rollout")
    p_rm.add_argument("mode", nargs="?", choices=["shadow", "assist", "autonomous"], help="Nuevo modo")

    p_sr = sub.add_parser("skill-resolve", help="Resolver skills efímeras para una tarea")
    p_sr.add_argument("--query", required=True, help="Consulta de tarea")
    p_sr.add_argument("--top", type=int, default=3, help="Máximo de skills")
    p_sr.add_argument("--json", action="store_true", help="Salida JSON")

    p_ts = sub.add_parser("task-start", help="Crear run de tarea")
    p_ts.add_argument("--goal", required=True, help="Objetivo de la tarea")
    p_ts.add_argument("--scope", default="workspace", help="Ámbito de ejecución")
    p_ts.add_argument("--run-id", default="", help="ID opcional de run")

    p_tstep = sub.add_parser("task-step", help="Ejecutar un step sobre un run")
    p_tstep.add_argument("--run-id", required=True, help="ID de run")
    p_tstep.add_argument("--command", required=True, help="Comando del step")
    p_tstep.add_argument("--approve-high-risk", action="store_true", help="Aprobar step high-risk")
    p_tstep.add_argument("--allow-destructive", action="store_true", help="Permitir comando destructivo")

    p_tc = sub.add_parser("task-close", help="Cerrar run aplicando quality gate")
    p_tc.add_argument("--run-id", required=True, help="ID de run")
    p_tc.add_argument("--summary", default="", help="Resumen final")

    p_tr = sub.add_parser("task-run", help="Orquestar tarea completa end-to-end")
    p_tr.add_argument("--goal", required=True, help="Objetivo de la tarea")
    p_tr.add_argument("--scope", default="workspace", help="Ámbito de ejecución")
    p_tr.add_argument("--run-id", default="", help="ID opcional de run")
    p_tr.add_argument("--commands", nargs="*", default=[], help="Comandos a ejecutar en orden")
    p_tr.add_argument("--approve-high-risk", action="store_true", help="Aprobar high-risk")
    p_tr.add_argument("--allow-destructive", action="store_true", help="Permitir comandos destructivos")
    p_tr.add_argument("--summary", default="", help="Resumen final")

    # set-project
    p_sp = sub.add_parser("set-project", help="Establecer el proyecto activo (donde se aplican los cambios)")
    p_sp.add_argument("path", help="Ruta del proyecto activo")
    p_sp.add_argument("--description", "-d", default="", help="Notas sobre el proyecto")

    # install
    p_inst = sub.add_parser("install", help="Instalar skills (symlinks) en otro proyecto")
    p_inst.add_argument("path", help="Ruta del proyecto destino")
    p_inst.add_argument("--force", "-f", action="store_true", help="Sobreescribir archivos existentes")

    # add-agent
    p_agent = sub.add_parser("add-agent", help="Crear un agente personalizado")
    p_agent.add_argument("--name", "-n", help="Nombre/ID del agente")
    p_agent.add_argument("--description", "-d", default="", help="Descripción breve")
    p_agent.add_argument("--model", "-m", default="claude-sonnet-4-5", help="Modelo base")
    p_agent.add_argument("--tools", "-t", nargs="*", default=["codebase","terminal","search","vscode"], help="Lista de herramientas disponibles")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return 0

    dispatch = {
        "list":          cmd_list,
        "search":        cmd_search,
        "activate":      cmd_activate,
        "deactivate":    cmd_deactivate,
        "fetch":         cmd_fetch,
        "add":           cmd_add,
        "github-search": cmd_github_search,
        "sync-claude":   cmd_sync_claude,
        "adapt-copilot": cmd_adapt_copilot,
        "rebuild":       cmd_rebuild,
        "doctor":        cmd_doctor,
        "release-sync":  cmd_release_sync,
        "policy-validate": cmd_policy_validate,
        "rollout-mode":  cmd_rollout_mode,
        "skill-resolve": cmd_skill_resolve,
        "task-start":    cmd_task_start,
        "task-step":     cmd_task_step,
        "task-close":    cmd_task_close,
        "task-run":      cmd_task_run,
        "set-project":   cmd_set_project,
        "install":       cmd_install,
        "add-agent":    cmd_add_agent,
    }

    fn = dispatch.get(args.cmd)
    if fn is None:
        print(f"Comando desconocido: {args.cmd}")
        return 1

    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
