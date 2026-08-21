# Rollout checklist

Working state of the phased rollout in `docs/plan.md`. Check items off via PR
so the history shows when each gate was passed and on what evidence. Do not
start a phase before the previous phase's exit criteria are checked.

## Phase 0: Foundations (weeks 0-4)

- [ ] Agent identity policy adopted; registry live (`registry/agents.yaml`)
      and wired into existing IAM/PAM, not a parallel stack
- [ ] Kill switch tested on at least one real agent (see
      `docs/runbooks/kill-switch.md`)
- [ ] Anchor table written per team (`governance/anchors/`), reviewed at
      leadership level
- [ ] Frozen instruments registered (`registry/resources.yaml`,
      `frozen: true`) and write access actually revoked, not just declared
- [ ] Cost attribution per run and per team working; hard caps enforceable
      by the runtime; anomaly alerts firing to owners
- [ ] This spec repo live with CI validation on every PR

## Phase 1: Single-player graphs, shared library (weeks 4-10)

- [ ] Engineers running scoped dynamic workflows with caps, first-run
      confirmation on
- [ ] 3-5 workflows promoted into the team plugin (namespaced, versioned,
      SHA-pinned); consumers install, don't copy
- [ ] Group-scoped plugin assignment configured; managed settings control
      who can run workflows
- [ ] Cost-per-run baselines recorded in each promoted spec
- [ ] At least one workflow with a measured quality anchor

## Phase 2: Durable multi-human graphs (months 2-4)

- [ ] Pilot workflow selected: one team, one recurring cross-boundary
      workflow that already exists
- [ ] Pilot spec merged (start from `specs/TEMPLATE.md`; see the reference
      `specs/example-team/weekly-release-review.md`)
- [ ] Ticket-based runtime running: run = parent issue, gates = assigned
      child issues, 24h escalation to named backup
- [ ] Chat notifications for pending gates with structured
      approve/reject/modify responses
- [ ] Run records logged per `schemas/run-record.schema.json`
- [ ] Metrics tooling exists: something (a script, a saved query, a
      spreadsheet fed from ticket exports) actually computes the
      `metrics/gate-health.md` numbers from run data; the success gate
      below depends on four of them, and prose definitions don't
      compute themselves
- [ ] Four weeks of pilot metrics collected

**Pilot success gate (required before further Phase 2 investment):**

- [ ] Median gate latency < 24h
- [ ] Override rate in band (not ~0%, not >30%)
- [ ] Cost per run under the agreed threshold
- [ ] External anchor moved or held

If latency blows out or override rate sits at zero: the constraint is review
capacity or gate design. Invest in fewer/better gates or more anchors, not
more orchestration infrastructure.

## Phase 3: Scaling oversight (months 4-6)

- [ ] Sampling enabled only where decision-rights evidence exists;
      irreversible/externally visible actions still 100% gated
- [ ] Gate health dashboard live (latency, override rate, rubber-stamp
      flags, spend, pending gates by assignee)
- [ ] Audit plane immutable and complete per run
- [ ] Pathology guards enforced as platform defaults, not per-spec opt-ins
- [ ] First quarterly spec review completed
      (`docs/runbooks/quarterly-spec-review.md`)

## Phase 3+ backlog (scheduled, not started)

- [ ] **Registry-vs-reality reconciliation job.** The registries document
      intent; IAM enforces it, and nothing yet detects drift between the
      two (an agent deleted here but alive in the identity provider, a
      frozen instrument that quietly regained a writer, a standing PAT
      behind a `kind: jit` entry). A scheduled job diffing actual
      identities and instrument IAM against `registry/*.yaml` is the
      highest-value automation after the pilot; until it exists, the
      quarterly review's manual attestation is the only control, and that
      is a known gap, not a guarantee.

## Escalation triggers for heavier runtimes

- [ ] Ticket-based state has failed for a stated, written reason before any
      LangGraph checkpointer work begins
- [ ] LangGraph alone has failed for a stated, written reason (crash
      recovery, multi-day waits at scale) before Temporal is added
