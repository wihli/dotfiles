#!/usr/bin/env python3
"""Render canonical explain-diff Markdown as immutable, standalone HTML."""

from __future__ import annotations

import argparse
import hashlib
from html import escape, unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit


class RenderError(Exception):
    """A renderer input or provenance invariant was not met."""


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
ASSET_ROOT = SKILL_ROOT / "assets"
PANDOC_TEMPLATE = ASSET_ROOT / "pandoc-fragment.html"
STYLESHEET = ASSET_ROOT / "explainer.css"

TOC_START = "<!-- explain-diff:toc:start -->"
TOC_END = "<!-- explain-diff:toc:end -->"
BODY_START = "<!-- explain-diff:body:start -->"
BODY_END = "<!-- explain-diff:body:end -->"
H1 = re.compile(r"^(?P<indent>[ \t]{0,3})#(?!#)[ \t]+(?P<title>.*?)[ \t]*$")
H2 = re.compile(r"^(?P<indent>[ \t]{0,3})##(?!#)[ \t]+(?P<title>.*?)[ \t]*$")
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
HREF = re.compile(r'(?P<prefix>\shref=")(?P<url>[^"]*)(?P<suffix>")', re.IGNORECASE)
IMAGE = re.compile(r"<img\b(?P<attributes>[^>]*)/?>", re.IGNORECASE)
ASSET_TAG = re.compile(
    r"<(?:script|iframe|object|embed|audio|video|source|link)\b[^>]*(?:/>|>.*?</(?:script|iframe|object|embed|audio|video|source|link)\s*>)",
    re.IGNORECASE | re.DOTALL,
)
TABLE = re.compile(r"(?P<table><table\b[^>]*>.*?</table>)", re.IGNORECASE | re.DOTALL)
BLOCKQUOTE = re.compile(r"<blockquote>(?P<content>.*?)</blockquote>", re.IGNORECASE | re.DOTALL)
ALLOWED_TAGS = frozenset(
    {
        "a", "blockquote", "br", "code", "dd", "div", "dl", "dt", "em",
        "figcaption", "figure", "h2", "h3", "h4", "h5", "h6", "hr", "li",
        "nav", "ol", "p", "pre", "s", "span", "strong", "sub", "sup", "table",
        "tbody", "td", "th", "thead", "tr", "ul",
    }
)
BLOCKED_TAGS = frozenset(
    {"audio", "embed", "iframe", "object", "script", "source", "style", "video"}
)
VOID_TAGS = frozenset({"br", "hr"})
GLOBAL_ATTRIBUTES = frozenset({"class", "id"})
TAG_ATTRIBUTES = {
    "a": frozenset({"aria-hidden", "href", "tabindex", "title"}),
    "ol": frozenset({"start", "type"}),
    "td": frozenset({"colspan", "rowspan"}),
    "th": frozenset({"colspan", "rowspan", "scope"}),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, help="canonical explainer Markdown path")
    parser.add_argument("--html", required=True, help="derived HTML output path")
    parser.add_argument(
        "--manifest",
        help="artifact manifest path; defaults to manifest.json beside the Markdown",
    )
    return parser.parse_args()


def require_file(value: str, description: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RenderError(f"invalid {description} {path}: file does not exist; provide an existing file")
    return path


def require_output_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.parent.is_dir():
        raise RenderError(
            f"invalid --html {path}: parent directory does not exist; prepare an artifact revision first"
        )
    if path.is_dir():
        raise RenderError(f"invalid --html {path}: expected a file path, not a directory")
    return path


def require_mapping(value: object, description: str) -> dict:
    if not isinstance(value, dict):
        raise RenderError(f"invalid manifest {description}: expected an object")
    return value


def require_text(value: object, description: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        suffix = "may be empty" if allow_empty else "must be a non-empty string"
        raise RenderError(f"invalid manifest {description}: {suffix}")
    return value


def require_relative_output(value: object, description: str) -> str:
    name = require_text(value, description)
    path = Path(name)
    if path.is_absolute() or path.name != name or name in {".", ".."}:
        raise RenderError(
            f"invalid manifest {description} {name!r}: use a plain filename inside the revision"
        )
    return name


def load_manifest(path: Path, markdown: Path, output: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RenderError(f"invalid manifest {path}: {error}; repair or provide valid JSON") from error

    manifest = require_mapping(manifest, "root")
    project = require_mapping(manifest.get("project"), "project")
    subject = require_mapping(manifest.get("subject"), "subject")
    revision = require_mapping(manifest.get("revision"), "revision")
    comparison = require_mapping(manifest.get("comparison"), "comparison")
    outputs = require_mapping(manifest.get("outputs"), "outputs")

    require_text(project.get("root"), "project.root")
    require_text(subject.get("id"), "subject.id")
    require_text(revision.get("id"), "revision.id")
    snapshot_sha256 = require_text(revision.get("snapshot_sha256"), "revision.snapshot_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256):
        raise RenderError(
            "invalid manifest revision.snapshot_sha256: expected a lowercase SHA-256 digest"
        )
    require_text(revision.get("variant"), "revision.variant")
    require_text(comparison.get("base"), "comparison.base", allow_empty=True)
    require_text(comparison.get("head"), "comparison.head", allow_empty=True)
    require_text(comparison.get("source"), "comparison.source")

    expected_markdown = require_relative_output(outputs.get("markdown"), "outputs.markdown")
    expected_html = require_relative_output(outputs.get("html"), "outputs.html")
    raw_diff_name = require_relative_output(outputs.get("raw_diff"), "outputs.raw_diff")
    if markdown.name != expected_markdown:
        raise RenderError(
            f"invalid --markdown {markdown}: manifest expects {expected_markdown}; use the canonical artifact path"
        )
    if output.name != expected_html:
        raise RenderError(
            f"invalid --html {output}: manifest expects {expected_html}; use the derived artifact path"
        )
    raw_diff = markdown.parent / raw_diff_name
    if not raw_diff.is_file():
        raise RenderError(
            f"invalid manifest outputs.raw_diff {raw_diff_name!r}: {raw_diff} does not exist"
        )
    if hashlib.sha256(raw_diff.read_bytes()).hexdigest() != snapshot_sha256:
        raise RenderError(
            "invalid manifest revision.snapshot_sha256: raw.diff does not match the recorded snapshot"
        )
    return manifest


def is_frontmatter_boundary(line: str) -> bool:
    return line.rstrip("\r\n") in {"---", "..."}


def plain_title(markdown_title: str) -> str:
    value = markdown_title.rstrip(" #\t")
    value = re.sub(r"[ \t]+\{#[^}]+\}$", "", value)
    value = re.sub(r"!?(?:\[([^\]]+)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"<[^>]*>", "", value)
    return value.strip()


def split_title(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines(keepends=True)
    title_indexes: list[tuple[int, str]] = []
    in_frontmatter = bool(lines and is_frontmatter_boundary(lines[0]))
    in_fence: str | None = None

    for index, line in enumerate(lines):
        if in_frontmatter:
            if index and is_frontmatter_boundary(line):
                in_frontmatter = False
            continue
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if in_fence is None:
                in_fence = marker[0]
            elif in_fence == marker[0]:
                in_fence = None
            continue
        if in_fence is not None:
            continue
        match = H1.match(line)
        if match:
            title = plain_title(match.group("title"))
            if title:
                title_indexes.append((index, title))

    if len(title_indexes) != 1:
        raise RenderError(
            "expected exactly one top-level Markdown H1; add one '# Review title' and use H2 for sections"
        )
    title_index, title = title_indexes[0]
    del lines[title_index]
    return title, "".join(lines)


def extract_section(markdown: str, section_name: str) -> tuple[str, str]:
    """Remove one H2 section so derived HTML can place document chrome deliberately."""
    lines = markdown.splitlines(keepends=True)
    headings: list[tuple[int, str]] = []
    in_frontmatter = bool(lines and is_frontmatter_boundary(lines[0]))
    in_fence: str | None = None

    for index, line in enumerate(lines):
        if in_frontmatter:
            if index and is_frontmatter_boundary(line):
                in_frontmatter = False
            continue
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if in_fence is None:
                in_fence = marker[0]
            elif in_fence == marker[0]:
                in_fence = None
            continue
        if in_fence is not None:
            continue
        match = H2.match(line)
        if match:
            headings.append((index, plain_title(match.group("title")).casefold()))

    matches = [position for position, name in headings if name == section_name.casefold()]
    if len(matches) > 1:
        raise RenderError(f"expected at most one H2 named {section_name!r}")
    if not matches:
        return markdown, ""

    start = matches[0]
    end = next((position for position, _ in headings if position > start), len(lines))
    section = "".join(lines[start + 1 : end]).strip()
    remaining = "".join(lines[:start] + lines[end:])
    return remaining, section


def cache_directory() -> Path:
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    directory = cache_home / "explain-diff"
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    return directory


def between(document: str, start: str, end: str, description: str) -> str:
    try:
        after_start = document.split(start, 1)[1]
        return after_start.split(end, 1)[0].strip()
    except IndexError as error:
        raise RenderError(f"Pandoc did not produce the expected {description} fragment") from error


def render_with_pandoc(markdown: str) -> tuple[str, str]:
    if shutil.which("pandoc") is None:
        raise RenderError("Pandoc is unavailable; install Pandoc 3 or make it available on PATH")
    for asset in (PANDOC_TEMPLATE, STYLESHEET):
        if not asset.is_file():
            raise RenderError(f"renderer asset missing: {asset}; reinstall the explain-diff skill")

    with tempfile.TemporaryDirectory(prefix="render-", dir=cache_directory()) as temporary:
        input_path = Path(temporary) / "explainer.md"
        input_path.write_text(markdown, encoding="utf-8")
        input_path.chmod(0o600)
        result = subprocess.run(
            [
                "pandoc",
                "--from=gfm-raw_html",
                "--to=html5",
                "--standalone",
                "--toc",
                "--toc-depth=3",
                "--highlight-style=pygments",
                f"--template={PANDOC_TEMPLATE}",
                "--metadata=lang:en",
                str(input_path),
            ],
            capture_output=True,
            text=True,
        )
    if result.returncode:
        detail = result.stderr.strip() or "Pandoc returned no diagnostic"
        raise RenderError(f"Pandoc failed to render the Markdown: {detail}")
    toc = between(result.stdout, TOC_START, TOC_END, "table of contents")
    body = between(result.stdout, BODY_START, BODY_END, "body")
    return toc, body


def is_safe_href(value: str) -> bool:
    if value != value.strip() or any(ord(character) < 0x20 for character in value):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if value.startswith("//"):
        return False
    return not parsed.scheme or parsed.scheme.lower() in {"http", "https", "mailto"}


class SafeHTMLFragment(HTMLParser):
    """Allow Pandoc's structural HTML while discarding executable markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.open_tags: list[str] = []
        self.blocked_tags: list[str] = []

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.blocked_tags:
            if tag in BLOCKED_TAGS:
                self.blocked_tags.append(tag)
            return
        if tag in BLOCKED_TAGS:
            self.blocked_tags.append(tag)
            return
        if tag not in ALLOWED_TAGS:
            return

        allowed = GLOBAL_ATTRIBUTES | TAG_ATTRIBUTES.get(tag, frozenset())
        rendered_attributes: list[str] = []
        for name, value in attributes:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name == "href" and not is_safe_href(value):
                continue
            if name == "tabindex" and not re.fullmatch(r"-?\d+", value):
                continue
            if name in {"colspan", "rowspan", "start"} and not value.isdigit():
                continue
            if name == "type" and value not in {"1", "a", "A", "i", "I"}:
                continue
            if name == "scope" and value not in {"col", "colgroup", "row", "rowgroup"}:
                continue
            if name == "aria-hidden" and value not in {"true", "false"}:
                continue
            rendered_attributes.append(f' {name}="{escape(value, quote=True)}"')
        self.output.append(f'<{tag}{"".join(rendered_attributes)}>')
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(
        self, tag: str, attributes: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attributes)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.blocked_tags:
            if tag == self.blocked_tags[-1]:
                self.blocked_tags.pop()
            return
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS or tag not in self.open_tags:
            return
        while self.open_tags:
            opened = self.open_tags.pop()
            self.output.append(f"</{opened}>")
            if opened == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.blocked_tags:
            self.output.append(escape(data))

    def finish(self) -> str:
        self.close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")
        return "".join(self.output)


def sanitize_html(fragment: str) -> str:
    parser = SafeHTMLFragment()
    parser.feed(fragment)
    return parser.finish()


def sanitize_hrefs(fragment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        url = unescape(match.group("url"))
        if not is_safe_href(url):
            return ""
        return f'{match.group("prefix")}{escape(url, quote=True)}{match.group("suffix")}'

    return HREF.sub(replace, fragment)


def omit_images(fragment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = re.search(r'\balt="([^"]*)"', match.group("attributes"), re.IGNORECASE)
        label = unescape(alt.group(1)) if alt else "image"
        return f'<span class="image-omitted">[Image omitted: {escape(label)}]</span>'

    return IMAGE.sub(replace, fragment)


def decorate_labels(fragment: str) -> str:
    labels = {
        "Observed:": "evidence evidence-observed",
        "Inferred:": "evidence evidence-inferred",
        "Inference:": "evidence evidence-inferred",
        "Unresolved:": "evidence evidence-unresolved",
        "Blocker:": "severity severity-blocker",
        "High:": "severity severity-high",
        "High finding:": "severity severity-high",
        "Medium:": "severity severity-medium",
        "Medium finding:": "severity severity-medium",
        "Low:": "severity severity-low",
        "Low finding:": "severity severity-low",
        "Info:": "severity severity-info",
    }
    evidence_tones = {
        "Observed:": "observed",
        "Inferred:": "inferred",
        "Inference:": "inferred",
        "Unresolved:": "unresolved",
    }
    for label, classes in labels.items():
        if label in evidence_tones:
            tone = evidence_tones[label]
            fragment = fragment.replace(
                f"<p><strong>{label}</strong>",
                f'<p class="evidence-note evidence-note--{tone}">'
                f'<span class="{classes}">{label}</span>',
            )
        fragment = fragment.replace(
            f"<strong>{label}</strong>", f'<span class="{classes}">{label}</span>'
        )
    return fragment


def verdict_status(fragment: str) -> tuple[str, str]:
    match = BLOCKQUOTE.search(fragment)
    if match is None:
        return "neutral", "Review"
    text = unescape(re.sub(r"<[^>]+>", "", match.group("content"))).strip().lower()
    if not text.startswith("verdict:"):
        return "neutral", "Review"
    negative_approval = (
        "do not approve",
        "don't approve",
        "cannot approve",
        "can't approve",
        "not ready to approve",
        "should not approve",
        "must not approve",
    )
    if any(phrase in text for phrase in negative_approval):
        return "attention", "Request changes"
    if "request changes" in text or "blocker" in text:
        return "attention", "Request changes"
    if "no actionable" in text or "approve" in text:
        return "clear", "Looks good"
    return "neutral", "Review complete"


def decorate_verdict(fragment: str) -> str:
    match = BLOCKQUOTE.search(fragment)
    if match is None:
        return fragment
    text = re.sub(r"<[^>]+>", "", match.group("content")).strip()
    if not text.lower().startswith("verdict:"):
        return fragment
    tone, _ = verdict_status(fragment)
    rendered = (
        f'<div class="verdict verdict--{tone}">'
        '<p class="verdict-label">Review verdict</p>'
        f"{match.group(0)}</div>"
    )
    return f"{fragment[:match.start()]}{rendered}{fragment[match.end():]}"


def wrap_tables(fragment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        table = match.group("table")
        classes = "table-scroll"
        if re.search(r"<th[^>]*>Severity</th>", table, re.IGNORECASE):
            classes += " table-severity"
        return (
            f'<div class="{classes}" tabindex="0" role="region" '
            f'aria-label="Scrollable table">{table}</div>'
        )

    return TABLE.sub(replace, fragment)


def normalize_fragments(toc: str, body: str) -> tuple[str, str]:
    toc = ASSET_TAG.sub("", toc)
    body = ASSET_TAG.sub("", body)
    toc = omit_images(sanitize_hrefs(toc))
    body = omit_images(sanitize_hrefs(body))
    toc = sanitize_html(toc)
    body = sanitize_html(body)
    if not toc:
        toc = '<nav id="TOC" role="doc-toc" aria-label="Table of contents"></nav>'
    elif "<nav" not in toc:
        toc = f'<nav id="TOC" role="doc-toc" aria-label="Table of contents">{toc}</nav>'
    else:
        toc = toc.replace(
            '<nav id="TOC" role="doc-toc">',
            '<nav id="TOC" role="doc-toc" aria-label="Table of contents">',
            1,
        )
    body = decorate_verdict(decorate_labels(wrap_tables(body)))
    return toc, body


def mobile_toc(toc: str) -> str:
    clone = toc.replace('id="TOC"', 'id="mobile-TOC"', 1)
    clone = clone.replace('aria-label="Table of contents"', 'aria-label="Mobile contents"', 1)
    return re.sub(r'\s+id="toc-[^"]+"', "", clone)


def short_value(value: str, limit: int = 12) -> str:
    return value if len(value) <= limit else f"{value[:limit]}…"


def is_pull_request_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return (
        parsed.scheme in {"http", "https"}
        and len(parts) >= 4
        and parts[-2] in {"pull", "pulls"}
        and parts[-1].isdigit()
    )


def source_label(value: str) -> str:
    if is_pull_request_url(value):
        return f"PR #{urlsplit(value).path.rstrip('/').split('/')[-1]}"
    return "Review source"


def files_url(value: str) -> str | None:
    if not is_pull_request_url(value):
        return None
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, f"{parsed.path.rstrip('/')}/files", "", ""))


def link(label: str, href: str, classes: str = "") -> str:
    if not is_safe_href(href):
        return escape(label)
    class_attribute = f' class="{classes}"' if classes else ""
    return f'<a{class_attribute} href="{escape(href, quote=True)}">{escape(label)}</a>'


def fact(label: str, value: str, *, code: bool = True) -> str:
    rendered = f"<code>{escape(value)}</code>" if code else escape(value)
    return f"<dt>{escape(label)}</dt><dd>{rendered}</dd>"


def render_provenance(
    manifest: dict, raw_diff_name: str, provenance_note: str
) -> tuple[str, str, str]:
    project = manifest["project"]
    subject = manifest["subject"]
    revision = manifest["revision"]
    comparison = manifest["comparison"]
    source = comparison["source"]
    source_fact = link(source_label(source), source) if is_safe_href(source) else escape(source)
    facts = [
        f"<dt>Source</dt><dd>{source_fact}</dd>",
        fact("Repository", project["root"]),
        fact("Subject", subject["id"]),
        fact("Base", comparison["base"] or "not recorded"),
        fact("Head", comparison["head"] or "not recorded"),
        fact("Snapshot SHA-256", revision["snapshot_sha256"]),
        fact("Variant", revision["variant"]),
        fact("Revision", revision["id"]),
        f'<dt>Raw diff</dt><dd>{link(raw_diff_name, f"./{raw_diff_name}")}</dd>',
    ]
    note = (
        f'<div class="provenance-note">{provenance_note}</div>' if provenance_note else ""
    )
    footer = (
        '<footer class="artifact-footer"><details class="artifact-provenance">'
        "<summary>Artifact provenance</summary>"
        f"{note}"
        f'<dl class="artifact-facts">{"".join(facts)}</dl>'
        "</details></footer>"
    )
    sidebar_facts = (
        '<dl class="sidebar-facts">'
        f'<div><dt>Head</dt><dd><code>{escape(short_value(comparison["head"], 8) or "not recorded")}</code></dd></div>'
        f'<div><dt>Snapshot</dt><dd><code>{escape(short_value(revision["snapshot_sha256"], 8))}</code></dd></div>'
        "</dl>"
    )
    actions: list[str] = []
    if is_safe_href(source):
        label = "Open PR" if is_pull_request_url(source) else "Open source"
        actions.append(link(label, source, "report-action report-action--primary"))
    changed_files = files_url(source)
    if changed_files:
        actions.append(link("Changed files", changed_files, "report-action"))
    actions.append(link("Raw diff", f"./{raw_diff_name}", "report-action"))
    return sidebar_facts, "".join(actions), footer


def build_document(
    title: str, toc: str, body: str, provenance_note: str, manifest: dict
) -> str:
    raw_diff_name = manifest["outputs"]["raw_diff"]
    sidebar_facts, actions, footer = render_provenance(
        manifest, raw_diff_name, provenance_note
    )
    tone, status = verdict_status(body)
    source = manifest["comparison"]["source"]
    kicker = f"Review briefing · {source_label(source)}"
    stylesheet = STYLESHEET.read_text(encoding="utf-8").strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  <title>{escape(title)}</title>
  <style>
{stylesheet}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to review</a>
  <div class="page-shell">
    <aside class="toc-rail" aria-label="Review navigation">
      <div class="sidebar-brand"><span class="sidebar-mark" aria-hidden="true">∆</span><span>Literate diff</span></div>
      <div class="sidebar-status sidebar-status--{tone}">
        <span class="sidebar-status-dot" aria-hidden="true"></span>
        <div><p>Review snapshot</p><strong>{escape(status)}</strong></div>
      </div>
      <p class="sidebar-label">On this page</p>
      {toc}
      {sidebar_facts}
    </aside>
    <div class="reading-pane">
      <header class="report-header">
        <p class="report-kicker">{escape(kicker)}</p>
        <h1>{escape(title)}</h1>
        <div class="report-actions" aria-label="Review links">{actions}</div>
      </header>
      <details class="mobile-toc mobile-toc--{tone}">
        <summary><span>On this page</span><span>{escape(status)}</span></summary>
        {mobile_toc(toc)}
      </details>
      <main id="main-content" class="review-content">
        <article class="article">
{body}
        </article>
        {footer}
      </main>
    </div>
  </div>
</body>
</html>
"""


def write_immutable(path: Path, content: str) -> tuple[bool, bool]:
    encoded = content.encode("utf-8")
    if path.exists():
        if path.is_symlink():
            raise RenderError(f"invalid --html {path}: output must not be a symlink")
        if path.read_bytes() == encoded:
            return False, True
        raise RenderError(
            f"refusing to overwrite existing {path}: completed revisions are immutable; prepare a new variant"
        )
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_bytes(encoded)
        temporary.chmod(0o600)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return True, False


def main() -> int:
    os.umask(0o077)
    args = parse_args()
    try:
        markdown_path = require_file(args.markdown, "--markdown")
        output_path = require_output_path(args.html)
        manifest_path = require_file(
            args.manifest or str(markdown_path.with_name("manifest.json")), "--manifest"
        )
        manifest = load_manifest(manifest_path, markdown_path, output_path)
        title, markdown = split_title(markdown_path.read_text(encoding="utf-8"))
        markdown, provenance_markdown = extract_section(markdown, "Provenance")
        toc, body = normalize_fragments(*render_with_pandoc(markdown))
        provenance_note = ""
        if provenance_markdown:
            _, provenance_note = normalize_fragments(
                *render_with_pandoc(provenance_markdown)
            )
        created, reused = write_immutable(
            output_path, build_document(title, toc, body, provenance_note, manifest)
        )
    except (OSError, RenderError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "created": created,
                "reused": reused,
                "html_path": str(output_path),
                "manifest_path": str(manifest_path),
                "markdown_path": str(markdown_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
