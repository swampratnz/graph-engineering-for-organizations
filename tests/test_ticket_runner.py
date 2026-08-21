"""Regression tests for scripts/ticket_runner.py path handling.

The runner writes run state under runs/<run_id>/, where run_id comes from
--run-id or is derived from the spec's frontmatter name. A crafted id must not
be able to escape runs/. Stdlib unittest only, to keep the two-pinned-deps
footprint.

Run:  python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "ticket_runner", ROOT / "scripts" / "ticket_runner.py")
ticket_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ticket_runner)


class RunDirCase(unittest.TestCase):
    def test_normal_run_id_ok(self):
        runs = ROOT / "runs"
        rid = "weekly-release-review-2026-08-21"
        self.assertEqual(ticket_runner.run_dir(runs, rid), runs / rid)

    def test_traversal_run_ids_rejected(self):
        # die() calls sys.exit(1); each of these must abort, not return a path.
        for bad in ("../evil", "..", ".", "/etc/passwd", "a/b", ".hidden",
                    "back\\slash", "", "with\x00null"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    ticket_runner.run_dir(ROOT / "runs", bad)


if __name__ == "__main__":
    unittest.main()
