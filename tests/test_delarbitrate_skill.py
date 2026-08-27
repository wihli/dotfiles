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
        self.assertIn(
            "Use `delarbitrate-auth` when it is available", self.skill
        )
        for command in (
            "<delarbitrate-command> doctor --json",
            "<delarbitrate-command> run --task-file <task-file> --workspace <workspace> [--source <source-path>]... --json",
            "<delarbitrate-command> continue <run-id> --answer-file <answer-file> --json",
            "<delarbitrate-command> show <run-id> --json",
        ):
            self.assertIn(command, self.skill)
        for status in ("`complete`", "`needs_human`", "`blocked`"):
            self.assertIn(status, self.skill)
        self.assertIn("Ask only `human_brief.question`", self.skill)
        self.assertIn("authority_kind", self.skill)
        self.assertIn("answer-only", self.skill)
        self.assertIn("do not call `continue`", self.skill)

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

    def test_explicit_invocation_is_consent_and_children_can_investigate(self) -> None:
        self.assertIn("authorizes Codex and Claude", self.skill)
        self.assertIn("normal read-only agents, skills, and tools", self.skill)
        self.assertIn("owning read-only skill", self.skill)
        self.assertIn("starting context", self.skill)
        self.assertIn("bounded findings and locators", self.skill)
        self.assertIn("Never copy a secret", self.skill)
        self.assertNotIn("data-export approval", self.skill)

    def test_uses_live_sources_and_does_not_create_worktrees(self) -> None:
        self.assertIn("one `--source <absolute-path>`", self.skill)
        self.assertIn("- `/absolute/path`", self.skill)
        self.assertIn("Do not create a worktree", self.skill)
        self.assertIn("live workspace", self.skill)
        self.assertNotIn("immutable source bundle", self.skill)

    def test_relays_only_observed_progress_and_routes_new_evidence_to_a_fresh_run(self) -> None:
        self.assertIn("JSONL progress events from stderr", self.skill)
        self.assertIn("Do not infer progress from silence", self.skill)
        self.assertIn("Do not expose provider prompts", self.skill)
        self.assertIn("blocked_reason` is `insufficient_evidence", self.skill)
        self.assertIn("start a fresh `run`", self.skill)
        self.assertIn("Do not spend a second paid run", self.skill)

    def test_retries_ambiguous_keychain_failure_outside_sandbox(self) -> None:
        self.assertIn("restricted command sandbox", self.skill)
        self.assertIn("retry the exact doctor command once", self.skill)
        self.assertIn("approval mechanism", self.skill)
        self.assertIn("Do not create a setup command or recovery script", self.skill)
        self.assertIn("Only recommend `delarbitrate-auth setup`", self.skill)

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
