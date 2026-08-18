#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin/.local/bin/crumb"


class CrumbTest(unittest.TestCase):
    def run_crumb(
        self, *args: str, state_home: Path, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["XDG_STATE_HOME"] = str(state_home)
        return subprocess.run(
            ["gforth", str(SCRIPT), *args],
            cwd=cwd or REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_records_message_with_timestamp_and_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            working_dir = root / "project"
            working_dir.mkdir()

            result = self.run_crumb(
                "paused", "after", "the", "timeout",
                state_home=root,
                cwd=working_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "Recorded: paused after the timeout\n")
            lines = (root / "crumb/history.tsv").read_text().splitlines()
            self.assertEqual(len(lines), 1)
            timestamp, cwd, message = lines[0].split("\t")
            self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
            self.assertEqual(Path(cwd).resolve(), working_dir.resolve())
            self.assertEqual(message, "paused after the timeout")

    def test_no_arguments_lists_existing_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_dir = root / "crumb"
            state_dir.mkdir()
            history = state_dir / "history.tsv"
            history.write_text(
                "2026-08-18T09:30:00\t/tmp/first\tfirst note\n"
                "2026-08-18T10:45:00\t/tmp/second\tsecond note\n"
            )

            result = self.run_crumb(state_home=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, history.read_text())

    def test_new_records_are_appended_to_existing_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            first = self.run_crumb("first", state_home=root)
            second = self.run_crumb("second", state_home=root)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            messages = [
                line.split("\t", 2)[2]
                for line in (root / "crumb/history.tsv").read_text().splitlines()
            ]
            self.assertEqual(messages, ["first", "second"])

    def test_no_arguments_with_no_history_is_successful(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_crumb(state_home=Path(temp_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "No breadcrumbs yet.\n")

    def test_rejects_a_message_that_would_corrupt_the_tsv_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            result = self.run_crumb("two\tfields", state_home=root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("use fewer than 2048 bytes of single-line text", result.stderr)
            self.assertFalse((root / "crumb/history.tsv").exists())

    def test_rejects_a_message_too_large_for_a_history_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            result = self.run_crumb("x" * 2048, state_home=root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("use fewer than 2048 bytes", result.stderr)
            self.assertFalse((root / "crumb/history.tsv").exists())


if __name__ == "__main__":
    unittest.main()
