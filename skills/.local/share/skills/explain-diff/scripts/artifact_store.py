#!/usr/bin/env python3
"""Prepare stable, private XDG directories for explain-diff artifacts."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


SCHEMA_VERSION = 1
STORE_VERSION = "1"


class StoreError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="prepare or reuse a revision")
    prepare.add_argument("--repo-root", required=True)
    prepare.add_argument("--subject", required=True)
    prepare.add_argument("--snapshot-file", required=True)
    prepare.add_argument("--base", default="")
    prepare.add_argument("--head", default="")
    prepare.add_argument("--variant", default="general")
    prepare.add_argument("--source", default="local-diff")
    prepare.add_argument("--data-root")
    prepare.add_argument("--state-root")
    return parser.parse_args()


def git_root(path: Path) -> Path:
    if not path.is_dir():
        raise StoreError(
            f"invalid --repo-root {path}: directory does not exist; provide a Git working tree"
        )
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise StoreError(
            f"invalid --repo-root {path}: not a Git working tree; provide a repository path"
        )
    return Path(result.stdout.strip()).resolve()


def slug(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (normalized or fallback)[:48]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def write_private(path: Path, content: bytes) -> None:
    path.write_bytes(content)
    path.chmod(0o600)


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    write_private(temporary, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    os.replace(temporary, path)


def update_latest(subject_dir: Path, revision_id: str) -> None:
    latest = subject_dir / "latest"
    if latest.exists() and not latest.is_symlink():
        raise StoreError(f"invalid latest pointer {latest}: expected a symlink; move it aside")
    temporary = subject_dir / f".latest-{os.getpid()}"
    if temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(Path("revisions") / revision_id)
    os.replace(temporary, latest)


def prepare(args: argparse.Namespace) -> dict:
    repo = git_root(Path(args.repo_root).expanduser())
    subject = args.subject.strip()
    variant = args.variant.strip()
    if not subject:
        raise StoreError("invalid --subject '': provide a stable review identity")
    if not variant:
        raise StoreError("invalid --variant '': provide an audience or focus name")

    snapshot_file = Path(args.snapshot_file).expanduser()
    if not snapshot_file.is_file():
        raise StoreError(
            f"invalid --snapshot-file {snapshot_file}: file does not exist; provide a diff or patch"
        )
    snapshot = snapshot_file.read_bytes()
    if not snapshot:
        raise StoreError(
            f"invalid --snapshot-file {snapshot_file}: snapshot file is empty; provide a non-empty diff or patch"
        )

    project_key = f"{slug(repo.name, 'repository')}-{digest(str(repo))[:10]}"
    subject_key = f"{slug(subject, 'review')}-{digest(subject)[:10]}"
    snapshot_hash = hashlib.sha256(snapshot).hexdigest()
    revision_hash = digest(f"{snapshot_hash}\0{variant}\0{STORE_VERSION}")
    revision_id = revision_hash[:16]

    data_home = Path(
        args.data_root or os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
    ).expanduser()
    state_home = Path(
        args.state_root or os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
    ).expanduser()
    data_root = data_home / "explain-diff"
    state_root = state_home / "explain-diff"
    revisions = data_root / "projects" / project_key / "subjects" / subject_key / "revisions"
    subject_dir = revisions.parent
    revision_dir = revisions / revision_id
    revisions.mkdir(parents=True, mode=0o700, exist_ok=True)
    state_root.mkdir(parents=True, mode=0o700, exist_ok=True)

    created = not revision_dir.exists()
    if created:
        temporary = revisions / f".{revision_id}.tmp-{os.getpid()}"
        temporary.mkdir(mode=0o700)
        try:
            write_private(temporary / "raw.diff", snapshot)
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "generator": {"name": "explain-diff", "store_version": STORE_VERSION},
                "project": {"key": project_key, "root": str(repo)},
                "subject": {"id": subject, "key": subject_key},
                "revision": {
                    "id": revision_id,
                    "snapshot_sha256": snapshot_hash,
                    "variant": variant,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                "comparison": {"base": args.base, "head": args.head, "source": args.source},
                "outputs": {
                    "markdown": "explainer.md",
                    "html": "explainer.html",
                    "raw_diff": "raw.diff",
                },
            }
            write_json_atomic(temporary / "manifest.json", manifest)
            temporary.rename(revision_dir)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    else:
        manifest_path = revision_dir / "manifest.json"
        raw_path = revision_dir / "raw.diff"
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise StoreError(f"invalid existing revision {revision_dir}: {error}; move it aside") from error
        revision = manifest.get("revision", {})
        if revision.get("snapshot_sha256") != snapshot_hash or revision.get("variant") != variant:
            raise StoreError(f"invalid existing revision {revision_dir}: provenance does not match")
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != snapshot_hash:
            raise StoreError(f"invalid existing revision {revision_dir}: raw.diff does not match")

    update_latest(subject_dir, revision_id)
    index_path = state_root / "index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text())
        except json.JSONDecodeError as error:
            raise StoreError(f"invalid state index {index_path}: {error}; repair or move it aside") from error
    else:
        index = {"schema_version": SCHEMA_VERSION, "subjects": {}}
    if index.get("schema_version") != SCHEMA_VERSION or not isinstance(
        index.get("subjects"), dict
    ):
        raise StoreError(f"invalid state index {index_path}: unsupported structure; move it aside")
    index_key = f"{project_key}/{subject_key}"
    entry = index["subjects"].setdefault(
        index_key,
        {"project_key": project_key, "subject_key": subject_key, "subject": subject, "revisions": []},
    )
    if revision_id not in entry["revisions"]:
        entry["revisions"].append(revision_id)
    entry["latest_revision"] = revision_id
    entry["latest_path"] = str(revision_dir)
    write_json_atomic(index_path, index)

    return {
        "created": created,
        "reused": not created,
        "revision_id": revision_id,
        "revision_dir": str(revision_dir),
        "markdown_path": str(revision_dir / "explainer.md"),
        "html_path": str(revision_dir / "explainer.html"),
        "manifest_path": str(revision_dir / "manifest.json"),
        "raw_diff_path": str(revision_dir / "raw.diff"),
    }


def main() -> int:
    os.umask(0o077)
    args = parse_args()
    try:
        result = prepare(args)
    except (StoreError, KeyError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
