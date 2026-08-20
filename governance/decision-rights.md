# Decision rights

Who decides what, per `docs/plan.md` (Operating model). Every decision here
leaves a trace: a PR on this repo, a gate decision record, or a registry edit.

## Roles

| Role | Holds | Named as |
|------|-------|----------|
| Workflow DRI | Quality, cost, and gate design for one spec | `owner` in the spec frontmatter |
| Shared services maintainer | Plugin library, platform defaults (pathology guards, templates, validator) | CODEOWNERS on `workflows/`, `schemas/`, `scripts/` |
| Security/identity owner | Agent registry, credential lifecycle, kill switches, frozen-instrument enforcement | CODEOWNERS on `registry/` |
| Gate reviewers | Resolving gates of their class | `reviewers` per gate, with backups via `escalate_to` |

The shared services maintainer is a fractional role until Phase 2 demands
more. Do not create a team for it before then.

## Decisions

### New workflow into the shared library (`status: draft → pilot → promoted`)

DRI proposes via PR changing the spec's status; shared services reviews. Like
a code review, not a committee. Promotion to `promoted` requires the Phase 1
exit evidence in the spec's Promotion history table: cost-per-run baseline and
at least a defined quality anchor.

### Autonomy increase (removing a gate, widening a cap, `full-gating → sampling`)

PR on the spec, approved by shared services AND the security/identity owner.
The PR description must show:

1. Demonstrated anchor coverage — `anchor_class: external` with anchors from
   the team's anchor table, and anchor outcomes recorded in run records.
2. Four weeks of gate metrics for the gate being relaxed: latency, override
   rate in band (not ~0%, not >30%), no unresolved rubber-stamp flags.

Internal metrics alone never justify an autonomy increase. Gates of class
`irreversible` or `external` keep 100% review even under sampling oversight.

### Kill switch

The security/identity owner or the spec's DRI may stop any agent or workflow
with **no approval needed**. Restart requires approval: a PR flipping the
registry status back to `active`, approved by the security/identity owner.
See `docs/runbooks/kill-switch.md`.

### Gate changes (reviewers, timeouts, escalation paths)

DRI decides via PR on the spec. The validator enforces the invariants: every
gate has a timeout behavior, escalation names a person, and the spec owner
never reviews their own gates.

### Separation of duties

A spec's `owner` may not appear as a reviewer on any of its gates and may not
be its escalation target. Enforced by CI. If the org is too small to staff a
gate without the owner, that workflow keeps `full-gating` with a reviewer from
another team — or doesn't run.
