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
if "--print" in args:
    provider = "claude"
elif "run" in args and "--agent" in args:
    provider = "opencode"
elif "-p" in args:
    provider = "pi"
else:
    provider = "codex"
model = args[args.index("--model") + 1]
prompt = sys.stdin.read()
stage = prompt.split("# Stage: ", 1)[1].splitlines()[0]
print(json.dumps({"args": args, "cwd": os.getcwd(),
    "child": os.environ.get("THABTO_CHILD"),
    "claude_token": "CLAUDE_CODE_OAUTH_TOKEN" in os.environ,
    "opencode_config": os.environ.get("OPENCODE_CONFIG")}), file=sys.stderr)
if "STALL" in prompt:
    marker = pathlib.Path(os.environ["MARKER"])
    subprocess.Popen([sys.executable, "-c",
        "import time,pathlib;time.sleep(1.2);pathlib.Path(" + repr(str(marker)) + ").touch()"])
    pathlib.Path(str(marker) + ".started").touch()
    time.sleep(30)
if "FAIL" in prompt and provider == "claude":
    print("synthetic provider failure", file=sys.stderr)
    sys.exit(7)
if "REVIEW_FAIL" in prompt and stage == "review" and model == "test-codex-b":
    print("synthetic review failure", file=sys.stderr)
    sys.exit(8)
answer = f"{provider}:{model} {stage} answer"
if provider == "claude":
    if "MALFORMED" in prompt:
        print("not json")
    else:
        print(json.dumps({"type": "result", "is_error": "ERROR_RESULT" in prompt,
            "result": "" if "EMPTY" in prompt else answer}))
elif provider == "opencode":
    if "OC_ERROR" in prompt:
        print(json.dumps({"type": "error", "error": {"name": "ProviderError", "message": "synthetic opencode error"}}))
        sys.exit(0)
    for event in ({"type": "step_start", "part": {}}, {"type": "text", "part": {"text": "interim narration"}},
                  {"type": "tool_use", "part": {"tool": "read"}}, {"type": "step_finish", "part": {}},
                  {"type": "step_start", "part": {}}, {"type": "text", "part": {"text": answer}},
                  {"type": "step_finish", "part": {"cost": 0.01}}):
        print(json.dumps(event))
elif provider == "pi":
    print(json.dumps({"type": "session", "id": "s1", "version": 1}))
    print(json.dumps({"type": "message_end", "message": {"role": "user", "content": [{"type": "text", "text": "q"}]}}))
    if "PI_ERROR" in prompt:
        print(json.dumps({"type": "message_end", "message": {"role": "assistant", "content": [],
            "stopReason": "error", "errorMessage": "synthetic pi error"}}))
        sys.exit(0)
    print(json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
        "content": [{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": answer}]}}))
    print(json.dumps({"type": "agent_end"}))
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
        # Fakes finish in well under a second; the stage timeout only needs to stay clear of
        # interpreter start-up on a loaded machine.
        self.command = [sys.executable, str(DRIVER), "--task-file", str(self.task),
                        "--workspace", str(self.workspace), "--claude-model", "test-claude",
                        "--codex-model", "test-codex", "--timeout", "30"]
        for provider in ("claude", "codex", "opencode", "pi"):
            executable = self.root / (provider + " fake")
            executable.write_text(FAKE)
            executable.chmod(0o755)
            if provider in ("claude", "codex"):
                self.command += ["--" + provider + "-executable", str(executable)]

    def run_driver(self, task=None, extra=()):
        if task:
            self.task.write_text(task)
        return subprocess.run(self.command + list(extra), env=self.env,
                              text=True, capture_output=True, timeout=90)

    def run_path(self):
        return next((self.root / "state/thabto").iterdir())

    def run_metadata(self):
        return json.loads((self.run_path() / "run.json").read_text())

    @staticmethod
    def answer(provider, stage, model=None):
        return f"{provider}:{model or 'test-' + provider} {stage} answer"

    def test_complete_exchange_routes_reviews_and_keeps_raw_outputs(self):
        result = self.run_driver()
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.run_path()
        self.assertEqual((run / "task.md").read_text(), self.task.read_text())
        metadata = self.run_metadata()
        self.assertEqual(metadata["status"], "awaiting_synthesis")
        self.assertEqual(metadata["schema"], 3)
        self.assertRegex(metadata["started_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertGreaterEqual(metadata["finished_at"], metadata["started_at"])
        self.assertEqual(metadata["participants"], [
            {"name": "claude", "harness": "claude-code", "model": "test-claude", "effort": "high"},
            {"name": "codex", "harness": "codex", "model": "test-codex", "effort": "high"}])
        self.assertEqual(sorted(metadata["ring"]), ["claude", "codex"])
        self.assertIsInstance(metadata["seed"], int)
        self.assertEqual(metadata["review_targets"], {"claude": "codex", "codex": "claude"})
        self.assertEqual(metadata["final_answers"], {"claude": "revision/claude/answer.md",
                                                     "codex": "revision/codex/answer.md"})
        for stage in ("attempt", "review", "revision"):
            for provider in ("claude", "codex"):
                record = metadata["stages"][stage][provider]
                self.assertEqual((record["outcome"], record["exit_code"]), ("answered", 0))
                self.assertGreaterEqual(record["seconds"], 0)
                self.assertGreaterEqual(record["finished_at"], record["started_at"])
        for provider, peer in (("claude", "codex"), ("codex", "claude")):
            attempt = (run / f"attempt/{provider}/prompt.md").read_text()
            self.assertNotIn("attempt answer", attempt)
            review = (run / f"review/{provider}/prompt.md").read_text()
            self.assertIn(self.answer(peer, "attempt"), review)
            self.assertNotIn(self.answer(provider, "attempt"), review)
            revision = (run / f"revision/{provider}/prompt.md").read_text()
            self.assertIn(self.answer(provider, "attempt"), revision)
            self.assertIn(self.answer(peer, "review"), revision)
            self.assertNotIn(self.answer(provider, "review"), revision)
            for stage in ("attempt", "review", "revision"):
                folder = run / stage / provider
                self.assertEqual((folder / "answer.md").read_text().strip(), self.answer(provider, stage))
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
        metadata = self.run_metadata()
        claude = metadata["stages"]["attempt"]["claude"]
        self.assertEqual((claude["outcome"], claude["exit_code"]), ("failed", 7), result.stderr)
        self.assertEqual(metadata["stages"]["attempt"]["codex"]["outcome"], "answered")
        self.assertFalse((run / "review").exists())
        self.assertIn("synthetic provider failure", (run / "attempt/claude/stderr.log").read_text())
        self.assertEqual(metadata["status"], "failed")
        self.assertIn("needs two", metadata["error"])
        self.assertIn(str(run), result.stderr)
        self.assertEqual(metadata["participants"][0]["failed_at"], "attempt")
        self.assertNotIn("review", metadata["stages"])

    def three_way(self, task=None, extra=()):
        self.task.write_text(task or self.task.read_text())
        command = [sys.executable, str(DRIVER), "--task-file", str(self.task), "--workspace", str(self.workspace),
                   "--timeout", "30", "--seed", "7",
                   "--participant", "claude-code:test-claude", "--participant", "codex:test-codex:high",
                   "--participant", "codex:test-codex-b:medium",
                   "--claude-executable", str(self.root / "claude fake"),
                   "--codex-executable", str(self.root / "codex fake"), *extra]
        return subprocess.run(command, env=self.env, text=True, capture_output=True, timeout=90)

    def test_three_participants_form_a_seeded_ring(self):
        result = self.three_way()
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = self.run_metadata()
        names = [p["name"] for p in metadata["participants"]]
        self.assertEqual(names, ["claude", "codex", "codex-2"])
        self.assertEqual(metadata["participants"][2], {"name": "codex-2", "harness": "codex",
                                                       "model": "test-codex-b", "effort": "medium"})
        self.assertEqual(metadata["seed"], 7)
        ring = metadata["ring"]
        self.assertEqual(sorted(ring), sorted(names))
        targets = metadata["review_targets"]
        self.assertEqual(targets, {ring[i]: ring[(i + 1) % 3] for i in range(3)})
        models = {"claude": "test-claude", "codex": "test-codex", "codex-2": "test-codex-b"}
        run = self.run_path()
        for reviewer, target in targets.items():
            review = (run / f"review/{reviewer}/prompt.md").read_text()
            self.assertIn(self.answer(target.split("-")[0], "attempt", models[target]), review)
            for other in set(names) - {target}:
                self.assertNotIn(self.answer(other.split("-")[0], "attempt", models[other]), review)
            revision = (run / f"revision/{target}/prompt.md").read_text()
            self.assertIn(self.answer(reviewer.split("-")[0], "review", models[reviewer]), revision)
        self.assertEqual(set(metadata["final_answers"]), set(names))
        self.assertTrue(all(path.startswith("revision/") for path in metadata["final_answers"].values()))
        codex_b = json.loads((run / "attempt/codex-2/stderr.log").read_text())["args"]
        self.assertIn("test-codex-b", codex_b)
        self.assertIn('model_reasoning_effort="medium"', codex_b)
        # Same seed, same ring.
        self.assertEqual(self.three_way().returncode, 0)
        rings = {json.loads((r / "run.json").read_text())["ring"][0] for r in (self.root / "state/thabto").iterdir()}
        self.assertEqual(len(rings), 1)

    def test_attempt_failure_drops_one_participant_and_the_run_continues(self):
        result = self.three_way("FAIL")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("attempt: claude failed", result.stderr)
        metadata = self.run_metadata()
        self.assertEqual(metadata["status"], "awaiting_synthesis")
        self.assertEqual(metadata["participants"][0]["failed_at"], "attempt")
        self.assertEqual(metadata["stages"]["attempt"]["claude"]["outcome"], "failed")
        self.assertEqual(set(metadata["review_targets"]), {"codex", "codex-2"})
        self.assertEqual(metadata["review_targets"], {"codex": "codex-2", "codex-2": "codex"})
        self.assertEqual(set(metadata["stages"]["review"]), {"codex", "codex-2"})
        self.assertEqual(metadata["final_answers"], {"codex": "revision/codex/answer.md",
                                                     "codex-2": "revision/codex-2/answer.md"})
        prompt = (self.run_path() / "synthesis-prompt.md").read_text()
        self.assertIn("Failed participants: claude (at attempt)", prompt)
        self.assertNotIn("claude:", prompt.split("Failed participants")[0])

    def test_review_failure_skips_the_orphaned_revision(self):
        result = self.three_way("REVIEW_FAIL")
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = self.run_metadata()
        target = metadata["review_targets"]["codex-2"]
        self.assertEqual(metadata["stages"]["review"]["codex-2"]["outcome"], "failed")
        self.assertEqual(metadata["participants"][2]["failed_at"], "review")
        self.assertEqual(metadata["stages"]["revision"][target], {"outcome": "skipped", "reason": "no review received"})
        self.assertNotIn("codex-2", metadata["stages"]["revision"])
        self.assertEqual(metadata["final_answers"][target], f"attempt/{target}/answer.md")
        self.assertEqual(metadata["final_answers"]["codex-2"], "attempt/codex-2/answer.md")
        prompt = (self.run_path() / "synthesis-prompt.md").read_text()
        self.assertIn(f"- {target}: attempt/{target}/answer.md (no revision: no review received)", prompt)
        self.assertIn("codex-2 (at review)", prompt)

    def multi_harness(self, task=None, extra=()):
        self.task.write_text(task or self.task.read_text())
        command = [sys.executable, str(DRIVER), "--task-file", str(self.task), "--workspace", str(self.workspace),
                   "--timeout", "30", "--seed", "3",
                   "--participant", "codex:test-codex", "--participant", "opencode:openai/test-oc",
                   "--participant", "pi:openai-codex/test-pi:medium",
                   "--codex-executable", str(self.root / "codex fake"),
                   "--opencode-executable", str(self.root / "opencode fake"),
                   "--pi-executable", str(self.root / "pi fake"), *extra]
        return subprocess.run(command, env=self.env, text=True, capture_output=True, timeout=90)

    def latest_metadata(self):
        run = sorted((self.root / "state/thabto").iterdir())[-1]
        return run, json.loads((run / "run.json").read_text())

    def test_opencode_and_pi_run_read_only_on_openai_models(self):
        result = self.multi_harness()
        self.assertEqual(result.returncode, 0, result.stderr)
        run, metadata = self.latest_metadata()
        self.assertEqual([p["name"] for p in metadata["participants"]], ["codex", "opencode", "pi"])
        opencode = json.loads((run / "attempt/opencode/stderr.log").read_text())
        for flag in ("run", "--pure", "--agent", "thabto-child", "--format", "json", "--variant", "high"):
            self.assertIn(flag, opencode["args"])
        self.assertEqual(opencode["args"][opencode["args"].index("--model") + 1], "openai/test-oc")
        self.assertFalse(opencode["claude_token"])
        config = Path(opencode["opencode_config"])
        self.assertEqual(config, SKILL / "harness/opencode.json")
        agent = json.loads(config.read_text())["agent"]["thabto-child"]
        self.assertEqual(agent["mode"], "primary")
        self.assertEqual({k for k, v in agent["permission"].items() if v == "allow"},
                         {"read", "glob", "grep", "list", "external_directory"})
        for denied in ("edit", "bash", "webfetch", "websearch", "task", "skill"):
            self.assertEqual(agent["permission"][denied], "deny")
        pi = json.loads((run / "attempt/pi/stderr.log").read_text())
        for flag in ("-p", "--no-session", "--no-extensions", "--no-skills", "--no-prompt-templates", "--offline"):
            self.assertIn(flag, pi["args"])
        self.assertEqual(pi["args"][pi["args"].index("--tools") + 1], "read,grep,find,ls")
        self.assertEqual(pi["args"][pi["args"].index("--mode") + 1], "json")
        self.assertEqual(pi["args"][pi["args"].index("--model") + 1], "openai-codex/test-pi:medium")
        self.assertFalse(pi["claude_token"])
        self.assertIsNone(pi["opencode_config"])
        for stage in ("attempt", "review", "revision"):
            self.assertEqual((run / f"{stage}/opencode/answer.md").read_text().strip(),
                             self.answer("opencode", stage, "openai/test-oc"))
            self.assertEqual((run / f"{stage}/pi/answer.md").read_text().strip(),
                             self.answer("pi", stage, "openai-codex/test-pi:medium"))
        self.assertNotIn("interim", (run / "attempt/opencode/answer.md").read_text())
        self.assertNotIn("hmm", (run / "attempt/pi/answer.md").read_text())
        self.assertEqual(set(metadata["final_answers"]), {"codex", "opencode", "pi"})

    def test_harness_reported_errors_drop_only_that_participant(self):
        for marker, name, token in (("OC_ERROR", "opencode", "OpenCode reported an error"),
                                    ("PI_ERROR", "pi", "Pi reported an error")):
            with self.subTest(name=name):
                result = self.multi_harness(marker)
                self.assertEqual(result.returncode, 0, result.stderr)
                run, metadata = self.latest_metadata()
                self.assertEqual(metadata["stages"]["attempt"][name]["outcome"], "failed")
                self.assertIn(token, (run / f"attempt/{name}/error.txt").read_text())
                self.assertEqual(next(p for p in metadata["participants"] if p["name"] == name)["failed_at"], "attempt")
                self.assertEqual(len(metadata["final_answers"]), 2)
                self.assertNotIn(name, metadata["final_answers"])

    def test_opencode_and_pi_accept_openai_models_only(self):
        for spec in ("opencode:anthropic/claude-opus-5-5", "pi:anthropic/claude-opus-5-5", "pi:gpt-6-sol"):
            with self.subTest(spec=spec):
                command = [sys.executable, str(DRIVER), "--task-file", str(self.task), "--workspace", str(self.workspace),
                           "--participant", "codex:test-codex", "--participant", spec,
                           "--codex-executable", str(self.root / "codex fake"),
                           "--opencode-executable", str(self.root / "opencode fake"),
                           "--pi-executable", str(self.root / "pi fake")]
                result = subprocess.run(command, env=self.env, text=True, capture_output=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("OpenAI models only", result.stderr)
                self.assertFalse((self.root / "state/thabto").exists())

    def test_participant_spec_errors_are_explicit(self):
        base = [sys.executable, str(DRIVER), "--task-file", str(self.task), "--workspace", str(self.workspace),
                "--claude-executable", str(self.root / "claude fake"), "--codex-executable", str(self.root / "codex fake")]
        cases = {
            "pi": ["--participant", "pi:gpt-6-sol", "--participant", "codex:gpt-6-sol"],
            "HARNESS:MODEL": ["--participant", "codex", "--participant", "codex:gpt-6-sol"],
            "at least two": ["--participant", "codex:gpt-6-sol"],
            "not both": ["--participant", "codex:gpt-6-sol", "--claude-model", "x"],
            "both --claude-model and --codex-model": ["--codex-model", "x"],
        }
        for token, extra in cases.items():
            with self.subTest(token=token):
                result = subprocess.run(base + extra, env=self.env, text=True, capture_output=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(token, result.stderr)
                self.assertFalse((self.root / "state/thabto").exists())

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
        outcomes = {record["outcome"] for record in self.run_metadata()["stages"]["attempt"].values()}
        self.assertEqual(outcomes, {"timeout"})

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
            self.assertEqual(self.run_metadata()["status"], "cancelled")
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
