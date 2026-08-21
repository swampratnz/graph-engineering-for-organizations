# Graph Engineering for Teams: Organizational Implementation Plan

Prepared: 20 Aug 2026. Research-grounded plan for running multi-agent graph workflows across an organization with multiple humans interacting. Written generically: adopting organizations map the roles and systems named here onto their own.

## What the research says (condensed)

Each numbered claim is sourced, or explicitly labeled a planning
assumption, in [Sources](#sources-for-the-research-claims) at the end of
this document.

1. **The adoption gap is organizational, not technical.** Most organizations are experimenting with agents; a minority are scaling them. The failures cluster around governance gaps, cost control, and integration, not model capability.
2. **Human review capacity is the binding constraint on fleet size.** Field estimates: an operator with no purpose-built surface manages 2-3 agents before situational awareness breaks; with a proper operator surface (kanban, run registry, alerting) that rises to 10-20. Plan headcount around review capacity, not agent count.
3. **Durable execution is the load-bearing primitive.** The converged pattern: persist state at every node boundary, pause at human gates via an interrupt/signal mechanism, resume from exact state hours or days later, survive process death while waiting. LangGraph (interrupt + checkpointer) and Temporal (signals + event sourcing) are the reference implementations; production teams increasingly run both (LangGraph for reasoning, Temporal for durability). Session memory is not durable execution: chat history doesn't prove which side effect ran or whether a retry would duplicate it.
4. **Idempotency is non-negotiable.** Any node with side effects must be safe to retry. Derive idempotency keys from (run_id, step_id).
5. **Distribution is a solved problem in the Claude stack.** Dynamic workflows are shareable across teams via plugins (namespaced, versioned, SHA-pinnable marketplaces). Org-level skill/plugin provisioning supports group-scoped rollout. Admins can disable workflows via managed settings. This is the spec-repo-as-team-IP layer, productized.
6. **Agent identity governance is the widest industry gap.** Large majorities of organizations have no documented policy for creating/removing AI identities. Emerging consensus: every agent gets a unique first-class identity (delegation, not impersonation), human owner, JIT/ephemeral credentials, kill switch, and a registry. The Salesloft-Drift breach pattern (compromised agent credentials indistinguishable from legitimate activity) is the canonical failure.
7. **Regulation is arriving.** EU AI Act treats much high-impact multi-agent orchestration as high-risk: human oversight, immutable audit trails, incident testing, persistent identity through the agent lifecycle. Building the audit plane now is cheaper than retrofitting.
8. **Multi-agent pathologies are documented.** Sycophancy cascading (agents converge on confident wrong consensus), infinite handoff loops, non-converging debates. Mitigations: caps on rounds, small group sizes, fresh-context verifiers, arbitration defaults, and external anchors.
9. **Selective human validation works.** Production HITL pipelines hit very high automation rates by routing only low-confidence/exception cases to humans, not by gating everything.

## Design principles

- Humans are nodes with contracts: defined input, structured output (approve | reject | modify + reason), and timeout behavior (escalate, default-deny, or reroute). An ungated timeout is silent node failure.
- Agent autonomy scales with anchor density. Workflows judged by external ground truth (cash, churn, third-party measurement, frozen telemetry) can run wide with sampling oversight. Workflows with only internal metrics need tight gates regardless of architecture.
- Measurement infrastructure is frozen: no optimizing agent (or team being measured) holds write access to the instruments that measure it.
- Gates have budgets. Every 100%-review gate must justify itself against sampling; approval fatigue degrades gates within weeks.
- Two graph shapes, chosen deliberately: (a) personal graphs with contracted outputs meeting at team boundaries (default; matches existing engineering ownership), (b) shared multi-owner graphs (only for workflows that genuinely cross ownership boundaries: incident response, release management, cross-team review).

## Phase 0: Foundations (weeks 0-4)

**Agent identity and registry.** Every agent/workflow gets: unique identity (no shared credentials, no impersonation of humans), named human owner, scoped JIT credentials, kill switch, entry in a central registry. Extend existing IAM/PAM rather than a parallel stack; if the org already has an AI/agent identity policy, this phase operationalizes it. Named owner: the security/identity owner.

**Anchor definition.** Per team (or business unit): a one-page objective/anchor table. Objectives are what graphs optimize; anchors are external signals used to verify (cash landed, churn, customer-found incidents, third-party seeds, frozen-config telemetry). This table sets the autonomy ceiling per workflow, and is a leadership-level artifact, reviewed at whatever level owns the objectives it encodes.

**Cost plumbing.** Per-run and per-team attribution, hard caps per run, alerts on anomalous spend. Do this before adoption, not after the first surprise bill. Dynamic workflows consume meaningfully more than normal sessions by design.

**Spec repo.** Git repo for GRAPH SPECs and workflow scripts. Every spec has an owner; orphaned specs are flagged (ownership decay is the org-layer silent node failure). Review specs like code.

## Phase 1: Single-player graphs, shared library (weeks 4-10)

- Individual engineers run dynamic workflows on scoped tasks with caps. First-run confirmation stays on.
- Good runs get saved, named, and promoted into a team plugin (namespaced, versioned, SHA-pinned marketplace). Layered architecture: repositories own app-specific context; a small shared-services function owns cross-cutting plugins (review standards, security checks, deploy patterns). Install, don't copy.
- Org provisioning: group-scoped plugin assignment so each team sees only its relevant workflows. Admin managed-settings control which populations can run workflows at all.
- Exit criteria: 3-5 workflows promoted to the shared library, cost-per-run baselines established, at least one workflow with a measured quality anchor.

## Phase 2: Durable multi-human graphs (months 2-4)

Only for workflows that genuinely cross ownership boundaries.

**Runtime choice, in order of pragmatism:**
1. *Ticket-based state (start here).* Run = parent issue; each pending human gate = child issue assigned to a person; gate resolution transitions state and resumes the run. Works with GitHub Projects/Jira; no new infrastructure; fully auditable by default.
2. *LangGraph + Postgres checkpointer* when you need programmatic graphs: interrupt() pauses at a nominated node, persists state, resumes on human input without consuming compute while waiting.
3. *Add Temporal underneath* when runs must survive worker crashes and multi-day waits at scale: approval as a signal, workflow blocks on wait_condition, event-sourced history doubles as the audit trail.

**Human node contract (enforced for every gate):**
- Input: artifact + minimum context to judge it (never the worker's full chat)
- Output: structured decision + reason (feeds the audit plane)
- Timeout: explicit (escalate to named backup after N hours / default-deny / reroute)
- Authorization: which roles may resolve which gate class; spec authors cannot approve their own graph's outputs

**Surfaces by output shape:**
- Code-shaped → PR review (diff, discussion, audit free)
- Decision-shaped → chat with structured response options (Slack/Discord; Claude Tag-style multiplayer where available)
- Fleet health → run dashboard: active runs, pending gates by assignee, gate latency, spend, anomalies. If the org already runs an operational status dashboard, point that pattern at agent runs rather than building a new surface.

**Resource registry.** Declare shared resources (tables, APIs, files) per workflow; scheduler flags contention between concurrent runs. Rule: two nodes writing the same resource need an edge, not parallelism. Build before the first collision, not after.

## Phase 3: Scaling oversight (months 4-6)

- **Sampling replaces blanket gating** where anchors permit: statistical review of N% of outputs, 100% gating reserved for irreversible or externally visible actions (payments, sends, publishes, prod changes).
- **Gate health metrics:** latency, override rate, and rubber-stamp detection. Near-zero override rate means the gate is theater (remove it) or reviewers stopped looking (fix it). Consider occasional known-bad canaries to measure whether review is real.
- **Audit plane:** immutable per-run record of nodes executed, models used, gates resolved (by whom, when, why), spend, and anchor outcomes. Aligns with EU AI Act high-risk requirements; cheap now, expensive to retrofit.
- **Pathology guards as platform defaults:** round caps on any agent-debate pattern, small agent-group ceilings, fresh-context verifiers mandatory on judgment nodes, arbitration defaults on non-convergence.
- **Quarterly spec review:** kill orphaned workflows, re-verify owners, re-baseline costs.

## Operating model

**Roles:**
- Workflow DRI: one named owner per spec (quality, cost, gate design)
- Shared services maintainer(s): owns the plugin library and platform defaults (fractional role initially; do not create a team before Phase 2 demands it)
- Security/identity owner: agent registry, credential lifecycle, kill switches, frozen-instrument enforcement
- Gate reviewers: named per gate class, with backups and escalation paths

**Decision rights:**
- New workflow to shared library: DRI proposes, shared services reviews (like a code review, not a committee)
- Autonomy increase (removing a gate, widening a cap): requires demonstrated anchor coverage + 4 weeks of gate metrics
- Kill switch: security owner or DRI, no approval needed to stop, approval needed to restart

**Metrics that decide whether this is working:**
1. Gate latency (median hours from gate-open to resolution)
2. Override rate per gate (target band: not ~0%, not >30%)
3. Cost per run vs. value of run output (per workflow)
4. Anchor movement (did the external metric improve)
5. Review load per person per week (against the 10-20 supervised-agent ceiling)

## Pilot specification (v1, four weeks)

- One team, one recurring cross-boundary workflow that already exists
- State in the ticket system; gates as assigned issues with 24h escalation to a named backup
- Chat notifications for pending gates; structured approve/reject/modify responses
- Per-run spend cap; runs and outcomes logged to the audit record
- Separation of duties: workflow author excluded from approving its outputs
- Success gate for Phase 2 investment: median gate latency < 24h, override rate in band, cost per run < agreed threshold, and the workflow's external anchor moved or held

If gate latency blows out or override rate sits at zero, the finding is that the organization's review capacity or gate design is the constraint, and the correct next investment is fewer/better gates or more anchors, not more orchestration infrastructure.

## What deliberately isn't in this plan

- No bespoke orchestration platform before the ticket-based version has failed for a stated reason
- No org-wide rollout before one pilot has produced four weeks of gate metrics
- No shared multi-owner graphs for work that personal graphs with output contracts can serve
- No autonomy increases justified by internal metrics alone

## Sources for the research claims

Retrofitted 2026-08 (see `docs/practical-guide-design.md` §8.5): claims
above are either cited here or labeled planning assumptions. Vendor
numbers flagged [vendor].

1. **Adoption gap is organizational**: Gartner, [>40% of agentic
   projects canceled by end-2027 over costs/value/risk
   controls](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027)
   (Jun 2025); McKinsey State of AI (Nov 2025): 23% scaling agents, 39%
   experimenting; MIT NANDA (Aug 2025, methodology contested): ~95% of
   pilots without P&L impact, attributed to adoption mismanagement.
2. **Review capacity as binding constraint**: the 2-3 / 10-20
   supervised-agent figures are **planning assumptions**, not measured
   results; treat them as defaults to re-baseline against your own
   review-load metric (`metrics/gate-health.md` §6). Published support
   for the direction: approval-arithmetic analyses
   ([oversight-fatigue](https://hackernoon.com/the-oversight-fatigue-problem-why-hitl-breaks-down-at-scale-and-what-comes-after)),
   a documented [99.7%-by-day-3 approval-rate
   case](https://aipatternbook.com/approval-fatigue), and 59.8% of
   builders relying on human review
   ([LangChain, Dec 2025](https://www.langchain.com/state-of-agent-engineering)).
3. **Durable execution**: [LangGraph
   `interrupt()`/checkpointer](https://www.langchain.com/blog/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt)
   and [Temporal signals/event
   sourcing](https://temporal.io/blog/announcing-openai-agents-sdk-integration)
   as reference implementations.
4. **Idempotency**: standard durable-execution practice (Temporal
   activity semantics); stated here as a design rule.
5. **Distribution via plugins**: product capability of the Claude
   stack; verify against current vendor docs at adoption time [vendor].
6. **Agent identity gap**: [OWASP Non-Human Identities Top
   10](https://owasp.org/www-project-non-human-identities-top-10/)
   (2025); [Microsoft Entra Agent
   ID](https://learn.microsoft.com/en-us/entra/agent-id/) (JIT,
   no-standing-credential agent identities, GA 2026); the
   Salesloft-Drift breach as the canonical failure pattern.
7. **Regulation**: [EU AI Act Article 14 (human oversight, safe
   interrupt)](https://artificialintelligenceact.eu/article/14/); GPAI
   obligations live Aug 2025; high-risk obligations postponed to Dec
   2027 / Aug 2028 by the mid-2026 Digital Omnibus
   ([analysis](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/));
   re-verify dates before relying on them.
8. **Multi-agent pathologies**: cataloged in [OWASP's agentic threat
   corpus](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
   (cascading failures, HITL flooding); sycophancy-cascade and
   non-convergence specifics are **planning assumptions** drawn from the
   multi-agent literature; the guards (round caps, group ceilings,
   fresh-context verifiers) are cheap regardless.
9. **Selective validation works**: tiered/risk-based oversight with
   sampled review as converging practice
   ([CSA autonomy levels, Jan 2026](https://cloudsecurityalliance.org/blog/2026/01/28/levels-of-autonomy));
   high automation rates with exception-routing are widely reported by
   platform vendors [vendor].
