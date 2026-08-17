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


if __name__ == "__main__":
    unittest.main()
