from pathlib import Path
import subprocess
import tempfile
import unittest


AUTH_CHECK = Path(__file__).resolve().parents[1] / "bin/.local/bin/auth-check"


class BuildkiteAuthCheckTests(unittest.TestCase):
    def test_buildkite_status_obeys_quiet_and_strict_without_exposing_auth_output(self):
        # A workstation check must report expired sessions without printing the
        # account data returned by bk or opening an interactive login.
        cases = (
            (0, (), 0, "ok"),
            (0, ("--quiet",), 0, None),
            (1, (), 0, "NEEDS LOGIN"),
            (1, ("--strict",), 1, "NEEDS LOGIN"),
            (1, ("--quiet", "--strict"), 1, "NEEDS LOGIN"),
            (None, ("--strict",), 0, "not installed"),
        )
        for bk_exit, flags, expected_exit, expected_status in cases:
            with self.subTest(bk_exit=bk_exit, flags=flags), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "bash").symlink_to("/bin/bash")
                calls = root / "calls"
                if bk_exit is not None:
                    bk = root / "bk"
                    bk.write_text(
                        '#!/bin/bash\n'
                        'printf "%s\\n" "$*" >> "$BK_CALLS"\n'
                        'printf "private-auth-output\\n"\n'
                        'exit "$BK_EXIT"\n'
                    )
                    bk.chmod(0o755)
                result = subprocess.run(
                    ["/bin/bash", str(AUTH_CHECK), *flags],
                    env={"PATH": tmp, "BK_CALLS": str(calls), "BK_EXIT": str(bk_exit)},
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, expected_exit, result.stdout)
                self.assertNotIn("private-auth-output", result.stdout + result.stderr)
                rows = [line for line in result.stdout.splitlines() if "buildkite" in line]
                if expected_status is None:
                    self.assertEqual(rows, [])
                else:
                    self.assertEqual(len(rows), 1, result.stdout)
                    self.assertIn(expected_status, rows[0])
                if bk_exit is not None:
                    self.assertEqual(calls.read_text(), "auth status\n")
                if bk_exit == 1:
                    self.assertIn("bk auth login --scopes read_only", rows[0])


if __name__ == "__main__":
    unittest.main()
