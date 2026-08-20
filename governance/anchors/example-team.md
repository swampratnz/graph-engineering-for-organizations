# Anchor table — example-team

Reference table backing the example pilot spec
(`specs/example-team/weekly-release-review.md`). Replace with your own team's
table, copied from `TEMPLATE.md`.

Owner: alice · Reviewed: 2026-08-20 · Next review: 2026-11-20

## Objectives

| # | Objective | Why it matters |
|---|-----------|----------------|
| 1 | Ship weekly releases without customer-visible regressions | Release confidence is the constraint on release cadence |

## Anchors

| Anchor id | Measures objective | Source (instrument) | Frozen? | Latency |
|-----------|--------------------|---------------------|---------|---------|
| `customer-found-incidents` | 1 | Support ticket tag (support-owned) | yes | continuous |
| `release-rollback-rate` | 1 | `telemetry.release-health` (frozen config) | yes | per release |

## Autonomy ceilings implied

| Workflow (spec name) | Anchors covering it | Ceiling |
|----------------------|---------------------|---------|
| `weekly-release-review` | both | sampling eligible for the `notes-quality` gate after 4 weeks of in-band gate metrics; `release-go-no-go` stays 100% (class: external) |
