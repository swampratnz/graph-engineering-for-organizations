"""Regression tests for scripts/validate.py.

Zero new dependencies: stdlib unittest only, so the enforcement layer keeps
its two-pinned-deps footprint. Each test copies the repo into a temp dir,
mutates the copy, runs the validator against it as a subprocess, and asserts
on exit code and emitted GE-* codes. The bundled example-team files are the
fixtures, so the tests exercise exactly what ships.

Run:  python3 -m unittest discover -s tests

The suite exists because a validator whose green/red IS the product had no
test but the three bundled specs staying green. It locks in the core
invariants and, in particular, the registry-level self-approval bypass that
a blind enterprise evaluation surfaced (see the EX-SELF cases below).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns(".git", ".venv", "venv", "runs", "__pycache__",
                                "*.pyc", "tests")


def run_validator(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "scripts/validate.py"], cwd=root,
                          capture_output=True, text=True)


class ValidatorCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="ge-validate-"))
        self.repo = self.dir / "repo"
        shutil.copytree(ROOT, self.repo, ignore=IGNORE)
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    # -- helpers -----------------------------------------------------------
    def spec(self, name: str) -> Path:
        return self.repo / "specs" / "example-team" / f"{name}.md"

    def edit(self, path: Path, old: str, new: str, count: int = 1) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture drift: {old!r} not in {path.name}")
        path.write_text(text.replace(old, new, count), encoding="utf-8")

    def set_exceptions(self, body: str) -> None:
        (self.repo / "governance" / "exceptions.yaml").write_text(
            body, encoding="utf-8")

    def assert_clean(self, res: subprocess.CompletedProcess) -> None:
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def assert_error(self, res, code: str) -> None:
        self.assertEqual(res.returncode, 1, f"expected failure:\n{res.stdout}")
        self.assertIn(code, res.stdout, res.stdout)

    # -- baseline ----------------------------------------------------------
    def test_bundled_repo_is_green(self):
        self.assert_clean(run_validator(self.repo))

    # -- core invariants ---------------------------------------------------
    def test_owner_reviewing_own_gate(self):
        self.edit(self.spec("weekly-release-review"),
                  "reviewers: [bob]", "reviewers: [alice]")  # alice is owner
        self.assert_error(run_validator(self.repo), "GE-SELF-APPROVE")

    def test_write_to_frozen_instrument(self):
        self.edit(self.spec("ci-failure-explainer"),
                  "writes: [repo.issue-comments]",
                  "writes: [telemetry.release-health]")
        self.assert_error(run_validator(self.repo), "GE-FROZEN-WRITE")

    def test_missing_gate_timeout(self):
        self.edit(self.spec("ci-failure-explainer"),
                  "    timeout_hours: 48\n", "")
        self.assert_error(run_validator(self.repo), "GE-SCHEMA")

    def test_undefined_external_anchor(self):
        self.edit(self.spec("dependency-update-triage"),
                  "anchors: [dependency-regression-rate]",
                  "anchors: [made-up-anchor]")
        self.assert_error(run_validator(self.repo), "GE-ANCHOR-UNREG")

    def test_standing_credential(self):
        self._standing_release_bot()
        self.assert_error(run_validator(self.repo), "GE-CRED-STANDING")

    def test_agent_as_reviewer(self):
        self.edit(self.spec("ci-failure-explainer"),
                  "reviewers: [bob]", "reviewers: [example-explainer-bot]")
        self.assert_error(run_validator(self.repo), "GE-HUMAN-ROLE")

    # -- exception register: the self-approval bypass and its guards -------
    def _standing_release_bot(self) -> None:
        """example-release-bot (owner alice) on a standing credential.

        Match the 6-space-indented entry line, not the literal `kind: jit`
        in the file's header comment (the trap a real evaluator hit).
        """
        self.edit(self.repo / "registry" / "agents.yaml",
                  "      kind: jit", "      kind: pat")

    def _standing_release_bot_scalar(self) -> None:
        """example-release-bot with a non-dict `credentials` value. This is
        the form that evaded GE-CRED-STANDING before the credential check
        stopped requiring credentials to be a dict: the kind check was
        skipped entirely for a bare scalar."""
        self.edit(
            self.repo / "registry" / "agents.yaml",
            '    credentials:\n'
            '      kind: jit\n'
            '      scope: "repo:example/notes-page write; telemetry read-only"\n'
            '      issued_via: "CI OIDC exchange, 1h TTL, no standing secrets"',
            "    credentials: standing")

    def _exc(self, target: str, approver: str) -> str:
        return (
            "exceptions:\n"
            "  - id: EX-T\n"
            f"    target: {target}\n"
            "    code: GE-CRED-STANDING\n"
            "    reason: probe\n"
            f"    approved_by: [{approver}]\n"
            "    granted: 2026-08-21\n"
            "    expires: 2026-10-01\n")

    def test_selfapprove_via_registry_path_is_void(self):
        # The exact enterprise-evaluation bypass: registry-file target,
        # approved by the standing agent's own owner. Must NOT waive.
        self._standing_release_bot()
        self.set_exceptions(self._exc("registry/agents.yaml", "alice"))
        self.assert_error(run_validator(self.repo), "GE-EXC-SELF")

    def test_selfapprove_via_agent_id_is_void(self):
        self._standing_release_bot()
        self.set_exceptions(self._exc("example-release-bot", "alice"))
        self.assert_error(run_validator(self.repo), "GE-EXC-SELF")

    def test_independent_approver_waives_standing_credential(self):
        # A genuinely independent approver may waive; this is the intended
        # relief valve, and it must still work after closing the bypass.
        self._standing_release_bot()
        self.set_exceptions(self._exc("example-release-bot", "security-owner"))
        res = run_validator(self.repo)
        self.assert_clean(res)
        self.assertIn("WAIVED", res.stdout)

    def test_nonwaivable_code_rejected(self):
        self.set_exceptions(self._exc("weekly-release-review", "security-owner")
                            .replace("GE-CRED-STANDING", "GE-SELF-APPROVE"))
        self.assert_error(run_validator(self.repo), "GE-EXC-NONWAIVABLE")

    # -- the chained GE-EXC-SELF bypass and its two guards -----------------
    def test_chained_exc_self_waiver_is_rejected(self):
        # EXC-A self-approves a standing-credential waiver; EXC-B tries to
        # waive the GE-EXC-SELF finding that catches EXC-A. Single actor
        # (alice owns example-release-bot). EXC-B must be rejected because
        # GE-EXC-* is non-waivable, and the run must fail.
        self._standing_release_bot()
        self.set_exceptions(
            "exceptions:\n"
            "  - id: EXC-A\n"
            "    code: GE-CRED-STANDING\n"
            "    target: example-release-bot\n"
            "    approved_by: [alice]\n"
            "    reason: self-approved waiver\n"
            "    granted: 2026-08-21\n"
            "    expires: 2026-11-01\n"
            "  - id: EXC-B\n"
            "    code: GE-EXC-SELF\n"
            "    target: governance/exceptions.yaml\n"
            "    approved_by: [alice]\n"
            "    reason: waive the void finding itself\n"
            "    granted: 2026-08-21\n"
            "    expires: 2026-11-01\n")
        res = run_validator(self.repo)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("GE-EXC-NONWAIVABLE", res.stdout)
        self.assertIn("EXC-B", res.stdout)
        # And the self-approval it tried to shield is still an error.
        self.assertIn("GE-EXC-SELF", res.stdout)

    def test_void_exception_does_not_suppress_target(self):
        # A voided self-approved waiver must not swallow the error it targeted;
        # both the void finding and the underlying credential error surface.
        self._standing_release_bot()
        self.set_exceptions(self._exc("example-release-bot", "alice"))
        res = run_validator(self.repo)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("GE-EXC-SELF", res.stdout)
        self.assertIn("GE-CRED-STANDING", res.stdout)
        self.assertNotIn("WAIVED", res.stdout)

    def test_exception_with_ge_exc_code_rejected(self):
        # An exception whose code is itself in the GE-EXC-* family is rejected
        # at parse time, even with a genuinely independent approver.
        self.set_exceptions(
            self._exc("governance/exceptions.yaml", "security-owner")
            .replace("GE-CRED-STANDING", "GE-EXC-SELF"))
        self.assert_error(run_validator(self.repo), "GE-EXC-NONWAIVABLE")

    # -- non-dict credentials must not evade the standing-credential check --
    def test_non_dict_credentials_are_standing(self):
        # A bare `credentials: standing` scalar is not a verified JIT
        # credential and must be flagged, not silently accepted.
        self._standing_release_bot_scalar()
        self.assert_error(run_validator(self.repo), "GE-CRED-STANDING")

    def test_void_does_not_suppress_scalar_credential(self):
        # The reported gap: with a non-dict standing credential, a
        # self-approved waiver produced only GE-EXC-SELF and swallowed the
        # credential error. Both must now surface, with no WAIVED line.
        self._standing_release_bot_scalar()
        self.set_exceptions(self._exc("example-release-bot", "alice"))
        res = run_validator(self.repo)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("GE-EXC-SELF", res.stdout)
        self.assertIn("GE-CRED-STANDING", res.stdout)
        self.assertNotIn("WAIVED", res.stdout)

    def test_independent_approver_waives_scalar_credential(self):
        # The other half of the same gap: the independent-approver waiver
        # must produce a WAIVED line, not a "matches no current error"
        # warning (which meant the error never fired to be matched).
        self._standing_release_bot_scalar()
        self.set_exceptions(self._exc("example-release-bot", "security-owner"))
        res = run_validator(self.repo)
        self.assert_clean(res)
        self.assertIn("WAIVED", res.stdout)
        self.assertNotIn("matches no current error", res.stdout)


if __name__ == "__main__":
    unittest.main()
