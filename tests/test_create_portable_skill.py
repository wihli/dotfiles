from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = (
    REPO_ROOT
    / "skills"
    / ".local"
    / "share"
    / "skills"
    / "create-portable-skill"
)


class CreatePortableSkillTests(unittest.TestCase):
    def test_skill_defines_a_three_harness_portability_contract(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text()

        self.assertIn("name: create-portable-skill", skill)
        self.assertIn("Claude Code", skill)
        self.assertIn("Codex", skill)
        self.assertIn("OpenCode", skill)
        self.assertIn("~/.local/share/skills", skill)
        self.assertIn("~/.claude/skills", skill)
        self.assertIn("~/.agents/skills", skill)
        self.assertIn("~/.codex/skills", skill)
        self.assertIn("unavailable", skill)
        self.assertIn("Self-audit", skill)

    def test_codex_interface_invokes_the_shared_skill(self) -> None:
        interface = (SKILL_ROOT / "agents" / "openai.yaml").read_text()

        self.assertIn('display_name: "Create Portable Skill"', interface)
        self.assertIn(
            'short_description: "Create skills for Claude, Codex, and OpenCode"',
            interface,
        )
        self.assertIn("$create-portable-skill", interface)

    def test_installer_exposes_the_shared_source_to_all_three_harnesses(self) -> None:
        install_script = (REPO_ROOT / "install.sh").read_text()

        self.assertIn(
            "ensure_link ~/.local/share/skills ~/.claude/skills", install_script
        )
        self.assertIn(
            'ensure_link "$skill_dir" "$HOME/.agents/skills/$skill_name"',
            install_script,
        )
        self.assertIn(
            'ensure_link "$skill_dir" "$HOME/.codex/skills/$skill_name"',
            install_script,
        )

        skill = (SKILL_ROOT / "SKILL.md").read_text()
        self.assertIn(
            "OpenCode discovers `~/.agents/skills` and `~/.claude/skills`", skill
        )


if __name__ == "__main__":
    unittest.main()
