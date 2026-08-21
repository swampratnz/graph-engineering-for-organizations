# Anchor table: <team>

One page per team (or business unit). Objectives are what graphs
optimize; anchors are the external signals used to verify them. This table
sets the autonomy ceiling for every workflow the team runs: a workflow may
only claim `anchor_class: external` for anchors listed here.

This `.md` file is the prose (objectives, rationale, ceilings); the sibling
`<team>.yaml` (copy `TEMPLATE.yaml`) is the machine-readable source CI
enforces: spec anchors must exist there, and each anchor's instrument must
be registered and frozen. Keep the two in the same PR when they change.

Owner: <name> · Reviewed: <date> · Next review: <date, quarterly>

## Objectives

| # | Objective | Why it matters |
|---|-----------|----------------|
| 1 | e.g. Reduce time from merge to customer | ... |

## Anchors

| Anchor id | Measures objective | Source (instrument) | Frozen? | Latency |
|-----------|--------------------|---------------------|---------|---------|
| `cash-collected` | 1 | Accounting system export | yes (finance-owned) | weekly |
| `churn-30d` | 1 | Billing system | yes (finance-owned) | monthly |
| `customer-found-incidents` | 1 | Support ticket tag, third-party triage | yes | continuous |

Rules:

- An anchor must be measured by an instrument the optimizing team (and its
  agents) cannot write to. Register each instrument in
  `registry/resources.yaml` with `frozen: true`; CI then rejects any spec
  that declares a write on it.
- Internal metrics (velocity, agent self-evaluation, LLM-judge scores without
  external seeds) are not anchors. They may inform, never justify, autonomy.
- Anchor latency matters: a workflow whose only anchor reads monthly cannot
  use weekly gate-metric evidence to widen autonomy faster than the anchor
  can contradict it.

## Autonomy ceilings implied

| Workflow (spec name) | Anchors covering it | Ceiling |
|----------------------|---------------------|---------|
| `weekly-release-review` | `customer-found-incidents`, `release-rollback-rate` | sampling eligible after 4 weeks of gate metrics |
| <internal-only workflow> | none | full-gating, regardless of architecture |
