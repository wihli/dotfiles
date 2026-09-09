import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/.local/share/skills/thabto"
DRIVER = SKILL / "scripts/thabto.py"
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time
args = sys.argv[1:]
provider = "claude" if "--print" in args else "codex"
prompt = sys.stdin.read()
stage = prompt.split("# Stage: ", 1)[1].splitlines()[0]
print(json.dumps({"args": args, "cwd": os.getcwd(),
    "child": os.environ.get("THABTO_CHILD"),
    "claude_token": "CLAUDE_CODE_OAUTH_TOKEN" in os.environ}), file=sys.stderr)
if "STALL" in prompt:
    marker = pathlib.Path(os.environ["MARKER"])
    subprocess.Popen([sys.executable, "-c",
        "import time,pathlib;time.sleep(1.2);pathlib.Path(" + repr(str(marker)) + ").touch()"])
    pathlib.Path(str(marker) + ".started").touch()
    time.sleep(30)
if "FAIL" in prompt and provider == "claude":
    print("synthetic provider failure", file=sys.stderr)
    sys.exit(7)
answer = provider + " " + stage + " answer"
if provider == "claude":
    if "MALFORMED" in prompt:
        print("not json")
    else:
        print(json.dumps({"type": "result", "is_error": "ERROR_RESULT" in prompt,
            "result": "" if "EMPTY" in prompt else answer}))
else:
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "interim"}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}))
    if "MISSING_FINAL" not in prompt:
        pathlib.Path(args[args.index("--output-last-message") + 1]).write_text(answer)
'''


class ThabtoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="thabto test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.task = self.root / "task.md"
        self.task.write_text("Investigate installer discovery. Keep this request verbatim.")
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.root / "state"),
                        CLAUDE_CODE_OAUTH_TOKEN="synthetic-test-token", MARKER=str(self.root / "marker"))
        self.env.pop("THABTO_CHILD", None)
        self.env.pop("DELARBITRATE_CHILD", None)
        self.command = [sys.executable, str(DRIVER), "--task-file", str(self.task),
                        "--workspace", str(self.workspace), "--claude-model", "test-claude",
                        "--codex-model", "test-codex", "--timeout", "5"]
        for provider in ("claude", "codex"):
            executable = self.root / (provider + " fake")
            executable.write_text(FAKE)
            executable.chmod(0o755)
            self.command += ["--" + provider + "-executable", str(executable)]

    def run_driver(self, task=None, extra=()):
        if task:
            self.task.write_text(task)
        return subprocess.run(self.command + list(extra), env=self.env,
                              text=True, capture_output=True, timeout=10)

    def run_path(self):
        return next((self.root / "state/thabto").iterdir())

    def test_complete_exchange_routes_reviews_and_keeps_raw_outputs(self):
        result = self.run_driver()
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.run_path()
        self.assertEqual((run / "task.md").read_text(), self.task.read_text())
        self.assertEqual(json.loads((run / "run.json").read_text())["status"], "awaiting_synthesis")
        for provider, peer in (("claude", "codex"), ("codex", "claude")):
            attempt = (run / f"attempt/{provider}/prompt.md").read_text()
            self.assertNotIn("attempt answer", attempt)
            review = (run / f"review/{provider}/prompt.md").read_text()
            self.assertIn(f"{peer} attempt answer", review)
            self.assertNotIn(f"{provider} attempt answer", review)
            revision = (run / f"revision/{provider}/prompt.md").read_text()
            self.assertIn(f"{provider} attempt answer", revision)
            self.assertIn(f"{peer} review answer", revision)
            self.assertNotIn(f"{provider} review answer", revision)
            for stage in ("attempt", "review", "revision"):
                folder = run / stage / provider
                self.assertEqual((folder / "answer.md").read_text().strip(), f"{provider} {stage} answer")
                self.assertTrue((folder / "stdout.log").read_text())
                receipt = json.loads((folder / "stderr.log").read_text())
                self.assertEqual(receipt["child"], "1")
                self.assertEqual(receipt["claude_token"], provider == "claude")
                self.assertEqual(Path(receipt["cwd"]), self.workspace)
                self.assertNotIn("--output-schema", receipt["args"])
                self.assertNotIn("--json-schema", receipt["args"])
        self.assertIn("revision/claude/answer.md", (run / "synthesis-prompt.md").read_text())
        self.assertIn("revision/codex/answer.md", (run / "synthesis-prompt.md").read_text())
        self.assertFalse((run / "synthesis.md").exists())
        self.assertEqual(list(self.workspace.iterdir()), [])
        self.assertEqual(run.stat().st_mode & 0o777, 0o700)

    def test_native_read_only_flags_and_model_selection_reach_fake_executables(self):
        self.assertEqual(self.run_driver().returncode, 0)
        run = self.run_path()
        claude = json.loads((run / "attempt/claude/stderr.log").read_text())["args"]
        codex = json.loads((run / "attempt/codex/stderr.log").read_text())["args"]
        self.assertEqual(claude[claude.index("--permission-mode") + 1], "plan")
        self.assertEqual(claude[claude.index("--tools") + 1], "Read,Glob,Grep")
        self.assertIn("--strict-mcp-config", claude)
        self.assertEqual(codex[codex.index("--sandbox") + 1], "read-only")
        self.assertIn("mcp_servers={}", codex)
        self.assertEqual(codex[codex.index("--ask-for-approval") + 1], "never")
        self.assertIn("test-claude", claude)
        self.assertIn("test-codex", codex)

    def test_provider_failure_stops_before_review_and_preserves_diagnostics(self):
        result = self.run_driver("FAIL")
        self.assertNotEqual(result.returncode, 0)
        run = self.run_path()
        self.assertFalse((run / "review").exists())
        self.assertIn("synthetic provider failure", (run / "attempt/claude/stderr.log").read_text())
        self.assertEqual(json.loads((run / "run.json").read_text())["status"], "failed")
        self.assertIn(str(run), result.stderr)

    def test_missing_or_invalid_final_answer_is_a_failure(self):
        for task in ("MALFORMED", "ERROR_RESULT", "EMPTY", "MISSING_FINAL"):
            with self.subTest(task=task):
                result = self.run_driver(task)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("failed", result.stderr.lower())

    def test_timeout_kills_descendants_and_keeps_partial_logs(self):
        started = time.monotonic()
        result = self.run_driver("STALL", ["--timeout", "1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - started, 3)
        self.assertIn("timed out", result.stderr)
        time.sleep(1.3)
        self.assertFalse((self.root / "marker").exists())
        logs = list(self.run_path().glob("attempt/*/stderr.log"))
        self.assertTrue(any(path.read_text() for path in logs))

    def test_sigterm_cancels_process_groups(self):
        self.task.write_text("STALL")
        process = subprocess.Popen(self.command, env=self.env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 4
            while not (self.root / "marker.started").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / "marker.started").exists())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=3)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(json.loads((self.run_path() / "run.json").read_text())["status"], "cancelled")
            time.sleep(1.3)
            self.assertFalse((self.root / "marker").exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_recursive_invocation_fails_before_creating_run(self):
        self.env["THABTO_CHILD"] = "1"
        result = self.run_driver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recurs", result.stderr.lower())
        self.assertFalse((self.root / "state/thabto").exists())

    def test_invalid_input_fails_before_launch(self):
        for extra in (["--timeout", "0"], ["--timeout", "nan"],
                      ["--workspace", str(self.root / "absent")],
                      ["--claude-executable", str(self.root / "absent")]):
            with self.subTest(extra=extra):
                self.assertNotEqual(self.run_driver(extra=extra).returncode, 0)
                self.assertFalse((self.root / "state/thabto").exists())
        self.assertNotEqual(self.run_driver("   ").returncode, 0)

    def test_skill_contract_is_portable_and_reserves_synthesis_for_coordinator(self):
        skill = (SKILL / "SKILL.md").read_text()
        keys = [line.split(":", 1)[0] for line in skill.split("---", 2)[1].splitlines() if line]
        self.assertEqual(keys, ["name", "description"])
        for text in ("THABTO_CHILD", "scripts/thabto.py", "synthesis.md", "read-only",
                     "Claude Code", "Codex", "Pi", "OpenCode", "implement"):
            self.assertIn(text, skill)


if __name__ == "__main__":
    unittest.main()
