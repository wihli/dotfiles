import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/.local/share/skills/explain-diff"
RENDERER = SKILL_ROOT / "scripts/render_explainer.py"
STYLESHEET = SKILL_ROOT / "assets/explainer.css"


MARKDOWN = """# A restrained review

> **Verdict:** Request changes because the migration can replace a live hostname.

## Provenance

The stored comparison uses the pull request merge base rather than a moving branch.

## Goal

**Observed:** the checked source returns a full hostname after refresh.

**Inferred:** appending the zone again doubles that hostname.

**Unresolved:** a staging plan has not established convergence.

## Evidence

```html
<script>alert("this must remain code")</script>
```

[unsafe link](javascript:alert(1))

<div onclick="alert('raw event')">raw event handler</div>
<style>@import url(https://example.com/tracker.css);</style>
<a href='javascript:alert(2)' onclick='alert(3)'>raw unsafe link</a>

| Severity | Finding | Response |
| --- | --- | --- |
| Blocker | A host can be replaced | Fix the FQDN input |
| Low | Review wording is unclear | Clarify it |

## Review map

1. Read the exact patch in [raw.diff](raw.diff).
2. Inspect the [PR files](https://github.com/example/repo/pull/42/files).
"""
RAW_DIFF = "diff --git a/example b/example\n+safe change\n"


class ExplainDiffRendererTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for renderer tests")
    def test_rendered_document_has_one_title_safe_content_and_review_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, markdown, manifest, html = self._fixture(Path(temporary))
            result = self._render(markdown, html, manifest)

            self.assertEqual(0, result.returncode, result.stderr)
            rendered = html.read_text()
            self.assertEqual(1, rendered.count("<h1>"))
            self.assertEqual(1, rendered.count("<title>"))
            self.assertNotIn('class="title"', rendered)
            self.assertIn('name="viewport" content="width=device-width, initial-scale=1"', rendered)
            self.assertEqual(1, rendered.count('id="TOC"'))
            self.assertEqual(1, rendered.count('id="mobile-TOC"'))
            ids = re.findall(r'\sid="([^"]+)"', rendered)
            self.assertEqual(len(ids), len(set(ids)), "generated IDs must be unique")
            self.assertEqual(2, rendered.count('role="doc-toc"'))
            self.assertIn('<ul>', rendered)
            self.assertNotRegex(rendered, re.compile(r"^\s*columns\s*:", re.MULTILINE))

            self.assertIn('class="toc-rail"', rendered)
            self.assertIn('class="sidebar-brand"', rendered)
            self.assertIn('class="sidebar-status sidebar-status--attention"', rendered)
            self.assertIn('class="reading-pane"', rendered)
            self.assertIn('class="mobile-toc mobile-toc--attention"', rendered)
            self.assertIn('class="report-kicker">Review briefing · PR #42</p>', rendered)
            self.assertIn('class="verdict-label">Review verdict</p>', rendered)

            self.assertIn("Artifact provenance", rendered)
            self.assertIn("The stored comparison uses the pull request merge base", rendered)
            self.assertIn("moving branch.</p>", rendered)
            article = rendered.split('<article class="article">', 1)[1].split("</article>", 1)[0]
            self.assertNotIn('id="provenance"', article)
            self.assertLess(article.index('id="goal"'), article.index('id="evidence"'))
            self.assertIn(hashlib.sha256(RAW_DIFF.encode()).hexdigest(), rendered)
            self.assertIn('href="https://github.com/example/repo/pull/42"', rendered)
            self.assertIn('href="https://github.com/example/repo/pull/42/files"', rendered)
            self.assertIn('href="./raw.diff"', rendered)
            self.assertIn(">Open PR</a>", rendered)
            self.assertIn(">Changed files</a>", rendered)

            self.assertIn('class="kw">script</span>', rendered)
            self.assertIn('&lt;', rendered)
            self.assertNotIn("<script>alert", rendered)
            self.assertNotIn("javascript:", rendered)
            self.assertNotIn("onclick", rendered)
            self.assertNotIn("<style>@import", rendered)
            self.assertIn('class="evidence evidence-observed"', rendered)
            self.assertIn('class="evidence evidence-inferred"', rendered)
            self.assertIn('class="evidence evidence-unresolved"', rendered)
            self.assertIn('class="evidence-note evidence-note--observed"', rendered)
            self.assertIn('class="evidence-note evidence-note--inferred"', rendered)
            self.assertIn('class="evidence-note evidence-note--unresolved"', rendered)
            self.assertIn('class="table-scroll table-severity"', rendered)

            for forbidden in (
                "<script",
                "<link",
                "<img",
                "<iframe",
                "<object",
                "<embed",
                "<audio",
                "<video",
                "<source",
                "src=",
                "@import",
                "url(",
            ):
                self.assertNotIn(forbidden, rendered)

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for renderer tests")
    def test_negative_approval_language_is_not_classified_as_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            caution = MARKDOWN.replace(
                "Request changes because the migration can replace a live hostname.",
                "Do not approve until the migration plan proves convergence.",
            )
            _, markdown, manifest, html = self._fixture(root, caution)

            result = self._render(markdown, html, manifest)

            self.assertEqual(0, result.returncode, result.stderr)
            rendered = html.read_text()
            self.assertIn('class="verdict verdict--attention"', rendered)
            self.assertIn(">Request changes</strong>", rendered)
            self.assertNotIn('class="verdict verdict--clear"', rendered)

    def test_secondary_text_colors_meet_normal_text_contrast(self) -> None:
        css = STYLESHEET.read_text()
        palettes = [
            dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6});", block))
            for block in re.findall(r":root\s*\{([^}]+)\}", css)
        ]
        self.assertGreaterEqual(len(palettes), 2)

        for scheme, colors in zip(("light", "dark"), palettes[:2], strict=True):
            for background in ("paper", "rail"):
                with self.subTest(scheme=scheme, background=background):
                    self.assertGreaterEqual(
                        self._contrast(colors["faint"], colors[background]),
                        4.5,
                    )

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for renderer tests")
    def test_renderer_output_is_deterministic_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, first_markdown, first_manifest, first_html = self._fixture(root / "first")
            _, second_markdown, second_manifest, second_html = self._fixture(root / "second")

            first = self._render(first_markdown, first_html, first_manifest)
            second = self._render(second_markdown, second_html, second_manifest)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual(first_html.read_bytes(), second_html.read_bytes())

            repeated = self._render(first_markdown, first_html, first_manifest)
            self.assertEqual(0, repeated.returncode, repeated.stderr)
            self.assertTrue(json.loads(repeated.stdout)["reused"])

            first_html.write_text("different bytes")
            immutable = self._render(first_markdown, first_html, first_manifest)
            self.assertNotEqual(0, immutable.returncode)
            self.assertIn("completed revisions are immutable", immutable.stderr)

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for renderer tests")
    def test_renderer_rejects_tampered_raw_diff_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, markdown, manifest, html = self._fixture(Path(temporary))
            (root / "raw.diff").write_text("different snapshot\n")

            result = self._render(markdown, html, manifest)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("raw.diff does not match the recorded snapshot", result.stderr)

    def _fixture(
        self, root: Path, markdown_text: str = MARKDOWN
    ) -> tuple[Path, Path, Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        markdown = root / "explainer.md"
        manifest = root / "manifest.json"
        html = root / "explainer.html"
        raw_diff = root / "raw.diff"
        markdown.write_text(markdown_text)
        raw_diff.write_text(RAW_DIFF)
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generator": {"name": "explain-diff", "store_version": "1"},
                    "project": {"key": "repo-example", "root": "/work/repo"},
                    "subject": {"id": "https://github.com/example/repo/pull/42", "key": "pr-42"},
                    "revision": {
                        "id": "fixture-revision",
                        "snapshot_sha256": hashlib.sha256(RAW_DIFF.encode()).hexdigest(),
                        "variant": "general",
                    },
                    "comparison": {
                        "base": "1111111111111111111111111111111111111111",
                        "head": "2222222222222222222222222222222222222222",
                        "source": "https://github.com/example/repo/pull/42",
                    },
                    "outputs": {
                        "markdown": "explainer.md",
                        "html": "explainer.html",
                        "raw_diff": "raw.diff",
                    },
                }
            )
        )
        return root, markdown, manifest, html

    @staticmethod
    def _contrast(foreground: str, background: str) -> float:
        def luminance(color: str) -> float:
            channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
        return (lighter + 0.05) / (darker + 0.05)

    def _render(
        self, markdown: Path, html: Path, manifest: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(RENDERER),
                "--markdown",
                str(markdown),
                "--html",
                str(html),
                "--manifest",
                str(manifest),
            ],
            capture_output=True,
            env=os.environ | {"XDG_CACHE_HOME": str(markdown.parent / "cache")},
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
