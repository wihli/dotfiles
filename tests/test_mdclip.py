#!/usr/bin/env python3

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin/.local/bin/mdclip"


def load_mdclip():
    loader = importlib.machinery.SourceFileLoader("mdclip", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("could not create import spec for mdclip")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MdclipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mdclip = load_mdclip()

    def test_preserves_nested_lists_and_wrapped_item_text(self) -> None:
        markdown = """\
1. Confirm this is the right runbook.
   - Use this for a live MongoDB Atlas cluster that is degraded while
     application, worker, test, or automation traffic is still pointed at it.
   - If the incident is primarily deleted, corrupted, or accidentally modified
     data, use the [snapshot/data recovery runbook](https://example.com) instead.

2. Identify the affected cluster.
   - Environment, region, cluster name, replica set vs. sharded cluster.
"""

        result = self.mdclip.render_markdown(markdown)

        self.assertIn("<ol>", result)
        self.assertIn("<ul>", result)
        self.assertEqual(result.count("<ol>"), 1)
        self.assertIn(
            "<li>Use this for a live MongoDB Atlas cluster that is degraded while "
            "application, worker, test, or automation traffic is still pointed at it.</li>",
            result,
        )
        self.assertIn(
            '<li>If the incident is primarily deleted, corrupted, or accidentally modified '
            'data, use the <a href="https://example.com">snapshot/data recovery runbook</a> '
            "instead.</li>",
            result,
        )
        self.assertNotIn("<p>application, worker", result)
        self.assertNotIn("<p>data, use", result)

    def test_preserves_wrapped_top_level_list_item_text(self) -> None:
        markdown = """\
- Record every change: previous value, new value, owner, and revert
  condition.
"""

        result = self.mdclip.render_markdown(markdown)

        self.assertIn(
            "<li>Record every change: previous value, new value, owner, and revert condition.</li>",
            result,
        )
        self.assertNotIn("<p>condition.", result)

    def test_does_not_emphasize_underscores_inside_words(self) -> None:
        markdown = "- NVMe-backed clusters include M400_NVME, M200_NVME, and M60_NVME.\n"

        result = self.mdclip.render_markdown(markdown)

        self.assertIn("M400_NVME, M200_NVME, and M60_NVME", result)
        self.assertNotIn("<em>NVME, M200</em>", result)


if __name__ == "__main__":
    unittest.main()
