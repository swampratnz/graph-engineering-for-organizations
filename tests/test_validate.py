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

    # -- a non-date created must be caught on agents as it is on specs ------
    def test_agent_created_not_a_date(self):
        # created declares format: date, but Draft 2020-12 treats format as an
        # annotation, so a present-but-garbage value slips the schema. It is
        # backstopped on specs (check_ownership); an agent registry entry must
        # be caught identically (GE-SCHEMA), not validate clean.
        self.edit(self.repo / "registry" / "agents.yaml",
                  "created: 2026-08-20", "created: banana")
        self.assert_error(run_validator(self.repo), "GE-SCHEMA")

    # -- self-approval must resolve every target form, not just spec names ---
    def _backup_reviews_weekly(self) -> None:
        """Make dana (backup owner of weekly-release-review, owner alice) a
        gate reviewer, raising a waivable GE-BACKUP-APPROVE on that spec."""
        self.edit(self.spec("weekly-release-review"),
                  "reviewers: [carol]", "reviewers: [carol, dana]")

    def test_selfapprove_via_spec_path_is_void(self):
        # The file-path bypass: err() matches a waiver by the spec's file path
        # as well as its name, so an owner-approved exception aimed at the path
        # must still be voided, not applied. (Was WAIVED before the fix.)
        self._backup_reviews_weekly()
        self.set_exceptions(
            "exceptions:\n"
            "  - id: EX-PATH\n"
            "    target: specs/example-team/weekly-release-review.md\n"
            "    code: GE-BACKUP-APPROVE\n"
            "    reason: probe\n"
            "    approved_by: [alice]\n"          # alice owns this spec
            "    granted: 2026-08-21\n"
            "    expires: 2026-10-01\n")
        res = run_validator(self.repo)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("GE-EXC-SELF", res.stdout)
        self.assertIn("GE-BACKUP-APPROVE", res.stdout)
        self.assertNotIn("WAIVED", res.stdout)

    def test_selfapprove_via_resources_path_is_void(self):
        # A file-level waiver on registry/resources.yaml can only be signed by
        # someone who owns no resource in it; a resource owner is a party.
        self.edit(self.repo / "registry" / "resources.yaml",
                  "  - id: release.notes-page", "  - id: repo.main")  # dup id
        self.set_exceptions(
            "exceptions:\n"
            "  - id: EX-RES\n"
            "    target: registry/resources.yaml\n"
            "    code: GE-REG\n"
            "    reason: probe\n"
            "    approved_by: [alice]\n"          # alice owns repo.main
            "    granted: 2026-08-21\n"
            "    expires: 2026-10-01\n")
        res = run_validator(self.repo)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("GE-EXC-SELF", res.stdout)

    def test_unknown_exception_target_is_rejected(self):
        # A target that names no known spec/agent/governance file cannot have
        # its approver checked, so it is rejected rather than applied blind.
        self._standing_release_bot()
        self.set_exceptions(self._exc("registry/nope.yaml", "security-owner"))
        self.assert_error(run_validator(self.repo), "GE-EXC-INVALID")

    # -- self-approval must not be dodged by a look-alike approver handle ----
    def _standing_bot_exc(self, approver_line: str) -> None:
        self._standing_release_bot()
        self.set_exceptions(
            "exceptions:\n"
            "  - id: EX-H\n"
            "    target: example-release-bot\n"
            "    code: GE-CRED-STANDING\n"
            "    reason: probe\n"
            f"    {approver_line}\n"
            "    granted: 2026-08-21\n"
            "    expires: 2026-10-01\n")

    def test_whitespace_approver_is_rejected(self):
        # 'alice ' (trailing space) is alice; it must not slip past GE-EXC-SELF.
        self._standing_bot_exc('approved_by: ["alice "]')
        res = run_validator(self.repo)
        self.assert_error(res, "GE-EXC-INVALID")
        self.assertNotIn("WAIVED", res.stdout)

    def test_homoglyph_approver_is_rejected(self):
        # Cyrillic 'а' (U+0430) + 'lice' renders as 'alice' but is a different
        # string; a non-ASCII approver handle is rejected outright.
        self._standing_bot_exc('approved_by: ["аlice"]')
        res = run_validator(self.repo)
        self.assert_error(res, "GE-EXC-INVALID")
        self.assertNotIn("WAIVED", res.stdout)

    # -- GE-HUMAN-ROLE is non-waivable -------------------------------------
    def test_human_role_is_nonwaivable(self):
        self.edit(self.spec("ci-failure-explainer"),
                  "reviewers: [bob]", "reviewers: [example-explainer-bot]")
        self.set_exceptions(
            self._exc("ci-failure-explainer", "security-owner")
            .replace("GE-CRED-STANDING", "GE-HUMAN-ROLE"))
        res = run_validator(self.repo)
        self.assert_error(res, "GE-EXC-NONWAIVABLE")
        self.assertIn("GE-HUMAN-ROLE", res.stdout)

    # -- an empty credentials block is a standing credential ----------------
    def test_empty_credentials_are_standing(self):
        self.edit(
            self.repo / "registry" / "agents.yaml",
            '    credentials:\n'
            '      kind: jit\n'
            '      scope: "repo:example/notes-page write; telemetry read-only"\n'
            '      issued_via: "CI OIDC exchange, 1h TTL, no standing secrets"',
            "    credentials: {}")
        self.assert_error(run_validator(self.repo), "GE-CRED-STANDING")

    # -- a non-date `created` is caught despite format being an annotation --
    def test_created_not_a_date(self):
        self.edit(self.spec("ci-failure-explainer"),
                  "created: 2026-08-20", "created: banana")
        self.assert_error(run_validator(self.repo), "GE-SCHEMA")


if __name__ == "__main__":
    unittest.main()
