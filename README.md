# ðŸ¤– Agente Copilot Free JT7 â€” 962 Skills

Sistema de skills expertos para GitHub Copilot, basado en [Free JT7](https://github.com/free-jt7) y el catÃ¡logo [Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills).

**962 skills** organizados en 9 categorÃ­as â€” disponibles **siempre** en cualquier proyecto VS Code y en github.com.

---

## âœ¨ Â¿QuÃ© incluye?

| CategorÃ­a | Skills | Ejemplos |
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

## ðŸš€ InstalaciÃ³n rÃ¡pida â€” cualquier proyecto

### OpciÃ³n 1: Script automÃ¡tico (Windows)

```powershell
# Desde la raÃ­z de tu proyecto
iwr https://raw.githubusercontent.com/javiertarazon/agente-copilot/master/setup-project.ps1 | iex
```

> **alternativa offline:** si ya tienes este repositorio descargado puedes usar
> el helper local `add-free-jt7-agent.ps1` que hace exactamente lo mismo:
>
```powershell
# en cualquier carpeta, path por defecto es el cwd
.\add-free-jt7-agent.ps1 -Path "C:\ruta\a\tu-proyecto" -Ide cursor -UpdateUserSettings [-Force]
```


### OpciÃ³n 2: Clone + install

```powershell
# Clonar el agente (una sola vez)
git clone https://github.com/javiertarazon/agente-copilot.git "D:\agente-copilot"
cd "D:\agente-copilot"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt 2>$null

# Instalar en TU proyecto (crea symlinks)
python skills_manager.py install "C:\ruta\a\tu-proyecto" --ide auto
# --ide auto instala solo IDEs detectados en tu entorno

# Forzar compatibilidad en todos los IDE soportados
python skills_manager.py install "C:\ruta\a\tu-proyecto" --ide all --update-user-settings

# Detectar perfiles disponibles
python skills_manager.py ide-detect

# Integrar solo Codex en el workspace (AGENTS.md + .codex/)
python skills_manager.py install "C:\ruta\a\tu-proyecto" --ide codex

# Integrar Claude Code y Gemini CLI
python skills_manager.py install "C:\ruta\a\tu-proyecto" --ide claude-code
python skills_manager.py install "C:\ruta\a\tu-proyecto" --ide gemini-cli
```

### OpciÃ³n 3: Workspace multiroot (recomendado para desarrollo)

Abre `free-jt7-multiroot.code-workspace` en VS Code. Edita la segunda carpeta para apuntar a tu proyecto activo.

---

## âš™ï¸ ConfiguraciÃ³n permanente en VS Code (ya hecha si seguiste el setup)

AÃ±ade esto a tu `settings.json` de usuario (`Ctrl+Shift+P` â†’ "Open User Settings JSON"):

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

> ðŸ’¡ **Con esta config, TODOS los proyectos VS Code usan automÃ¡ticamente los 963 skills. No necesitas nada extra por proyecto.**

---

## ðŸŽ¯ Uso de skills

### AutomÃ¡tico (desde Copilot Chat)

Copilot detecta el dominio de tu solicitud y carga el skill correcto:

```
"crea un Dockerfile optimizado para Node.js"  â†’ skill: docker-expert
"diseÃ±a una arquitectura de microservicios"    â†’ skill: microservices-patterns
"escribe tests para esta funciÃ³n Python"       â†’ skill: python-testing-patterns
"optimiza esta query SQL"                      â†’ skill: sql-optimization-patterns
```

### Manual â€” carga un skill especÃ­fico

```
@copilot Usa el skill react-state-management y ayÃºdame con Redux Toolkit
```

### Modo agente Free JT7

En VS Code Copilot Chat, selecciona el agente `free-jt7` (aparece en el menÃº de agentes):

```
@free-jt7 analiza la arquitectura de este proyecto y sugiere mejoras
```

---

## ðŸ”§ GestiÃ³n de skills y agentes

```powershell
cd "D:\agente-copilot"
.\.venv\Scripts\Activate.ps1

# Buscar un skill
python skills_manager.py search "docker kubernetes"

# Listar por categorÃ­a
python skills_manager.py list --category development

# Ver skills activos
python skills_manager.py list --active

# Activar skills adicionales
python skills_manager.py activate python-pro fastapi-pro

# Generar una skill nueva desde plantilla
python skills_manager.py add --name "mi-skill" --description "DescripciÃ³n breve"

# Crear un agente personalizado
python skills_manager.py add-agent --name "Mi Agente" --description "Ayuda con CI/CD" --model claude-2 --tools codebase terminal

# Instalar EN otro proyecto
python skills_manager.py install "D:\mis-proyectos\mi-app"
```

> ðŸ›  **Nota:** los comandos `add` y `add-agent` generan los archivos necesarios automÃ¡ticamente; edÃ­talos despuÃ©s para completar la documentaciÃ³n y las reglas del skill/agent.

---

## ðŸ§­ Operating Model (AutonomÃ­a)

El agente soporta un runtime operacional con policy y runs trazables:

```powershell
# Validar policy operativa
python skills_manager.py policy-validate

# Ver/cambiar modo rollout
python skills_manager.py rollout-mode
python skills_manager.py rollout-mode shadow
python skills_manager.py rollout-mode assist
python skills_manager.py rollout-mode autonomous

# Resolver skills efÃ­meras para una tarea
python skills_manager.py skill-resolve --query "docker kubernetes" --top 3

# Orquestar run completo
python skills_manager.py task-run --goal "auditar CI" --commands "ls" "python skills_manager.py doctor"

# Modo granular
python skills_manager.py task-start --goal "revisar seguridad"
python skills_manager.py task-step --run-id <id> --command "Get-ChildItem"
python skills_manager.py task-close --run-id <id> --summary "verificaciÃ³n completada"
```

Artefactos generados:
- `copilot-agent/runs/<run_id>.json`
- `copilot-agent/runs/<run_id>.events.jsonl`
- Policy: `.github/free-jt7-policy.yaml`

---

## ðŸ“ Estructura del repositorio

```
agente-copilot/
â”œâ”€â”€ .github/
â”‚   â”œâ”€â”€ copilot-instructions.md     # â† Instrucciones globales de Copilot
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â””â”€â”€ free-jt7.agent.md       # â† DefiniciÃ³n del agente VS Code
â”‚   â”œâ”€â”€ skills/                     # â† 963 skills individuales
â”‚   â”‚   â””â”€â”€ <nombre>/SKILL.md
â”‚   â””â”€â”€ instructions/               # â† Instrucciones por categorÃ­a
â”œâ”€â”€ skills/                         # â† Skills organizados por categorÃ­a
â”œâ”€â”€ skills_manager.py               # â† CLI de gestiÃ³n
â”œâ”€â”€ setup-project.ps1               # â† Instalador rÃ¡pido por proyecto
â”œâ”€â”€ free-jt7-multiroot.code-workspace
â””â”€â”€ copilot-agent/
    â”œâ”€â”€ active-project.json         # â† Proyecto activo actual
    â””â”€â”€ RESUME.md                   # â† Estado del agente
```

---

## ðŸŒ GitHub Copilot en github.com

Las instrucciones estÃ¡n en la rama `master` (rama por defecto). Copilot en github.com las carga automÃ¡ticamente cuando trabajas en cualquier pull request o cÃ³digo del repositorio.

---

## ðŸ“Š VersiÃ³n actual

- **v3.0** - Agente Free JT7 multi-ides + runtime operativo + 962 skills
- Ultima actualizacion: 26 de febrero de 2026

> ðŸš€ **Nota:** se subirÃ¡ una etiqueta/tags `v3.0` al repositorio remoto para esta versiÃ³n.

---

*962 skills â€” MIT License*



