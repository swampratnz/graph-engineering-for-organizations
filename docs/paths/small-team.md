# The small-team path (2–10 people)

For teams with no platform function, no compliance department, and no
slack time: what applies at your size, what to defer, what it costs, and
the honest math on who can review what. Everything here is the same
rules and the same validator as the enterprise path: smaller *scope*,
never weaker rules.

## What's live at your size, what's dormant

**The minimum live set**, enough for CI to be green and the governance
to be real:

- One GRAPH SPEC (yours, from the [tutorial](../tutorial-first-workflow.md))
- Its agent entry in [`registry/agents.yaml`](../../registry/agents.yaml)
  (owner, JIT credential description, kill switch, review date)
- Its resource entries in [`registry/resources.yaml`](../../registry/resources.yaml)
- Real handles in [`.github/CODEOWNERS`](../../.github/CODEOWNERS), and
  branch protection with the `validate` check required
  ([platform hardening](../platform-hardening.md) covers the four
  repository settings; skip the SIEM/audit-log-streaming items until
  something routes money or production)

**Deliberately dormant**, each with the trigger that wakes it:

| Dormant machinery | Wake it when |
|-------------------|--------------|
| Anchor tables ([`governance/anchors/`](../../governance/anchors/TEMPLATE.md)) | You want *sampling* oversight; anchors are how autonomy is earned. Until then `anchor_class: internal` + full gating is the honest claim |
| Shared plugin library, shared-services role ([plan Phase 1](../plan.md)) | You have 3–5 workflows and a second team wants them |
| Metrics tooling | Issue timestamps and a monthly eyeball are the metrics pipeline until the numbers get big enough to argue about |
| [Compliance mapping](../../governance/compliance-mapping.md) | A customer, insurer, or regulator asks; then it's a crosswalk you fill from records you already have |
| [Quarterly spec review](../runbooks/quarterly-spec-review.md) | Calendar it now; at this size it's ~30 minutes to re-confirm owners, bump `review_by` dates, and prune exceptions |

## The separation-of-duties math

The framework's one rule that bites at small scale: **whoever builds a
workflow, someone else approves its outputs**. The owner rule is
non-waivable, the backup rule waivable by exception. Verified against the
validator, size by size:

| People | Shape | What the validator says |
|--------|-------|-------------------------|
| **1** | not possible | **And honestly so.** The schema requires a distinct `backup_owner`, and the owner reviewing their own gates is never waivable (`GE-SELF-APPROVE`). Solo: use the concepts (caps, registry, kill switch, run records) and keep `status: draft`, find one outside reviewer, or don't pretend |
| **2** | A owns, B backup **and** reviewer; every gate `on_timeout: default_deny` | Runs, with one exception (`GE-BACKUP-APPROVE`). Here's the catch the validator enforces: **neither A nor B may approve that exception** (`GE-EXC-SELF` voids it). You need one outside human (an advisor, a fractional security-owner, a trusted peer) as the named approver, re-confirming every ≤90 days. That forced quarterly outside glance is a feature, not a bug |
| **3** | A owns, B backup, C reviews; `on_timeout: default_deny` | **Fully clean, zero exceptions.** This is the framework's real self-contained floor. Escalation isn't available (it needs a fresh fourth person), so `default_deny` fails safe instead |
| **4+** | A owns, B backup, C reviews, D takes escalation | The full pattern, the [walkthrough's](../walkthrough.md) alice/bob/carol/dana team |

The two-person exception, concretely (in
[`governance/exceptions.yaml`](../../governance/exceptions.yaml); keep
the register empty until you actually need it):

```yaml
# - id: EX-2026-002
#   target: <your-spec-name>
#   code: GE-BACKUP-APPROVE
#   reason: >
#     Two-person team; the backup is the only possible reviewer.
#     Outside approver re-confirms quarterly.
#   approved_by: [<outside-human-handle>]   # not the owner, not the backup
#   granted: 2026-08-20
#   expires: 2026-11-18                     # <= 90 days; renewal is deliberate
```

One more small-team fact in your favor: **when the agent authors the
work, one human reviewer who didn't trigger the run already constitutes
independent review**. That's what branch protection's "author cannot
approve their own PR" encodes, and it's why two people plus a bot is a
sturdier review structure than two people alone ever was.

## Your first workflow

Prescribed, not a menu. The evidence says pick **one** narrow,
recurring, internal-facing chore and measure it: in
[MIT's study of failed pilots](https://fortune.com/2025/08/18/mit-report-95-percent-generative-ai-pilots-at-companies-failing-cfo/)
(Aug 2025; methodology contested), the winners picked one pain point
and executed well, while MIT attributes most failures to a learning
gap: generic tools bolted on without adapting to the workflow.
Best-evidenced starters:

| Workflow | Why it works first |
|----------|--------------------|
| **CI-failure explainer** ([bundled reference](../../specs/example-team/ci-failure-explainer.md)) | Suggest-only; blast radius = one misleading comment; high frequency; saves the log spelunk |
| Release-notes drafter ([reference](../../specs/example-team/weekly-release-review.md)) | Weekly cadence; write-behind-a-gate; output already gets reviewed anyway |
| Dependency digest / update triage ([reference](../../specs/example-team/dependency-update-triage.md)) | High toil, externally measurable, the canonical earned-autonomy story |
| Support-ticket triage notes | Same suggest-only shape as the explainer, for teams whose pain is the queue |

Explicitly **not** first: anything customer-facing (the
[Klarna reversal](https://www.forbes.com/sites/quickerbettertech/2025/05/18/business-tech-news-klarna-reverses-on-ai-says-customers-like-talking-to-people/)
is the cautionary tale), anything writing to production, and not three
workflows at once. And hold the prerequisite line: CI you trust, tests
worth trusting, branch protection on.
[DORA 2025](https://dora.dev/dora-report-2025/): AI amplifies what your
team already is.

## What it costs

Publish-date numbers (2025–2026; re-check before budgeting):

- Most AI-paying small firms spend **≤$40/month** total
  ([JPMorgan Chase Institute, 2025](https://www.jpmorganchase.com/institute/all-topics/business-growth-and-entrepreneurship/understanding-ai-use-by-small-businesses)).
- One practitioner's four-workflow GitHub Actions + Claude suite for a
  3–5 dev team: ~4 hours setup, ~3–4 hours/week saved, **$15–25/month**
  in API costs
  ([report](https://dev.to/whoffagents/github-actions-claude-code-i-automated-my-entire-dev-workflow-4h0h);
  single datapoint, consistent with API-rate math).
- Subscription seats (Copilot, Claude) run $10–40/user/month at standard
  tiers. Note the industry shift toward usage-based billing for
  agent-heavy use, which is exactly why every spec carries
  `cap_per_run_usd` and an alert threshold. The cap is not paperwork;
  it's the mechanism that makes the bill boring.

Measure before you scale: run a two-week before/after on one number
(hours on the chore, time-to-merge). Self-perception is documented to be
untrustworthy:
[METR's trial](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
found developers 19% slower while believing they were 20% faster.

## The ladder up

Autonomy is earned per workflow, by PR, with evidence, never by vibes.
The three bundled specs are the rungs, live:

| Rung | The agent may… | Live example | To graduate |
|------|----------------|--------------|-------------|
| L0 | nothing yet | your spec at `status: draft` | it validates |
| L1 | suggest: comments, drafts, digests | [`ci-failure-explainer`](../../specs/example-team/ci-failure-explainer.md) | 4 weeks of gate metrics, cost baseline ([decision rights](../../governance/decision-rights.md)) |
| L2 | act, behind a gate on every run | [`weekly-release-review`](../../specs/example-team/weekly-release-review.md) | external anchors + 4 weeks in-band override rate |
| L3 | act with sampled oversight; `irreversible`/`external` gates stay at 100% | [`dependency-update-triage`](../../specs/example-team/dependency-update-triage.md) | keep earning it; degradation → revert to full gating by PR |

## What your git history is quietly buying you

Only [31% of small firms feel prepared](https://www.uschamber.com/technology/empowering-small-business-the-impact-of-technology-on-u-s-small-business)
for AI rules that require disclosure, risk assessment, and human
oversight (US Chamber, Aug 2025). Running this framework, you already
have the answers the checklists ask for: an inventory of every agent
with a named owner (the registry), proof of human oversight (gate
decisions with reasons), spend control (caps in every spec), an
off-switch (kill-switch runbook), and change control (everything by
reviewed PR). When a customer or insurer asks, that's the evidence pack.
See the [FAQ](../faq.md) and, when you genuinely need it, the
[compliance mapping](../../governance/compliance-mapping.md).

## Keeping comprehension

The failure mode that sneaks up on agent-heavy small teams is merging
work nobody can explain. Two habits, both already in the contract: the
gate's **reason field is mandatory** ("LGTM" is not a resolution), and
the reviewer should be able to walk through the change out loud before
approving. Weekly, the owner glances at three numbers from issue
timestamps (gate latency, override rate, cost per run;
[definitions](../../metrics/gate-health.md)). Ten minutes, and it's the
whole health check at this size.

*Next:* do the [tutorial](../tutorial-first-workflow.md) if you haven't;
watch the [walkthrough](../walkthrough.md) team operate; and when a
second team wants your workflows or someone says "audit," switch to the
[enterprise path](enterprise.md).
