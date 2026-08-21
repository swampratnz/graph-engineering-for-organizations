# Tutorial: your first governed workflow

About an hour, hands-on. At the end you will have: this repo validating
green on your own fork, the rules learned by breaking them, **your own
first GRAPH SPEC passing CI**, and one run of it executed by hand. All
decisions are pre-made: defaults first, understanding as you go,
customization after.

**You need:** git and a GitHub account, Python 3.10+ (on Windows, call
`python` wherever this doc says `python3`), one teammate for
step 5 (they'll spend two minutes). **Your repo needs**, before an agent
touches it: CI you actually trust, tests worth trusting, and branch
protection on the default branch.
[DORA 2025](https://dora.dev/dora-report-2025/) finds AI amplifies what
a team already is, so fix those first; this framework won't rescue them.

## Step 1: Get to green (10 min)

Fork this repo (or "Use this template"), clone it, and run the
validator:

```sh
git clone <your-fork-url> && cd graph-engineering-for-organizations
pip install -r requirements.txt
python3 scripts/validate.py
```

Expected final line:

```
3 spec(s), 3 agent(s), 5 resource(s), 1 anchor table(s), 0 active exception(s): 0 error(s), 0 warning(s)
```

That's the whole enforcement layer: one script, two pinned dependencies,
exit 0. Everything else in this tutorial is about what it's checking.

## Step 2: Read the smallest spec (10 min)

Open
[`specs/example-team/ci-failure-explainer.md`](../specs/example-team/ci-failure-explainer.md),
the minimal reference spec, just under 50 frontmatter lines. Read it
top to bottom; here is what each block is doing:

- **Identity and ownership** (`name`…`review_by`): one accountable human
  (`owner: dana`), a named absence cover (`backup_owner: alice`), and a
  quarterly `review_by` date. A lapsed date fails CI, because ownership
  decay is how workflows go feral.
- **`shape` / `runtime`**: a `personal` graph on the `ticket` runtime.
  Your issue tracker is the state store and audit trail; no
  infrastructure.
- **`agents`**: the bot's identity, which must exist in
  [`registry/agents.yaml`](../registry/agents.yaml) with a human owner,
  JIT credentials, and a kill switch. Find `example-explainer-bot` there
  now; that's the other half of this spec.
- **`autonomy`**: `internal` + `full-gating`, the humblest honest claim.
  External anchors and sampling come later, earned
  ([decision rights](../governance/decision-rights.md)).
- **`cost`**: a $1 hard cap per run, alert at $0.50. The runtime must
  stop the run at cap; CI checks alert < cap.
- **`resources`**: reads the repo, writes only issue comments. Declared
  up front, so CI can catch a write to something frozen or contended.
- **`gates`**: one human node. bob reviews a *weekly digest* of the
  bot's comments (batching keeps review cost below the value of the
  work; a per-comment gate would be rubber-stamped within weeks), with a
  48h timeout that fails safe (`default_deny`).
- **`pathology_guards` / `kill_switch`**: caps on multi-agent failure
  modes, and the documented way to stop everything.

## Step 3: Break it, three ways (10 min)

The fastest way to learn the rules is to trip them. Make each edit to
`specs/example-team/ci-failure-explainer.md`, run
`python3 scripts/validate.py`, read the error, undo
(`git checkout -- specs/`).

**Break 1: let the owner review her own gate.** Change
`reviewers: [bob]` to `reviewers: [dana]`:

```
ERROR   specs/example-team/ci-failure-explainer.md: [GE-SELF-APPROVE] gate 'weekly-digest-review': spec owner 'dana' is a reviewer: authors cannot approve their own graph's outputs
```

This is one of the two rules **no exception can waive**: self-certified
work is invisible-from-inside failure ([SECURITY.md](../SECURITY.md)).

**Break 2: write to a measurement instrument.** Change
`writes: [repo.issue-comments]` to `writes: [telemetry.release-health]`:

```
ERROR   specs/example-team/ci-failure-explainer.md: [GE-FROZEN-WRITE] writes frozen resource 'telemetry.release-health': measurement instruments are frozen; no optimizing agent holds write access to what measures it
```

The other never-waivable rule. The thing that measures a workflow must
not be writable by it; otherwise the metrics look great while reality
diverges.

**Break 3: drop a gate's timeout.** Delete the `timeout_hours: 48`
line:

```
ERROR   specs/example-team/ci-failure-explainer.md: [GE-SCHEMA] gates/0: 'timeout_hours' is a required property
```

A gate with no timeout behavior is a silent node failure waiting to
happen: the run just rots. Every gate declares what happens when the
human doesn't show up. (Full error-code reference:
[validator-errors.md](validator-errors.md).)

## Step 4: Write your own (20 min)

Pick one chore: recurring, already done manually, internal-facing, low
blast radius. Good first picks: a CI-failure explainer for *your* repo,
a release-notes drafter, a weekly dependency digest. Explicitly not:
anything customer-facing or writing to production (see
[why](paths/small-team.md#your-first-workflow)).

Copy the template and the minimal spec side by side:

```sh
cp specs/TEMPLATE.md specs/<your-team>/<your-workflow>.md
```

Fill the frontmatter with the smallest honest value per field:

| Field | Smallest honest value |
|-------|----------------------|
| `status` | `pilot` (or `draft` while you argue about it; drafts skip the gate requirement) |
| `owner` / `backup_owner` | Two different real people who agreed. Who can hold what at your size: [the separation table](paths/small-team.md#the-separation-of-duties-math) |
| `shape` / `runtime` | `personal` / `ticket` |
| `autonomy` | `internal`, `anchors: []`, `full-gating`; always start here |
| `cost` | The most a single run is worth to you; alert below it |
| `resources` | Everything it touches, registered in [`registry/resources.yaml`](../registry/resources.yaml) in the same PR. Give your spec its own write targets rather than reusing another active spec's; two active writers on one resource fail CI (`GE-CONTENTION`) |
| `gates` | One gate, a reviewer who is neither owner nor backup, `on_timeout: default_deny` (escalation needs a fourth person; add it when you have one) |
| `pathology_guards` | `1 / 2 / true / reject` for a single-agent graph |
| `kill_switch` | How you'd actually stop it, and who may |

Register the agent identity in [`registry/agents.yaml`](../registry/agents.yaml)
(copy `example-explainer-bot`'s entry; `credentials.kind: jit`, and the
registry *describes* the credential, never contains it) and any new
resources. Then loop on `python3 scripts/validate.py` until:

```
4 spec(s), 4 agent(s), ... 0 error(s)
```

Every error you hit names its rule; that's the curriculum working.

## Step 5: Run it by hand, once (15 min)

Before wiring any automation, execute one run manually; you play the
runtime. This proves the contract while it's still cheap to change:

1. **Open the parent issue** in your repo using the run format from
   [implementation-examples.md](implementation-examples.md#1-ticket-based-state-start-here):
   title `[run] <name> <date>`, the step checklist, the spend line.
2. **Do the agent step yourself**: ask your coding agent (Claude Code or
   otherwise) to produce the artifact (the release-notes draft, the
   failure explanation) and paste it into the parent issue. Check the
   step off.
3. **Open the gate child issue**, assigned to your reviewer, containing
   the artifact and the minimum context to judge it, never the agent's
   full transcript. Include the reply contract:
   `/approve <reason>`, `/reject <reason>`, `/modify <what> <reason>`.
4. **Your teammate replies with a decision and a reason.** The reason is
   the point: it's what makes review measurable later.
5. **Close out**: record the decision and a run record on the parent
   issue (formats: [`schemas/gate-decision.schema.json`](../schemas/gate-decision.schema.json),
   [`schemas/run-record.schema.json`](../schemas/run-record.schema.json)).
   Prefer it scripted? `python3 scripts/ticket_runner.py --help` executes
   exactly this lifecycle locally and validates the records against the
   schemas as it goes.

That issue thread is a complete, audit-grade run. Automation (a cron
that opens the issues, a webhook that resumes on the reply) changes the
labor, not the contract.

## Step 6: Where to go from here

- Open the PR for your spec and let a teammate review it against the
  [PR checklist](../.github/pull_request_template.md); the workflow now
  officially exists.
- Wire the real runtime when manual runs get old:
  [implementation-examples.md](implementation-examples.md).
- Follow your size's path from here: [small team](paths/small-team.md) ·
  [enterprise](paths/enterprise.md).

**The clock**: steps budget to ~65 minutes. If it took you meaningfully
longer, the docs failed, not you; please open an issue saying where the
time went. Time-to-first-green is this guide's own gate metric
([design](practical-guide-design.md#6-how-well-know-the-guide-works)),
and its instrument is [`metrics/tutorial-runs.md`](../metrics/tutorial-runs.md):
add your run by PR, honest numbers only, blockers included.
