import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FINISH = ROOT / "skills/.local/share/skills/thabto/scripts/thabto_finish.py"

VERDICT = {
    "schema": 2,
    "coordinator": {"harness": "claude-code", "model": "claude-fable-5-1"},
    "material_disagreement": True,
    "selected_backbone": "codex",
    "claims": [
        {"id": "c1", "text": "The sum query double-counts the shared queue.",
         "positions": {"claude": "asserts", "codex": "disputes"}, "disposition": "supported", "basis": "evidence"},
        {"id": "c2", "text": "The tuner applies one duration change twice.",
         "positions": {"claude": "silent", "codex": "asserts"}, "disposition": "unresolved", "basis": "unverified",
         "settle_by": "Tuner logs for one deploy show whether the change is applied once or twice."},
    ],
    "ground_truth": None,
}


class ThabtoFinishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="thabto finish ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "20260925T200247Z-929d77ae1000"
        self.run.mkdir()
        self.write_run({"schema": 2, "status": "awaiting_synthesis",
                        "participants": [{"name": "claude", "harness": "claude-code"},
                                         {"name": "codex", "harness": "codex"}]})
        self.synthesis = self.root / "answer.md"
        self.synthesis.write_text("Final answer.\n")

    def write_run(self, metadata):
        (self.run / "run.json").write_text(json.dumps(metadata))

    def run_json(self):
        return json.loads((self.run / "run.json").read_text())

    def finish(self, verdict=VERDICT, synthesis=None, raw=None):
        path = self.root / "verdict.json"
        path.write_text(raw if raw is not None else json.dumps(verdict))
        command = [sys.executable, str(FINISH), "--run", str(self.run),
                   "--synthesis", str(synthesis or self.synthesis), "--verdict", str(path)]
        return subprocess.run(command, text=True, capture_output=True, timeout=30)

    def label(self, outcome, note="", answer="correct"):
        command = [sys.executable, str(FINISH), "--run", str(self.run), "--label", outcome, "--note", note]
        if answer is not None:
            command += ["--answer", answer]
        return subprocess.run(command, text=True, capture_output=True, timeout=30)

    def test_finish_records_synthesis_verdict_and_status(self):
        result = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.run), result.stdout)
        self.assertEqual((self.run / "synthesis.md").read_text(), "Final answer.\n")
        verdict = json.loads((self.run / "verdict.json").read_text())
        self.assertEqual(verdict["claims"], VERDICT["claims"])
        self.assertRegex(verdict["recorded_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIsNone(verdict["ground_truth"])
        metadata = self.run_json()
        self.assertEqual(metadata["status"], "synthesized")
        self.assertEqual(metadata["synthesized_at"], verdict["recorded_at"])
        # Re-finishing an unlabeled run corrects it in place.
        corrected = copy.deepcopy(VERDICT)
        corrected["selected_backbone"] = "merged"
        self.assertEqual(self.finish(corrected).returncode, 0)
        self.assertEqual(json.loads((self.run / "verdict.json").read_text())["selected_backbone"], "merged")

    def test_invalid_verdicts_are_rejected_naming_the_field(self):
        cases = []

        def case(token, mutate):
            verdict = copy.deepcopy(VERDICT)
            mutate(verdict)
            cases.append((token, verdict))

        case("schema", lambda v: v.update(schema=1))
        case("coordinator", lambda v: v.update(coordinator={"harness": "claude-code"}))
        case("selected_backbone", lambda v: v.update(selected_backbone="gpt"))
        case("ground_truth", lambda v: v.update(ground_truth={"outcome": "codex"}))
        case("claims", lambda v: v.update(claims=[]))
        case("positions", lambda v: v["claims"][0]["positions"].pop("codex"))
        case("positions", lambda v: v["claims"][0]["positions"].update(pi="asserts"))
        case("positions['claude']", lambda v: v["claims"][0]["positions"].update(claude="agrees"))
        case("disposition", lambda v: v["claims"][0].update(disposition="maybe"))
        case("basis", lambda v: v["claims"][1].update(basis="vibes"))
        case("duplicated", lambda v: v["claims"][1].update(id="c1"))
        case("material_disagreement", lambda v: v.update(material_disagreement=False))
        # "Not proven" is unresolved; rejected means evidence contradicts the claim.
        case("contradicts", lambda v: v["claims"][0].update(disposition="rejected", basis="unverified"))
        case("contradicts", lambda v: v["claims"][0].update(disposition="rejected", basis="preference"))
        case("settle_by", lambda v: v["claims"][1].pop("settle_by"))
        case("settle_by", lambda v: v["claims"][1].update(settle_by="  "))
        for token, verdict in cases:
            with self.subTest(token=token):
                result = self.finish(verdict)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(token, result.stderr)
                self.assertFalse((self.run / "synthesis.md").exists())
                self.assertEqual(self.run_json()["status"], "awaiting_synthesis")
        result = self.finish(raw="not json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not valid JSON", result.stderr)

    def test_material_disagreement_false_requires_no_disputed_claim(self):
        verdict = copy.deepcopy(VERDICT)
        verdict["material_disagreement"] = False
        verdict["claims"][0]["positions"]["codex"] = "silent"
        self.assertEqual(self.finish(verdict).returncode, 0)

    def test_empty_synthesis_and_wrong_status_are_rejected(self):
        empty = self.root / "empty.md"
        empty.write_text("  \n")
        result = self.finish(synthesis=empty)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty", result.stderr)
        for status in ("running", "failed", "cancelled"):
            with self.subTest(status=status):
                self.write_run({"schema": 2, "status": status, "participants": []})
                result = self.finish()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(status, result.stderr)
                self.assertFalse((self.run / "synthesis.md").exists())

    def test_label_sets_ground_truth_and_blocks_refinish(self):
        result = self.label("codex")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verdict.json", result.stderr)
        self.assertEqual(self.finish().returncode, 0)
        self.assertNotEqual(self.label("gpt").returncode, 0)
        # The final answer is THABTO's product, so every label also grades it.
        result = self.label("codex", answer=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--answer", result.stderr)
        self.assertNotEqual(self.label("codex", answer="mostly").returncode, 0)
        result = self.label("codex", "Fix merged in PR 174300 matched codex's claim c1.", answer="partly")
        self.assertEqual(result.returncode, 0, result.stderr)
        truth = json.loads((self.run / "verdict.json").read_text())["ground_truth"]
        self.assertEqual((truth["outcome"], truth["answer"], truth["note"]),
                         ("codex", "partly", "Fix merged in PR 174300 matched codex's claim c1."))
        self.assertRegex(truth["labeled_at"], r"Z$")
        result = self.finish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ground-truth", result.stderr)

    def test_legacy_run_without_participants_expects_claude_and_codex(self):
        self.write_run({"status": "awaiting_synthesis", "settings": {"claude_model": "sonnet"}})
        self.assertEqual(self.finish().returncode, 0)
        verdict = copy.deepcopy(VERDICT)
        verdict["claims"][0]["positions"] = {"claude": "asserts", "pi": "disputes"}
        result = self.finish(verdict)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("['claude', 'codex']", result.stderr)

    def test_pending_lists_only_unlabeled_verdicts_with_disputed_claims(self):
        state = self.root / "state"
        unlabeled = state / "20260926T003110Z-aaaaaaaaaaaa"
        unlabeled.mkdir(parents=True)
        (unlabeled / "task.md").write_text("# User request (verbatim)\nInvestigate the   alert in   production.\n")
        (unlabeled / "verdict.json").write_text(json.dumps(VERDICT))
        labeled = state / "20260927T000000Z-bbbbbbbbbbbb"
        labeled.mkdir()
        done = copy.deepcopy(VERDICT)
        done["ground_truth"] = {"outcome": "codex", "answer": "correct", "note": "", "labeled_at": "2026-10-01T00:00:00Z"}
        (labeled / "verdict.json").write_text(json.dumps(done))
        # Labeled before answers were graded: listed so the answer grade can be added.
        ungraded = state / "20260927T120000Z-dddddddddddd"
        ungraded.mkdir()
        old = copy.deepcopy(VERDICT)
        old["ground_truth"] = {"outcome": "claude", "note": "", "labeled_at": "2026-10-01T00:00:00Z"}
        (ungraded / "verdict.json").write_text(json.dumps(old))
        (state / "20260928T000000Z-cccccccccccc").mkdir()  # no verdict yet
        result = subprocess.run([sys.executable, str(FINISH), "--pending", "--state", str(state)],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("20260926T003110Z-aaaaaaaaaaaa  selected=codex  disagreement=True", result.stdout)
        self.assertIn("task: # User request (verbatim) Investigate the alert in production.", result.stdout)
        self.assertIn("disputed c1 [supported]: The sum query double-counts the shared queue.  (claude=asserts, codex=disputes)",
                      result.stdout)
        self.assertNotIn("c2", result.stdout)  # not disputed: one side silent
        self.assertNotIn("bbbbbbbbbbbb", result.stdout)
        self.assertIn("20260927T120000Z-dddddddddddd  selected=codex  disagreement=True  labeled=claude, answer ungraded",
                      result.stdout)
        self.assertIn("2 run(s) await a label or an answer grade.", result.stdout)
        result = subprocess.run([sys.executable, str(FINISH), "--pending", "--state", str(state), "--label", "codex"],
                                text=True, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)

    def test_argument_combinations(self):
        for extra in (["--synthesis", str(self.synthesis)], ["--label", "codex", "--verdict", str(self.synthesis)], []):
            with self.subTest(extra=extra):
                result = subprocess.run([sys.executable, str(FINISH), "--run", str(self.run), *extra],
                                        text=True, capture_output=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, str(FINISH), "--run", str(self.root / "absent"), "--label", "codex",
                                 "--answer", "correct"],
                                text=True, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absent", result.stderr)


if __name__ == "__main__":
    unittest.main()
