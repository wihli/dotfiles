import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "skills/.local/share/skills/thabto/scripts/thabto_stats.py"
T0 = 1_800_000_000  # any fixed epoch; mtimes below are offsets from it


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def stage(run, name, provider, seconds, stdout=None, answer="answer text"):
    """Create one stage folder whose answer.md mtime is `seconds` after prompt.md."""
    folder = run / name / provider
    prompt = write(folder / "prompt.md", "# Stage: " + name)
    os.utime(prompt, (T0, T0))
    if stdout is not None:
        write(folder / "stdout.log", stdout)
    if answer is not None:
        out = write(folder / "answer.md", answer)
        os.utime(out, (T0 + seconds, T0 + seconds))


class ThabtoStatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="thabto stats ")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.thabto = root / "thabto"
        self.delarbitrate = root / "delarbitrate/runs"
        self.build_thabto_runs()
        self.build_delarbitrate_runs()

    def build_thabto_runs(self):
        # Complete run: alias model, Claude JSON carries the resolved model, cost, duration.
        run = self.thabto / "20260910T171439Z-aaaaaaaaaaaa"
        write(run / "run.json", json.dumps({
            "status": "awaiting_synthesis", "workspace": "/w",
            "settings": {"claude_model": "sonnet", "codex_model": "gpt-x",
                         "claude_effort": "high", "codex_effort": "max"}}))
        write(run / "task.md", "task")
        write(run / "synthesis.md", "final")
        # modelUsage lists a cheap utility model first; the participant model carries the spend.
        claude_json = json.dumps({"type": "result", "result": "x", "duration_ms": 90000, "total_cost_usd": 1.5,
                                  "modelUsage": {"claude-haiku-4-5-20251001": {"costUSD": 0.002, "outputTokens": 17},
                                                 "claude-sonnet-5": {"costUSD": 1.498, "outputTokens": 9000}}})
        codex_jsonl = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 3}})
        for name in ("attempt", "review", "revision"):
            stage(run, name, "claude", 600, stdout=claude_json, answer="claude " * 10)
            stage(run, name, "codex", 120, stdout=codex_jsonl, answer="codex " * 20)
        # Failed run: no answers, an error, no synthesis.
        run = self.thabto / "20260911T213919Z-bbbbbbbbbbbb"
        write(run / "run.json", json.dumps({
            "status": "failed", "error": "claude timed out after 600 seconds.",
            "settings": {"claude_model": "opus", "codex_model": "gpt-x",
                         "claude_effort": "high", "codex_effort": "high"}}))
        stage(run, "attempt", "claude", 0, answer=None)
        stage(run, "attempt", "codex", 60)
        # Future schema: explicit participants with harnesses.
        run = self.thabto / "20260930T000000Z-cccccccccccc"
        write(run / "run.json", json.dumps({
            "status": "awaiting_synthesis",
            "participants": [
                {"name": "codex", "harness": "codex", "model": "gpt-6-sol", "effort": "high"},
                {"name": "pi", "harness": "pi", "model": "gpt-6-sol", "effort": "high"}]}))
        for participant in ("codex", "pi"):
            stage(run, "attempt", participant, 30)
        # Unreadable: no run.json at all.
        write(self.thabto / "20260912T000000Z-dddddddddddd/task.md", "task")
        # Schema-2 run with driver-recorded timings, a verdict, and a ground-truth label.
        run = self.thabto / "20261001T120000Z-eeeeeeeeeeee"
        write(run / "run.json", json.dumps({
            "schema": 2, "status": "synthesized",
            "participants": [
                {"name": "claude", "harness": "claude-code", "model": "claude-fable-5-1", "effort": "high"},
                {"name": "codex", "harness": "codex", "model": "gpt-6-sol", "effort": "high"}],
            "stages": {"attempt": {"claude": {"seconds": 300, "outcome": "answered", "exit_code": 0},
                                   "codex": {"seconds": 90, "outcome": "answered", "exit_code": 0}}}}))
        write(run / "synthesis.md", "final")
        # File timestamps (600 s) and Claude's self-reported duration (90 s) both disagree with the driver (300 s).
        fable_json = json.dumps({"type": "result", "result": "x", "duration_ms": 90000, "total_cost_usd": 3.0,
                                 "modelUsage": {"claude-fable-5-1": {"costUSD": 3.0, "outputTokens": 100}}})
        stage(run, "attempt", "claude", 600, stdout=fable_json)
        stage(run, "attempt", "codex", 120)
        write(run / "verdict.json", json.dumps({
            "schema": 1, "coordinator": {"harness": "claude-code", "model": "claude-fable-5-1"},
            "material_disagreement": True, "selected_backbone": "claude",
            "claims": [
                {"id": "c1", "text": "a", "positions": {"claude": "asserts", "codex": "disputes"},
                 "disposition": "supported", "basis": "evidence"},
                {"id": "c2", "text": "b", "positions": {"claude": "disputes", "codex": "asserts"},
                 "disposition": "rejected", "basis": "evidence"},
                {"id": "c3", "text": "c", "positions": {"claude": "silent", "codex": "asserts"},
                 "disposition": "supported", "basis": "evidence"},
                {"id": "c4", "text": "d", "positions": {"claude": "asserts", "codex": "disputes"},
                 "disposition": "unresolved", "basis": "unverified"}],
            "ground_truth": {"outcome": "claude", "note": "fix merged", "labeled_at": "2026-10-02T00:00:00Z"}}))

    def build_delarbitrate_runs(self):
        config = json.dumps({"codex_candidate_model": "gpt-5.6-terra", "claude_candidate_model": "claude-sonnet-5",
                             "codex_judge_model": "gpt-5.6-sol", "claude_tiebreak_model": "opus"})
        run = self.delarbitrate / "d1-complete"
        write(run / "effective-config.json", config)
        write(run / "manifest.json", json.dumps({
            "status": "complete", "selected_candidate_backbone": "codex",
            "arbitration_path": ["codex_and_claude_candidates", "two_swapped_codex_judges"],
            "started_at_unix_ms": 1_000_000, "finished_at_unix_ms": 1_000_000 + 180_000,
            "provider_launches": 5, "provider_retries": 1}))
        write(run / "normalized-judgments.json", json.dumps([
            {"selected_backbone": "codex", "material_disagreement": False, "resolution": "resolved"},
            {"selected_backbone": "codex", "material_disagreement": True, "resolution": "resolved"}]))
        run = self.delarbitrate / "d2-needs-human"
        write(run / "effective-config.json", config)
        write(run / "manifest.json", json.dumps({
            "status": "needs_human", "selected_candidate_backbone": None, "arbitration_path": [],
            "started_at_unix_ms": 2_000_000, "finished_at_unix_ms": 2_000_000 + 60_000,
            "provider_launches": 2, "provider_retries": 0}))
        run = self.delarbitrate / "d3-aborted"
        write(run / "effective-config.json", config)
        write(run / "task.md", "task")

    def run_stats(self, *extra):
        command = [sys.executable, str(STATS), "--thabto-state", str(self.thabto),
                   "--delarbitrate-state", str(self.delarbitrate), *extra]
        return subprocess.run(command, text=True, capture_output=True, timeout=30)

    def summary(self):
        result = self.run_stats("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_thabto_runs_report_status_models_timing_and_cost(self):
        runs = {run["run_id"]: run for run in self.summary()["thabto"]["runs"]}
        complete = runs["20260910T171439Z-aaaaaaaaaaaa"]
        self.assertEqual(complete["started_at"], "2026-09-10T17:14:39Z")
        self.assertEqual(complete["status"], "awaiting_synthesis")
        self.assertTrue(complete["synthesized"])
        self.assertIsNone(complete["error"])
        claude, codex = complete["participants"]
        self.assertEqual((claude["harness"], claude["requested_model"], claude["resolved_model"], claude["effort"]),
                         ("claude-code", "sonnet", "claude-sonnet-5", "high"))
        self.assertEqual((codex["harness"], codex["requested_model"], codex["resolved_model"]),
                         ("codex", "gpt-x", None))
        # Harness-reported duration wins over file timestamps; Codex has only timestamps.
        self.assertAlmostEqual(claude["stages"]["attempt"]["minutes"], 1.5)
        self.assertAlmostEqual(codex["stages"]["attempt"]["minutes"], 2.0)
        self.assertEqual(claude["stages"]["attempt"]["cost_usd"], 1.5)
        self.assertIsNone(codex["stages"]["attempt"]["cost_usd"])
        self.assertEqual(codex["stages"]["attempt"]["tokens"], {"input_tokens": 7, "output_tokens": 3})
        self.assertEqual(codex["stages"]["revision"]["answer_bytes"], len("codex " * 20))

    def test_failed_and_future_runs_degrade_to_unknown_not_errors(self):
        summary = self.summary()["thabto"]
        runs = {run["run_id"]: run for run in summary["runs"]}
        failed = runs["20260911T213919Z-bbbbbbbbbbbb"]
        self.assertEqual(failed["status"], "failed")
        self.assertFalse(failed["synthesized"])
        self.assertIn("timed out", failed["error"])
        self.assertIsNone(failed["participants"][0]["stages"]["attempt"]["minutes"])
        self.assertNotIn("review", failed["participants"][0]["stages"])
        future = runs["20260930T000000Z-cccccccccccc"]
        self.assertEqual([p["harness"] for p in future["participants"]], ["codex", "pi"])
        self.assertEqual(future["participants"][1]["requested_model"], "gpt-6-sol")
        self.assertEqual(summary["unreadable"], ["20260912T000000Z-dddddddddddd"])
        self.assertEqual(summary["counts"], {"runs": 4, "synthesized": 2, "failed": 1, "unreadable": 1})
        self.assertIsNone(runs["20260910T171439Z-aaaaaaaaaaaa"]["verdict"])

    def test_driver_timings_win_and_verdict_yields_a_scorecard(self):
        summary = self.summary()["thabto"]
        run = {r["run_id"]: r for r in summary["runs"]}["20261001T120000Z-eeeeeeeeeeee"]
        claude, codex = run["participants"]
        self.assertAlmostEqual(claude["stages"]["attempt"]["minutes"], 5.0)
        self.assertAlmostEqual(codex["stages"]["attempt"]["minutes"], 1.5)
        self.assertEqual(claude["stages"]["attempt"]["outcome"], "answered")
        self.assertEqual(run["verdict"], {
            "material_disagreement": True, "selected_backbone": "claude", "claims": 4, "disputed_claims": 3,
            "scorecard": {"claude": {"right": 2, "wrong": 0}, "codex": {"right": 0, "wrong": 2}},
            "ground_truth": "claude"})
        self.assertEqual(summary["verdicts"], {"runs_with_verdict": 1,
                                               "material_disagreement": {"true": 1, "false": 0}, "labeled": 1})
        groups = {(g["harness"], g["model"]): g for g in summary["by_participant"]}
        fable = groups[("claude-code", "claude-fable-5-1")]
        self.assertEqual((fable["verdicts"], fable["selected"], fable["disputed_right"], fable["disputed_wrong"],
                          fable["truth_wins"]), (1, 1, 2, 0, 1))
        sol = groups[("codex", "gpt-6-sol")]
        self.assertEqual((sol["verdicts"], sol["selected"], sol["disputed_right"], sol["disputed_wrong"],
                          sol["truth_wins"]), (1, 0, 0, 2, 0))
        self.assertEqual(groups[("codex", "gpt-x")]["verdicts"], 0)

    def test_participant_aggregate_groups_by_harness_and_model(self):
        groups = {(g["harness"], g["model"]): g for g in self.summary()["thabto"]["by_participant"]}
        claude = groups[("claude-code", "claude-sonnet-5")]
        self.assertEqual((claude["runs"], claude["failed"]), (1, 0))
        self.assertAlmostEqual(claude["mean_minutes"]["attempt"], 1.5)
        self.assertAlmostEqual(claude["mean_cost_usd"], 4.5)
        codex = groups[("codex", "gpt-x")]
        self.assertEqual((codex["runs"], codex["failed"]), (2, 1))
        self.assertAlmostEqual(codex["mean_minutes"]["attempt"], 1.5)  # (2.0 + 1.0) / 2
        self.assertIsNone(codex["mean_cost_usd"])
        # The failed run's Claude participant is keyed by its alias because no output resolved it.
        self.assertEqual(groups[("claude-code", "opus")]["failed"], 1)
        self.assertIn(("pi", "gpt-6-sol"), groups)

    def test_delarbitrate_runs_and_judge_selection(self):
        summary = self.summary()["delarbitrate"]
        runs = {run["run_id"]: run for run in summary["runs"]}
        complete = runs["d1-complete"]
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(complete["selected"], "codex")
        self.assertEqual(complete["candidates"], {"claude": "claude-sonnet-5", "codex": "gpt-5.6-terra"})
        self.assertEqual(complete["judge_model"], "gpt-5.6-sol")
        self.assertTrue(complete["material_disagreement"])
        self.assertAlmostEqual(complete["minutes"], 3.0)
        self.assertEqual((complete["launches"], complete["retries"]), (5, 1))
        self.assertEqual(runs["d2-needs-human"]["status"], "needs_human")
        self.assertIsNone(runs["d2-needs-human"]["material_disagreement"])
        self.assertEqual(runs["d3-aborted"]["status"], "incomplete")
        self.assertEqual(summary["counts"], {"runs": 3, "complete": 1, "needs_human": 1, "blocked": 0, "incomplete": 1})
        self.assertEqual(summary["selected"], {"codex": 1})
        self.assertEqual(summary["material_disagreement"], {"true": 1, "false": 0, "unknown": 2})

    def test_text_output_lists_runs_and_aggregates(self):
        result = self.run_stats()
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ("THABTO runs", "20260910T171439Z-aaaaaaaaaaaa", "claude-sonnet-5", "Delarbitrate runs",
                     "d1-complete", "codex 1", "unreadable", "20260912T000000Z-dddddddddddd",
                     "verdicts: 1 runs", "ground truth labeled 1"):
            self.assertIn(text, result.stdout)

    def test_missing_default_state_is_empty_but_explicit_missing_path_is_an_error(self):
        env = dict(os.environ, XDG_STATE_HOME=str(Path(self.temp.name) / "absent"))
        result = subprocess.run([sys.executable, str(STATS), "--json"], text=True, capture_output=True,
                                timeout=30, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["thabto"]["counts"]["runs"], 0)
        self.assertEqual(summary["delarbitrate"]["counts"]["runs"], 0)
        result = self.run_stats("--thabto-state", str(Path(self.temp.name) / "absent"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absent", result.stderr)


if __name__ == "__main__":
    unittest.main()
