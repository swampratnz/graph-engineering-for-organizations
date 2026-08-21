# Gate health metrics

The five metrics that decide whether this whole system is working, with
definitions precise enough to compute from run records
(`schemas/run-record.schema.json`). Reviewed weekly per workflow by its DRI;
org-wide at the quarterly spec review.

## 1. Gate latency

Median hours from gate-open (the run enters `waiting_on_gate` for that gate)
to a decision record's `decided_at`. Per gate, weekly.

- Pilot success threshold: median < 24h.
- Blowout means the org's review capacity or gate design is the constraint;
  the fix is fewer/better gates or more anchors, not more orchestration.

## 2. Override rate

Share of decisions that are `reject` or `modify`, per gate, rolling 4 weeks.

- Target band: **not ~0%, not >30%.**
- ~0% → the gate is theater (remove it) or reviewers stopped looking (fix
  it). Distinguish via rubber-stamp detection below.
- \>30% → the graph produces junk; fix the workflow upstream before scaling.

## 3. Rubber-stamp detection

Signals that review isn't real, checked per reviewer per gate:

- Decision time from open to approve consistently under the plausible
  minimum reading time for the artifact.
- Reason text entropy: identical or near-identical `reason` strings across
  approvals.
- **Canaries:** occasionally route a known-bad artifact through the gate
  (owner plants it; reviewers know canaries exist, not when). A missed
  canary is a gate-design finding, never an individual's performance metric;
  the moment it becomes one, people game it and the signal dies.

## 4. Cost per run vs. value

`spend_usd` per run record against the workflow's stated value per run
(DRI's estimate, revisited quarterly). Alert at `alert_threshold_usd`, hard
stop at `cap_per_run_usd`.

## 5. Anchor movement

Did the external metric improve or hold while the workflow ran? From
`anchor_outcomes` in run records against the team's anchor table. This is
the only evidence that counts toward autonomy increases
(`governance/decision-rights.md`).

## 6. Review load per person

Pending-gate assignments and decisions per reviewer per week, against the
10-20 supervised-agent ceiling (2-3 without a proper operator surface).
When a reviewer trends toward the ceiling, that constrains fleet growth;
plan headcount around review capacity, not agent count.
