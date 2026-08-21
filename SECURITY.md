# Security policy

## Reporting

- **Vulnerability in this repo's tooling** (validator, CI, schemas): open a
  private security advisory on this repository, or contact the
  security/identity owner listed in `.github/CODEOWNERS` directly. Do not
  open a public issue for exploitable problems.
- **Suspected agent compromise or misbehavior** (unexpected actions,
  anomalous spend, credential misuse): this is an operational incident, not
  a disclosure; go straight to `docs/runbooks/incident-response.md`.
  Anyone may pull a kill switch they're authorized on without approval.

## Threat model

The threats this repo's controls are designed around, and where each control
lives. Review this table when changing any of the referenced files.

| # | Threat | Canonical failure | Controls |
|---|--------|-------------------|----------|
| 1 | **Agent credential compromise**: a stolen agent credential acts indistinguishably from the agent | Salesloft-Drift breach pattern | One unique identity per agent, no shared bot accounts (`registry/agents.yaml`); JIT/short-TTL credentials enforced by CI (`GE-CRED-STANDING`); kill switch with named holders, stop-without-approval (`docs/runbooks/kill-switch.md`); quarterly recertification (`GE-AGENT-RECERT`) |
| 2 | **Prompt injection via workflow inputs**: issue text, PR bodies, or fetched artifacts steer the agent | Agent exfiltrates data or self-escalates mid-run | Gates on externally visible actions (`class: external`/`irreversible` keep 100% review); gate input is artifact + minimum context, never raw transcripts; agents treat processed content as data (`AGENTS.md` ground rule 9); resource declarations bound what a run may touch |
| 3 | **Measurement tampering**: an optimizing agent (or the team measured) edits its own instrument | Metrics look great; reality diverges | `frozen: true` in `registry/resources.yaml`; CI rejects any spec writing a frozen resource (`GE-FROZEN-WRITE`, non-waivable); real IAM revocation required, registry documents it |
| 4 | **Governance tampering**: weakening the rules to get a run approved | Validator edited, gate deleted, self-approval | Branch protection + CODEOWNERS on `scripts/`, `schemas/`, `registry/`, `governance/` (`docs/platform-hardening.md`); separation of duties enforced by CI (`GE-SELF-APPROVE`, non-waivable); exceptions only via `governance/exceptions.yaml` with approver + expiry, checked by CI |
| 5 | **Review decay**: approvals continue, attention stops | Rubber-stamped gate ships a bad irreversible action | Override-rate band + rubber-stamp detection + canaries (`metrics/gate-health.md`); gate budgets and sampling rules (`governance/decision-rights.md`) |
| 6 | **Ownership decay**: workflows outlive their owners | Orphaned agent runs unwatched for months | `review_by` on every spec and agent, enforced by CI (`GE-ORPHAN`, `GE-AGENT-RECERT`); weekly scheduled CI run so decay surfaces without PR traffic; quarterly review runbook |
| 7 | **Supply chain**: compromised action or dependency runs in CI | Malicious action exfiltrates the repo token | Actions pinned to commit SHAs; CI token read-only (`permissions: contents: read`); pinned Python deps (`requirements.txt`); Dependabot for controlled updates |
| 8 | **Runaway spend**: a looping graph burns budget | Surprise bill | Per-run hard cap + alert threshold in every spec, alert strictly below cap (`GE-COST-ALERT`); `cap_exceeded` run status in the audit record |

## Non-waivable rules

`governance/exceptions.yaml` can waive most validator rules with a named
approver and an expiry. Three never bend, and the validator refuses exceptions
targeting them:

- **`GE-FROZEN-WRITE`**: writes to frozen measurement instruments.
- **`GE-SELF-APPROVE`**: a spec owner reviewing or receiving escalation for
  their own gates.
- **`GE-HUMAN-ROLE`**: a governance role (owner, backup, reviewer, escalation
  target, or kill-switch holder) held by a registered agent identity instead
  of a human. A waivable version would let a spec owner self-approve putting an
  agent identity in a review or kill-switch role.

## Hardening baseline

The platform-level controls (branch protection, token scopes, credential
issuance patterns, audit log retention) live in
`docs/platform-hardening.md`. A deployment is not considered hardened until
that checklist is applied and verified; the rules in this repo are only as
strong as the platform's enforcement that changes go through PR + CI.
