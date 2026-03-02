import tempfile
import unittest
from argparse import Namespace
from contextlib import contextmanager
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import skills_manager as sm


@contextmanager
def isolated_workspace():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        originals = {}
        mappings = {
            "ROOT": root,
            "SKILLS_DIR": root / ".github" / "skills",
            "INDEX_FILE": root / ".github" / "skills" / ".skills_index.json",
            "ACTIVE_FILE": root / ".github" / "skills" / ".active_skills.json",
            "SOURCES_FILE": root / ".github" / "skills" / ".sources.json",
            "LEGACY_SKILLS_DIR": root / "skills",
            "LEGACY_INDEX_FILE": root / "skills" / ".skills_index.json",
            "CLAUDE_MD": root / "CLAUDE.md",
            "COPILOT_AGENT": root / "copilot-agent",
            "GH_SKILLS_DIR": root / ".github" / "skills",
            "GH_INSTR_DIR": root / ".github" / "instructions",
            "COPILOT_INSTR": root / ".github" / "copilot-instructions.md",
            "VERSION_FILE": root / "VERSION",
            "README_MD": root / "README.md",
            "CHANGELOG_MD": root / "CHANGELOG.md",
            "AGENT_FILE": root / ".github" / "agents" / "free-jt7.agent.md",
            "LEGACY_AGENT_FILE": root / ".github" / "agents" / "freejt7.agent.md",
            "POLICY_FILE": root / ".github" / "free-jt7-policy.yaml",
            "LEGACY_POLICY_FILE": root / ".github" / "freejt7-policy.yaml",
            "MODEL_ROUTING_FILE": root / ".github" / "free-jt7-model-routing.json",
            "MODEL_ROUTING_LEGACY_FILE": root / ".github" / "freejt7-model-routing.json",
            "ROLLOUT_FILE": root / "copilot-agent" / "rollout-mode.json",
            "OPENCLAW_REPO_DIR": root / "OPEN CLAW",
        }
        for key, value in mappings.items():
            originals[key] = getattr(sm, key)
            setattr(sm, key, value)
        try:
            sm.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            sm.GH_INSTR_DIR.mkdir(parents=True, exist_ok=True)
            sm.AGENT_FILE.parent.mkdir(parents=True, exist_ok=True)
            yield root
        finally:
            for key, value in originals.items():
                setattr(sm, key, value)


def write_skill(base: Path, skill_id: str, description: str, category: str = "general"):
    target = base / ".github" / "skills" / skill_id / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"""---
name: {skill_id}
description: {description}
metadata:
  category: {category}
  source: local
  risk: safe
---

# {skill_id}
""",
        encoding="utf-8",
    )


class SkillsManagerIntegrationTests(unittest.TestCase):
    def test_activate_deactivate_sync_flow(self):
        with isolated_workspace() as root:
            write_skill(root, "python-pro", "python", "development")
            (root / ".github" / "copilot-instructions.md").write_text("skills", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("skills", encoding="utf-8")
            sm._rebuild_index_from_disk()

            rc = sm.cmd_activate(Namespace(skill_ids=["python-pro"]))
            self.assertEqual(rc, 0)
            self.assertTrue(any(s["active"] for s in sm.load_index()))

            rc = sm.cmd_deactivate(Namespace(skill_ids=["python-pro"]))
            self.assertEqual(rc, 0)
            self.assertFalse(any(s["active"] for s in sm.load_index()))

    def test_install_works_without_active_project(self):
        with isolated_workspace() as root:
            write_skill(root, "docker-expert", "docker", "infrastructure")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")
            target = root / "target-project"
            target.mkdir()

            rc = sm.cmd_install(
                Namespace(
                    path=str(target),
                    force=False,
                    ide="vscode",
                    update_user_settings=False,
                    appdata_root="",
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue((target / ".github" / "copilot-instructions.md").exists())
            self.assertTrue((target / ".github" / "free-jt7-model-routing.json").exists())
            self.assertTrue((target / ".vscode" / "settings.json").exists())

    def test_install_all_ides_writes_workspace_adapters(self):
        with isolated_workspace() as root:
            write_skill(root, "planner-pro", "planning", "general")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")
            target = root / "project-all-ides"
            target.mkdir()

            rc = sm.cmd_install(
                Namespace(
                    path=str(target),
                    force=False,
                    ide="all",
                    update_user_settings=False,
                    appdata_root="",
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue((target / ".vscode" / "settings.json").exists())
            self.assertTrue((target / ".cursor" / "settings.json").exists())
            self.assertTrue((target / ".cursor" / "rules" / "freejt7.mdc").exists())
            self.assertTrue((target / ".kiro" / "settings.json").exists())
            self.assertTrue((target / ".kiro" / "steering" / "freejt7.md").exists())
            self.assertTrue((target / ".antigravity" / "freejt7.runtime.json").exists())
            self.assertTrue((target / ".codex" / "freejt7-agent.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".claude" / "freejt7-agent.md").exists())
            self.assertTrue((target / "CLAUDE.md").exists())
            self.assertTrue((target / ".gemini" / "freejt7-agent.md").exists())
            self.assertTrue((target / "GEMINI.md").exists())
            self.assertTrue((target / ".github" / "free-jt7-model-routing.json").exists())

    def test_install_updates_user_settings_for_selected_ides(self):
        with isolated_workspace() as root:
            write_skill(root, "qa-pro", "tests", "testing")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")
            target = root / "project-user-settings"
            target.mkdir()
            appdata_root = root / "appdata"
            appdata_root.mkdir(parents=True, exist_ok=True)

            original = os.environ.get("FREE_JT7_APPDATA_ROOT")
            os.environ["FREE_JT7_APPDATA_ROOT"] = str(appdata_root)
            try:
                rc = sm.cmd_install(
                    Namespace(
                        path=str(target),
                        force=False,
                        ide="all",
                        update_user_settings=True,
                        appdata_root=str(appdata_root),
                    )
                )
            finally:
                if original is None:
                    os.environ.pop("FREE_JT7_APPDATA_ROOT", None)
                else:
                    os.environ["FREE_JT7_APPDATA_ROOT"] = original

            self.assertEqual(rc, 0)
            self.assertTrue((appdata_root / "Code" / "User" / "settings.json").exists())
            self.assertTrue((appdata_root / "Cursor" / "User" / "settings.json").exists())
            self.assertTrue((appdata_root / "Kiro" / "User" / "settings.json").exists())
            self.assertTrue((appdata_root / "Antigravity" / "User" / "settings.json").exists())
            self.assertTrue((appdata_root / "ClaudeCode" / "config.json").exists())
            self.assertTrue((appdata_root / "GeminiCLI" / "settings.json").exists())
            self.assertTrue((appdata_root / ".codex" / "config.toml").exists())
            self.assertTrue((appdata_root / ".codex" / "freejt7.config.json").exists())

    def test_doctor_detects_missing_files(self):
        with isolated_workspace():
            rc = sm.cmd_doctor(Namespace())
            self.assertEqual(rc, 1)

    def test_gateway_bootstrap_writes_runtime_files(self):
        with isolated_workspace() as root:
            project = root / "gateway-project"
            rc = sm.cmd_gateway_bootstrap(
                Namespace(
                    project=str(project),
                    ide="vscode",
                    profile="default",
                    owner_phone="+34123456789",
                    telegram_bot_token="123:abc",
                    appdata_root="",
                    force=True,
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue((project / ".openclaw" / "openclaw.json").exists())
            self.assertTrue((project / ".openclaw" / "free-jt7-model-resolution.json").exists())
            self.assertTrue((project / ".env.free-jt7.example").exists())
            self.assertTrue((project / "FREEJT7_GATEWAY.md").exists())

    def test_easy_onboard_dry_run_writes_credentials_and_runtime_config(self):
        with isolated_workspace() as root:
            project = root / "easy-onboard-project"
            rc = sm.cmd_easy_onboard(
                Namespace(
                    project=str(project),
                    owner_phone="+34123456789",
                    telegram_bot_token="123456:abc",
                    openai_api_key="sk-demo-openai",
                    anthropic_api_key="",
                    gemini_api_key="",
                    interactive=False,
                    ide="vscode",
                    profile="default",
                    appdata_root="",
                    force=True,
                    openclaw_repo="",
                    dry_run=True,
                    timeout_ms=1000,
                    port=18789,
                    verbose=False,
                    skip_start=False,
                    skip_whatsapp_login=False,
                    strict=True,
                )
            )
            self.assertEqual(rc, 0)

            cred_path = project / ".secrets" / "free-jt7.env"
            self.assertTrue(cred_path.exists())
            cred_text = cred_path.read_text(encoding="utf-8")
            self.assertIn("OWNER_PHONE=+34123456789", cred_text)
            self.assertIn("TELEGRAM_BOT_TOKEN=123456:abc", cred_text)
            self.assertIn("OPENAI_API_KEY=sk-demo-openai", cred_text)

            cfg = sm.load_json(project / ".openclaw" / "openclaw.json", {})
            self.assertEqual(cfg.get("gateway", {}).get("mode"), "local")
            self.assertEqual(cfg.get("channels", {}).get("whatsapp", {}).get("allowFrom"), ["+34123456789"])
            self.assertEqual(cfg.get("channels", {}).get("telegram", {}).get("botToken"), "123456:abc")

    def test_plugin_enable_disable_validate_flow(self):
        with isolated_workspace() as root:
            project = root / "plugin-project"
            plugin_dir = project / "plugins" / "device-pair"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            (plugin_dir / "openclaw.plugin.json").write_text(
                '{"name":"device-pair","version":"1.0.0"}',
                encoding="utf-8",
            )

            rc = sm.cmd_plugin_enable(
                Namespace(
                    project=str(project),
                    plugin_id="device-pair",
                    source="local",
                    path=str(plugin_dir),
                    manifest="",
                    package="",
                )
            )
            self.assertEqual(rc, 0)

            rc = sm.cmd_plugin_validate(
                Namespace(
                    project=str(project),
                    plugin_id="device-pair",
                    json=False,
                )
            )
            self.assertEqual(rc, 0)

            cfg = sm.load_json(project / ".openclaw" / "openclaw.json", {})
            entries = cfg.get("plugins", {}).get("entries", {})
            self.assertTrue(entries.get("device-pair", {}).get("enabled"))

            rc = sm.cmd_plugin_disable(
                Namespace(
                    project=str(project),
                    plugin_id="device-pair",
                )
            )
            self.assertEqual(rc, 0)
            cfg = sm.load_json(project / ".openclaw" / "openclaw.json", {})
            entries = cfg.get("plugins", {}).get("entries", {})
            self.assertFalse(entries.get("device-pair", {}).get("enabled"))

    def test_phase7_smoke_and_resilience_dry_run_emit_reports(self):
        with isolated_workspace() as root:
            project = root / "phase7-project"
            project.mkdir(parents=True, exist_ok=True)
            self.assertEqual(
                sm.cmd_gateway_bootstrap(
                    Namespace(
                        project=str(project),
                        ide="vscode",
                        profile="default",
                        owner_phone="",
                        telegram_bot_token="",
                        appdata_root="",
                        force=True,
                    )
                ),
                0,
            )

            smoke_rc = sm.cmd_phase7_smoke(
                Namespace(
                    project=str(project),
                    openclaw_repo="",
                    timeout_ms=1000,
                    approve_code="DEMO-CODE",
                    ide="vscode",
                    profile="default",
                    appdata_root="",
                    live=False,
                )
            )
            self.assertEqual(smoke_rc, 0)

            resilience_rc = sm.cmd_gateway_resilience(
                Namespace(
                    project=str(project),
                    openclaw_repo="",
                    attempts=3,
                    interval_ms=1,
                    timeout_ms=1000,
                    min_success_ratio=1.0,
                    live=False,
                )
            )
            self.assertEqual(resilience_rc, 0)

            phase7_dir = sm.COPILOT_AGENT / "phase7"
            smoke_reports = list(phase7_dir.glob("smoke-*.json"))
            resilience_reports = list(phase7_dir.glob("resilience-*.json"))
            self.assertTrue(smoke_reports)
            self.assertTrue(resilience_reports)


if __name__ == "__main__":
    unittest.main()

