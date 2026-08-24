from pathlib import Path
import re
import tomllib
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "delarbitrate/.config/delarbitrate/config.toml"


class DelarbitrateConfigTests(unittest.TestCase):
    def test_candidate_models_reduce_cost_without_changing_judges(self) -> None:
        config = tomllib.loads(CONFIG.read_text())

        self.assertEqual("gpt-5.6-terra", config["codex_candidate_model"])
        self.assertEqual("max", config["codex_candidate_effort"])
        self.assertEqual("claude-sonnet-5", config["claude_candidate_model"])
        self.assertEqual("high", config["claude_candidate_effort"])
        self.assertEqual("gpt-5.6-sol", config["codex_judge_model"])
        self.assertEqual("max", config["codex_judge_effort"])
        self.assertEqual("opus", config["claude_tiebreak_model"])
        self.assertEqual("max", config["claude_tiebreak_effort"])

    def test_installer_stows_delarbitrate_configuration(self) -> None:
        install_script = (REPO_ROOT / "install.sh").read_text()

        self.assertRegex(
            install_script,
            re.compile(r"for pkg in [^\n]*\bdelarbitrate\b[^\n]*; do"),
        )


if __name__ == "__main__":
    unittest.main()
