#!/usr/bin/env python3
"""
adapt_skills.py â€” Adapta skills de antigravity-awesome-skills al sistema
Copilot/FreeJT7 del workspace.

Acciones:
  1. Lee skills de _antigravity_tmp/skills/*/SKILL.md
  2. Categoriza con CATEGORY_KEYWORDS
  3. Copia a .github/skills/<nombre>/SKILL.md  (formato FreeJT7/Copilot)
  4. Copia a skills/<categoria>/<nombre>/SKILL.md  (para skills_manager.py)
  5. Genera .github/instructions/<categoria>.instructions.md  (auto-detect Copilot)
  6. Actualiza skills/.skills_index.json
  7. Genera resumen copilot-agent/RESUME.md
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# â”€â”€â”€ Rutas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT          = Path(__file__).resolve().parent
SRC           = ROOT / "_antigravity_tmp" / "skills"
GH_SKILLS     = ROOT / ".github" / "skills"
LOCAL_SKILLS  = ROOT / "skills"
GH_INSTR      = ROOT / ".github" / "instructions"
COPILOT_AGENT = ROOT / "copilot-agent"
INDEX_FILE    = LOCAL_SKILLS / ".skills_index.json"

# â”€â”€â”€ CategorÃ­as â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "architecture":   ["architect", "c4-", "cqrs", "event-sourcing", "adr",
                       "brainstorm", "refactor", "monorepo", "nestjs",
                       "elixir", "haskell", "inngest", "system-design",
                       "design-pattern", "microservice", "ddd", "clean-arch"],
    "business":       ["seo", "crm", "growth", "pricing", "marketing", "sales",
                       "content", "copy", "hr", "competitor", "market",
                       "startup", "notion-", "defi", "contract", "conductor",
                       "product-manager", "pm-", "roadmap", "okr",
                       "go-to-market", "copywriting", "cro-"],
    "data-ai":        ["llm", "rag", "agent-", "langchain", "langgraph",
                       "crewai", "embedding", "hugging", "fal-", "dbt",
                       "feature-eng", "hybrid-search", "mlops", "data-sci",
                       "data-eng", "data-qual", "graphql", "analytics",
                       "faiss", "prompt-eng", "ai-agent", "ai-engineer",
                       "ai-ml", "openai", "anthropic", "gemini", "vector-"],
    "development":    ["python", "typescript", "javascript", "golang", "rust",
                       "java", "php", "ruby", "swift", "flutter", "django",
                       "fastapi", "react", "vue", "nextjs", "laravel",
                       "shopify", "expo", "bun", "prisma", "clickhouse",
                       "discord-bot", "slack-bot", "mobile", "ios-dev",
                       "android", "dotnet", "csharp", "kotlin", "scala",
                       "elixir", "rails", "spring", "express", "nuxt",
                       "svelte", "astro", "remix", "tauri", "electron",
                       "threejs", "3d-web", "webgl", "zustand", "redux"],
    "general":        ["git-", "github-issue", "planning", "docs-",
                       "code-review", "debug", "clean-code", "commit",
                       "create-pr", "readme", "tutorial", "mermaid",
                       "prompt-lib", "context-", "finishing-", "writing",
                       "refactor", "address-github", "code-quality",
                       "linting", "formatting"],
    "infrastructure": ["docker", "kubernetes", "terraform", "aws", "azure-",
                       "devops", "helm", "cicd", "ci-", "gitlab-ci",
                       "github-action", "prometheus", "grafana", "istio",
                       "nginx", "serverless", "gitops", "mlops", "k8s",
                       "ansible", "pulumi", "cdk-", "cloud-", "gcp",
                       "vercel", "railway", "fly-", "render-"],
    "security":       ["security", "pentest", "xss", "sql-inject", "auth-",
                       "oauth", "gdpr", "vulnerab", "burp", "metasploit",
                       "idor", "active-directory", "threat-model", "stride",
                       "malware", "firmware", "incident-resp", "pci-",
                       "sast", "csrf", "owasp", "jwt-", "ssl-", "tls-",
                       "encryption", "crypto-", "ssrf", "rce-", "lfi-"],
    "testing":        ["test", "tdd", "playwright", "cypress", "jest",
                       "pytest", "qa-", "ab-test", "unit-test", "e2e-",
                       "bats-", "screen-reader", "vitest", "selenium",
                       "load-test", "perf-test", "benchmark", "mock-",
                       "fixture-", "coverage"],
    "workflow":       ["slack-", "jira", "notion-", "airtable", "hubspot",
                       "trello", "asana", "monday", "zapier", "stripe-",
                       "sentry", "datadog", "linear-", "zendesk",
                       "github-workflow", "confluence", "make-", "clickup",
                       "todoist", "figma", "automation", "n8n", "trigger-",
                       "inngest", "workflow-", "orchestr"],
}

# Mapeo applyTo para Copilot auto-detect  
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


# â”€â”€â”€ Utilidades â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parsea YAML frontmatter simple."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ':' in line and not line.startswith(' '):
            k, _, v = line.partition(':')
            v = v.strip().strip('"').strip("'")
            meta[k.strip()] = v
    return meta, text[m.end():]


def categorize(skill_id: str, description: str) -> str:
    combined = (skill_id + " " + description).lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in combined:
                return cat
    return "general"


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# â”€â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    if not SRC.exists():
        print(f"ERROR: {SRC} no existe. Ejecuta primero el clone.")
        sys.exit(1)

    skills_dirs = [d for d in SRC.iterdir() if d.is_dir()]
    total       = len(skills_dirs)
    print(f"Procesando {total} skills...")

    index: list[dict] = []
    cat_skills: dict[str, list[dict]] = {c: [] for c in CATEGORY_KEYWORDS}
    cat_skills["general"] = cat_skills.get("general", [])

    errors = 0
    for i, skill_dir in enumerate(sorted(skills_dirs), 1):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        # Saltar si ya fue procesado
        if (GH_SKILLS / skill_dir.name / "SKILL.md").exists():
            # AÃºn lo indexamos aunque ya exista
            _meta, _ = parse_frontmatter(
                (GH_SKILLS / skill_dir.name / "SKILL.md")
                .read_bytes().decode("utf-8", errors="replace")
            )
            _id   = _meta.get("name", skill_dir.name)
            _desc = _meta.get("description", "")
            _cat  = categorize(_id, _desc)
            entry = {
                "id": skill_dir.name, "name": _id, "description": _desc[:120],
                "category": _cat,
                "path":    f"skills/{_cat}/{skill_dir.name}/SKILL.md",
                "gh_path": f".github/skills/{skill_dir.name}/SKILL.md",
                "active": False, "source": _meta.get("source","antigravity"),
                "risk": _meta.get("risk","unknown"),
            }
            index.append(entry)
            cat_skills.setdefault(_cat, []).append(entry)
            continue

        try:
            raw = skill_md.read_bytes().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  [WARN] {skill_dir.name}: {e}")
            errors += 1
            continue

        meta, body = parse_frontmatter(raw)
        skill_id   = meta.get("name", skill_dir.name)
        description= meta.get("description", "")
        category   = categorize(skill_id, description)

        # â”€â”€ 1. Copiar a .github/skills/<nombre>/SKILL.md â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        gh_dest = ensure(GH_SKILLS / skill_dir.name) / "SKILL.md"
        try:
            shutil.copy2(skill_md, gh_dest)
        except Exception as e:
            gh_dest.write_text(raw, encoding="utf-8")

        # Copiar archivos auxiliares del skill (si los hay)
        for aux in skill_dir.iterdir():
            if aux.name != "SKILL.md" and aux.is_file():
                try:
                    shutil.copy2(aux, GH_SKILLS / skill_dir.name / aux.name)
                except Exception:
                    pass

        # â”€â”€ 2. Copiar a skills/<categoria>/<nombre>/SKILL.md â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        local_dest = ensure(LOCAL_SKILLS / category / skill_dir.name) / "SKILL.md"
        try:
            shutil.copy2(skill_md, local_dest)
        except Exception:
            local_dest.write_text(raw, encoding="utf-8")

        # â”€â”€ 3. Registrar en Ã­ndice â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        entry = {
            "id":          skill_dir.name,
            "name":        skill_id,
            "description": description[:120],
            "category":    category,
            "path":        f"skills/{category}/{skill_dir.name}/SKILL.md",
            "gh_path":     f".github/skills/{skill_dir.name}/SKILL.md",
            "active":      False,
            "source":      meta.get("source", "antigravity"),
            "risk":        meta.get("risk", "unknown"),
        }
        index.append(entry)
        cat_skills.setdefault(category, []).append(entry)

        if i % 100 == 0:
            print(f"  {i}/{total} procesados...")

    print(f"\nFase 1 completa: {len(index)} skills indexados ({errors} errores).\n")

    # â”€â”€ 4. Guardar Ã­ndice local â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    INDEX_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Ãndice guardado: {INDEX_FILE}")

    # â”€â”€ 5. Generar .github/instructions/<categoria>.instructions.md â”€â”€â”€â”€â”€â”€â”€
    ensure(GH_INSTR)
    for cat, entries in cat_skills.items():
        if not entries:
            continue
        apply_to = CATEGORY_APPLY_TO.get(cat, "**/*")
        lines = [
            f"---",
            f'applyTo: "{apply_to}"',
            f"---",
            f"",
            f"# Skills de experto â€” categorÃ­a: {cat}",
            f"",
            f"Cuando el usuario haga una solicitud relacionada con **{cat}**, "
            f"consulta automÃ¡ticamente el SKILL.md correspondiente en "
            f"`.github/skills/<nombre>/SKILL.md` antes de responder.",
            f"",
            f"## Skills disponibles en esta categorÃ­a ({len(entries)})",
            f"",
            f"| ID | DescripciÃ³n |",
            f"|-----|-------------|",
        ]
        for e in sorted(entries, key=lambda x: x["id"]):
            desc = e["description"][:80].replace("|", "\\|")
            lines.append(f"| `{e['id']}` | {desc} |")
        lines += [
            "",
            "## InstrucciÃ³n de uso",
            "",
            "1. **Identifica** quÃ© skill es mÃ¡s relevante para la solicitud.",
            "2. **Lee** el archivo `.github/skills/<id>/SKILL.md` para obtener "
            "   contexto experto, metodologÃ­a y mejores prÃ¡cticas.",
            "3. **Aplica** ese conocimiento en tu respuesta.",
            "4. Si mÃºltiples skills son relevantes, combÃ­nalas.",
        ]
        out = GH_INSTR / f"{cat}.instructions.md"
        out.write_text("\n".join(lines), encoding="utf-8")

    print(f"  {len(cat_skills)} archivos .instructions.md generados en .github/instructions/")

    # â”€â”€ 6. EstadÃ­sticas por categorÃ­a â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\nDistribuciÃ³n por categorÃ­a:")
    for cat in sorted(cat_skills):
        n = len(cat_skills.get(cat, []))
        bar = "â–ˆ" * (n // 10)
        print(f"  {cat:<20} {n:>4}  {bar}")

    total_ok = len(index)
    print(f"\nTotal: {total_ok} skills listos.")
    print(f"  .github/skills/   â†’ {total_ok} carpetas")
    print(f"  skills/<cat>/     â†’ {total_ok} carpetas categorizadas")
    print(f"  .github/instructions/ â†’ {len(cat_skills)} archivos auto-detect")


if __name__ == "__main__":
    main()

