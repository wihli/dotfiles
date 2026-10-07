#!/usr/bin/env python3
"""Record a THABTO synthesis and verdict, or label a run's ground truth. Python 3.10+."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


VERDICT_SCHEMA = 2
POSITIONS = ("asserts", "disputes", "silent")
# The coordinator's ruling on each claim. "rejected" means evidence contradicts the claim;
# a claim that is merely unproven is "unresolved", or the scorecard would credit whoever
# doubted it even when the claim later proves true.
DISPOSITIONS = ("supported", "rejected", "unresolved")
BASES = ("evidence", "preference", "unverified")
# How the real outcome graded the coordinator's final answer.
ANSWER_GRADES = ("correct", "partly", "wrong", "unknown")
LEGACY_PARTICIPANTS = ("claude", "codex")


class VerdictError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path, what):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise VerdictError(f"Cannot read {what} {path}: {error.strerror}.") from None
    except ValueError as error:
        raise VerdictError(f"{what} {path} is not valid JSON: {error}.") from None


def participants_of(metadata):
    names = [p.get("name") for p in metadata.get("participants") or [] if isinstance(p, dict)]
    return tuple(name for name in names if name) or LEGACY_PARTICIPANTS


def expect(condition, message):
    if not condition:
        raise VerdictError(message)


def validate_verdict(verdict, participants):
    expect(isinstance(verdict, dict), "Verdict must be a JSON object.")
    expect(verdict.get("schema") == VERDICT_SCHEMA,
           f"verdict.schema is {verdict.get('schema')!r}; this script writes schema {VERDICT_SCHEMA}.")
    coordinator = verdict.get("coordinator")
    expect(isinstance(coordinator, dict) and all(isinstance(coordinator.get(k), str) and coordinator[k].strip()
                                                   for k in ("harness", "model")),
           "verdict.coordinator must be {\"harness\": <str>, \"model\": <str>} naming who synthesized.")
    expect(isinstance(verdict.get("material_disagreement"), bool),
           "verdict.material_disagreement must be true or false.")
    backbones = set(participants) | {"merged", "none"}
    expect(verdict.get("selected_backbone") in backbones,
           f"verdict.selected_backbone is {verdict.get('selected_backbone')!r}; use one of {sorted(backbones)}.")
    expect(verdict.get("ground_truth") is None,
           "verdict.ground_truth must be null at synthesis time; add it later with --label.")
    claims = verdict.get("claims")
    expect(isinstance(claims, list) and claims, "verdict.claims must be a non-empty list of claims.")
    seen = set()
    disputed = False
    for index, claim in enumerate(claims):
        where = f"verdict.claims[{index}]"
        expect(isinstance(claim, dict), f"{where} must be an object.")
        claim_id = claim.get("id")
        expect(isinstance(claim_id, str) and claim_id.strip(), f"{where}.id must be a non-empty string.")
        expect(claim_id not in seen, f"{where}.id {claim_id!r} is duplicated; claim ids must be unique.")
        seen.add(claim_id)
        expect(isinstance(claim.get("text"), str) and claim["text"].strip(), f"{where}.text must be a non-empty string.")
        positions = claim.get("positions")
        expect(isinstance(positions, dict) and set(positions) == set(participants),
               f"{where}.positions must have exactly one entry per participant {list(participants)}; "
               f"got {sorted(positions) if isinstance(positions, dict) else positions!r}.")
        for name, position in positions.items():
            expect(position in POSITIONS, f"{where}.positions[{name!r}] is {position!r}; use one of {list(POSITIONS)}.")
        expect(claim.get("disposition") in DISPOSITIONS,
               f"{where}.disposition is {claim.get('disposition')!r}; use one of {list(DISPOSITIONS)}.")
        expect(claim.get("basis") in BASES, f"{where}.basis is {claim.get('basis')!r}; use one of {list(BASES)}.")
        expect(claim["disposition"] != "rejected" or claim["basis"] == "evidence",
               f"{where} is rejected with basis {claim['basis']!r}; reject only with evidence that contradicts "
               "the claim, and mark an unproven claim unresolved.")
        if claim["disposition"] == "unresolved":
            settle_by = claim.get("settle_by")
            expect(isinstance(settle_by, str) and settle_by.strip(),
                   f"{where}.settle_by must name the check that would settle this unresolved claim.")
        disputed = disputed or ({"asserts", "disputes"} <= set(positions.values()))
    expect(verdict["material_disagreement"] == disputed,
           f"verdict.material_disagreement is {verdict['material_disagreement']}, but the claims "
           f"{'do' if disputed else 'do not'} contain a claim one participant asserts and another disputes.")


def load_run(run):
    metadata = load_json(run / "run.json", "run.json")
    expect(isinstance(metadata, dict), f"{run / 'run.json'} must contain an object.")
    return metadata


def finish(run, synthesis_path, verdict_path):
    metadata = load_run(run)
    status = metadata.get("status")
    expect(status in ("awaiting_synthesis", "synthesized"),
           f"Run status is {status!r}; only an exchange that finished all stages can be synthesized.")
    existing = run / "verdict.json"
    if existing.exists():
        previous = load_json(existing, "existing verdict")
        expect(not (isinstance(previous, dict) and previous.get("ground_truth")),
               f"{existing} already carries a ground-truth label; edit it by hand instead of re-finishing.")
    try:
        synthesis = synthesis_path.read_text(encoding="utf-8")
    except OSError as error:
        raise VerdictError(f"Cannot read synthesis {synthesis_path}: {error.strerror}.") from None
    expect(synthesis.strip(), f"Synthesis file {synthesis_path} is empty.")
    verdict = load_json(verdict_path, "verdict")
    validate_verdict(verdict, participants_of(metadata))
    verdict["recorded_at"] = utc_now()
    (run / "synthesis.md").write_text(synthesis, encoding="utf-8")
    existing.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    metadata["status"] = "synthesized"
    metadata["synthesized_at"] = verdict["recorded_at"]
    (run / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded synthesis.md and verdict.json; status synthesized: {run}")


def label(run, outcome, answer, note):
    metadata = load_run(run)
    outcomes = set(participants_of(metadata)) | {"both", "neither", "unknown"}
    expect(outcome in outcomes, f"Label {outcome!r} is not one of {sorted(outcomes)}.")
    expect(answer in ANSWER_GRADES, f"Answer grade {answer!r} is not one of {list(ANSWER_GRADES)}.")
    verdict_path = run / "verdict.json"
    expect(verdict_path.exists(), f"{verdict_path} does not exist; record the synthesis and verdict first.")
    verdict = load_json(verdict_path, "verdict")
    verdict["ground_truth"] = {"outcome": outcome, "answer": answer, "note": note, "labeled_at": utc_now()}
    verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(f"Labeled ground truth {outcome!r}, final answer {answer!r}: {run}")


def pending(state):
    """List runs whose verdict lacks a ground-truth label or an answer grade, with the
    claims that divided the participants, so a human can label them in one pass."""
    waiting = 0
    for run in sorted(state.iterdir()) if state.is_dir() else []:
        verdict = read_optional_json(run / "verdict.json")
        if not isinstance(verdict, dict):
            continue
        truth = verdict.get("ground_truth")
        if isinstance(truth, dict) and truth.get("answer"):
            continue
        waiting += 1
        task = (run / "task.md").read_text(encoding="utf-8", errors="replace") if (run / "task.md").exists() else ""
        labeled = f"  labeled={truth.get('outcome')}, answer ungraded" if isinstance(truth, dict) else ""
        print(f"\n{run.name}  selected={verdict.get('selected_backbone')}  "
              f"disagreement={verdict.get('material_disagreement')}{labeled}")
        print("  task: " + " ".join(task.split())[:240])
        for claim in verdict.get("claims") or []:
            positions = claim.get("positions") or {}
            if {"asserts", "disputes"} <= set(positions.values()):
                who = ", ".join(f"{name}={position}" for name, position in positions.items())
                print(f"  disputed {claim.get('id')} [{claim.get('disposition')}]: {claim.get('text')}  ({who})")
    print(f"\n{waiting} run(s) await a label or an answer grade." if waiting
          else "No runs await a label or an answer grade.")


def read_optional_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def parse_args():
    state_home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="THABTO run directory.")
    parser.add_argument("--synthesis", type=Path, help="File holding the coordinator's final answer.")
    parser.add_argument("--verdict", type=Path, help="JSON file holding the structured verdict.")
    parser.add_argument("--label", help="Ground-truth outcome: a participant name, both, neither, or unknown.")
    parser.add_argument("--answer", help=f"With --label: how the outcome graded the final answer "
                                          f"({', '.join(ANSWER_GRADES)}).")
    parser.add_argument("--note", default="", help="What settled the ground truth (used with --label).")
    parser.add_argument("--pending", action="store_true", help="List runs still awaiting a ground-truth label or an answer grade.")
    parser.add_argument("--state", type=Path, default=state_home / "thabto",
                        help="THABTO run directory root for --pending (default: $XDG_STATE_HOME/thabto).")
    args = parser.parse_args()
    if args.pending:
        if args.run or args.synthesis or args.verdict or args.label or args.answer:
            parser.error("--pending takes no other action; pass it alone (optionally with --state).")
        args.state = args.state.resolve()
        if not args.state.is_dir():
            parser.error(f"State {str(args.state)!r} is not a directory.")
        return args
    recording = args.synthesis is not None or args.verdict is not None
    if recording and (args.synthesis is None or args.verdict is None or args.label):
        parser.error("Pass both --synthesis and --verdict to record a synthesis, or --label alone to label one.")
    if not recording and not args.label:
        parser.error("Pass --synthesis with --verdict, --label, or --pending.")
    if args.label and not args.answer:
        parser.error("--label needs --answer: grade the final answer against the outcome "
                     f"({', '.join(ANSWER_GRADES)}).")
    if args.answer and not args.label:
        parser.error("--answer is used with --label.")
    if args.run is None:
        parser.error("--run is required; pass the run path the driver printed.")
    args.run = args.run.resolve()
    if not args.run.is_dir():
        parser.error(f"Run {str(args.run)!r} is not a directory; pass the run path the driver printed.")
    return args


def main():
    args = parse_args()
    try:
        if args.pending:
            pending(args.state)
        elif args.label:
            label(args.run, args.label, args.answer, args.note)
        else:
            finish(args.run, args.synthesis.resolve(), args.verdict.resolve())
    except VerdictError as error:
        print(f"thabto_finish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
