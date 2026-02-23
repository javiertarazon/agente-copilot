#!/usr/bin/env python3
"""Regenera el índice de skills desde .github/skills/*/SKILL.md"""
import json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORY_KEYWORDS = {
    "architecture":   ["architect","c4-","cqrs","event-sourcing","adr","brainstorm","monorepo","nestjs","system-design","design-pattern","microservice","ddd","clean-arch"],
    "business":       ["seo","crm","growth","pricing","marketing","sales","content","copy","hr","competitor","market","startup","defi","contract","conductor","product-manager","pm-","roadmap","okr","go-to-market","copywriting","cro-"],
    "data-ai":        ["llm","rag","agent-","langchain","langgraph","crewai","embedding","hugging","fal-","dbt","feature-eng","hybrid-search","mlops","data-sci","data-eng","data-qual","graphql","analytics","faiss","prompt-eng","ai-agent","ai-engineer","ai-ml","openai","anthropic","gemini","vector-"],
    "development":    ["python","typescript","javascript","golang","rust","java","php","ruby","swift","flutter","django","fastapi","react","vue","nextjs","laravel","shopify","expo","bun","prisma","clickhouse","discord-bot","slack-bot","mobile","ios-dev","android","dotnet","csharp","kotlin","scala","rails","spring","express","nuxt","svelte","astro","remix","tauri","electron","threejs","3d-web","webgl","zustand","redux"],
    "general":        ["git-","github-issue","planning","docs-","code-review","debug","clean-code","commit","create-pr","readme","tutorial","mermaid","prompt-lib","context-","finishing-","writing","address-github","code-quality","linting","formatting"],
    "infrastructure": ["docker","kubernetes","terraform","aws","azure-","devops","helm","cicd","ci-","gitlab-ci","github-action","prometheus","grafana","istio","nginx","serverless","gitops","k8s","ansible","pulumi","cdk-","cloud-","gcp","vercel","railway","fly-","render-"],
    "security":       ["security","pentest","xss","sql-inject","auth-","oauth","gdpr","vulnerab","burp","metasploit","idor","active-directory","threat-model","stride","malware","firmware","incident-resp","pci-","sast","csrf","owasp","jwt-","ssl-","tls-","encryption","crypto-","ssrf","rce-","lfi-"],
    "testing":        ["test","tdd","playwright","cypress","jest","pytest","qa-","ab-test","unit-test","e2e-","bats-","screen-reader","vitest","selenium","load-test","perf-test","benchmark","mock-","fixture-","coverage"],
    "workflow":       ["slack-","jira","notion-","airtable","hubspot","trello","asana","monday","zapier","stripe-","sentry","datadog","linear-","zendesk","github-workflow","confluence","make-","clickup","todoist","figma","automation","n8n","trigger-","inngest","workflow-","orchestr"],
}

def categorize(sid, desc):
    c = (sid + " " + desc).lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in c: return cat
    return "general"

def parse_fm(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m: return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta

index = []
for skill_md in sorted((ROOT / ".github" / "skills").glob("*/SKILL.md")):
    skill_id = skill_md.parent.name
    try:
        raw = skill_md.read_bytes().decode("utf-8", "replace")
        meta = parse_fm(raw)
    except Exception:
        meta = {}
    name = meta.get("name", skill_id)
    desc = meta.get("description", "")
    cat  = categorize(name, desc)
    index.append({
        "id": skill_id, "name": name, "description": desc[:120],
        "category": cat,
        "path":    f"skills/{cat}/{skill_id}/SKILL.md",
        "gh_path": f".github/skills/{skill_id}/SKILL.md",
        "active": False,
        "source": meta.get("source", "antigravity"),
        "risk":   meta.get("risk", "unknown"),
    })

out = ROOT / "skills" / ".skills_index.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Indice regenerado: {len(index)} entries")
cats = Counter(e["category"] for e in index)
for c, n in sorted(cats.items()):
    bar = chr(9608) * (n // 15)
    print(f"  {c:<22} {n:>4}  {bar}")
