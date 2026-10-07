# THABTO — Two Heads Are Better Than One

THABTO gives one read-only question to two or more AI models. Each model answers on its own, reviews another model's answer, and then revises its answer. The agent that started the run (the coordinator) reads the results and writes one final answer. It also records which claims the models disagreed on and how it ruled on each claim, so you can compare models over time.

`SKILL.md` holds the instructions that the coordinator agent follows. This file explains the tool for people.

## Start a run

Name THABTO in your request to Claude Code or Codex:

> use thabto to investigate why the nightly export job stalls

> use thabto to review the retry logic in `scripts/deploy.py`

The coordinator writes your request and the relevant context to a task file, runs the driver, and reports progress. A run with the default models takes about 10–20 minutes. THABTO starts only when you name it.

THABTO is read-only. Each model can read local files in the workspace. Each model cannot edit files, run shell commands, use MCP servers, or reach the network. For implementation work, use THABTO to investigate or design the change, then implement it in a normal session.

## What a run does

1. **Attempt.** Each participant answers the task in parallel. No participant sees another participant's answer.
2. **Review.** The driver shuffles the participants into a ring. Each participant reviews the next participant's attempt and lists errors and omissions. With two participants, they review each other.
3. **Revision.** Each participant that received a review revises its own answer. It can accept or reject each correction.
4. **Synthesis.** The coordinator reads the final answers, goes back to the attempts and reviews when it must settle a claim, and writes one answer. Agreement between models counts as zero evidence; the coordinator rules on each claim from the sources. For each claim the evidence cannot settle yet, the answer names the check that would settle it.
5. **Verdict.** The coordinator records a `verdict.json` file. For each claim that decided the outcome, the file stores each participant's position (`asserts`, `disputes`, or `silent`) and the coordinator's ruling:

   | Ruling | Meaning |
   |---|---|
   | `supported` | Evidence shows the claim holds |
   | `rejected` | Evidence contradicts the claim |
   | `unresolved` | The evidence at hand cannot settle the claim. The verdict records the check that would settle it in `settle_by` |

   A claim that is plausible but unproven is `unresolved`. The finish script refuses a `rejected` ruling without evidence.

Each stage starts a fresh process for each participant. A failed or timed-out participant drops out of the later stages. The run continues if at least two attempts succeeded.

## Participants

| Harness | Models | Read-only controls |
|---|---|---|
| Claude Code | Claude | Plan mode; tools limited to Read, Glob, Grep; no MCP servers |
| Codex | OpenAI | Codex `read-only` sandbox; no MCP servers |
| OpenCode | OpenAI only (`openai/…`) | `thabto-child` agent in `harness/opencode.json` |
| Pi | OpenAI only (`openai-codex/…`) | Tools limited to read, grep, find, ls; offline; no extensions |

Claude runs only in Claude Code, because Anthropic's terms limit Claude subscription sign-in to Anthropic's own apps. The driver rejects a Claude model on OpenCode or Pi, and it removes Anthropic credentials from the environment of those harnesses.

The default pair is `claude-opus-5-5` and `gpt-6-sol` at `high` effort. For a hard task, ask for the frontier pair (`fable` and `gpt-6-astra`). To run more than two participants, or to compare harnesses with the same model, ask for specific participants, for example "use thabto with codex, opencode, and pi on gpt-6-sol".

## Read the scoreboard

```sh
python3 ~/.local/share/skills/thabto/scripts/thabto_stats.py
```

The report lists every run and the time and cost of each stage. The `final answer` line counts how the real outcome graded THABTO's answers: `correct`, `partly`, `wrong`, `unknown`, or `ungraded` for labels recorded before answers were graded. This line measures THABTO itself.

A per-model table follows. Its columns are:

| Column | Meaning |
|---|---|
| `runs` / `failed` | Runs the model took part in, and runs where it failed at some stage |
| `verdicts` | Runs with a recorded verdict |
| `selected` | Runs where the coordinator built its answer mainly on this model's answer. Most runs record `merged` |
| `right/wrong-on-disputed` | On claims where the models disagreed, how often this model's position matched the coordinator's ruling. Only rulings based on evidence count |
| `truth-wins` | Labeled runs where the real outcome showed this model, or both models, to be right |

`right/wrong` measures agreement with the coordinator, which is itself a model and can be wrong. `truth-wins` measures agreement with what actually happened. Use `truth-wins` to decide which model is more accurate.

Add `--json` for machine-readable output.

## Label the real outcome

After the real answer is known, such as a merged fix, a confirmed root cause, or a metric that settles the question, record it on the run:

```sh
python3 ~/.local/share/skills/thabto/scripts/thabto_finish.py --pending
python3 ~/.local/share/skills/thabto/scripts/thabto_finish.py \
  --run ~/.local/state/thabto/<run-id> --label codex --answer correct \
  --note "PR 1234 merged codex's fix"
```

`--pending` lists runs that have no label or no answer grade yet, with the claims the models disagreed on. `--label` says which participant the outcome proved right: a participant name, `both`, `neither`, or `unknown`. `--answer` grades the coordinator's final answer, which is what you received: `correct`, `partly`, `wrong`, or `unknown`. A new label replaces the old label and note, so repeat the note when you add a grade to an older label. Label from independent facts such as metrics, logs, or merge state, or from the position you adopted. Use `unknown` when nothing settled the question. Another model's opinion is never a label.

## Run files

Each run is a private directory under `~/.local/state/thabto/<run-id>/` (or `$XDG_STATE_HOME/thabto/`):

| Path | Contents |
|---|---|
| `task.md` | The task each participant received |
| `run.json` | Participants, review ring and seed, status, and time and exit code for each stage |
| `attempt/<name>/`, `review/<name>/`, `revision/<name>/` | `prompt.md`, `command.json`, raw `stdout.log` and `stderr.log`, `answer.md`, and `error.txt` on failure |
| `synthesis-prompt.md` | The list of final answers that the coordinator reads |
| `synthesis.md`, `verdict.json` | The coordinator's answer and verdict, after synthesis |

A run's `status` is `running`, `awaiting_synthesis`, `synthesized`, `failed`, or `cancelled`. A run stays at `awaiting_synthesis` until the coordinator records a verdict.

## Source files

| File | Purpose |
|---|---|
| `SKILL.md` | Instructions for the coordinator agent |
| `scripts/thabto.py` | Driver: runs the attempt, review, and revision stages |
| `scripts/thabto_finish.py` | Validates and stores the synthesis and verdict; records labels |
| `scripts/thabto_stats.py` | Reads all runs and prints the scoreboard |
| `harness/opencode.json` | Read-only agent definition for OpenCode |

To add a harness, add one entry to `HARNESSES` in `scripts/thabto.py`. The entry gives the command, the function that reads the final answer, and the credentials to remove.

Edit the source in `wihli-dotfiles/skills/.local/share/skills/thabto/`, then run `./install.sh`. Run the tests from the repository root:

```sh
python3 -m unittest tests/test_thabto.py tests/test_thabto_finish.py tests/test_thabto_stats.py
```
