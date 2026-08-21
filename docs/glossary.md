# Glossary

One line per term, linking to the file where the rule actually lives.
The linked file is authoritative; this page is only a map.

- **Graph engineering**: designing and operating AI-agent workflows as
  explicit graphs with humans, budgets, and rules as versioned, CI-checked
  contracts. Full definition and term history:
  [what-is-graph-engineering.md](what-is-graph-engineering.md).
- **GRAPH SPEC**: the one-file contract for a workflow, YAML frontmatter
  (machine-validated) plus prose. Template: [`specs/TEMPLATE.md`](../specs/TEMPLATE.md).
- **Node / edge**: a unit of work (agent, human gate, deterministic step)
  and the data/control flow between units, described in the spec's Graph
  section.
- **Gate (human node)**: a human decision point with a contract: named
  reviewers, structured `approve | reject | modify` + reason output, a
  timeout, and explicit timeout behavior. Defined per spec
  ([template](../specs/TEMPLATE.md)); decision format:
  [`schemas/gate-decision.schema.json`](../schemas/gate-decision.schema.json).
- **Gate class**: `irreversible` / `external` / `quality`. The first two
  (payments, sends, publishes, prod changes) keep 100% review even under
  sampling ([decision rights](../governance/decision-rights.md)).
- **Anchor**: an external signal used to verify a workflow's outcomes
  (cash landed, churn, customer-found incidents), as opposed to internal
  metrics the workflow could game. Declared per team:
  [`governance/anchors/`](../governance/anchors/TEMPLATE.md).
- **Anchor class**: `external` (named anchors from the team's table;
  unlocks sampling) or `internal` (tight gates regardless of
  architecture). Spec frontmatter field.
- **Anchor table**: the per-team registry of anchors and their measuring
  instruments; the machine-readable `.yaml` side is what CI enforces
  ([template](../governance/anchors/TEMPLATE.yaml)).
- **Frozen instrument**: a measurement system (`frozen: true` in
  [`registry/resources.yaml`](../registry/resources.yaml)) that no
  optimizing agent or measured team may write. Writes fail CI
  (`GE-FROZEN-WRITE`) and are never waivable ([SECURITY.md](../SECURITY.md)).
- **Owner / Workflow DRI**: the one person accountable for a spec's
  quality, cost, and gate design (`owner` in frontmatter). May never
  review their own gates ([decision rights](../governance/decision-rights.md)).
- **Backup owner**: covers the owner's absence; also barred from
  reviewing (waivable by exception for small teams).
- **Separation of duties**: whoever builds a workflow, someone else
  approves its outputs. Owner rule non-waivable (`GE-SELF-APPROVE`);
  backup rule waivable ([SECURITY.md](../SECURITY.md)).
- **Personal / shared graph**: a workflow owned within one boundary vs
  one that genuinely crosses ownership boundaries (incident response,
  release management). Default is personal ([plan](plan.md)).
- **Oversight: full-gating / sampling**: every run human-gated vs a
  seeded random N% reviewed, earned via external anchors plus four weeks
  of in-band gate metrics ([decision rights](../governance/decision-rights.md)).
- **Override rate**: share of gate decisions that are reject/modify.
  Target band: not ~0%, not >30% ([gate health](../metrics/gate-health.md)).
- **Rubber-stamping**: approvals continuing after attention has stopped;
  detected via decision-time and reason-entropy signals plus canaries
  ([gate health](../metrics/gate-health.md)).
- **Canary**: a known-bad artifact occasionally routed through a gate to
  measure whether review is real. A missed canary is a gate-design
  finding, never an individual's metric ([gate health](../metrics/gate-health.md)).
- **Run record**: the immutable per-run audit record: nodes, models,
  gates (who/when/why), spend, anchor outcomes
  ([schema](../schemas/run-record.schema.json)).
- **JIT credential**: just-in-time, scoped, short-TTL credential (OIDC
  exchange or per-agent App token). Standing credentials on active agents
  fail CI (`GE-CRED-STANDING`; [platform hardening](platform-hardening.md)).
- **Kill switch**: the documented, tested way to stop an agent: named
  holders, no approval needed to stop, approval needed to restart
  ([runbook](runbooks/kill-switch.md)).
- **Exception**: the only sanctioned way to run out of compliance with a
  validator rule: named approver plus expiry ≤ 90 days, checked by CI
  ([`governance/exceptions.yaml`](../governance/exceptions.yaml)).
- **Orphaned spec**: an active spec past its `review_by` date; fails CI
  (`GE-ORPHAN`) until ownership is re-confirmed or the spec is killed.
- **Pathology guards**: platform defaults against documented multi-agent
  failure modes: debate-round caps, group-size ceilings, fresh-context
  verifiers, arbitration defaults ([plan](plan.md)).
- **Fresh-context verifier**: an agent that re-checks a judgment with
  clean context (no accumulated conversation), guarding against
  confidence cascades.
- **Idempotency key**: a `(run_id, step_id)`-derived key making any
  side-effect node safe to retry ([implementation examples](implementation-examples.md)).
- **Ticket runtime**: running a graph with the ticket system as state
  store, gate surface, and audit trail at once: run = parent issue, gate =
  assigned child issue. The default starting runtime
  ([implementation examples](implementation-examples.md)).
- **Shadow agent**: an agent running with no registry entry, owner, or
  kill switch; the default failure mode this repo's registries exist to
  prevent ([SECURITY.md](../SECURITY.md) threat #1).
- **Comprehension debt**: merged changes no human on the team can
  explain; guarded by gate reasons and reviewers who can walk through the
  change ([primer](what-is-graph-engineering.md), Honest limits).
- **GE-\* code**: the validator's error codes, one per rule; every error
  printed by CI carries one ([reference](validator-errors.md)).
