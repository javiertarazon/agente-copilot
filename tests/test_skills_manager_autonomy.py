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


class SkillsManagerAutonomyTests(unittest.TestCase):
    def test_policy_validate_and_rollout_mode(self):
        with isolated_workspace():
            rc = sm.cmd_policy_validate(Namespace())
            self.assertEqual(rc, 0)
            rc = sm.cmd_rollout_mode(Namespace(mode="shadow"))
            self.assertEqual(rc, 0)
            self.assertTrue(sm.ROLLOUT_FILE.exists())

    def test_skill_resolve_finds_candidates(self):
        with isolated_workspace() as root:
            write_skill(root, "docker-expert", "docker", "infrastructure")
            sm._rebuild_index_from_disk()
            rc = sm.cmd_skill_resolve(Namespace(query="docker", top=3, json=False))
            self.assertEqual(rc, 0)

    def test_task_run_shadow_succeeds_and_persists_run(self):
        with isolated_workspace() as root:
            write_skill(root, "python-pro", "python", "development")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "openclaw.agent.md").write_text("ok", encoding="utf-8")

            sm.cmd_rollout_mode(Namespace(mode="shadow"))
            rc = sm.cmd_task_run(
                Namespace(
                    goal="listar archivos del proyecto",
                    scope="workspace",
                    run_id="run-shadow-1",
                    commands=["ls"],
                    approve_high_risk=False,
                    allow_destructive=False,
                    summary="ok",
                )
            )
            self.assertEqual(rc, 0)
            run_file = sm.COPILOT_AGENT / "runs" / "run-shadow-1.json"
            self.assertTrue(run_file.exists())
            run_data = sm.load_json(run_file, {})
            self.assertEqual(run_data.get("status"), "succeeded")


if __name__ == "__main__":
    unittest.main()
