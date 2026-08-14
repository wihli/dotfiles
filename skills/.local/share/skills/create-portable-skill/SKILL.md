---
name: create-portable-skill
description: Create or update portable skills for Claude Code, Codex, and OpenCode. Use for new shared skills, ports, installer changes, or cross-harness audits.
---

# Create Portable Skill

Build one source-controlled skill whose core workflow works unchanged in Claude Code, Codex, and OpenCode. Keep harness-specific metadata or adapters optional so another harness can ignore them safely.

## Establish the contract

Before editing:

1. Read the target repository's agent instructions and inspect its current skill layout, installer, tests, and worktree status.
2. Identify concrete prompts that should and should not trigger the skill.
3. Name the canonical source directory. In `wihli-dotfiles`, use `skills/.local/share/skills/<skill-name>/`; never edit an installed home-directory copy.
4. Classify each harness as source-compatible, discovery-verified, behavior-verified, or unavailable. Do not turn static compatibility into a runtime-validation claim.
5. Ask only when a missing choice would materially change the skill. Otherwise choose the smallest testable implementation.

## Keep the core portable

- Put only `name` and `description` in `SKILL.md` frontmatter. Use a lowercase kebab-case name matching the directory.
- Make the description say what the skill does and when it should trigger.
- Write imperative, tool-neutral instructions. Describe capabilities such as reading files, searching text, running commands, and editing files instead of naming harness-specific tool-call syntax.
- Resolve bundled paths relative to the skill directory. Do not assume a harness-specific current working directory.
- Use common local runtimes for deterministic scripts, fail explicitly, and follow XDG paths for generated config, data, cache, and state.
- Keep harness-specific metadata in optional files such as `agents/openai.yaml`. The core workflow must not depend on a harness reading those files.
- Isolate a genuinely harness-specific operation behind a small adapter and document the reduced behavior when that adapter is unavailable.
- Keep the skill concise. Add `scripts/`, `references/`, or `assets/` only when they prevent repeated work or keep `SKILL.md` focused.

## Verify discovery

For this dotfiles repository, one canonical source under `~/.local/share/skills` reaches the harnesses through these installed paths:

| Harness | Discovery path | Required evidence |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/<skill-name>` | Resolve the link, then list or invoke the skill. |
| Codex | `~/.agents/skills/<skill-name>` | Resolve the per-skill link, then list or invoke the skill. |
| OpenCode | OpenCode discovers `~/.agents/skills` and `~/.claude/skills` as compatibility paths. | Recheck the current official OpenCode skill documentation, then list or invoke the skill when the executable is available. |

Do not add another discovery root merely for symmetry. Change installer wiring only when current harness documentation or an installed runtime proves the existing path insufficient; then update installer tests and repository documentation together.

The installer also maintains `~/.codex/skills` for Codex-specific compatibility. That path is not a substitute for verifying the current documented user discovery path.

## Implement test-first

1. Add a failing test for the skill's durable contract: source path, frontmatter, required portable guidance, optional metadata, and installer discovery paths.
2. If a harness supplies a skill creator, use it only to scaffold the source-owned directory. Do not make that provider tool a runtime dependency of the finished skill.
3. Implement the smallest `SKILL.md` and resources that satisfy the triggering examples.
4. Run the creator's structural validator when available, plus the repository's focused tests and whitespace checks.
5. Run the repository installer when its instructions require it. Preserve unrelated worktree changes.
6. Resolve each installed path and exercise a representative prompt in every available harness. Restart the harness or its skill catalog after adding a discovery entry during an active session before treating absence as a wiring failure.
7. Report unavailable harnesses and untested behavior plainly.

## Audit the result

Record a compact matrix before completion:

| Check | Pass condition |
| --- | --- |
| Ownership | The canonical files live in the user's source repository. |
| Format | `SKILL.md` uses the portable frontmatter and relative resources. |
| Core workflow | No required step depends on one harness's private tool syntax or metadata. |
| Discovery | Each supported harness can find the same canonical skill through a documented installed path. |
| Behavior | A realistic triggering prompt produces the intended workflow in each available harness. |
| Honesty | Static checks, live checks, unavailable runtimes, and remaining gaps are distinguished. |

### Self-audit

When changing this skill, apply the entire workflow to `create-portable-skill` itself. Its own source, instructions, discovery, validation, and behavior claims must meet the same portability contract it applies to other skills.
