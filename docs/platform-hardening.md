# Platform hardening checklist

The rules in this repo are enforced by CI on PRs — which only matters if the
platform forces changes through PRs and CI. A repo admin applies this
checklist at setup (Phase B of `AGENTS.md`); the security/identity owner
re-verifies it at the quarterly review. Items are written for GitHub;
translate equivalents for GitLab/Bitbucket.

## Repository settings

- [ ] **Branch protection (or a ruleset) on `main`:**
  - Require a pull request before merging; **no direct pushes for anyone,
    including admins** ("Do not allow bypassing the above settings").
  - Require the `validate` status check to pass.
  - Require review from Code Owners (this activates the routing in
    `.github/CODEOWNERS` — without it, CODEOWNERS is advisory).
  - Dismiss stale approvals on new pushes.
  - Require approval of the most recent reviewable push (prevents
    approve-then-swap).
  - Block force pushes and branch deletion.
- [ ] **Signed commits** required on `main` (ruleset), or commit
  verification monitored — pick one and write it down.
- [ ] CODEOWNERS placeholders replaced with real handles; the file itself is
  owned by the security/identity owner (it is, via the `/governance/` and
  root patterns — verify after edits).

## Actions / CI

- [ ] Workflow permissions default set to **read-only** at the repo (or org)
  level; individual workflows request more explicitly. This repo's
  `validate.yml` declares `permissions: contents: read`.
- [ ] Actions restricted to a pinned allowlist, and all uses pinned to
  **full commit SHAs** (as `validate.yml` does), not tags — tags are
  mutable.
- [ ] Dependabot enabled for `github-actions` and `pip`
  (`.github/dependabot.yml`) so pins are raised by reviewed PR, not by
  hand-editing under pressure.
- [ ] No workflow in this repo uses `pull_request_target` with checkout of
  PR code. Keep it that way.
- [ ] **Scheduled-run keepalive.** GitHub disables scheduled workflows after
  ~60 days of repository inactivity — and the weekly validate run is the
  control that surfaces orphaned specs and lapsed recertifications on
  exactly the low-traffic repos that need it. Pick one: an external pinger
  hitting the workflow's `workflow_dispatch` (calendar-driven), or a
  standing calendar entry for the security owner to confirm monthly that
  the schedule is still enabled. Write down which.
- [ ] Repository/org secrets: this repo needs **none**. An added secret is a
  finding — the validator and CI run on public repo content only.

## Agent identities (the real ones behind `registry/agents.yaml`)

- [ ] One identity per agent: a **GitHub App** (or cloud workload identity)
  per agent, never a shared "bot" account, never a personal access token,
  never a human's credentials. Delegation, not impersonation.
- [ ] Credentials are **just-in-time**: OIDC federation or App installation
  tokens with ≤1h TTL. No standing PATs. `registry/agents.yaml` entries
  must state `credentials.kind: jit` — CI errors on anything else
  (`GE-CRED-STANDING`); a temporary, expiring exception is the only out.
- [ ] Scopes are minimal and enumerated in the registry entry's
  `credentials.scope`, and match what the identity can actually do.
- [ ] Kill switch tested: revoking the App installation / trust binding
  actually severs access within minutes. Drill quarterly
  (`docs/runbooks/kill-switch.md`).
- [ ] Agent identities appear in the org **audit log**; audit log streaming
  to your SIEM enabled if available. You cannot investigate threat #1
  (`SECURITY.md`) without this.

## Frozen instruments

- [ ] For every `frozen: true` resource in `registry/resources.yaml`, write
  access is revoked **in the measuring system's own IAM** for: every agent
  identity, and every member of the team being measured. The registry
  documents the intent; the instrument's IAM enforces it.
- [ ] Change control for instrument configuration (dashboards, queries,
  telemetry config) is owned outside the measured team.

## Ticket runtime (Phase 2 pilots)

- [ ] Gate child-issues can only be closed/resolved by the assigned
  reviewer or their escalation target — enforce via workflow automation or
  accept and monitor via the audit trail.
- [ ] Run-record attachments are append-only in practice: edits to
  historical run records are a finding.

## Verification

After applying: attempt a direct push to `main` (should fail), open a
test PR touching `registry/` (should require the security owner), and
confirm `validate` blocks merge when failing. Record the date and results
in the PR that checks off `docs/rollout-checklist.md` Phase 0.
