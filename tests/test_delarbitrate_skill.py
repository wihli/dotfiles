from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills/delarbitrate"


class DelarbitrateSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = (SKILL_ROOT / "SKILL.md").read_text()

    def test_frontmatter_is_portable_and_trigger_is_explicit(self) -> None:
        frontmatter = self.skill.split("---", maxsplit=2)[1]
        keys = [
            line.split(":", maxsplit=1)[0]
            for line in frontmatter.splitlines()
            if line
        ]
        self.assertEqual(["name", "description"], keys)
        self.assertIn("name: delarbitrate", frontmatter)
        self.assertIn("explicitly requests multi-model arbitration", frontmatter)
        self.assertIn("Do not trigger for ordinary reviews", self.skill)

    def test_routes_exact_cli_states_and_continuation(self) -> None:
        for command in (
            "delarbitrate doctor --json",
            "delarbitrate run --task-file <task-file> --workspace <workspace> --json",
            "delarbitrate continue <run-id> --answer-file <answer-file> --json",
            "delarbitrate show <run-id> --json",
        ):
            self.assertIn(command, self.skill)
        for status in ("`complete`", "`needs_human`", "`blocked`"):
            self.assertIn(status, self.skill)
        self.assertIn("Ask only `human_brief.question`", self.skill)

    def test_preserves_request_and_enforces_read_only_child_boundary(self) -> None:
        self.assertIn("User request (verbatim)", self.skill)
        self.assertIn("without editing, summarizing, or correcting it", self.skill)
        self.assertIn("Established context", self.skill)
        self.assertIn("Source paths", self.skill)
        self.assertIn("DELARBITRATE_CHILD", self.skill)
        self.assertIn("refuse to invoke Delarbitrate", self.skill)
        self.assertIn("leave the workspace and external systems unchanged", self.skill)
        self.assertIn("Do not log in", self.skill)
        self.assertIn("add a connector", self.skill)

    def test_documents_claude_and_codex_discovery_paths(self) -> None:
        for path in (
            "~/.local/share/skills/delarbitrate",
            "~/.claude/skills/delarbitrate",
            "~/.agents/skills/delarbitrate",
            "~/.codex/skills/delarbitrate",
        ):
            self.assertIn(path, self.skill)
        self.assertIn("OpenCode", self.skill)
        self.assertIn("Pi", self.skill)


if __name__ == "__main__":
    unittest.main()
