#!/usr/bin/env python3
"""Summarize retained THABTO runs. Read-only. Python 3.10+."""

import argparse
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import sys


STAGES = ("attempt", "review", "revision")
# Runs written before participants were explicit name only a provider; these are the
# harnesses those providers always ran in.
LEGACY_HARNESS = {"claude": "claude-code", "codex": "codex"}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def started_at_from_run_id(run_id):
    try:
        return datetime.strptime(run_id[:16], "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def minutes_between(prompt, answer):
    if not answer.exists():
        return None
    return round((answer.stat().st_mtime - prompt.stat().st_mtime) / 60, 4)


def harness_report(harness, folder):
    """Model, cost, duration, and tokens that a harness wrote into its own output."""
    report = {"resolved_model": None, "cost_usd": None, "minutes": None, "tokens": None}
    stdout = folder / "stdout.log"
    if not stdout.exists():
        return report
    if harness == "claude-code":
        result = read_json(stdout)
        if isinstance(result, dict):
            usage = result.get("modelUsage")
            if isinstance(usage, dict) and usage:
                # Claude Code lists every model the session touched, including a cheap
                # utility model for side calls; the participant's model is the one that
                # carried the spend.
                report["resolved_model"] = max(
                    usage, key=lambda model: ((usage[model] or {}).get("costUSD") or 0,
                                              (usage[model] or {}).get("outputTokens") or 0))
            report["cost_usd"] = result.get("total_cost_usd")
            if isinstance(result.get("duration_ms"), (int, float)):
                report["minutes"] = round(result["duration_ms"] / 60000, 4)
    elif harness == "codex":
        for line in stdout.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "turn.completed":
                report["tokens"] = event.get("usage")
    return report


def participants_of(metadata):
    explicit = metadata.get("participants")
    if isinstance(explicit, list):
        return [{"name": p.get("name"), "harness": p.get("harness"), "requested_model": p.get("model"),
                 "effort": p.get("effort")} for p in explicit if isinstance(p, dict)]
    settings = metadata.get("settings") or {}
    return [{"name": provider, "harness": harness, "requested_model": settings.get(provider + "_model"),
             "effort": settings.get(provider + "_effort")} for provider, harness in LEGACY_HARNESS.items()]


def verdict_of(run, names):
    """Verdict facts plus a scorecard: on claims one participant asserted and another
    disputed, whoever sided with the coordinator's disposition was right."""
    verdict = read_json(run / "verdict.json")
    if not isinstance(verdict, dict):
        return None
    scorecard = {name: {"right": 0, "wrong": 0} for name in names}
    disputed = 0
    for claim in verdict.get("claims") or []:
        positions = claim.get("positions") or {}
        if not {"asserts", "disputes"} <= set(positions.values()):
            continue
        disputed += 1
        correct = {"supported": "asserts", "rejected": "disputes"}.get(claim.get("disposition"))
        if not correct:
            continue
        for name, position in positions.items():
            if name in scorecard and position != "silent":
                scorecard[name]["right" if position == correct else "wrong"] += 1
    truth = verdict.get("ground_truth") or {}
    return {
        "material_disagreement": verdict.get("material_disagreement"),
        "selected_backbone": verdict.get("selected_backbone"),
        "claims": len(verdict.get("claims") or []),
        "disputed_claims": disputed,
        "scorecard": scorecard,
        "ground_truth": truth.get("outcome") if isinstance(truth, dict) else None,
    }


def thabto_run(run):
    metadata = read_json(run / "run.json")
    if not isinstance(metadata, dict):
        return None
    participants = []
    for participant in participants_of(metadata):
        stages = {}
        resolved = None
        for name in STAGES:
            folder = run / name / (participant["name"] or "")
            if not (folder / "prompt.md").exists():
                continue
            report = harness_report(participant["harness"], folder)
            resolved = resolved or report["resolved_model"]
            answer = folder / "answer.md"
            recorded = ((metadata.get("stages") or {}).get(name) or {}).get(participant["name"]) or {}
            # Driver wall-clock covers the whole child process; harness self-reports and
            # file timestamps are fallbacks for runs recorded before the driver kept time.
            if isinstance(recorded.get("seconds"), (int, float)):
                minutes = round(recorded["seconds"] / 60, 4)
            elif report["minutes"] is not None:
                minutes = report["minutes"]
            else:
                minutes = minutes_between(folder / "prompt.md", answer)
            stages[name] = {
                "minutes": minutes,
                "outcome": recorded.get("outcome"),
                "answer_bytes": answer.stat().st_size if answer.exists() else None,
                "cost_usd": report["cost_usd"],
                "tokens": report["tokens"],
            }
        participants.append({**participant, "resolved_model": resolved, "stages": stages})
    return {
        "run_id": run.name,
        "started_at": started_at_from_run_id(run.name),
        "status": metadata.get("status"),
        "synthesized": (run / "synthesis.md").exists(),
        "verdict": verdict_of(run, [p["name"] for p in participants]),
        "error": metadata.get("error"),
        "participants": participants,
    }


def mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def by_participant(runs):
    groups = defaultdict(list)
    for run in runs:
        for participant in run["participants"]:
            key = (participant["harness"], participant["resolved_model"] or participant["requested_model"])
            groups[key].append((run, participant))
    rows = []
    for (harness, model), members in sorted(groups.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        verdicts = [(run["verdict"], p["name"]) for run, p in members if run["verdict"]]
        rows.append({
            "harness": harness, "model": model, "runs": len(members),
            "failed": sum(run["status"] == "failed" for run, _ in members),
            "mean_minutes": {name: mean(p["stages"].get(name, {}).get("minutes") for _, p in members)
                             for name in STAGES},
            "mean_cost_usd": mean(sum(s["cost_usd"] for s in p["stages"].values() if s["cost_usd"] is not None)
                                  if any(s["cost_usd"] is not None for s in p["stages"].values()) else None
                                  for _, p in members),
            "verdicts": len(verdicts),
            "selected": sum(v["selected_backbone"] == name for v, name in verdicts),
            "disputed_right": sum(v["scorecard"].get(name, {}).get("right", 0) for v, name in verdicts),
            "disputed_wrong": sum(v["scorecard"].get(name, {}).get("wrong", 0) for v, name in verdicts),
            "truth_wins": sum(v["ground_truth"] in (name, "both") for v, name in verdicts),
        })
    return rows


def thabto_summary(state):
    runs, unreadable = [], []
    for path in sorted(p for p in state.iterdir() if p.is_dir()) if state.is_dir() else []:
        run = thabto_run(path)
        (runs if run else unreadable).append(run or path.name)
    verdicts = [r["verdict"] for r in runs if r["verdict"]]
    return {
        "state": str(state),
        "counts": {"runs": len(runs), "synthesized": sum(r["synthesized"] for r in runs),
                   "failed": sum(r["status"] == "failed" for r in runs), "unreadable": len(unreadable)},
        "verdicts": {"runs_with_verdict": len(verdicts),
                     "material_disagreement": {"true": sum(v["material_disagreement"] is True for v in verdicts),
                                               "false": sum(v["material_disagreement"] is False for v in verdicts)},
                     "labeled": sum(v["ground_truth"] is not None for v in verdicts)},
        "runs": runs,
        "unreadable": unreadable,
        "by_participant": by_participant(runs),
    }


def fmt_minutes(value):
    return "-" if value is None else f"{value:.1f}"


def format_text(summary):
    lines = []
    thabto = summary["thabto"]
    c = thabto["counts"]
    lines.append(f"THABTO runs: {c['runs']} ({c['synthesized']} synthesized, {c['failed']} failed, "
                 f"{c['unreadable']} unreadable) in {thabto['state']}")
    for run in thabto["runs"]:
        names = ", ".join(f"{p['harness']}:{p['resolved_model'] or p['requested_model']}" for p in run["participants"])
        lines.append(f"  {run['run_id']}  {run['status']:<19} synth={'y' if run['synthesized'] else 'n'}  {names}")
        for p in run["participants"]:
            timing = "  ".join(f"{s}={fmt_minutes(p['stages'].get(s, {}).get('minutes'))}m" for s in STAGES)
            lines.append(f"      {p['harness']:<12} {timing}")
        if run["error"]:
            lines.append(f"      error: {run['error']}")
    for name in thabto["unreadable"]:
        lines.append(f"  {name}  unreadable (no run.json)")
    v = thabto["verdicts"]
    lines.append(f"  verdicts: {v['runs_with_verdict']} runs (material disagreement true {v['material_disagreement']['true']}, "
                 f"false {v['material_disagreement']['false']}; ground truth labeled {v['labeled']})")
    lines.append("")
    lines.append("By participant (harness, model): runs failed | mean minutes attempt/review/revision | mean cost | "
                 "verdicts selected right/wrong-on-disputed truth-wins")
    for g in thabto["by_participant"]:
        m = g["mean_minutes"]
        cost = "-" if g["mean_cost_usd"] is None else f"${g['mean_cost_usd']:.2f}"
        lines.append(f"  {g['harness']:<12} {str(g['model']):<24} {g['runs']:>4} {g['failed']:>6} | "
                     f"{fmt_minutes(m['attempt'])}/{fmt_minutes(m['review'])}/{fmt_minutes(m['revision'])} | {cost:>7} | "
                     f"{g['verdicts']:>3} {g['selected']:>3} {g['disputed_right']}/{g['disputed_wrong']} {g['truth_wins']}")
    return "\n".join(lines) + "\n"


def parse_args():
    state_home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thabto-state", type=Path, default=None,
                        help="THABTO run directory (default: $XDG_STATE_HOME/thabto).")
    parser.add_argument("--json", action="store_true", help="Emit the summary as JSON.")
    args = parser.parse_args()
    # A missing default is a fresh machine; a missing explicit path is a typo worth stopping on.
    if args.thabto_state is not None and not args.thabto_state.is_dir():
        parser.error(f"{args.thabto_state} is not a directory; pass an existing run directory or omit the flag.")
    args.thabto_state = (args.thabto_state or state_home / "thabto").resolve()
    return args


def main():
    args = parse_args()
    summary = {"thabto": thabto_summary(args.thabto_state)}
    sys.stdout.write(json.dumps(summary, indent=2) + "\n" if args.json else format_text(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
