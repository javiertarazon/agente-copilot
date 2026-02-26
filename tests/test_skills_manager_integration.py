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
            "AGENT_FILE": root / ".github" / "agents" / "freejt7.agent.md",
            "POLICY_FILE": root / ".github" / "freejt7-policy.yaml",
            "ROLLOUT_FILE": root / "copilot-agent" / "rollout-mode.json",
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
            (root / ".github" / "agents" / "freejt7.agent.md").write_text("skills", encoding="utf-8")
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
            (root / ".github" / "agents" / "freejt7.agent.md").write_text("ok", encoding="utf-8")
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
            self.assertTrue((target / ".vscode" / "settings.json").exists())

    def test_install_all_ides_writes_workspace_adapters(self):
        with isolated_workspace() as root:
            write_skill(root, "planner-pro", "planning", "general")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "freejt7.agent.md").write_text("ok", encoding="utf-8")
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

    def test_install_updates_user_settings_for_selected_ides(self):
        with isolated_workspace() as root:
            write_skill(root, "qa-pro", "tests", "testing")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "freejt7.agent.md").write_text("ok", encoding="utf-8")
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
            self.assertFalse((appdata_root / ".codex" / "config.toml").exists())

    def test_doctor_detects_missing_files(self):
        with isolated_workspace():
            rc = sm.cmd_doctor(Namespace())
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

