import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills/explain-diff"
STORE = SKILL_ROOT / "scripts/artifact_store.py"


class ExplainDiffSkillTests(unittest.TestCase):
    def test_skill_contract_is_portable_and_local_only(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text()
        frontmatter = skill.split("---", maxsplit=2)[1]
        keys = [
            line.split(":", maxsplit=1)[0]
            for line in frontmatter.splitlines()
            if line
        ]

        self.assertEqual(["name", "description"], keys)
        self.assertIn("name: explain-diff", frontmatter)
        self.assertLessEqual(len(frontmatter.split("description: ", maxsplit=1)[1]), 200)
        for required in (
            "background",
            "intuition before details",
            "literate diff",
            "Observed",
            "Inferred",
            "Unresolved",
            "Markdown",
            "HTML",
            "raw diff",
            "$XDG_DATA_HOME",
            "$XDG_STATE_HOME",
            "scripts/artifact_store.py",
        ):
            self.assertIn(required, skill)

        interface = (SKILL_ROOT / "agents/openai.yaml").read_text()
        self.assertIn('display_name: "Explain Diff"', interface)
        self.assertIn("$explain-diff", interface)

    def test_prepare_reuses_exact_snapshot_and_revisions_changed_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._git_repo(root)
            data_root = root / "data"
            state_root = root / "state"
            snapshot = root / "change.diff"
            snapshot.write_text("diff --git a/app.py b/app.py\n+print('hello')\n")

            first = self._prepare(repo, snapshot, data_root, state_root)
            second = self._prepare(repo, snapshot, data_root, state_root)

            self.assertTrue(first["created"])
            self.assertFalse(first["reused"])
            self.assertFalse(second["created"])
            self.assertTrue(second["reused"])
            self.assertEqual(first["revision_dir"], second["revision_dir"])

            revision_dir = Path(first["revision_dir"])
            self.assertEqual(snapshot.read_bytes(), (revision_dir / "raw.diff").read_bytes())
            self.assertEqual(
                revision_dir.resolve(), (revision_dir.parent.parent / "latest").resolve()
            )
            manifest_text = (revision_dir / "manifest.json").read_text()
            self.assertIn(str(repo.resolve()), manifest_text)
            self.assertEqual(0o600, (revision_dir / "raw.diff").stat().st_mode & 0o777)

            snapshot.write_text("diff --git a/app.py b/app.py\n+print('goodbye')\n")
            changed = self._prepare(repo, snapshot, data_root, state_root)

            self.assertTrue(changed["created"])
            self.assertNotEqual(first["revision_dir"], changed["revision_dir"])
            self.assertEqual(
                Path(changed["revision_dir"]).resolve(),
                (revision_dir.parent.parent / "latest").resolve(),
            )

            index = json.loads((state_root / "explain-diff/index.json").read_text())
            entry = next(iter(index["subjects"].values()))
            self.assertEqual(2, len(entry["revisions"]))
            self.assertEqual(changed["revision_id"], entry["latest_revision"])

    def test_prepare_honors_xdg_defaults_and_rejects_empty_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._git_repo(root)
            snapshot = root / "change.diff"
            snapshot.write_text("one change\n")
            env = os.environ | {
                "XDG_DATA_HOME": str(root / "xdg-data"),
                "XDG_STATE_HOME": str(root / "xdg-state"),
            }

            result = self._run_prepare(repo, snapshot, env=env)
            self.assertEqual(0, result.returncode, result.stderr)
            prepared = json.loads(result.stdout)
            self.assertTrue(
                Path(prepared["revision_dir"]).is_relative_to(root / "xdg-data/explain-diff")
            )
            self.assertTrue((root / "xdg-state/explain-diff/index.json").is_file())

            snapshot.write_bytes(b"")
            failed = self._run_prepare(repo, snapshot, env=env)
            self.assertNotEqual(0, failed.returncode)
            self.assertIn("snapshot file is empty", failed.stderr)
            self.assertIn("provide a non-empty diff", failed.stderr)

    def _git_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def _prepare(
        self, repo: Path, snapshot: Path, data_root: Path, state_root: Path
    ) -> dict:
        result = self._run_prepare(
            repo,
            snapshot,
            "--data-root",
            str(data_root),
            "--state-root",
            str(state_root),
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def _run_prepare(
        self, repo: Path, snapshot: Path, *extra: str, env: dict | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(STORE),
                "prepare",
                "--repo-root",
                str(repo),
                "--subject",
                "pr:42",
                "--snapshot-file",
                str(snapshot),
                "--base",
                "main",
                "--head",
                "feature",
                *extra,
            ],
            capture_output=True,
            env=env,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
