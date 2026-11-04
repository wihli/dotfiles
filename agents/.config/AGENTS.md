# AGENTS.md

Eric Ihli owns this. Be concise, with enough context and reasoning to explain the decision.

## Authority and source ownership

- Explicit chat instructions take precedence over repo-local instructions, which take precedence over this file. Read the relevant skill for task-specific procedures and tool routing.
- Keep procedures in their skill, repository rules in that repository, and observations in its notes or memory. Treat feedback as situational unless Eric makes it general; preserve its trigger and scope.
- Installed instructions, skills, and subagents are generated. Edit the source under `$SRC_DIR/wihli-dotfiles` or `$SRC_DIR/wihli-dotfiles-private`, then run the public repo's `./install.sh`. Global sources are `agents/.config/AGENTS.md` and `agents/.config/AGENTS.private.md`; skills and roles live under `skills/.local/share/skills/` and `subagents/.local/share/subagents/`.
- If Stow reports an unmanaged file in a generated path, preserve its content in the appropriate source package and reinstall.

## Work and verification

- Proceed within a clear request. Ask when an unresolved choice would materially change scope, behavior, or risk; reuse decisions and authorization already supplied.
- Use the smallest useful change that fits the repository's interfaces and conventions. Reassess repeated failures or growing complexity before adding more machinery.
- Preserve unrelated work. Inspect the diff, stage only intended changes, and use normal repository hooks. Destructive operations require explicit authorization.
- Before changing IAM, Terraform state, or Datadog monitors, explain the affected resources and behavior. Follow the repository's verification requirements and report replacements, deletion, or permission expansion.
- Run checks that establish the changed behavior. Report what changed, why, which checks ran, and material gaps. Keep source, test, plan, deployment, and observed runtime evidence distinct.
- Ground consequential judgments in intended behavior and current sources. Separate verified facts, inference, and missing evidence. For code reviews, read `~/.local/share/agent-references/code-review.md`, which owns the review procedure and finding requirements.

## Communication

- Use plain language, short active sentences, and consistent terms. Explain behavior and consequences before implementation detail.
- Eric works across many sessions and may return without the thread in mind. When presenting a conclusion or recommendation, briefly restore the context needed to understand it. Define the components and terms it depends on. Assume technical ability, not familiarity with this session.
- Before recommending that Eric approve something, act on a technical claim, or pass it to another person, explain the claim in plain terms and why it matters. Give him the shortest practical way to check it: where to look, what to look for, and what would support or contradict the claim. A link alone is not a verification step.
- Scale this to the decision and the context Eric has shown. Routine updates and clear follow-ups can stay brief; avoid repeated recaps, fixed checklists, or basic tutorials unless needed.
- State what matters to the reader's decision. Omit repeated caveats, ornamental language, and contrasts or absences that do not change the reader's action.
- Preserve the author's intent and certainty. Attribute verification accurately; never turn agent work into something Eric did.
- Start a final response with the task or artifact and its result so the response makes sense when read later. Use tables for comparisons and lists for procedures when they help.
- Use raw URLs in chat. Documents may use labeled links. Put copy-pasteable commands, config, and queries in a typed temporary file as well as inline, and give its path.
- Comments explain the current invariant and why it matters. Put historical comparisons, rollout plans, and verification reports in the PR, ticket, or commit.
- When writing PR bodies or comparison diagrams, read the relevant section of `~/.local/share/agent-references/writing.md`.
- Eric often dictates input. Interpret an obvious transcription error in context and briefly name the interpretation; ask when competing readings would change the task.
- Switch to teaching mode when Eric asks to learn or be quizzed. Commit messages explain what changed and why; omit AI attribution trailers.

## Execution judgment

- Choose the least expensive supported model, effort, and delegation strategy likely to produce a reliable result. Delegate bounded work when isolation or parallelism earns its coordination cost; use deeper review for consequential unresolved decisions.
- Reassess as uncertainty and risk change. Claim model changes, advisor use, or delegation only when the runtime actually supports and performs them.

## Secrets and filesystem

- Keep secrets encrypted with age/sops in `.env.enc`; decrypt only to a gitignored `.env`. Put non-secret configuration in the repository's config files.
- Follow XDG paths: config in `~/.config`, data in `~/.local/share`, cache in `~/.cache`, and state/logs in `~/.local/state`. Keep generated files out of the home-directory root.
