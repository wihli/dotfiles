#!/usr/bin/env python3
"""Label THABTO runs with two independent read-only judges. Python 3.10+.

Each run needs a label-evidence.md the coordinator gathered. A Claude Code judge and a
Codex judge rule in parallel; the run is labeled only when both settle it the same way.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
from threading import Event
import uuid

from thabto import run_stage
from thabto_finish import ANSWER_GRADES, VerdictError, label, load_json, participants_of


EVIDENCE = "label-evidence.md"
GRADES = tuple(grade for grade in ANSWER_GRADES if grade != "unknown")

RULES = """You are a THABTO label judge. Work read-only: leave every file and system unchanged,
and do not invoke THABTO or other agents.

Decide three things about a finished THABTO run from independent evidence only:
1. outcome: which participant the real outcome proved right on the claims that divided
   them: a participant name, "both", or "neither".
2. answer: how the real outcome grades the coordinator's final answer: "correct",
   "partly", or "wrong".
3. attempts: how the real outcome grades each participant's first attempt, written
   before any review: "correct", "partly", or "wrong". An attempt is what the user
   would have received from that model alone, so grade it on its own claims and
   recommendations, not on corrections that arrived later.

Independent evidence means facts in the evidence file: metrics, logs, merge state, a
confirmed root cause, or the user adopting a position. The participants' answers, the
reviews, and the coordinator's synthesis and rulings are opinions under test, never
evidence. Judge each position against what the evidence shows happened. A participant
who only doubted a claim ("not proven") was not right about it if the claim proved true;
the participant who asserted it was. Compare the final answers, which may have changed
position after review. The user adopting a position counts even when the record does not
say what prompted it.

A run is settled once independent evidence decides at least one claim that divided the
participants, or the main finding of the coordinator's answer. Rule on the claims that
have evidence and name the claims still open in your reason; open claims alone do not
make the run unsettled. Return settled false only when no dividing claim and no main
finding has evidence: an unsettled run stays open for a later pass, and a wrong label
corrupts the record.

End your reply with one fenced JSON block, either
{"settled": true, "outcome": "<name|both|neither>", "answer": "<correct|partly|wrong>", "attempts": {"<name>": "<correct|partly|wrong>", ...}, "reason": "<one or two sentences citing the evidence>"}
or
{"settled": false, "reason": "<what is missing>"}
"""


def judge_prompt(run, names):
    metadata = load_json(run / "run.json", "run.json")
    verdict = load_json(run / "verdict.json", "verdict")
    finals = metadata.get("final_answers") or {}
    parts = [RULES, f"Participants: {', '.join(names)}.", "\n# Task the participants received\n",
             (run / "task.md").read_text(encoding="utf-8")]
    for name in names:
        path = run / "attempt" / name / "answer.md"
        text = path.read_text(encoding="utf-8") if path.exists() else "(no attempt recorded)"
        parts += [f"\n# First attempt of participant {name} (before review)\n", text]
    for name in names:
        path = run / finals.get(name, f"revision/{name}/answer.md")
        text = path.read_text(encoding="utf-8") if path.exists() else "(no final answer recorded)"
        parts += [f"\n# Final answer of participant {name}\n", text]
    parts += ["\n# Coordinator's final answer (the answer to grade)\n", (run / "synthesis.md").read_text(encoding="utf-8"),
              "\n# Coordinator's claim rulings (opinions, not evidence)\n",
              json.dumps(verdict.get("claims"), indent=2),
              "\n# Evidence gathered for labeling\n", (run / EVIDENCE).read_text(encoding="utf-8")]
    return "\n".join(parts) + "\n"


def parse_ruling(answer, names):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", answer, flags=re.S)
    if not blocks:
        raise ValueError("no fenced JSON ruling at the end of the reply")
    ruling = json.loads(blocks[-1])
    if not isinstance(ruling, dict) or not isinstance(ruling.get("settled"), bool):
        raise ValueError(f"ruling needs a boolean 'settled': {blocks[-1][:200]}")
    if not isinstance(ruling.get("reason"), str) or not ruling["reason"].strip():
        raise ValueError("ruling needs a non-empty 'reason'")
    if ruling["settled"]:
        outcomes = (*names, "both", "neither")
        if ruling.get("outcome") not in outcomes:
            raise ValueError(f"outcome {ruling.get('outcome')!r} is not one of {list(outcomes)}")
        if ruling.get("answer") not in GRADES:
            raise ValueError(f"answer {ruling.get('answer')!r} is not one of {list(GRADES)}")
        attempts = ruling.get("attempts")
        if (not isinstance(attempts, dict) or set(attempts) != set(names)
                or any(grade not in GRADES for grade in attempts.values())):
            raise ValueError(f"attempts must grade each participant {names} as one of {list(GRADES)}; "
                             f"got {attempts!r}")
    return ruling


def record_attempt_grades(run, rulings, names):
    """Store each participant's attempt grade where both settled judges agree. The grades
    live beside ground_truth so relabeling never drops them."""
    if not all(r["settled"] for r in rulings):
        return ""
    agreed = {name: rulings[0]["attempts"][name] for name in names
              if rulings[0]["attempts"][name] == rulings[1]["attempts"][name]}
    if agreed:
        verdict = load_json(run / "verdict.json", "verdict")
        verdict["attempt_grades"] = {**(verdict.get("attempt_grades") or {}), **agreed}
        (run / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    shown = [f"{name}={agreed[name]}" if name in agreed else f"{name} split" for name in names]
    return "; attempts " + "; ".join(shown)


def describe(judge, ruling):
    if not ruling["settled"]:
        return f"{judge}: unsettled; {ruling['reason']}"
    attempts = ",".join(f"{name}:{grade}" for name, grade in ruling["attempts"].items())
    return f"{judge}: outcome={ruling['outcome']} answer={ruling['answer']} attempts={attempts}; {ruling['reason']}"


def judge_run(run, judges, args, cancelled):
    names = list(participants_of(load_json(run / "run.json", "run.json")))
    verdict = load_json(run / "verdict.json", "verdict")
    existing = verdict.get("ground_truth") if isinstance(verdict.get("ground_truth"), dict) else None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:6]
    folder = run / "labeling" / stamp
    prompt = judge_prompt(run, names)
    records = {}
    args.workspace = run
    answers, errors = run_stage("judge", {name: prompt for name in judges}, judges, args, folder, cancelled, records)
    rulings, problems = {}, [f"{name}: {error}" for name, error in errors.items()]
    for name, answer in answers.items():
        try:
            rulings[name] = parse_ruling(answer, names)
        except ValueError as error:
            problems.append(f"{name}: {error}")
    first, second = (rulings.get(name) for name in judges)
    if problems:
        decision, line = "failed", "FAILED " + "; ".join(problems)
    elif not first["settled"] and not second["settled"]:
        decision, line = "unsettled", "unsettled (both judges)"
    elif (first["settled"] and second["settled"] and first["outcome"] == second["outcome"]
          and first["answer"] == second["answer"]):
        # An "unknown" label records that nothing had settled the run, so agreement may replace it.
        # Any other recorded outcome or answer grade stands; the user decides a conflict.
        held = existing if existing and existing.get("outcome") != "unknown" else None
        if held and held.get("outcome") != first["outcome"]:
            decision = "disagree"
            line = f"DISAGREE judges agree on outcome={first['outcome']} but existing label {held.get('outcome')} stands"
        elif held and held.get("answer") and held["answer"] != first["answer"]:
            decision = "disagree"
            line = (f"DISAGREE judges agree on answer={first['answer']} but existing answer grade "
                    f"{held['answer']} stands")
        elif held and held.get("answer") == first["answer"]:
            decision, line = "confirmed", f"confirmed outcome={first['outcome']} answer={first['answer']}"
        else:
            decision = "labeled"
            agreed = " ".join(describe(f"{name} ({judges[name]['model']})", rulings[name]) for name in judges)
            note = f"Dual judges agreed. {agreed}"
            if existing and existing.get("note"):
                note = f"{existing['note']}\n{note}"
            label(run, first["outcome"], first["answer"], note)
            line = f"labeled outcome={first['outcome']} answer={first['answer']}"
    else:
        decision, line = "disagree", "DISAGREE"
    if decision != "failed":
        line += record_attempt_grades(run, [first, second], names)
    if decision in ("disagree", "unsettled"):
        line += "".join(f"\n    {describe(name, rulings[name])}" for name in judges)
    (folder / "result.json").write_text(json.dumps(
        {"decision": decision, "judges": {name: {"model": judges[name]["model"], "ruling": rulings.get(name)}
                                          for name in judges},
         "problems": problems, "stages": records}, indent=2) + "\n", encoding="utf-8")
    print(f"{run.name}: {line}", flush=True)
    return decision


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, action="append", required=True, help="Run directory. Repeatable.")
    parser.add_argument("--claude-model", default="claude-opus-5-5")
    parser.add_argument("--codex-model", default="gpt-6-sol")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--timeout", type=float, default=600, help="Seconds per judge (default: 600).")
    parser.add_argument("--claude-executable", default="claude")
    parser.add_argument("--codex-executable", default="codex")
    args = parser.parse_args()
    if os.environ.get("THABTO_CHILD") == "1":
        parser.error("Recursive invocation refused: a provider child cannot launch THABTO labeling.")
    args.run = [run.resolve() for run in args.run]
    for run in args.run:
        for needed in ("run.json", "task.md", "synthesis.md", "verdict.json", EVIDENCE):
            if not (run / needed).is_file():
                parser.error(f"{run / needed} is missing; gather evidence into {EVIDENCE} as LABELING.md describes.")
    args.judges = {}
    for name, harness, model in (("claude", "claude-code", args.claude_model), ("codex", "codex", args.codex_model)):
        executable = getattr(args, f"{name}_executable")
        resolved = shutil.which(executable)
        if not resolved:
            parser.error(f"Executable {executable!r} not found; install {harness} or set --{name}-executable.")
        args.judges[name] = {"name": name, "harness": harness, "model": model, "effort": args.effort,
                             "executable": str(Path(resolved).absolute())}
    return args


def main():
    args = parse_args()
    cancelled = Event()
    signal.signal(signal.SIGINT, lambda *_: cancelled.set())
    signal.signal(signal.SIGTERM, lambda *_: cancelled.set())
    decisions = []
    for run in args.run:
        if cancelled.is_set():
            break
        try:
            decisions.append(judge_run(run, args.judges, args, cancelled))
        except (OSError, ValueError, VerdictError) as error:
            print(f"{run.name}: FAILED {error}", flush=True)
            decisions.append("failed")
    counts = {d: decisions.count(d) for d in ("labeled", "confirmed", "unsettled", "disagree", "failed")}
    print("Summary: " + ", ".join(f"{d} {n}" for d, n in counts.items()), flush=True)
    return 130 if cancelled.is_set() else (1 if counts["failed"] else 0)


if __name__ == "__main__":
    sys.exit(main())
