import tempfile
import unittest
from argparse import Namespace
from contextlib import contextmanager
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
            "AGENT_FILE": root / ".github" / "agents" / "openclaw.agent.md",
            "POLICY_FILE": root / ".github" / "openclaw-policy.yaml",
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
            (root / ".github" / "agents" / "openclaw.agent.md").write_text("skills", encoding="utf-8")
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
            (root / ".github" / "agents" / "openclaw.agent.md").write_text("ok", encoding="utf-8")
            target = root / "target-project"
            target.mkdir()

            rc = sm.cmd_install(Namespace(path=str(target), force=False))
            self.assertEqual(rc, 0)
            self.assertTrue((target / ".github" / "copilot-instructions.md").exists())

    def test_doctor_detects_missing_files(self):
        with isolated_workspace():
            rc = sm.cmd_doctor(Namespace())
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
