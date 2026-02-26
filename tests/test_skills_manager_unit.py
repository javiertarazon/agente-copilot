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
            (sm.SKILLS_DIR).mkdir(parents=True, exist_ok=True)
            (sm.GH_INSTR_DIR).mkdir(parents=True, exist_ok=True)
            (sm.AGENT_FILE.parent).mkdir(parents=True, exist_ok=True)
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


class SkillsManagerUnitTests(unittest.TestCase):
    def test_parse_frontmatter(self):
        meta, body = sm.parse_frontmatter(
            "---\nname: demo\nmetadata:\n  category: development\n---\nhello\n"
        )
        self.assertEqual(meta["name"], "demo")
        self.assertEqual(meta["metadata"]["category"], "development")
        self.assertEqual(body.strip(), "hello")

    def test_auto_categorize(self):
        cat = sm.auto_categorize("python-fastapi-pro", "API backend")
        self.assertIn(cat, {"development", "general"})

    def test_rebuild_from_disk_writes_main_and_legacy_index(self):
        with isolated_workspace() as root:
            write_skill(root, "demo-skill", "skill de prueba", "development")
            skills = sm._rebuild_index_from_disk()
            self.assertEqual(len(skills), 1)
            self.assertTrue(sm.INDEX_FILE.exists())
            self.assertTrue(sm.LEGACY_INDEX_FILE.exists())

    def test_add_persists_index(self):
        with isolated_workspace() as root:
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "freejt7.agent.md").write_text("ok", encoding="utf-8")
            args = Namespace(
                name="new-skill",
                description="desc",
                category="development",
                file=None,
                from_repo=None,
            )
            rc = sm.cmd_add(args)
            self.assertEqual(rc, 0)
            index = sm.load_index()
            self.assertTrue(any(s["id"] == "new-skill" for s in index))

    def test_set_project_works(self):
        with isolated_workspace() as root:
            target = root / "my-project"
            target.mkdir()
            rc = sm.cmd_set_project(Namespace(path=str(target), description="demo"))
            self.assertEqual(rc, 0)
            active = sm.load_json(sm.COPILOT_AGENT / "active-project.json", {})
            self.assertEqual(active.get("name"), "my-project")

    def test_resolve_ide_targets_auto_uses_detected_profiles(self):
        with isolated_workspace() as root:
            appdata = root / "appdata"
            (appdata / "Cursor" / "User").mkdir(parents=True, exist_ok=True)
            (appdata / "Cursor" / "User" / "settings.json").write_text("{}", encoding="utf-8")

            original = os.environ.get("FREE_JT7_APPDATA_ROOT")
            os.environ["FREE_JT7_APPDATA_ROOT"] = str(appdata)
            try:
                targets = sm._resolve_ide_targets("auto", appdata)
            finally:
                if original is None:
                    os.environ.pop("FREE_JT7_APPDATA_ROOT", None)
                else:
                    os.environ["FREE_JT7_APPDATA_ROOT"] = original

            self.assertIn("cursor", targets)

    def test_appdata_root_supports_macos_and_linux_defaults(self):
        original_pf = sm._platform_family
        original_override = os.environ.get("FREE_JT7_APPDATA_ROOT")
        try:
            os.environ.pop("FREE_JT7_APPDATA_ROOT", None)
            sm._platform_family = lambda: "darwin"
            mac_root = sm._appdata_root()
            self.assertIn("Library", str(mac_root))
            self.assertIn("Application Support", str(mac_root))

            sm._platform_family = lambda: "linux"
            linux_root = sm._appdata_root()
            self.assertTrue(str(linux_root).endswith(".config"))
        finally:
            sm._platform_family = original_pf
            if original_override is None:
                os.environ.pop("FREE_JT7_APPDATA_ROOT", None)
            else:
                os.environ["FREE_JT7_APPDATA_ROOT"] = original_override

    def test_ide_settings_path_for_claude_and_gemini_with_override_root(self):
        with isolated_workspace() as root:
            appdata = root / "appdata"
            appdata.mkdir(parents=True, exist_ok=True)
            claude = sm._ide_settings_path("claude-code", appdata)
            gemini = sm._ide_settings_path("gemini-cli", appdata)
            self.assertTrue(str(claude).endswith("ClaudeCode\\config.json") or str(claude).endswith("ClaudeCode/config.json"))
            self.assertTrue(str(gemini).endswith("GeminiCLI\\settings.json") or str(gemini).endswith("GeminiCLI/settings.json"))


if __name__ == "__main__":
    unittest.main()

