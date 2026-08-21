# The enterprise path

Structured as the questions platform, security, and compliance teams
actually bring to agent-fleet governance, each answered by an artifact
that already exists in this repo. Context stats are dated;
vendor-published numbers are flagged. The peer numbers: 23% of
organizations are scaling agents in at least one function
([McKinsey, Nov 2025](https://www.mckinsey.com/~/media/mckinsey/business%20functions/quantumblack/our%20insights/the%20state%20of%20ai/november%202025/the-state-of-ai-2025-agents-innovation_cmyk-v1.pdf)),
57% of surveyed builders have agents in production
([LangChain, Dec 2025](https://www.langchain.com/state-of-agent-engineering)),
and [Gartner predicts >40% of agentic projects canceled by
end-2027](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027)
for costs, unclear value, and inadequate risk controls. This path exists
to keep you out of that 40%.

## "Which framework do we standardize on? Are we locked in?"

Wrong layer for lock-in. This repo is the *contract* (ownership, gates,
budgets, resources, autonomy evidence), and your orchestration framework
is an implementation detail named in one frontmatter field (`runtime`).
Every major engine now ships the pause/approve primitive a gate needs;
the [crosswalk](../implementation-examples.md#runtime-crosswalk) maps the
gate contract onto LangGraph `interrupt()`, Temporal signals, Step
Functions `waitForTaskToken`, Microsoft Agent Framework checkpoints,
OpenAI Agents SDK approvals, and Claude Agent SDK hooks. Teams on
different engines can share one governance layer, and switching engines
is a `runtime` edit plus re-wiring, not a governance migration.

## "What do we show the auditor, and by when?"

The [compliance mapping](../../governance/compliance-mapping.md) maps
each artifact here (specs, registries, run records, gate decisions,
exception register) onto the **EU AI Act, NIST AI RMF (+ the GenAI
Profile, AI 600-1), ISO/IEC 42001, and SOC 2**. That artifact-to-clause
table is what compliance teams actually ask for.

Timeline as of 2026-08 (re-verify before relying on it; these dates
moved once already): EU AI Act GPAI obligations have applied since
**2 Aug 2025**; Article 50 transparency since **2 Aug 2026** (with a
transitional period to **2 Dec 2026** for the machine-readable marking
duties under Art. 50(2) on systems already on the market); and the
Digital Omnibus, now
[**Regulation (EU) 2026/1744**](https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng)
(Official Journal 24 Jul 2026, in force 27 Jul 2026), postponed
high-risk obligations to **2 Dec 2027** (Annex III) and **2 Aug 2028**
(Annex I)
([summary](https://www.hunton.com/privacy-and-cybersecurity-law-blog/eu-digital-omnibus-on-ai-enters-into-force)).
[Article 14](https://artificialintelligenceact.eu/article/14/), human
oversight with the real ability to intervene and interrupt to a safe
state, is the regulatory mirror of this repo's gate contracts and kill
switches. ISO/IEC 42001 intent is widespread
([76% of surveyed orgs plan to pursue
it](https://cloudsecurityalliance.org/), CSA 2025); its logging control
maps to the [run record](../../schemas/run-record.schema.json). The
strategic point: the audit plane here is a *by-product of normal
operation*. Building it now is cheap; retrofitting it under a deadline
is not.

## "Why does this live in a repo instead of our GRC tooling?"

Because GRC platforms *record attestations*; this repo **is the
control**. The PR gate plus the required `validate` check is the
enforcement point: a spec that violates policy cannot merge, which is a
stronger statement than a quarterly attestation that policy exists. Your
GRC tool then imports evidence from here (merged specs, run records,
the exception register with its approvers and expiries) instead of
collecting screenshots. This is the
[governance-as-code](https://ai.finos.org/governance-as-code/) pattern
FINOS formalized for financial services: machine-readable policy,
validated in CI, versioned next to what it governs.

## "Who is accountable when an agent causes an incident?"

Nameable in seconds, from files: every spec has an `owner` (the Workflow
DRI, holding quality, cost, and gate design) and `backup_owner`; every
agent identity has a human `owner` and named kill-switch holders
([registry](../../registry/agents.yaml)); every gate decision records
who approved what, when, and why. The
[incident runbook](../runbooks/incident-response.md) starts from those
files, and [decision rights](../../governance/decision-rights.md) settles
the rest (stop needs no approval; restart does). The inverse case is the
one to fear: an unregistered shadow agent, nobody's inventory, nobody's
owner, doing something nobody can stop (the identity-risk class the
[OWASP NHI Top 10](https://owasp.org/www-project-non-human-identities-top-10/)
catalogs).

## "How many reviewers does a fleet need, and when can the human come out?"

Do the arithmetic before the rollout plan does it to you: 50 agents × 20
tool calls/hour with 10% routed to humans is
[~100 approvals/hour, several FTEs of pure
approving](https://hackernoon.com/the-oversight-fatigue-problem-why-hitl-breaks-down-at-scale-and-what-comes-after).
Unmanaged, gates die quietly; one documented team hit a
[99.7% approval rate by day three](https://aipatternbook.com/approval-fatigue).
This repo's plan assumes review capacity is the binding constraint
([plan](../plan.md)) and manages it as a first-class metric:
[review load per person](../../metrics/gate-health.md) against the 10–20
supervised-agent ceiling, override-rate bands, and rubber-stamp
detection with canaries.

The human comes out **per workflow, on evidence**: external anchors plus
four weeks of in-band gate metrics unlock sampling
([decision rights](../../governance/decision-rights.md)), `irreversible`
and `external` gates keep 100% review regardless, and degradation
reverts the spec to full gating by PR. This is the published consensus
pattern (oversight tiered by risk and reversibility, promotion on
recorded evidence:
[CSA autonomy levels, Jan 2026](https://cloudsecurityalliance.org/blog/2026/01/28/levels-of-autonomy)),
with a paper trail
([worked example](../../specs/example-team/dependency-update-triage.md)).
One adversarial case your gate design must anticipate: OWASP classifies
[deliberately flooding human gates](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
(train the rubber-stamp, then slip the payload) as an attack.

## "How do we stop a running agent safely?"

Every agent registers a [kill switch](../runbooks/kill-switch.md) with
named holders before it gets credentials: stop requires no approval,
restart does, and the drill is quarterly. Specs declare idempotency keys
on side-effect nodes so a halt mid-run leaves resumable, non-duplicating
state, which is the "interrupt to a safe state" that
[EU AI Act Article 14](https://artificialintelligenceact.eu/article/14/)
asks you to demonstrate.

## "How do agents get credentials without a thousand service accounts?"

One identity per agent, **JIT only**: OIDC exchange or per-agent App
installation tokens, ≤1h TTL, scopes enumerated in the registry entry,
and CI errors on any active agent with standing credentials
(`GE-CRED-STANDING`). Extend your existing IAM/PAM rather than building
a parallel stack; the industry is converging on agents as first-class
directory principals with no standing secrets
([Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/),
GA 2026), and the long-lived-credential failure class tops the
[OWASP Non-Human Identities Top 10](https://owasp.org/www-project-non-human-identities-top-10/).
[Platform hardening](../platform-hardening.md) has the issuance
patterns. The registry documents intent, the IAM enforces it, and
reconciling the two is the
[known-gap automation](../rollout-checklist.md#phase-3-backlog-scheduled-not-started)
to build after the pilot.

## "In what order do we adopt this?"

The sequence the evidence supports, mapped to the
[rollout checklist](../rollout-checklist.md):

1. **Inventory + registry first** (Phase 0). You cannot govern agents
   you don't know exist. Kill switch tested on one real agent.
2. **One high-toil, easily verifiable workflow** (Phase 1–2 pilot): code
   review support, dependency updates, incident triage. Not
   customer-facing autonomy
   ([Klarna's reversal](https://www.forbes.com/sites/quickerbettertech/2025/05/18/business-tech-news-klarna-reverses-on-ai-says-customers-like-talking-to-people/)),
   not production write access (Replit's July 2025 database deletion).
3. **Frozen instruments before any autonomy increase.** The measured
   reason: perceived and actual results diverge
   ([METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/):
   19% slower while believing 20% faster), and throughput gains arrive
   with instability ([DORA 2025](https://dora.dev/dora-report-2025/)).
   Teams under pressure will relax the instrument; freeze it first.
4. **Gates with contracts, metrics from week one** (Phase 2). The pilot
   success gate is four numbers, not a demo.
5. **Earned sampling** (Phase 3): anchors + evidence, per workflow.
6. **Compliance crosswalk last**, filled from records you already have.

## "What ROI do we tell the CFO?"

Separate the two ledgers. Vendor-published: Uber ~21,000 developer hours
saved on migrations [vendor], Groupon review-to-production 86h→39min
[vendor], high autonomous-resolution rates from platform vendors
[vendor]. Independent: AI code reviewers catch
[18–46% of real bugs](https://www.greptile.com/benchmarks) in third-party
benchmarks; [METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
measured experienced developers slower while feeling faster;
[DORA](https://dora.dev/dora-report-2025/) finds throughput up *with*
instability up. So: commit to measuring **defect density, delivery
instability, and post-merge incidents** alongside throughput, per
workflow, against its anchor. That's the
[gate-health scoreboard](../../metrics/gate-health.md), and it's the
difference between an ROI story that survives a senior engineer's
scrutiny and one that doesn't. A credible internal comparison: Anthropic
reports ~27% of Claude-assisted work is *new capacity* rather than
speedup ([Dec 2025](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic))
[vendor]. Capacity framing often survives scrutiny better than speed
framing.

## "What threats does this cover?"

The [SECURITY.md threat model](../../SECURITY.md) maps eight threats to
their controls; cross-reference it with the
[OWASP Top 10 for Agentic Applications
(Dec 2025)](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/):
identity/privilege abuse → registries + JIT + kill switches; tool misuse
and goal hijacking → resource declarations + gates on
`external`/`irreversible` actions + minimum-context gate inputs;
cascading multi-agent failures → pathology guards; supply chain →
SHA-pinned CI. Prompt injection through processed data is the one risk
no spec fixes; treat gate contracts and blast-radius limits as the
mitigation, not any filter.

## What the platform team owns at steady state

The [hardening checklist](../platform-hardening.md) applied and
re-verified quarterly; the weekly scheduled `validate` run (decay
surfaces without traffic); the [quarterly
review](../runbooks/quarterly-spec-review.md) (recertification, kill
drill, exception pruning); and the registry-vs-IAM reconciliation job
when you build it. Everything else belongs to workflow owners; that
separation is the [operating model](../plan.md#operating-model).

*Scaling in from a smaller footprint? The [small-team
path](small-team.md) is the same rules with most machinery dormant,
useful for your first pilot team even inside a large org.*
