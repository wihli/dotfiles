from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills"
SUBAGENT_ROOT = REPO_ROOT / "subagents/.local/share/subagents"


class SkillCatalogTests(unittest.TestCase):
    def test_retired_workflow_skills_are_not_advertised(self) -> None:
        for name in ("investigate-readonly", "log-analyze", "multi-mind", "research"):
            with self.subTest(name=name):
                self.assertFalse((SKILL_ROOT / name / "SKILL.md").exists())

    def test_logalyzer_owns_the_xdg_project_log_workflow(self) -> None:
        skill = (SKILL_ROOT / "logalyzer/SKILL.md").read_text()
        reference = (SKILL_ROOT / "logalyzer/references/xdg-project-logs.md").read_text()

        self.assertIn("references/xdg-project-logs.md", skill)
        self.assertIn("XDG_STATE_HOME", reference)
        self.assertNotIn("~/.claude", reference)

    def test_review_agent_uses_non_skill_checklist_reference(self) -> None:
        reviewer = (
            REPO_ROOT / "subagents/.local/share/subagents/code-reviewer.md"
        ).read_text()

        self.assertIn(
            "~/.local/share/agent-references/review-checklists.md", reviewer
        )
        self.assertNotIn("skills/review-checklists/SKILL.md", reviewer)

    def test_north_star_does_not_reference_retired_research_skill(self) -> None:
        north_star = (SKILL_ROOT / "north-star/SKILL.md").read_text()

        self.assertNotIn("/research", north_star)
        self.assertNotIn("Task agents", north_star)

    def test_delegate_skill_carries_the_cross_harness_spawn_contract(self) -> None:
        # Codex reads no agent definition files and will not delegate unless a skill asks
        # it to, so this skill is the only thing that makes the saved roles reachable there.
        skill = (SKILL_ROOT / "delegate/SKILL.md").read_text()

        self.assertIn("~/.local/share/subagents/", skill)
        # A full-history fork refuses model overrides and hands the child context the role
        # definitions do not expect.
        self.assertIn('fork_turns="none"', skill)
        # The roster must not be hardcoded here; it drifts every time an agent is added.
        for agent in ("code-reviewer", "logalyzer", "pr-reviewer"):
            with self.subTest(agent=agent):
                self.assertNotIn(agent, skill)


    # Codex renders the whole skill catalog into a 2 percent slice of the model
    # window -- about 5,440 tokens at 272k -- and silently shortens descriptions
    # once the catalog exceeds it. Enabled Codex plugins already claim ~6,700
    # chars of that slice, so a personal skill gets one line of what it does plus
    # one line of when to use it. Long trigger-phrase lists blow the budget and
    # cost every other skill its description.
    MAX_FRONTMATTER_CHARS = 320
    MAX_CATALOG_CHARS = 3000

    def _frontmatter(self, path: Path) -> str:
        parts = path.read_text().split("---\n")
        self.assertGreaterEqual(len(parts), 3, f"{path} is missing frontmatter")
        return parts[1]

    def test_skill_description_plain_scalars_are_yaml_safe(self) -> None:
        for path in sorted(SKILL_ROOT.glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                line = next(
                    (
                        line
                        for line in self._frontmatter(path).splitlines()
                        if line.startswith("description: ")
                    ),
                    None,
                )
                self.assertIsNotNone(line, f"{path} has no description")
                value = line.removeprefix("description: ")
                if value.startswith(("'", '"', "|", ">")):
                    continue
                self.assertNotIn(
                    ": ", value, f"{path} must quote a description containing ': '"
                )

    def test_no_skill_description_exceeds_the_per_skill_budget(self) -> None:
        for path in sorted(SKILL_ROOT.glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                self.assertLessEqual(
                    len(self._frontmatter(path)), self.MAX_FRONTMATTER_CHARS
                )

    def test_catalog_frontmatter_stays_within_the_codex_budget(self) -> None:
        total = sum(
            len(self._frontmatter(path))
            for path in sorted(SKILL_ROOT.glob("*/SKILL.md"))
        )
        self.assertLessEqual(total, self.MAX_CATALOG_CHARS)


    # Every subagent's name and description sits in the main session's context on every
    # Claude launch, whether or not an agent is dispatched. Long trigger examples are the
    # usual cause of bloat: three worked examples cost more than the routing signal they
    # add. Keep one example only where two agents compete for the same prompt, and keep
    # operational detail (allow lists, tool inventories, output paths) in the body, where
    # it loads on dispatch instead of on launch. A `tools:` list is functional config, so
    # the per-agent cap covers the description prose and the repo cap covers everything.
    MAX_AGENT_DESCRIPTION_CHARS = 520
    MAX_AGENT_FRONTMATTER_TOTAL = 2900

    def _agent_frontmatter(self, path: Path) -> str:
        parts = path.read_text().split("---\n")
        self.assertGreaterEqual(len(parts), 3, f"{path} is missing frontmatter")
        return parts[1]

    def _agent_description(self, path: Path) -> str:
        lines = self._agent_frontmatter(path).split("\n")
        start = next(
            (i for i, line in enumerate(lines) if line.startswith("description:")), None
        )
        self.assertIsNotNone(start, f"{path} has no description")
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if lines[i] and not lines[i][0].isspace()
            ),
            len(lines),
        )
        return "\n".join(lines[start:end])

    def test_no_subagent_description_exceeds_the_per_agent_budget(self) -> None:
        for path in sorted(SUBAGENT_ROOT.glob("*.md")):
            with self.subTest(agent=path.stem):
                self.assertLessEqual(
                    len(self._agent_description(path)),
                    self.MAX_AGENT_DESCRIPTION_CHARS,
                )

    def test_subagent_frontmatter_total_stays_bounded(self) -> None:
        total = sum(
            len(self._agent_frontmatter(path))
            for path in sorted(SUBAGENT_ROOT.glob("*.md"))
        )
        self.assertLessEqual(total, self.MAX_AGENT_FRONTMATTER_TOTAL)


if __name__ == "__main__":
    unittest.main()
