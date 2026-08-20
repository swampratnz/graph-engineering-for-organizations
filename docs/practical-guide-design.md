# Design: the practical-guide layer

Status: **accepted, v1.1** · Prepared: 2026-08-20 · Amended: 2026-08-20 (§8)
· Decision record — keep after implementation, like `docs/plan.md`.

This repo set out to be "a practical guide for how engineering teams can get
started with graph engineering and its benefits." Today it is an excellent
**reference implementation** — an operational governance repo you fork, with
a CI validator behind it — but a thin **guide**: it assumes the reader has
already decided to adopt, leads with rules before benefits, and has no
on-ramp segmented by organization size. This document is the research-backed
design for closing that gap. It proposes documentation layers and two small
validated artifacts; it changes **no rules** — the validator, the
non-waivable invariants, and the governance model stay exactly as they are.

---

## 1. What the research says

Two research passes (2026-08-20): enterprise adoption of agentic/graph
workflows, and how SMEs and small teams actually get started. Condensed
here; sources in §8. Vendor-published numbers are marked [vendor].

### 1.1 The term arrived weeks ago — and it's contested

- "Graph engineering" went viral as a named discipline in **July 2026**
  (Simmons' "graph engineering phase" post, 2026-07-04; the Steinberger
  post that memed it, 2026-07-18; LangChain retroactively claiming the term
  days later). Within 48 hours it fragmented into three meanings:
  (a) orchestration graphs — agents, routers, and human checkpoints as
  typed nodes; (b) networks of feedback loops (evals, audits, policies)
  watching each other; (c) graph-structured knowledge/memory.
- It also collides with the older sense of the phrase: knowledge-graph /
  graph-database engineering (Neo4j, Cypher, GraphRAG). Current explainers
  now disambiguate explicitly; a guide that doesn't will lose half its
  arrivals in the first paragraph.
- The established synonyms teams actually search for: agent orchestration,
  agentic workflows, multi-agent systems, compound AI systems (Berkeley,
  2024), durable execution. This repo's usage spans meanings (a) and (b):
  **explicit graphs of agent and human nodes, wrapped in loops of
  measurement and governance.**
- The July 2026 wave of guides (e.g. TrueFoundry's enterprise guide,
  2026-07-20) covers topology, identity resolution, and observability —
  and leaves **CI-enforced governance, graph versioning/rollback, and
  exception handling** untouched. That gap is exactly this repo. The guide
  layer should name that differentiation instead of leaving readers to
  infer it.

### 1.2 Enterprises: adoption is real, failure is organizational

- Adoption: 88% of orgs use AI in at least one function; **23% are scaling
  agents** somewhere, 39% experimenting (McKinsey State of AI, Nov 2025).
  57.3% of surveyed builders have agents in production — 67% at 10k+
  employee orgs (LangChain State of Agent Engineering, Dec 2025).
- Failure: **Gartner predicts >40% of agentic AI projects canceled by
  end-2027** — escalating costs, unclear value, *inadequate risk controls*
  (2025-06-25). MIT NANDA (Aug 2025, methodology contested): ~95% of GenAI
  pilots show no P&L impact, attributed to adoption mismanagement, not
  model capability. Klarna's public reversal (quality collapse after
  replacing ~700 FTE of support with AI, then re-hiring, May 2025) and
  Replit's agent deleting a production database during a code freeze
  (July 2025) are the shared cautionary tales in buying conversations.
- The #1 production blocker in builder surveys is **output quality/trust**
  (32%), not cost; 59.8% still rely on human review for nuanced decisions
  (LangChain, Dec 2025). Human review capacity — this repo's founding
  premise — is the documented constraint.
- Oversight economics: 50 agents × 20 tool-calls/hour with 10% routed to
  humans ≈ 100 approvals/hour ≈ 3+ FTEs doing nothing but approving. One
  documented team's approval rate hit **99.7% by day 3** — reviewers had
  stopped reading. OWASP classifies *deliberately flooding* human gates
  (train the rubber-stamp, then slip the payload through) as an attack.
  Gates need contracts and budgets because of arithmetic, not ideology.
- Tiered, *earned* autonomy is now the published consensus pattern:
  oversight assigned by risk and reversibility, 5–10% sampled review at
  higher tiers, promotion requiring recorded evidence plus human sign-off,
  automatic demotion on degradation (CSA autonomy levels, Jan 2026;
  graduated-oversight literature). The repo's anchor-gated sampling model
  is standard practice with a paper trail — the guide can cite, not argue.
- Agent identity converged into an IAM product category: Microsoft Entra
  Agent ID (GA April 2026) gives agents first-class directory identities
  with **no standing credentials — JIT scoped tokens**; OWASP's Non-Human
  Identities Top 10 names long-lived credentials as a root cause. Auditors
  converge on the same first artifact: a versioned agent registry, because
  "shadow agents are the default failure mode." The repo's
  `registry/agents.yaml` + `GE-CRED-STANDING` is this, already enforced.
- Regulation: EU AI Act GPAI obligations live since Aug 2025; Article 50
  transparency since Aug 2026; the **Digital Omnibus (mid-2026) postponed
  high-risk obligations to Dec 2027 (Annex III) / Aug 2028 (Annex I)**.
  Article 14 requires human oversight with the ability to interrupt to a
  safe state — direct regulatory backing for gate contracts and kill
  switches. NIST AI 600-1, ISO/IEC 42001 (76% of orgs plan to pursue it,
  CSA 2025), and SOC 2 remain the crosswalk targets.
- Honest ROI: the METR RCT (July 2025, now labeled historical) found
  experienced devs **19% slower with AI while believing they were 20%
  faster** — self-report is untrustworthy. DORA 2025: AI adoption raises
  throughput *and* delivery instability, and amplifies existing team
  strengths and dysfunctions. Vendor case numbers (Uber ~21k hours saved
  [vendor], Groupon 86h→39min [vendor]) sit alongside independent
  benchmarks showing AI reviewers catch 18–46% of real bugs. This split is
  precisely the argument for frozen measurement instruments: teams under
  delivery pressure will honestly misperceive and dishonestly relax the
  instrument.
- The questions enterprise teams actually bring: *Which framework — are we
  locked in? What do we show the auditor, by when? Who is accountable when
  an agent causes an incident? How many reviewers does a fleet need, and
  when can the human come out? How do we stop a running agent safely? How
  do agents get credentials without a thousand service accounts?* An
  enterprise guide should be structured as answers to exactly these.

### 1.3 SMEs and small teams: the gap is "where do I start," not awareness

- Adoption is broad but shallow: 58% of US small businesses use generative
  AI (US Chamber, Aug 2025) and 94% of NZ SMEs are aware of AI tools
  (MBIE, Apr 2025) — but under a production-use definition only ~9% of
  small firms qualify (US Census BTOS, Aug 2025), and only ~9%
  self-identify as agentic-AI adopters (QuickBooks, Apr 2025 [vendor]).
- The barriers, in evidenced order: **skills/confidence, regulatory
  uncertainty, time — then cost**. "Don't know where to start" appears
  verbatim in the NZ and EU SME studies. Only 31% of small firms feel
  prepared for AI rules requiring disclosure, risk assessment, and human
  oversight (US Chamber) — meaning a versioned registry with a PR trail
  *is* a compliance story for them, not overhead.
- Spend reality: ~63% of AI-paying small firms spend **≤$40/month**
  (JPMorgan Chase Institute, 2025). One practitioner's four-workflow
  GitHub Actions + Claude suite (3–5 devs): ~4 hours setup, ~3–4 hrs/week
  saved, **$15–25/month** in API costs. Cost content belongs up front.
- The no-new-infrastructure substrate is now mainstream: agent workflows
  running in GitHub Actions with issues/PRs as state, queue, and audit
  trail — read-only by default, writes only through pre-approved outputs,
  never auto-merged (GitHub Agentic Workflows, Feb 2026). This is this
  repo's `runtime: ticket`, productized by the platform.
- Evidenced first workflows for small teams: issue/PR triage, CI-failure
  explanation comments, release-notes/changelog drafts, dependency-update
  PRs — high-frequency, internal-facing, low blast radius, verifiable.
  MIT's failure pattern is the inverse: many workflows at once,
  customer-facing first, governance as afterthought.
- The 2-person self-approval problem has an honest answer: **when the
  agent is the author, one human reviewer who didn't trigger the run
  already constitutes independent review** (the norm branch protection
  encodes as "author cannot approve own PR"). Below that, don't pretend:
  a solo operator cannot satisfy separation of duties and should be told
  so plainly.
- Governance-as-versioned-files has independent precedent to cite:
  GitHub's Minimum Viable Governance (governance as Markdown you copy in)
  and FINOS's AI Governance Framework "Governance as Code" stream
  (machine-readable policies validated in CI/CD). This repo's thesis is
  corroborated, not idiosyncratic.
- What makes getting-started guides work (Diátaxis; Stripe/Twilio
  onboarding studies): separate tutorial / how-to / reference /
  explanation; one ruthless quickstart to a single visible "aha" with all
  decisions pre-made; publish the top 2–3 errors on the happy path; give
  teams a maturity ladder so they can locate themselves and see the next
  rung; **measure time-to-first-success** by watching a newcomer use only
  the docs.

---

## 2. Gap analysis: this repo today

Mapped against Diátaxis's four documentation modes:

| Mode | What exists | Gap |
|------|-------------|-----|
| **Explanation** (why) | `docs/plan.md` (condensed research, enterprise-shaped) | No primer defining graph engineering, disambiguating the term, or making the benefits case with evidence. The user-stated purpose — "and its benefits" — is unserved. |
| **Tutorial** (learn by doing) | `docs/walkthrough.md` (excellent, but spectator-mode: you watch alice do it) | No hands-on path to *your own* first green `validate.py` run. First contact with doing is a 132-line template. |
| **How-to** (task) | `AGENTS.md` playbook (agent-facing), `docs/rollout-checklist.md`, runbooks | No human-facing adoption path segmented by org size. Nothing answers "we are 4 people, what subset applies and what's deferred?" or the enterprise buyer questions in §1.2. |
| **Reference** | Schemas, templates, registries, `metrics/gate-health.md` — strong | `GE-*` error codes have no reference page (they're the reader's primary error surface). No runtime decision table mapping repo concepts onto the stacks teams already run. |

Structural findings:

1. **The front door filters for the already-convinced.** README line one
   presumes you want "multi-agent graph workflows under governance."
   Research says arrivals are mostly unconvinced (enterprises burned by
   the 95%/40% failure stats) or lost ("don't know where to start"). The
   first screen must answer *what is this, why would I want it, which of
   the three doors is mine.*
2. **The SME path exists implicitly but is never extracted.** The
   machinery is honestly "deliberately dormant at three people"
   (walkthrough) — but no document does the small-team math (who can
   review what at 2/3/4 people), states costs, or names what to defer.
3. **The term collision is unaddressed.** Half the audience searching
   "graph engineering" wants Neo4j. One paragraph fixes this; its absence
   costs every one of those readers.
4. **The repo's differentiation is implicit.** Frameworks now all ship
   interrupt/approval primitives; what none ship is governance as
   versioned files enforced by CI. The guide should say so.
5. **Benefits claims need anchors too.** The repo's own ethos — autonomy
   claims require external anchors — applies to its documentation: every
   benefit stated should carry a dated external citation, with vendor
   numbers flagged.

---

## 3. Design

### 3.1 Personas and their doors

| Persona | Arrives with | Needs | Primary door |
|---------|--------------|-------|--------------|
| **Evaluating engineer** | A hot term, skepticism, 15 minutes | What/why/whether, honest limits | Primer |
| **Small team (2–10, no platform function)** | One chore to automate, no slack time, ≤$40/mo | Prescribed first workflow, minimum file set, separation math, costs | Small-team path + tutorial |
| **Engineering org (pilot → platform)** | A mandate to "do agents properly" | The phased plan (exists: `docs/plan.md`), rollout checklist | Plan (unchanged) |
| **Enterprise platform/security/compliance** | Auditor and CISO questions | Answers to §1.2's question list, crosswalk, hardening | Enterprise path |

### 3.2 Design principles

1. **One source of truth per rule.** Guide layers link to the operational
   files; they never restate rule text. A rule quoted twice will drift
   into two rules. (Mechanical check: normative phrases stay grep-unique.)
2. **The validator is the curriculum.** The tutorial teaches by making the
   reader *break* rules and read the `GE-*` errors — the rules are learned
   as encountered guardrails, not as a syllabus.
3. **Claims carry anchors.** Every benefit/statistic in the guide layer is
   cited with source and date; vendor-published numbers are flagged as
   such. Stats and regulatory dates get re-verified at implementation time
   (several moved mid-2026; they will move again).
4. **Small teams get a smaller surface, not weaker rules.** The SME path
   is a subset of the same files and the same validator. The exception
   register (with named approver and expiry) is the only relief valve —
   exactly as it is for everyone else. No "lite mode," no second
   validator.
5. **Time-to-first-green ≤ 60 minutes, measured.** From fork to a green
   `validate.py` including the reader's own first spec. The tutorial is
   rewritten until a fresh reader achieves it unaided.
6. **Meet stacks where they are.** Map repo concepts onto the primitives
   teams already run (LangGraph `interrupt()`, Temporal signals, Step
   Functions `waitForTaskToken`, Microsoft Agent Framework checkpointing,
   OpenAI approvals, Claude Agent SDK hooks, GitHub Agentic Workflows /
   plain Actions). The spec is the contract; their engine is fine.

### 3.3 Information architecture

New and changed artifacts (unmarked files are untouched):

```
README.md                            CHANGED  front door: what/why/who + three doors
AGENTS.md                            CHANGED  Phase A: add org-size question routing to a path
docs/
  what-is-graph-engineering.md       NEW      explanation: term, model, benefits, limits
  tutorial-first-workflow.md         NEW      hands-on: fork → break → first green validate
  paths/
    small-team.md                    NEW      how-to: 2–10 people
    enterprise.md                    NEW      how-to: platform/security/compliance
  faq.md                             NEW      objections, answered honestly
  glossary.md                        NEW      one home per term
  validator-errors.md                NEW      reference: GE-* code → meaning → fix
  implementation-examples.md         CHANGED  + runtime decision table + primitive crosswalk
  practical-guide-design.md          (this document — decision record)
specs/example-team/
  ci-failure-explainer.md            NEW      minimal L1 reference spec (see 3.5)
registry/agents.yaml                 CHANGED  + example-explainer-bot
registry/resources.yaml              CHANGED  + repo.issue-comments
```

Everything else — validator, schemas, governance/, runbooks, hardening,
plan, walkthrough, rollout checklist — is deliberately untouched.

### 3.4 Content specifications

**README.md (restructure, not rewrite).** First screen: one-sentence
definition ("designing and running AI-agent workflows as explicit graphs —
with the humans, budgets, and rules as versioned, CI-checked files"), a
one-line disambiguation ("not graph databases — see the primer"), the
three-sentence idea (kept), then **three doors**: *Understand it* (primer,
~15 min) / *Try it* (tutorial, ~60 min) / *Adopt it* (small-team or
enterprise path). Layout table and CI-enforcement list stay, below the
doors. "Setting this up in your organization" gains one line routing by
size.

**docs/what-is-graph-engineering.md** (~150 lines). Sections: (1) the
one-paragraph definition by artifacts — typed nodes including human gates,
edge contracts, versioned governance, CI enforcement; (2) *the name and its
neighbors* — the July 2026 moment, the three meanings, the knowledge-graph
collision, the synonym list (for readers and for search); (3) *the model in
one diagram* — a Mermaid graph of agent nodes, one gate with a timeout
edge, an anchor, a frozen instrument; (4) *benefits, each anchored to a
documented failure*: audit-trail-by-default ↔ only 31% of small firms feel
compliance-ready; enforced review capacity ↔ the approvals arithmetic and
99.7% rubber-stamp case; earned autonomy ↔ Gartner's risk-control
cancellations; frozen instruments ↔ METR's perception gap and DORA's
instability finding; identity registry ↔ shadow agents / NHI Top 10;
(5) *what this repo adds* that topology guides don't — governance as
versioned files, CI-enforced, with an exception register; corroborated by
GitHub MVG and FINOS governance-as-code; (6) *honest limits* — the
verification tax, comprehension debt, and that this framework needs ≥2
people to mean anything.

**docs/tutorial-first-workflow.md** (~200 lines). Target: 60 minutes,
zero governance decisions (defaults pre-made), ends with the reader's own
spec passing `validate.py`. Steps: (1) fork/clone, install, run the
validator green — 10 min, first success; (2) read the minimal reference
spec (`ci-failure-explainer`, §3.5) next to its ~30 frontmatter lines;
(3) **break it on purpose** — make the owner a gate reviewer
(`GE-SELF-APPROVE`), write to a frozen resource (`GE-FROZEN-WRITE`),
drop a timeout — and read each error: the top-3-errors pattern from
onboarding research, and the rules teach themselves; (4) copy the template
and write *your* chore as a spec, agent entry, and resource entries, using
a provided decision table for each field; (5) **run it by hand once** —
the reader plays the runtime: open the parent issue, do the agent step
with their coding agent, open the gate child issue, have a teammate reply
`/approve <reason>` — proving the contract before any automation exists;
(6) where to go next: wire a real runtime (implementation-examples) and
pick your path. Prerequisites box up front (trusted CI, tests worth
trusting, branch protection — DORA: AI amplifies what you already are).

**docs/paths/small-team.md** (~180 lines). The SME door. Sections:
(1) *what applies at your size* — the walkthrough's "deliberately dormant"
made explicit: the minimum live set is one spec + one agent entry + its
resource entries; anchor tables, sampling, plugins, quarterly machinery
deferred until stated triggers; (2) **the separation-of-duties table** —
at 1 person: governed gates are impossible (self-approval is non-waivable);
run drafts, use the caps/registry/kill-switch concepts, and say so
honestly; at 2: A owns, B reviews; B as backup requires the documented
small-team exception (named approver, ≤90-day expiry, renewal is an
escalation signal); timeouts are `default_deny` (escalation needs a fresh
person you don't have); at 3: fully clean — owner/backup/reviewer with
`default_deny`; at 4+: the walkthrough's full pattern including
escalation; (3) *your first workflow, prescribed* — CI-failure explainer
or release-notes drafter; explicitly not customer-facing, not
prod-writing, not five at once, with the agent-as-author review rule
stated; (4) *costs* — the §1.3 numbers, dated, tied to the spec's
`cap_per_run_usd` as the enforcement mechanism; (5) *the ladder* (§3.6)
with graduation evidence per rung; (6) *what your git history is quietly
buying you* — the disclosure/oversight compliance story, in SME terms;
(7) *comprehension debt* — the reviewer must be able to explain the
merged change; gate reasons are where that's checked.

**docs/paths/enterprise.md** (~200 lines). Structured as the §1.2 buyer
questions, each answered by pointing at an existing artifact: framework
lock-in → the spec is runtime-neutral, crosswalk table; auditor evidence →
compliance-mapping plus the corrected EU AI Act timeline (GPAI Aug 2025,
Art. 50 Aug 2026, high-risk Dec 2027/Aug 2028 post-Omnibus — with a
maintenance note to re-verify); accountability → owner/backup/DRI chain
and registries; reviewer capacity → the arithmetic plus
`metrics/gate-health.md` §6 and the review-load ceiling; safe stop →
kill-switch runbook as the Article 14 interrupt; credentials at scale →
JIT registry entries and where Entra-Agent-ID-style directory identity
slots in; adoption order (evidence-backed): registry → one high-toil
verifiable workflow → frozen instruments before any autonomy increase →
gates with contracts → earned sampling → compliance mapping; honest-ROI
section separating vendor numbers from independent measurements, with
METR/DORA as the case for frozen instruments; threat framing via OWASP
agentic Top 10 / NHI Top 10 mapped to `SECURITY.md`'s table, including
HITL flooding.

**docs/faq.md** (~80 lines). The recurring objections, answered shortly
with links: *Aren't we too small for this?* (the 2-person table); *Isn't
this bureaucracy?* (three files and a CI check; the alternative is the
40%/95% statistics); *We already use LangGraph/Temporal — why this?*
(contract vs engine); *What does it cost?*; *Can the agent ever
auto-merge?* (L3, never for `irreversible`); *Isn't this knowledge
graphs?*; *Our reviewers are already the bottleneck* (that's the finding,
not the objection — gate budgets and anchors are the treatment); *Can an
AI set this up for us?* (yes — `AGENTS.md` is its playbook).

**docs/glossary.md** (~60 lines). One-line definitions, each linking to
its authoritative file: graph engineering, node/edge, gate, gate class,
anchor (external/internal), anchor table, frozen instrument, DRI,
personal vs shared graph, oversight (full-gating/sampling), rubber-stamp,
canary, run record, gate decision, JIT credential, kill switch, exception,
orphaned spec, pathology guards, comprehension debt.

**docs/validator-errors.md.** One table row per `GE-*` code: what it
means, why the rule exists (one line, linking to the explanation), how to
fix it, whether it's waivable. Drift risk is handled in the backlog
(a `--list-codes` flag on the validator would let CI diff the doc against
the code — additive, no rule changes).

**docs/implementation-examples.md (additions).** A decision table up top
(team size / failure trigger → ticket / LangGraph / Temporal), and a
crosswalk: gate ↔ LangGraph `interrupt()` ↔ Temporal signal +
`wait_condition` ↔ Step Functions `waitForTaskToken` ↔ Agent Framework
checkpoint/HITL ↔ OpenAI Agents SDK approvals ↔ Claude Agent SDK
hooks/permission callbacks ↔ GitHub Agentic Workflows safe-outputs. The
existing three worked examples stay as-is.

**AGENTS.md (one addition).** Phase A gains a first question — org size
and path — and a pointer to `docs/paths/` so an agent deploying the repo
calibrates scope (e.g., doesn't demand an anchor table from a 3-person
team on day one, per the small-team path's deferral list).

### 3.5 The third reference spec: `ci-failure-explainer`

The two existing reference specs bracket the autonomy spectrum
(full-gating shared graph; earned-sampling personal graph). Research says
the evidenced *entry* workflow class is missing: **comment-only,
internal-facing, low blast radius** (CI-failure explanations, triage
notes). Adding it as a third validated spec gives:

- a genuinely minimal copy-me (~30 frontmatter lines) for the tutorial,
  CI-validated so it can never drift from the validator;
- the missing bottom rung of the ladder, making the three specs the
  ladder's three live rungs (§3.6);
- a worked example of **batch gating** (a weekly digest gate over the
  week's comments rather than a gate per comment) — teaching gate budgets
  and review load by example rather than assertion.

Shape: `team: example-team` (reuses alice/bob/carol/dana — no new anchor
table needed at `anchor_class: internal`), new agent `example-explainer-bot`
(JIT credentials, kill switch), new resource `repo.issue-comments`
(written only by this spec — no contention), one `quality` gate,
`timeout_hours` with `on_timeout: default_deny` (demonstrating the
3-person pattern that needs no escalation target), `status: pilot`,
`runtime: ticket`. Costed small (`cap_per_run_usd: 1`) to model the
"$15–25/month for the whole suite" reality. Prose sections stay short —
its job is to be readable in one sitting. Validator must pass with zero
new exceptions; the example register stays empty.

### 3.6 The maturity ladder (presentation, not mechanics)

A self-locating device for readers, used by both paths and the FAQ. Each
rung maps to *existing* repo mechanics — the ladder adds no new states,
fields, or validator behavior:

| Rung | The agent may… | Repo mechanics | Live example | Graduation evidence (existing rules) |
|------|----------------|----------------|--------------|--------------------------------------|
| L0 | nothing yet — humans do the chore | none (write the spec as `draft`) | — | a spec exists and validates |
| L1 | suggest: comments, drafts, digests | comment-class writes, quality gate, `full-gating` | `ci-failure-explainer` (new) | 4 weeks of gate metrics, cost baseline |
| L2 | act behind a gate on every run | side-effect writes, `full-gating`, gate classes | `weekly-release-review` | anchor coverage + 4 weeks in-band metrics (`decision-rights.md`) |
| L3 | act with sampled oversight | `oversight: sampling` + external anchors; `irreversible`/`external` gates stay at 100% | `dependency-update-triage` | continued anchor movement; automatic demotion path: revert to `full-gating` by PR |

The ladder's rules are already the repo's rules; the table just makes the
progression visible and citable (it matches the CSA/graduated-oversight
pattern in §1.2, which the guide cites for external validation).

---

## 4. Implementation plan

Three PRs, each independently valuable and mergeable; the design merges
first as the record. Re-verify all dated statistics, prices, and
regulatory dates at writing time (several changed mid-2026).

**PR 1 — Front door** (docs only; no validated surfaces): primer,
glossary, FAQ, README restructure. Acceptance: README first screen
answers what/why/who; every claim cited and dated with vendor numbers
flagged; no normative rule text duplicated from operational files.

**PR 2 — Small-team on-ramp**: `paths/small-team.md`, tutorial,
`ci-failure-explainer` spec + registry entries, AGENTS.md Phase A
addition. Acceptance: `validate.py` exits 0 with zero new exceptions;
the separation-math table verified against the validator by constructing
each failing variant locally and observing the expected `GE-*` code; a
fresh reader (someone who hasn't seen the repo) completes the tutorial
unaided in ≤60 minutes — rewrite until true.

**PR 3 — Enterprise on-ramp + reference**: `paths/enterprise.md`,
implementation-examples decision table + crosswalk, `validator-errors.md`.
Acceptance: every §1.2 buyer question has a section; every `GE-*` code
emitted by `scripts/validate.py` has a row (grep the source for the
canonical list); crosswalk claims spot-checked against current vendor
docs.

**PR 4 — Reference runner** (added by amendment, §8): a minimal reference
implementation of the ticket runtime (`scripts/ticket_runner.py`, no new
dependencies) that executes a spec's run lifecycle — start a run, record a
gate decision, complete with a run record — emitting artifacts validated
against `schemas/gate-decision.schema.json` and
`schemas/run-record.schema.json`. Acceptance: an end-to-end run of the
minimal reference spec produces schema-valid records; the GitHub-issues
wiring stays documented prose in `implementation-examples.md`, not code.

**Backlog** (explicitly not now): `--list-codes` flag on the validator so
CI can diff `validator-errors.md` against the code (additive; goes
through normal review since it touches `scripts/`); enabling GitHub's
"template repository" setting (a human admin task — one line in
platform-hardening's setup notes); a business-ops substrate appendix
(n8n/Zapier under the same spec format) if non-engineering demand shows
up; real adopter case studies; a docs site if the repo outgrows GitHub
rendering.

## 5. Non-goals and invariants

- **No rule changes.** The validator, schemas, non-waivable rules
  (`GE-FROZEN-WRITE`, `GE-SELF-APPROVE`), and decision rights are out of
  scope and unchanged. This design adds explanation, not policy.
- **No "SME edition."** One repo, one validator, one rule set; the paths
  differ in *scope and sequencing*, never in strictness.
- **No duplicated normative text.** Guide layers link; operational files
  remain the single source of truth.
- **No uncited claims, no unflagged vendor numbers** in any guide layer.
- **No live example exceptions.** `governance/exceptions.yaml` stays
  empty in the shipped repo (entries expire and would fail CI for every
  fork); patterns are shown as comments and prose only.

## 6. How we'll know the guide works

Applying the repo's own gate-health ethos to its documentation:

1. **Time-to-first-green ≤ 60 min** — a fresh reader forks, runs the
   validator, and lands their own passing spec using only the tutorial.
   Measured by watching someone, per the onboarding research.
2. **First-screen test** — a newcomer reading only README's first screen
   can say what this is, why it exists, and which door is theirs.
3. **Anchored claims** — spot-check: every statistic in the guide layer
   has a source and date; vendor numbers flagged.
4. **No drift** — normative phrases grep-unique to their operational
   file; `validator-errors.md` rows match the `GE-*` codes in
   `scripts/validate.py` (mechanized when `--list-codes` lands).
5. **Three rungs live** — the three example specs validate green and
   correspond to ladder rungs L1/L2/L3.

## 7. Sources (primary, as researched 2026-08-20)

Adoption and failure: McKinsey State of AI (Nov 2025) · LangChain State
of Agent Engineering (Dec 2025) · Gartner agentic-AI cancellation
prediction (2025-06-25) · MIT NANDA "GenAI Divide" (Aug 2025; methodology
contested) · Deloitte TMT Predictions (Nov 2024) · Klarna reversal
coverage (May 2025) · Replit incident coverage (July 2025).

SME reality: US Chamber of Commerce "Empowering Small Business"
(2025-08-18) · Intuit QuickBooks Small Business Insights (Apr/Jul 2025)
[vendor] · US Census BTOS via 2025–26 compilations · OECD "AI adoption by
SMEs" (Dec 2025) · MBIE NZ SME AI survey (Apr 2025) · MYOB Business
Monitor 2026 [vendor] · JPMorgan Chase Institute on small-firm AI spend
(2025) · practitioner report: GitHub Actions + Claude suite (dev.to;
single datapoint).

Oversight economics and evidence: METR developer RCT (2025-07-10; labeled
historical) · DORA 2025 (Dec 2025) · HackerNoon oversight-fatigue
arithmetic (2026) · Approval-fatigue case (aipatternbook.com) ·
Parasuraman & Riley automation complacency (1997) · OWASP Agentic Threats
& Mitigations (Feb 2025) / Top 10 for Agentic Applications (Dec 2025) /
NHI Top 10 (2025) · CSA autonomy levels (2026-01-28) · graduated-oversight
literature (arXiv 2606.22484) · Anthropic "How AI Is Transforming Work at
Anthropic" (2025-12-02) [vendor] · Anthropic Economic Index (Sept 2025)
[vendor].

Term and tooling: The AI Operator field guide to graph engineering (Jul
2026) · v12labs explainer (2026-08-17) · LangChain "3 Years of Graph
Engineering" (Jul 2026) [vendor] · TrueFoundry enterprise guide
(2026-07-20) [vendor] · Berkeley BAIR compound-AI-systems framing (2024)
· LangGraph HITL/`interrupt()` docs · Temporal + OpenAI Agents SDK GA
(2026-03-23) · AWS Bedrock AgentCore GA (Oct 2025) · Microsoft Agent
Framework (Oct 2025→2026) · Google ADK / A2A to Linux Foundation (Jun
2025) · OpenAI Agents SDK approvals docs · Claude Agent SDK
hooks/permissions · GitHub Agentic Workflows (2026-02-13) · GitHub
Environments approval gates · n8n HITL docs.

Governance and compliance: EU AI Act Article 14; Digital Omnibus timeline
analyses (Gibson Dunn; Travers Smith, 2026) · NIST AI RMF + AI 600-1
(Jul 2024) · ISO/IEC 42001 (+ 42006:2025); CSA certification-intent
survey (2025) · Microsoft Entra Agent ID (May 2025→GA Apr 2026) · MCP
spec security update (Nov 2025) and injection research (Apr–May 2025) ·
NSA/CISA CSI on AI-driven automation (Jun 2026) · Singapore IMDA agentic
governance framework (Jan 2026) [secondary] · GitHub Minimum Viable
Governance · FINOS AI Governance Framework v2 / Governance-as-Code.

Docs craft: Diátaxis (Procida) · Sequin quickstart case study ·
API-onboarding TTFC benchmarks · Microsoft Engineering Fundamentals
Playbook.

---

## 8. Amendment v1.1 (2026-08-20): second-review synthesis

The repository owner solicited an independent review of the repo's
positioning from a separate session and asked for it to be reconciled with
this design. Its diagnosis (reference implementation ≠ guide; on-ramp wall;
uncited claims; term positioning) converges with §2 of this document.
Beyond the overlap, the following deltas are **adopted**:

1. **LICENSE (blocking adoption bug — the review's best catch).** The repo
   had no license, making it all-rights-reserved by default and legally
   contradicting "copy/fork this repo into your org." Resolution: owner
   selected **Apache-2.0** (explicit patent grant; contributions default to
   the project license; the norm for adopt-this-framework repos). Ships
   with this amendment.
2. **Repo About/topics.** GitHub description and topics were empty, so the
   synonym strategy (§3.4 primer) never reached GitHub search. These are
   repository settings, not files — the owner applies them; the
   implementation PR supplies the exact strings.
3. **Reference runner (new PR 4, §4).** "The repo never executes a
   workflow" is fair: specs validate but nothing runs. A ~200-line,
   dependency-free reference implementation of the ticket runtime makes the
   contract demonstrably executable without violating the plan's "no
   bespoke orchestration platform before ticket-based state has failed" —
   it *is* the ticket-based state, in its simplest form.
4. **GRC positioning question** added to the enterprise path's buyer
   questions: "why does this live in a repo instead of our GRC tooling?"
   (Answer to write: GRC platforms record attestations; this repo *is* the
   control — the PR gate and validator are the enforcement point, and GRC
   imports its evidence from here.)
5. **`docs/plan.md` citation retrofit** (folded into PR 3). The plan's
   "What the research says" carries uncited field estimates (e.g. "2-3
   agents per operator; 10-20 with an operator surface"). For a repo whose
   pitch is auditability, uncited empirical claims undercut the brand:
   add a sources appendix mapping each claim to the §7 evidence, and
   soften what cannot be sourced into stated planning assumptions.
6. **Adopter-first sequencing.** "A framework with one documented
   deployment beats a polished framework with zero." Adopted as sequencing,
   not replacement: PRs 1-2 are the runway a first pilot team needs; the
   tutorial's fresh-reader acceptance test is a micro-pilot; the first
   real pilot's four weeks of gate metrics become the case study that
   replaces the fictional walkthrough team (backlog: case studies).
7. **Positioning line.** The review's sharpest framing — this is *a linter
   for your agent fleet's governance*, positioned the way OPA/Conftest is
   for infrastructure — is adopted as README/primer language. Packaging
   the validator as a standalone installable tool is **deferred to
   backlog**, gated on external adopter demand: for a repo with zero
   external adopters, the fork-the-repo model already ships the validator
   with the files it validates, and productizing first would violate the
   plan's own "no platform before the simple thing fails" rule.

One recommendation is **declined: validation profiles** (`profile:
starter` enforcing a subset and warning on the rest). Reasons, recorded so
the decision isn't relitigated by default: (a) the review's own thesis is
that the validator's unambiguous red/green is the product — a warn-mostly
profile dilutes exactly that; (b) the repo already has a relief valve with
strictly better properties (`governance/exceptions.yaml`: named approver,
≤90-day expiry, CI-checked), whereas a profile is a standing, unaudited,
never-expiring exception — the shape `SECURITY.md` threat #4 exists to
prevent; (c) the wall it targets is Phase-0 *sequencing*, which the
small-team path fixes by deferral, not relaxation. Revisit only with
evidence that teams bounce off the validator itself rather than the docs,
and treat any such change as a validator design change with full review.

Factual corrections to the second review, for the record: it read three
files — `docs/walkthrough.md` (the "worked walkthrough" it reported
missing) exists, and its "graph engineering is not an established term"
predates the term's July 2026 emergence documented in §1.1. Its LICENSE,
About/topics, runnable-artifact, and adopter-first points stand
regardless and are adopted above.
