import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills/deliberate-review"
SCRIPT = SKILL_ROOT / "scripts/deliberate_review.py"


class DeliberateReviewSkillTests(unittest.TestCase):
    def run_skill(self, script: Path, *args: str, env: dict[str, str] | None = None):
        result = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def write_executable(self, path: Path, source: str) -> None:
        path.write_text(source)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_portable_contract_has_a_source_owned_validator(self) -> None:
        self.assertTrue((SKILL_ROOT / "SKILL.md").is_file())
        self.assertTrue(SCRIPT.is_file())

        skill = (SKILL_ROOT / "SKILL.md").read_text()
        frontmatter = skill.split("---", maxsplit=2)[1]
        keys = [
            line.split(":", maxsplit=1)[0]
            for line in frontmatter.splitlines()
            if line
        ]
        self.assertEqual(["name", "description"], keys)
        self.assertIn("name: deliberate-review", frontmatter)
        for required in (
            "Claude Code",
            "Codex",
            "OpenCode",
            "review",
            "status",
            "findings",
            "pause",
            "cancel",
            "resume",
            "guidance",
            "scripts/deliberate_review.py",
        ):
            self.assertIn(required, skill)

        validated = self.run_skill(SCRIPT, "validate")
        self.assertEqual("deliberate-review-validator-v1", validated["schema"])
        self.assertTrue(validated["valid"])

    def test_shared_skill_uses_fake_operations_from_both_discovery_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            run_dir = state_dir / "runs/review-42"
            (run_dir / "source").mkdir(parents=True)
            (run_dir / "source/github-pr.json").write_text(
                json.dumps({"repository": "VantaInc/example", "pull_request": 42})
            )
            workspace = root / "workspace"
            workspace.mkdir()
            git_bin = root / "fake-git"
            deliberate_bin = root / "fake-deliberate"
            call_log = root / "calls.jsonl"
            self.write_executable(
                git_bin,
                "#!/usr/bin/env python3\n"
                "import os\n"
                "print(os.environ['FAKE_GIT_REMOTES'])\n",
            )
            self.write_executable(
                deliberate_bin,
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['FAKE_CALL_LOG'], 'a') as handle:\n"
                "    handle.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if sys.argv[1] in {'review', 'status', 'message'}:\n"
                "    print(json.dumps({'status': 'ok', 'reply': 'fake provider result'}))\n"
                "else:\n"
                "    print('fake control recorded')\n",
            )
            environment = {
                **os.environ,
                "FAKE_GIT_REMOTES": "git@github.com:VantaInc/example.git",
                "FAKE_CALL_LOG": str(call_log),
            }

            actions = [
                ("review", ["--pr", "42", "--cwd", str(workspace)]),
                ("status", ["--repo", "VantaInc/example", "--pr", "42"]),
                (
                    "findings",
                    [
                        "--repo",
                        "VantaInc/example",
                        "--pr",
                        "42",
                        "--message",
                        "What did it find?",
                    ],
                ),
                ("pause", ["--repo", "VantaInc/example", "--pr", "42"]),
                ("cancel", ["--repo", "VantaInc/example", "--pr", "42"]),
                ("resume", ["--repo", "VantaInc/example", "--pr", "42"]),
                (
                    "guidance",
                    [
                        "--repo",
                        "VantaInc/example",
                        "--pr",
                        "42",
                        "--message",
                        "Focus on authorization.",
                    ],
                ),
            ]
            for discovery in (".claude/skills", ".agents/skills"):
                installed = root / discovery / "deliberate-review"
                installed.parent.mkdir(parents=True, exist_ok=True)
                installed.symlink_to(SKILL_ROOT, target_is_directory=True)
                for action, action_args in actions:
                    output = self.run_skill(
                        installed / "scripts/deliberate_review.py",
                        "execute",
                        action,
                        "--state-dir",
                        str(state_dir),
                        "--git-bin",
                        str(git_bin),
                        "--deliberate-bin",
                        str(deliberate_bin),
                        *action_args,
                        env=environment,
                    )
                    self.assertEqual("deliberate-review-operation-v1", output["schema"])
                    self.assertEqual(action, output["operation"])
                    self.assertEqual(0, output["result"]["exit_code"])

            calls = [json.loads(line) for line in call_log.read_text().splitlines()]
            self.assertEqual(14, len(calls))
            self.assertEqual(calls[:7], calls[7:])
            self.assertEqual("review", calls[0][0])
            self.assertIn("--detach", calls[0])
            self.assertIn("--json", calls[0])
            self.assertEqual(["status", "--state-dir", str(state_dir), "--json", "review-42"], calls[1])
            self.assertEqual("message", calls[2][0])
            self.assertIn("--json", calls[2])
            self.assertEqual("pause", calls[3][0])
            self.assertEqual("cancel", calls[4][0])
            self.assertEqual("unpause", calls[5][0])
            self.assertEqual("steer", calls[6][0])

    def test_bare_number_requires_one_current_github_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git_bin = root / "fake-git"
            self.write_executable(
                git_bin,
                "#!/usr/bin/env python3\n"
                "import os\n"
                "print(os.environ.get('FAKE_GIT_REMOTES', ''))\n",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "plan",
                    "review",
                    "--pr",
                    "42",
                    "--cwd",
                    str(root),
                    "--git-bin",
                    str(git_bin),
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "FAKE_GIT_REMOTES": "git@github.com:one/repo.git\ngit@github.com:two/repo.git"},
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("provide --repo owner/repo or a GitHub pull-request URL", result.stderr)

    def test_pull_request_url_plans_without_current_repository_context(self) -> None:
        planned = self.run_skill(
            SCRIPT,
            "plan",
            "review",
            "--url",
            "https://github.com/VantaInc/example/pull/42",
        )
        self.assertEqual(
            {"repository": "VantaInc/example", "pull_request": 42},
            planned["identity"],
        )
        self.assertIn("--detach", planned["command"])
        self.assertIn("--json", planned["command"])

    def test_draft_follow_up_asks_for_input_instead_of_calling_canonical_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "state"
            draft = state_dir / "drafts/review-42"
            draft.mkdir(parents=True)
            (draft / "draft.json").write_text(
                json.dumps(
                    {
                        "initial_request": {
                            "repository": "VantaInc/example",
                            "pull_request": 42,
                            "goal": None,
                        }
                    }
                )
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "plan",
                    "status",
                    "--state-dir",
                    str(state_dir),
                    "--repo",
                    "VantaInc/example",
                    "--pr",
                    "42",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("awaits input", result.stderr)

    def test_validator_needs_no_home_and_missing_cli_is_actionable(self) -> None:
        without_home = {
            key: value
            for key, value in os.environ.items()
            if key not in {"HOME", "XDG_STATE_HOME"}
        }
        validated = subprocess.run(
            [sys.executable, str(SCRIPT), "validate"],
            capture_output=True,
            text=True,
            env=without_home,
        )
        self.assertEqual(0, validated.returncode, validated.stderr)

        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "execute",
                    "review",
                    "--url",
                    "https://github.com/VantaInc/example/pull/42",
                    "--state-dir",
                    str(Path(temporary) / "state"),
                    "--deliberate-bin",
                    str(Path(temporary) / "missing-deliberate"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn("failed to run Deliberate", result.stderr)

    def test_explicit_run_is_an_id_not_a_filesystem_path(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "plan",
                "status",
                "--run",
                "../outside-state",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("run ID", result.stderr)


if __name__ == "__main__":
    unittest.main()
