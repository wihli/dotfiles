#!/usr/bin/env python3
"""Plan safe, local Deliberate review operations from durable review identity."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


SCHEMA = "deliberate-review-operation-v1"
VALIDATOR_SCHEMA = "deliberate-review-validator-v1"
ACTION_NAMES = ("review", "status", "findings", "pause", "cancel", "resume", "guidance")
JSON_ACTIONS = {"review", "status", "findings"}


class SkillError(Exception):
    pass


def default_state_dir() -> Path:
    root = os.environ.get("XDG_STATE_HOME")
    if root:
        return Path(root) / "deliberate"
    home = os.environ.get("HOME")
    if not home:
        raise SkillError("HOME is not set; pass --state-dir explicitly")
    return Path(home) / ".local/state/deliberate"


def positive_number(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("pull-request number must be a positive integer") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("pull-request number must be a positive integer")
    return number


def repository(value: str) -> str:
    value = value.strip().removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value):
        raise SkillError(f"invalid repository '{value}'; use owner/repo")
    return value


def run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise argparse.ArgumentTypeError("run ID must contain only letters, numbers, dot, underscore, or hyphen")
    return value


def pull_request_url(value: str) -> tuple[str, int]:
    parsed = urlsplit(value)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "github.com" or len(parts) != 4 or parts[2] != "pull":
        raise SkillError(f"invalid pull-request URL '{value}'; use https://github.com/owner/repo/pull/123")
    return repository(f"{parts[0]}/{parts[1]}"), positive_number(parts[3])


def github_repository_from_cwd(git_bin: str, cwd: Path) -> str:
    try:
        result = subprocess.run(
            [git_bin, "-C", str(cwd), "remote", "get-url", "--all", "origin"],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise SkillError(f"failed to run Git while resolving the current repository: {error}") from error
    if result.returncode:
        raise SkillError("current repository has no unique GitHub remote; provide --repo owner/repo or a GitHub pull-request URL")
    found = set()
    for remote in result.stdout.splitlines():
        remote = remote.strip().removesuffix(".git")
        for prefix in ("https://github.com/", "http://github.com/", "git@github.com:", "ssh://git@github.com/"):
            if remote.startswith(prefix):
                try:
                    found.add(repository(remote.removeprefix(prefix)))
                except SkillError:
                    pass
    if len(found) != 1:
        raise SkillError("current repository has no unique GitHub remote; provide --repo owner/repo or a GitHub pull-request URL")
    return found.pop()


def identity(args: argparse.Namespace) -> tuple[str, int]:
    if args.url:
        found_repo, found_pr = pull_request_url(args.url)
        if args.repo and repository(args.repo) != found_repo:
            raise SkillError("--repo does not match the pull-request URL")
        if args.pr and args.pr != found_pr:
            raise SkillError("--pr does not match the pull-request URL")
        return found_repo, found_pr
    if not args.pr:
        raise SkillError("provide --pr <number> or a GitHub pull-request URL")
    return (repository(args.repo) if args.repo else github_repository_from_cwd(args.git_bin, args.cwd), args.pr)


def json_file(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def entry_identity(location: Path) -> tuple[str, int] | None:
    for path, fields in (
        (location / "source/github-pr.json", ("repository", "pull_request")),
        (location / "draft-state.json", ("approved_request",)),
        (location / "draft.json", ("initial_request",)),
    ):
        value = json_file(path)
        if value is None:
            continue
        if fields[0] in {"approved_request", "initial_request"}:
            value = value.get(fields[0])
        if not isinstance(value, dict):
            continue
        try:
            return repository(str(value["repository"])), positive_number(str(value["pull_request"]))
        except (KeyError, SkillError, argparse.ArgumentTypeError):
            continue
    return None


def resolve_run(state_dir: Path, wanted: tuple[str, int]) -> dict:
    matches = []
    for kind in ("drafts", "runs"):
        parent = state_dir / kind
        if not parent.is_dir():
            continue
        for location in sorted(parent.iterdir()):
            if not location.is_dir() or location.is_symlink() or location.name.startswith(".") or entry_identity(location) != wanted:
                continue
            matches.append({"id": location.name, "kind": kind[:-1], "location": str(location)})
    if len(matches) != 1:
        repo, number = wanted
        if matches:
            raise SkillError(f"multiple Deliberate drafts or runs match {repo}#{number}; ask which run to use")
        raise SkillError(f"no Deliberate draft or run matches {repo}#{number}; start or identify the intended review")
    return matches[0]


def selected_run(args: argparse.Namespace) -> tuple[dict, tuple[str, int] | None]:
    if args.run:
        return {"id": args.run, "kind": "run"}, None
    wanted = identity(args)
    return resolve_run(args.state_dir, wanted), wanted


def plan(args: argparse.Namespace) -> dict:
    if args.state_dir is None:
        args.state_dir = default_state_dir()
    action = args.action
    if action == "review":
        repo, number = identity(args)
        command = [args.deliberate_bin, "review", "--state-dir", str(args.state_dir), "--pr", str(number), "--repo", repo]
        if args.goal:
            command.extend(["--goal", args.goal])
        command.extend(["--detach", "--json"])
        return {"schema": SCHEMA, "operation": action, "identity": {"repository": repo, "pull_request": number}, "command": command, "expects_json": True}

    selected, wanted = selected_run(args)
    if selected["kind"] != "run":
        raise SkillError(
            f"review draft '{selected['id']}' awaits input at "
            f"{Path(selected['location']) / 'draft-state.json'}; ask its exact open question before {action}"
        )
    run_id = selected["id"]
    commands = {
        "status": [args.deliberate_bin, "status", "--state-dir", str(args.state_dir), "--json", run_id],
        "pause": [args.deliberate_bin, "pause", "--state-dir", str(args.state_dir), run_id],
        "cancel": [args.deliberate_bin, "cancel", "--state-dir", str(args.state_dir), run_id],
        "resume": [args.deliberate_bin, "unpause", "--state-dir", str(args.state_dir), run_id],
    }
    if action in {"findings", "guidance"}:
        if not args.message or not args.message.strip():
            raise SkillError(f"{action} requires a non-empty --message")
        command = [args.deliberate_bin, "message" if action == "findings" else "steer", "--state-dir", str(args.state_dir)]
        if action == "findings":
            command.append("--json")
        command.extend([run_id, args.message.strip()])
    else:
        command = commands[action]
    result = {"schema": SCHEMA, "operation": action, "run_id": run_id, "command": command, "expects_json": action in JSON_ACTIONS}
    if wanted:
        result["identity"] = {"repository": wanted[0], "pull_request": wanted[1]}
    return result


def validate() -> dict:
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    try:
        frontmatter = skill.read_text().split("---", maxsplit=2)[1]
    except (OSError, IndexError):
        raise SkillError(f"missing portable skill manifest at {skill}")
    entries = [line.split(":", maxsplit=1) for line in frontmatter.splitlines() if line]
    if any(len(entry) != 2 for entry in entries):
        raise SkillError("SKILL.md frontmatter is not valid key/value metadata")
    keys = [entry[0] for entry in entries]
    name = next((entry[1].strip() for entry in entries if entry[0] == "name"), None)
    if keys != ["name", "description"] or name != "deliberate-review":
        raise SkillError("SKILL.md must use only name and description frontmatter for deliberate-review")
    return {"schema": VALIDATOR_SCHEMA, "valid": True, "skill": str(skill)}


def execute(args: argparse.Namespace) -> dict:
    operation = plan(args)
    try:
        result = subprocess.run(operation["command"], capture_output=True, text=True)
    except OSError as error:
        raise SkillError(f"failed to run Deliberate {operation['operation']}: {error}") from error
    if result.returncode:
        raise SkillError(f"Deliberate {operation['operation']} failed with exit code {result.returncode}; inspect its local result before retrying")
    response = None
    if operation["expects_json"]:
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise SkillError(f"Deliberate {operation['operation']} did not return valid JSON") from error
        if not isinstance(response, dict):
            raise SkillError(f"Deliberate {operation['operation']} did not return a JSON object")
    return {**operation, "result": {"exit_code": result.returncode, "response": response}}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("validate", "plan", "execute"))
    result.add_argument("action", nargs="?", choices=ACTION_NAMES)
    result.add_argument("--repo")
    result.add_argument("--pr", type=positive_number)
    result.add_argument("--url")
    result.add_argument("--run", type=run_id)
    result.add_argument("--goal")
    result.add_argument("--message")
    result.add_argument("--cwd", type=Path, default=Path.cwd())
    result.add_argument("--state-dir", type=Path)
    result.add_argument("--git-bin", default="git")
    result.add_argument("--deliberate-bin", default="deliberate")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.mode == "validate":
            output = validate()
        else:
            if not args.action:
                raise SkillError(f"{args.mode} requires an action")
            output = execute(args) if args.mode == "execute" else plan(args)
    except SkillError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
