# Labeling THABTO runs

Use when the user asks to label THABTO runs ("label pending THABTO runs", "grade the THABTO answers"). The procedure gathers independent evidence once, has a Claude Code judge and a Codex judge rule on it independently, and records a label only when both judges agree. The user decides every disagreement.

An explicit labeling request authorizes sending each run's files and the gathered evidence to both providers, as a THABTO request does. Never include secret values.

## 1. List the runs

```sh
python3 "<skill-directory>/scripts/thabto_finish.py" --pending
```

It prints each run that lacks a label or an answer grade, with the claims that divided the participants. Older runs (schema 1) have no `settle_by`; read their task, synthesis, and disputed claims to decide what would settle them.

## 2. Gather evidence for each run

Read the run's `task.md`, `synthesis.md`, and `verdict.json`. For each disputed claim and each `settle_by` check, fetch facts with the owning read-only skill: `pup` for Datadog, `gh` for PR merge state and diffs, `slack` for threads, `jira` for tickets, `glean` for docs. Prior evidence reports in `centcom/context/thabto-ground-truth-evidence-*.md` may already cover a run; re-verify a fact before reusing it when it could have changed.

Write `<run>/label-evidence.md`:

- One section per disputed claim, plus one for the final answer as a whole.
- Facts only, each with a source locator: the query and time window, the PR URL with merge state and date, the Slack permalink, the commit SHA. Quote short excerpts.
- Facts that favor either side. You are gathering, not judging; leave out your own ruling.
- Searches that found nothing, named as such, so the judges can tell "no evidence" from "not searched".
- The user's own adoption of a position counts as evidence; cite where it happened.

Never use a participant's answer, a review, the coordinator's synthesis, or any model's opinion as evidence.

If nothing can settle a run yet, skip it; it stays pending for a later pass.

## 3. Run the judges

```sh
python3 "<skill-directory>/scripts/thabto_label.py" --run "<run>" [--run "<run>" ...]
```

Defaults: `claude-opus-5-5` and `gpt-6-sol` at `high` effort, 600 s per judge. A run counts as settled once evidence decides at least one dividing claim or the answer's main finding; the judges rule on the claims that have evidence and name the ones still open. Both judges run read-only with no network and no MCP, the same isolation as THABTO participants. Each judge receives the task, every participant's final answer, the synthesis, the claim rulings, and `label-evidence.md`, and returns a ruling: settled or unsettled, an outcome, an answer grade, and a grade for each participant's first attempt (its answer before review, which is what that model alone would have given).

Per run, the script prints one decision and saves the judges' raw output under `<run>/labeling/<stamp>/`:

| Decision | Meaning | Action |
|---|---|---|
| `labeled` | Both judges settled the run with the same outcome and answer grade. The script recorded the label with both judges' reasons as the note | None |
| `confirmed` | Both judges agree with the outcome and answer grade already recorded. Nothing changes | None |
| `unsettled` | Neither judge found evidence deciding any dividing claim or the answer's main finding | Leave pending; gather more evidence later |
| `DISAGREE` | The judges differ, one settled and one did not, or both contradict a recorded outcome or answer grade | Surface to the user |
| `FAILED` | A judge failed or returned a malformed ruling | Read `labeling/<stamp>/judge/<name>/error.txt` and stderr; rerun that run |

Attempt grades are recorded per participant wherever both settled judges agree, in `verdict.json` `attempt_grades`, whatever the label decision; relabeling keeps them. To grade the attempts of runs labeled before attempt grading existed, rerun the judges on them with their existing evidence file. An existing label is never overturned. On an older run that already has an outcome label, agreement on the same outcome adds the answer grade and keeps the earlier note. An `unknown` label records only that nothing had settled the run, so agreement replaces it.

## 4. Report to the user

List the labeled runs briefly. For each `DISAGREE`, show the run's question in one line, each judge's ruling and reason, and the evidence they rested on, then ask the user to decide. Record the user's decision:

```sh
python3 "<skill-directory>/scripts/thabto_finish.py" --run "<run>" --label <outcome> --answer <grade> --note "User decided: <reason>"
```

Do not post anything externally.
