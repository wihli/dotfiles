from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills"


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


if __name__ == "__main__":
    unittest.main()
