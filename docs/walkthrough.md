# Walkthrough: a three-person team on a live repo

The fastest way to understand this repo is to watch a small team use it.
Say **alice**, **bob**, and **carol** run a live product repo (call it
`acme-app`) and want an AI agent to take over a recurring chore.

## The mental model: two repos

The live repo (`acme-app`) stays exactly what it is — code, CI, deploys.
Nothing in it changes.

This repo is the **rulebook and paper trail** for any AI agents let loose on
that live repo. Before an agent gets to do a job, three things about it must
be written down here: *who owns it* (a spec), *what identity it runs as*
(the agent registry), and *what it's allowed to touch* (the resource
registry). CI checks the paperwork is coherent — it will literally fail the
build if alice writes a workflow spec and also lists herself as the person
who approves its output.

The point at three-person scale: when an agent does something weird at 2am,
you can answer "what was it, who owns it, how do I stop it, and what did it
actually do" from files in git instead of from memory.

## A concrete run-through

The chore: every Friday, an agent drafts the week's release notes from
merged PRs and publishes them, with human sign-off before anything goes
public. (This is the bundled reference spec,
[`specs/example-team/weekly-release-review.md`](../specs/example-team/weekly-release-review.md)
— read it side by side with this.)

**Step 1 — alice writes the spec (about 30 minutes, one PR).**
She copies [`specs/TEMPLATE.md`](../specs/TEMPLATE.md) and fills in the
frontmatter. The important lines in plain English:

- `owner: alice` — alice is on the hook for quality and cost.
- `backup_owner: dana` — who takes over when alice is away. The backup,
  like the owner, can't review the workflow's gates (they operate it when
  the owner is out — CI enforces both, with an expiring exception available
  for teams too small to staff it).
- `gates:` — before publishing, a human must approve: `reviewers: [bob]`,
  `timeout_hours: 24`, and if bob ignores it for a day it escalates to
  carol instead of silently rotting.
- `cost: cap_per_run_usd: 10` — the run hard-stops at $10.
- `resources:` — what it reads and writes, declared up front.

**Step 2 — in the same PR, she registers the bot and the resources.**
In [`registry/agents.yaml`](../registry/agents.yaml): its own identity with
its own scoped, short-lived credential (never a person's token), and a
one-line kill switch. In [`registry/resources.yaml`](../registry/resources.yaml):
the notes page it writes.

**Step 3 — bob reviews the PR like code.**
The PR template gives him a checklist; CI runs the validator and
mechanically catches anything structural — an unregistered agent, a missing
timeout, a write to a frozen metric, alice reviewing her own gate. Merge.
The workflow now officially exists.

**Step 4 — running it needs no new infrastructure.**
Each Friday run is just a GitHub issue: the run opens a parent issue, and
when it hits the human gate it opens a **child issue assigned to bob**
containing the draft plus just enough context to judge it. Bob replies with
a structured decision — approve, reject, or modify, **plus a reason**. The
reason isn't bureaucracy: it's what later tells you whether reviews are
real or rubber-stamps. The run resumes, publishes, and the issue thread
*is* the audit record. (Concrete issue formats and the heavier runtime
options are in [`implementation-examples.md`](implementation-examples.md).)

**Step 5 — the small ongoing hygiene.**
Weekly, alice glances at three numbers
([`metrics/gate-health.md`](../metrics/gate-health.md)): how long gates sat
waiting, how often reviewers rejected or modified (~0% for weeks means the
gate is theater — remove it or fix it), and cost per run. Quarterly,
someone runs [`docs/runbooks/quarterly-spec-review.md`](runbooks/quarterly-spec-review.md).
CI helps: every spec and agent carries a review-by date, and a lapsed one
fails the build until someone re-confirms ownership or kills it.

**And if it goes wrong:** anyone authorized pulls the kill switch
([`docs/runbooks/kill-switch.md`](runbooks/kill-switch.md)) — revoke the
bot's credential, mark it disabled, no meeting required. Turning it back
*on* is what needs approval.

## What this looks like at small scale

Most of the repo's machinery is deliberately dormant at three people: a
handful of spec files, two or three bot identities, one recurring workflow,
and gate issues that take someone ten minutes a week. The
separation-of-duties rule is the one that bites — whoever builds a
workflow, someone *else* must approve its outputs — and that's exactly the
discipline that keeps a two-person blind spot from shipping.

The payoff is that nothing changes structurally as you grow: a fourth
workflow or a fourth team is another spec file and another registry entry,
checked by the same CI. When a workflow earns trust — measured against
external anchors, not vibes — the same files are where its autonomy gets
widened, one reviewed PR at a time. The second bundled example,
[`specs/example-team/dependency-update-triage.md`](../specs/example-team/dependency-update-triage.md),
shows that later stage: a personal graph running with sampling oversight
because its anchors earn it, with 100% review kept on the irreversible
step.
