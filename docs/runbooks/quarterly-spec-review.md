# Runbook: quarterly spec review

Ownership decay is the org-layer silent node failure. Once a quarter, the
shared services maintainer runs this; output is one PR plus a short summary.

## Steps

1. **Run the validator.** `python3 scripts/validate.py` — any spec past its
   `review_by` date is already flagged as orphaned.
2. **Re-verify owners.** Message every spec `owner` and `backup_owner`: "still
   yours?" No answer in a week = orphaned. Orphaned specs get 2 weeks to find
   an owner or move to `status: killed` (and their agents to `disabled`).
   Killing an orphan needs no approval; it's the kill-switch rule.
3. **Re-baseline costs.** Compare each active spec's actual cost-per-run
   (from run records) against `cap_per_run_usd`. Caps sitting far above
   actuals get tightened; specs regularly hitting caps get investigated, not
   raised silently.
4. **Gate health.** For every gate on an active spec, pull the quarter's
   metrics (`metrics/gate-health.md`): latency, override rate, rubber-stamp
   flags. Near-zero override → the gate is theater (propose removing it) or
   review stopped happening (fix reviewer load). Over ~30% → the workflow is
   producing junk; the fix is upstream, not more review.
5. **Registry hygiene and recertification.** Agents whose specs are
   killed/deprecated → `retired`, credentials destroyed. For every active
   agent: re-verify owner, credential scopes, and kill switch, then bump
   its `review_by` (+3 months) — a lapsed date fails CI. Resources no spec
   references → removed or marked. Anchor tables past their review date →
   back to their owners.
6. **Exception register.** Every entry in `governance/exceptions.yaml`
   is re-justified or removed. Expired and unused entries are already
   flagged by CI; anything renewed a second time is a standing gap —
   fix the underlying cause or accept it explicitly in decision-rights
   terms, not by serial renewal.
7. **Platform hardening re-check.** Re-verify `docs/platform-hardening.md`
   (branch protection intact, Actions token read-only, no repo secrets).
8. **Kill-switch drill.** Run the drill in `docs/runbooks/kill-switch.md`.
9. **Update `review_by`** (+3 months) on every spec that survived, in the
   same PR as any status changes.

## Summary format

Post to the org channel: specs reviewed / killed / orphaned-pending, cost
deltas, gates flagged, drill result, and review load per person per week
against the 10-20 supervised-agent ceiling.
