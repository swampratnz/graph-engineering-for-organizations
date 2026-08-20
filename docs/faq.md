# FAQ

The objections and questions that actually come up, answered short.
Rules referenced here live in the linked files; this page never overrides
them.

**Aren't we too small for this?**
The framework's honest floor is two people, and it runs comfortably at
three — most of the machinery is deliberately dormant at small scale (a
spec, two registry entries, one gate issue a week). The
[small-team path](paths/small-team.md) has the exact table of who can
hold which role at 1, 2, 3, and 4+ people. What a small team *shouldn't*
do is pretend: a solo operator cannot review their own gates, and the
validator won't let you paper over that.

**Isn't this just bureaucracy?**
The steady-state overhead is three kinds of files and one CI check;
running a workflow is a parent issue and a gate issue. Compare the
documented alternative: [~40% of agentic projects predicted canceled over
risk controls and unclear value](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027),
[~95% of GenAI pilots with no measurable
return](https://fortune.com/2025/08/18/mit-report-95-percent-generative-ai-pilots-at-companies-failing-cfo/).
The paperwork here is the treatment for the specific ways these projects
die — and every piece of it (gate reasons, run records) is data you'll
want anyway the first time something goes wrong at 2am.

**We already use LangGraph / Temporal / Step Functions. Why this?**
Different layer. Those are *engines*; this repo is the *contract* above
them — who owns the workflow, who reviews what, what it may spend and
touch, and CI that keeps all of that coherent. The spec's `runtime` field
names your engine; the [crosswalk](implementation-examples.md) maps gate
contracts onto each engine's pause/approve primitive. Adopting this
changes none of your orchestration code.

**Is this about knowledge graphs / Neo4j?**
No. Same words, different field — see
[the primer](what-is-graph-engineering.md#the-name-and-its-neighbors).
No graph database is involved.

**What does it cost?**
The governance layer itself: a git repo and a CI job. The workflows:
model spend is capped per run by each spec (`cap_per_run_usd`), and the
documented small-team reality is modest — most AI-paying small firms
spend [≤$40/month](https://www.jpmorganchase.com/institute/all-topics/business-growth-and-entrepreneurship/understanding-ai-use-by-small-businesses)
(JPMC Institute, 2025); one practitioner's four-workflow GitHub Actions
suite ran [$15–25/month in API costs](https://dev.to/whoffagents/github-actions-claude-code-i-automated-my-entire-dev-workflow-4h0h).
Numbers and dates in [the small-team path](paths/small-team.md).

**Can the agent ever act without a human?**
Yes — that's the point of the autonomy model, and it's earned, not
assumed: external anchors plus four weeks of in-band gate metrics unlock
*sampling* oversight ([decision rights](../governance/decision-rights.md)),
and [`dependency-update-triage`](../specs/example-team/dependency-update-triage.md)
shows the full paper trail. Two things never go unattended:
`irreversible` and `external` gate classes keep 100% review under any
oversight mode.

**Our reviewers are already the bottleneck.**
That's not an objection — that's the founding premise. Review capacity,
not model capability, is the binding constraint on fleet size
([plan](plan.md)), so gates carry budgets, timeouts, and health metrics,
and the sanctioned fix for an overloaded gate is *fewer, better gates or
more anchors* — never quietly stopping review. If your override rate sits
at ~0%, the gate is already dead; [measure it](../metrics/gate-health.md)
and fix it deliberately.

**Why won't the validator let us waive X even though everyone agrees?**
Most rules *are* waivable — by an [exception](../governance/exceptions.yaml)
with a named approver and an expiry, which is agreement made auditable.
Exactly two never bend: writes to frozen instruments and owners approving
their own outputs ([SECURITY.md](../SECURITY.md)). Both exist because the
failure they prevent (gamed metrics, self-certified work) is invisible
from inside while it's happening.

**Why isn't there a relaxed "starter mode"?**
Considered and declined — the reasoning is recorded in the
[design decision record](practical-guide-design.md#8-amendment-v11-2026-08-20-second-review-synthesis).
Short version: a warn-only profile is a standing, unaudited exception;
the honest relief valve for small teams is the exception register, and
the honest on-ramp is a smaller *scope* (one spec, machinery dormant),
not weaker rules. Green means one thing here.

**How does this relate to our GRC / compliance tooling?**
GRC platforms record attestations; this repo is the *control itself* —
the PR gate and validator are the enforcement point, and your GRC tool
imports its evidence (specs, run records, exception register) from here.
The [enterprise path](paths/enterprise.md) and
[compliance mapping](../governance/compliance-mapping.md) cover the
crosswalk to EU AI Act, NIST AI RMF, ISO/IEC 42001, and SOC 2.

**Can an AI agent set this up for our org?**
Yes — that's a designed path, not a hack: point any capable coding agent
at this repo and [`AGENTS.md`](../AGENTS.md) is its playbook, with the
hard rule that it gathers your org's facts from humans instead of
inventing them.

**Where do I actually start?**
[The tutorial](tutorial-first-workflow.md) — about an hour to your own
first validated spec — then [your size's path](paths/small-team.md)
([enterprise](paths/enterprise.md)).
