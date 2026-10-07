import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LABEL = ROOT / "skills/.local/share/skills/thabto/scripts/thabto_label.py"

# A judge CLI stand-in. JUDGE_CLAUDE / JUDGE_CODEX hold the ruling JSON it returns, or FAIL.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
provider = "claude" if "--print" in args else "codex"
prompt = sys.stdin.read()
pathlib.Path(os.environ["PROMPTS"], provider + ".md").write_text(prompt)
pathlib.Path(os.environ["PROMPTS"], provider + ".args").write_text(json.dumps(args))
ruling = os.environ["JUDGE_" + provider.upper()]
if ruling == "FAIL":
    sys.exit(3)
answer = "I read the evidence.\n\n```json\n" + ruling + "\n```\n"
if provider == "claude":
    print(json.dumps({"type": "result", "is_error": False, "result": answer}))
else:
    pathlib.Path(args[args.index("--output-last-message") + 1]).write_text(answer)
'''


def ruling(outcome="codex", answer="correct", settled=True, reason="Datadog shows 0 errors over 26 h.",
           attempts=None):
    if not settled:
        return json.dumps({"settled": False, "reason": "No outcome yet."})
    attempts = {"claude": "correct", "codex": "correct"} if attempts is None else attempts
    return json.dumps({"settled": True, "outcome": outcome, "answer": answer, "attempts": attempts, "reason": reason})


class ThabtoLabelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="thabto label ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / "state/thabto/20261001T000000Z-aaaaaaaaaaaa"
        for stage in ("attempt/claude", "attempt/codex", "revision/claude", "revision/codex"):
            (self.run / stage).mkdir(parents=True)
        (self.run / "attempt/claude/answer.md").write_text("CLAUDE ATTEMPT: impact unknown.")
        (self.run / "attempt/codex/answer.md").write_text("CODEX ATTEMPT: impact unproven.")
        (self.run / "revision/claude/answer.md").write_text("CLAUDE FINAL: no customer impact.")
        (self.run / "revision/codex/answer.md").write_text("CODEX FINAL: impact unproven.")
        (self.run / "run.json").write_text(json.dumps({
            "schema": 3, "status": "synthesized",
            "participants": [{"name": "claude", "harness": "claude-code"}, {"name": "codex", "harness": "codex"}],
            "final_answers": {"claude": "revision/claude/answer.md", "codex": "revision/codex/answer.md"}}))
        (self.run / "task.md").write_text("TASK: investigate the alert.")
        (self.run / "synthesis.md").write_text("SYNTHESIS: impact not proven.")
        self.write_verdict(None)
        (self.run / "label-evidence.md").write_text("EVIDENCE: 0 config errors in 26 h after deploy.")
        self.prompts = self.root / "prompts"
        self.prompts.mkdir()
        self.fakes = {}
        for provider in ("claude", "codex"):
            fake = self.root / (provider + " fake")
            fake.write_text(FAKE)
            fake.chmod(0o755)
            self.fakes[provider] = fake

    def write_verdict(self, ground_truth):
        (self.run / "verdict.json").write_text(json.dumps({
            "schema": 2, "coordinator": {"harness": "codex", "model": "gpt-6"},
            "material_disagreement": True, "selected_backbone": "codex",
            "claims": [{"id": "c1", "text": "No customer impact.", "positions": {"claude": "asserts", "codex": "disputes"},
                        "disposition": "unresolved", "basis": "unverified", "settle_by": "Error logs for 24 h."}],
            "ground_truth": ground_truth}))

    def verdict(self):
        return json.loads((self.run / "verdict.json").read_text())

    def label(self, claude, codex, runs=None):
        env = dict(os.environ, JUDGE_CLAUDE=claude, JUDGE_CODEX=codex, PROMPTS=str(self.prompts))
        env.pop("THABTO_CHILD", None)
        command = [sys.executable, str(LABEL), "--claude-executable", str(self.fakes["claude"]),
                   "--codex-executable", str(self.fakes["codex"]), "--timeout", "30"]
        for run in runs or [self.run]:
            command += ["--run", str(run)]
        return subprocess.run(command, env=env, text=True, capture_output=True, timeout=90)

    def test_agreeing_judges_label_the_run(self):
        result = self.label(ruling(), ruling(reason="Logs show no errors."))
        self.assertEqual(result.returncode, 0, result.stderr)
        truth = self.verdict()["ground_truth"]
        self.assertEqual((truth["outcome"], truth["answer"]), ("codex", "correct"))
        self.assertIn("Datadog shows 0 errors over 26 h.", truth["note"])
        self.assertIn("Logs show no errors.", truth["note"])
        self.assertIn("20261001T000000Z-aaaaaaaaaaaa: labeled outcome=codex answer=correct", result.stdout)
        decision = json.loads(next(self.run.glob("labeling/*/result.json")).read_text())
        self.assertEqual(decision["decision"], "labeled")

    def test_judges_see_evidence_and_run_read_only(self):
        self.label(ruling(), ruling())
        for provider in ("claude", "codex"):
            prompt = (self.prompts / (provider + ".md")).read_text()
            for text in ("TASK: investigate the alert.", "SYNTHESIS: impact not proven.",
                         "EVIDENCE: 0 config errors", "CLAUDE FINAL", "CODEX FINAL", "Error logs for 24 h.",
                         "CLAUDE ATTEMPT", "CODEX ATTEMPT",
                         # Partly settled runs are labeled on the claims that have evidence.
                         "Rule on the claims that"):
                self.assertIn(text, prompt)
        self.assertIn("plan", json.loads((self.prompts / "claude.args").read_text()))
        self.assertIn("read-only", json.loads((self.prompts / "codex.args").read_text()))

    def test_disagreement_is_surfaced_and_writes_nothing(self):
        result = self.label(ruling(outcome="claude", reason="Claude was right."), ruling(outcome="codex"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.verdict()["ground_truth"])
        self.assertIn("DISAGREE", result.stdout)
        self.assertIn("Claude was right.", result.stdout)
        # Same outcome but a different answer grade is still a disagreement.
        result = self.label(ruling(answer="partly"), ruling(answer="correct"))
        self.assertIn("DISAGREE", result.stdout)
        self.assertIsNone(self.verdict()["ground_truth"])

    def test_attempt_grades_record_only_where_judges_agree(self):
        # First attempts are what a single model alone would have answered; grading them
        # measures what review and synthesis added.
        result = self.label(ruling(attempts={"claude": "wrong", "codex": "correct"}),
                            ruling(attempts={"claude": "wrong", "codex": "partly"}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.verdict()["attempt_grades"], {"claude": "wrong"})
        self.assertIn("attempts claude=wrong; codex split", result.stdout)

    def test_attempt_grades_survive_relabeling_and_a_disputed_outcome(self):
        self.write_verdict({"outcome": "claude", "note": "Earlier label.", "labeled_at": "2026-10-06T00:00:00Z"})
        result = self.label(ruling(attempts={"claude": "partly", "codex": "wrong"}),
                            ruling(attempts={"claude": "partly", "codex": "wrong"}))
        self.assertIn("DISAGREE", result.stdout)
        verdict = self.verdict()
        self.assertEqual(verdict["ground_truth"]["outcome"], "claude")
        self.assertEqual(verdict["attempt_grades"], {"claude": "partly", "codex": "wrong"})
        subprocess.run([sys.executable, str(LABEL.parent / "thabto_finish.py"), "--run", str(self.run),
                        "--label", "both", "--answer", "correct"], check=True, capture_output=True)
        self.assertEqual(self.verdict()["attempt_grades"], {"claude": "partly", "codex": "wrong"})

    def test_settled_ruling_without_attempt_grades_fails(self):
        result = self.label(ruling(attempts={"claude": "correct"}), ruling())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("attempts", result.stdout)
        self.assertNotIn("attempt_grades", self.verdict())

    def test_unsettled_runs_stay_pending(self):
        result = self.label(ruling(settled=False), ruling(settled=False))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.verdict()["ground_truth"])
        self.assertIn("unsettled", result.stdout)
        self.assertNotIn("attempt_grades", self.verdict())
        result = self.label(ruling(settled=False), ruling())
        self.assertIn("DISAGREE", result.stdout)
        self.assertIsNone(self.verdict()["ground_truth"])

    def test_existing_label_gains_an_answer_grade_but_is_never_overturned(self):
        self.write_verdict({"outcome": "codex", "note": "Merged fix matched codex.", "labeled_at": "2026-10-06T00:00:00Z"})
        result = self.label(ruling(), ruling())
        self.assertEqual(result.returncode, 0, result.stderr)
        truth = self.verdict()["ground_truth"]
        self.assertEqual((truth["outcome"], truth["answer"]), ("codex", "correct"))
        self.assertTrue(truth["note"].startswith("Merged fix matched codex."))
        self.write_verdict({"outcome": "claude", "note": "Earlier label.", "labeled_at": "2026-10-06T00:00:00Z"})
        result = self.label(ruling(), ruling())
        self.assertIn("DISAGREE", result.stdout)
        self.assertIn("existing label claude", result.stdout)
        self.assertEqual(self.verdict()["ground_truth"]["outcome"], "claude")
        self.assertNotIn("answer", self.verdict()["ground_truth"])

    def test_a_recorded_answer_grade_is_never_overturned(self):
        self.write_verdict({"outcome": "codex", "answer": "partly", "note": "User decided.",
                            "labeled_at": "2026-10-07T00:00:00Z"})
        result = self.label(ruling(answer="correct"), ruling(answer="correct"))
        self.assertIn("DISAGREE", result.stdout)
        self.assertIn("existing answer grade partly", result.stdout)
        self.assertEqual(self.verdict()["ground_truth"]["answer"], "partly")
        # Agreement that matches the record changes nothing.
        result = self.label(ruling(answer="partly"), ruling(answer="partly"))
        self.assertIn("confirmed outcome=codex answer=partly", result.stdout)
        self.assertEqual(self.verdict()["ground_truth"]["note"], "User decided.")

    def test_agreement_replaces_an_unknown_label(self):
        # "unknown" records that nothing settled the run yet, not a position on who was right.
        self.write_verdict({"outcome": "unknown", "note": "No outcome yet.", "labeled_at": "2026-10-06T00:00:00Z"})
        result = self.label(ruling(), ruling())
        self.assertEqual(result.returncode, 0, result.stderr)
        truth = self.verdict()["ground_truth"]
        self.assertEqual((truth["outcome"], truth["answer"]), ("codex", "correct"))
        self.assertTrue(truth["note"].startswith("No outcome yet."))

    def test_failed_or_malformed_judge_labels_nothing_and_exits_nonzero(self):
        for claude in ("FAIL", '{"settled": true, "outcome": "gpt", "answer": "correct", "reason": "x"}'):
            with self.subTest(claude=claude):
                result = self.label(claude, ruling())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FAILED", result.stdout)
                self.assertIsNone(self.verdict()["ground_truth"])

    def test_missing_evidence_stops_before_any_judge_runs(self):
        (self.run / "label-evidence.md").unlink()
        result = self.label(ruling(), ruling())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("label-evidence.md", result.stderr)
        self.assertEqual(list(self.prompts.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
