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
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")

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

    def test_task_step_blocks_when_allowlist_enabled_and_bin_missing(self):
        with isolated_workspace() as root:
            write_skill(root, "ops-pro", "ops", "infrastructure")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")
            run_id = "allowlist-block-1"
            rc = sm.cmd_task_start(Namespace(goal="probar allowlist", scope="workspace", run_id=run_id, ide="auto", profile="default", appdata_root=""))
            self.assertEqual(rc, 0)
            self.assertEqual(sm.cmd_exec_allowlist(Namespace(action="add", bins=["get-childitem"])), 0)
            self.assertEqual(sm.cmd_exec_allowlist(Namespace(action="enable", bins=[])), 0)
            blocked = sm.cmd_task_step(
                Namespace(
                    run_id=run_id,
                    command="foobarbazcmd --version",
                    approve_high_risk=False,
                    allow_destructive=False,
                )
            )
            self.assertEqual(blocked, 1)
            run_data = sm.load_json(sm.COPILOT_AGENT / "runs" / f"{run_id}.json", {})
            self.assertEqual(run_data.get("status"), "blocked")

    def test_task_list_and_checklist_and_registry(self):
        with isolated_workspace() as root:
            write_skill(root, "infra-ops", "ops", "infrastructure")
            sm._rebuild_index_from_disk()
            (root / ".github" / "copilot-instructions.md").write_text("ok", encoding="utf-8")
            (root / ".github" / "agents" / "free-jt7.agent.md").write_text("ok", encoding="utf-8")
            sm.cmd_rollout_mode(Namespace(mode="shadow"))

            run_id = "run-checklist-1"
            rc = sm.cmd_task_run(
                Namespace(
                    goal="validar checklist",
                    scope="workspace",
                    run_id=run_id,
                    commands=["ls"],
                    approve_high_risk=False,
                    allow_destructive=False,
                    summary="ok",
                    ide="auto",
                    profile="default",
                    appdata_root="",
                )
            )
            self.assertEqual(rc, 0)
            self.assertEqual(sm.cmd_task_list(Namespace(status="", limit=10, json=False)), 0)
            self.assertEqual(sm.cmd_task_checklist(Namespace(run_id=run_id, json=False)), 0)
            tasks_yaml = sm.COPILOT_AGENT / "tasks.yaml"
            self.assertTrue(tasks_yaml.exists())
            content = tasks_yaml.read_text(encoding="utf-8")
            self.assertIn(run_id, content)
            self.assertIn("estado: \"completado\"", content)


if __name__ == "__main__":
    unittest.main()

