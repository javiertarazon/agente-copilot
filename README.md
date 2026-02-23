# 🤖 Agente Copilot OpenClaw — 963 Skills

Sistema de skills expertos para GitHub Copilot, basado en [OpenClaw](https://github.com/openclaw) y el catálogo [Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills).

**963 skills** organizados en 9 categorías — disponibles **siempre** en cualquier proyecto VS Code y en github.com.

---

## ✨ ¿Qué incluye?

| Categoría | Skills | Ejemplos |
|-----------|--------|---------|
| `architecture` | 83 | C4, DDD, ADRs, microservices |
| `business` | 130 | SEO, marketing, CRM, pricing |
| `data-ai` | 93 | LLMs, RAG, agentes, MLOps |
| `development` | 186 | Python, TS, React, Go, Rust, Java |
| `general` | 250 | Git, PRs, debug, planning |
| `infrastructure` | 71 | Docker, K8s, Terraform, CI/CD |
| `security` | 38 | Pentesting, OWASP, auth |
| `testing` | 34 | TDD, Playwright, Jest, Pytest |
| `workflow` | 78 | n8n, Jira, Slack, Figma |

---

## 🚀 Instalación rápida — cualquier proyecto

### Opción 1: Script automático (Windows)

```powershell
# Desde la raíz de tu proyecto
iwr https://raw.githubusercontent.com/javiertarazon/agente-copilot/master/setup-project.ps1 | iex
```

### Opción 2: Clone + install

```powershell
# Clonar el agente (una sola vez)
git clone https://github.com/javiertarazon/agente-copilot.git "D:\agente-copilot"
cd "D:\agente-copilot"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt 2>$null

# Instalar en TU proyecto (crea symlinks)
python skills_manager.py install "C:\ruta\a\tu-proyecto"
```

### Opción 3: Workspace multiroot (recomendado para desarrollo)

Abre `open-claw-multiroot.code-workspace` en VS Code. Edita la segunda carpeta para apuntar a tu proyecto activo.

---

## ⚙️ Configuración permanente en VS Code (ya hecha si seguiste el setup)

Añade esto a tu `settings.json` de usuario (`Ctrl+Shift+P` → "Open User Settings JSON"):

```json
{
  "github.copilot.chat.codeGeneration.useInstructionFiles": true,
  "github.copilot.chat.customInstructionsInSystemMessage": true,
  "chat.agent.enabled": true,
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": "D:/agente-copilot/.github/copilot-instructions.md" }
  ],
  "chat.agentFilesLocations": [
    "D:/agente-copilot/.github/agents"
  ]
}
```

> 💡 **Con esta config, TODOS los proyectos VS Code usan automáticamente los 963 skills. No necesitas nada extra por proyecto.**

---

## 🎯 Uso de skills

### Automático (desde Copilot Chat)

Copilot detecta el dominio de tu solicitud y carga el skill correcto:

```
"crea un Dockerfile optimizado para Node.js"  → skill: docker-expert
"diseña una arquitectura de microservicios"    → skill: microservices-patterns
"escribe tests para esta función Python"       → skill: python-testing-patterns
"optimiza esta query SQL"                      → skill: sql-optimization-patterns
```

### Manual — carga un skill específico

```
@copilot Usa el skill react-state-management y ayúdame con Redux Toolkit
```

### Modo agente OpenClaw

En VS Code Copilot Chat, selecciona el agente `openclaw` (aparece en el menú de agentes):

```
@openclaw analiza la arquitectura de este proyecto y sugiere mejoras
```

---

## 🔧 Gestión de skills

```powershell
cd "D:\agente-copilot"
.\.venv\Scripts\Activate.ps1

# Buscar un skill
python skills_manager.py search "docker kubernetes"

# Listar por categoría
python skills_manager.py list --category development

# Ver skills activos
python skills_manager.py list --active

# Activar skills adicionales
python skills_manager.py activate python-pro fastapi-pro

# Instalar EN otro proyecto
python skills_manager.py install "D:\mis-proyectos\mi-app"
```

---

## 📁 Estructura del repositorio

```
agente-copilot/
├── .github/
│   ├── copilot-instructions.md     # ← Instrucciones globales de Copilot
│   ├── agents/
│   │   └── openclaw.agent.md       # ← Definición del agente VS Code
│   ├── skills/                     # ← 963 skills individuales
│   │   └── <nombre>/SKILL.md
│   └── instructions/               # ← Instrucciones por categoría
├── skills/                         # ← Skills organizados por categoría
├── skills_manager.py               # ← CLI de gestión
├── setup-project.ps1               # ← Instalador rápido por proyecto
├── open-claw-multiroot.code-workspace
└── copilot-agent/
    ├── active-project.json         # ← Proyecto activo actual
    └── RESUME.md                   # ← Estado del agente
```

---

## 🌐 GitHub Copilot en github.com

Las instrucciones están en la rama `master` (rama por defecto). Copilot en github.com las carga automáticamente cuando trabajas en cualquier pull request o código del repositorio.

---

## 📊 Versión actual

- **v1.1** — 963 skills, Antigravity v5.7 + OpenClaw behaviors + awesome-copilot
- Última actualización: 2026-07-15

---

*963 skills — MIT License*
