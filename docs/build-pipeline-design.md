# Auto build pipeline design

Decision record, in the style of
[`practical-guide-design.md`](practical-guide-design.md): a reviewed
source system, a design for this repo, and the reasoning between them.
Nothing in this document is implemented yet. Each stage below lands as
its own PR when the maintainer approves it.

**The request:** review the automated build pipeline running on
[`swampratnz/community-agent`](https://github.com/swampratnz/community-agent),
then design an auto build pipeline for this repo. That pipeline ships its
own adoption spec,
[`PIPELINE-PLAYBOOK.md`](https://github.com/swampratnz/community-agent/blob/main/docs/PIPELINE-PLAYBOOK.md),
written to be handed to a session pointed at a target repository. This
document is that playbook's §9 deliverable (fit summary, prerequisite
gaps, per-component verdicts, staged plan, parameters, risks, cost),
produced for this repo, with one addition the source repo could not make:
here, the pipeline is itself expressed in the governance model it builds,
as a GRAPH SPEC with registered agents, a gate, and a kill switch.

---

## 1. The system reviewed

Community-agent runs a supervised multi-agent development pipeline:
agents propose work as issues, an adversarial agent vets proposals, a
build agent implements approved issues and opens PRs, a review agent
reviews every PR with a typed verdict, repair agents fix red CI, merge
conflicts, and changes-requested reviews, and deterministic workflows
sweep up everything that falls between. A human merges (with a narrow,
deliberately gated auto-merge exception). Coordination happens entirely
through GitHub issues and labels: there is no session-to-session channel,
no orchestrator process, no state outside the forge. Its own docs put it
well: the pipeline is already a graph, a label-driven state machine.

Three layers ([`CICD.md`](https://github.com/swampratnz/community-agent/blob/main/docs/CICD.md)):

| Layer | Content |
|---|---|
| Gate | `ci.yml` (build, lint, security-invariants jobs) plus check scripts; the same command list agents, CI, and humans all run |
| Autonomy | 17 workflows: build, review, autofix, conflict, revise, automerge, groundskeeper, retries, janitors, outcome reporting |
| Delivery | Pull-based: a systemd timer on the production host fast-forwards from `main`; no workflow deploys |

### What holds it up

Verified in the workflow files, not just the docs:

- **One kill switch.** All 7 agent workflows gate every step on the
  `CLAUDE_CODE_OAUTH_TOKEN` secret being present; remove it and the
  agentic half goes inert. Deterministic loops keep running.
- **Least-privilege tool grants.** The build worker's `--allowedTools`
  is an explicit allowlist: push is pinned to the exact string
  `git push origin HEAD`, there is no `gh pr merge`, no `gh api`, and no
  `gh issue edit` (an injected agent must not be able to label an
  arbitrary issue approved and spawn an unreviewed build). The docs are
  honest that this is defence in depth, not a guarantee: the agent has
  code execution, and branch protection is the enforceable backstop.
- **The workflow owns the state machine, not the agent.** Lane labels
  (`status:building`, `status:built`, `needs-human`) are set by
  deterministic steps before and after the agent runs; the agent signals
  refusal by writing a file, never by touching labels.
- **Identity separation.** The agent identity (`claude[bot]`) and the
  deterministic identity (`github-actions[bot]`) are distinct, and gates
  depend on it: only deterministic-identity comments are read back as
  handoff notes, only the agent identity's PRs can ever auto-merge, so
  recovered or forged work cannot launder itself past the gate.
- **Shared machinery is extracted and pinned.** The checkpoint and
  verify steps live in composite actions referenced repo-qualified
  (`swampratnz/community-agent/.github/actions/...@main`), never `./`,
  so a PR's own content cannot redefine the step that judges it. Tests
  pin the reference form and cross-workflow duplicate logic.
- **Auto-merge is deterministic and self-limiting.** No model, exact
  author-identity match, fresh verdict newer than the head commit, and a
  governance-path matcher that routes any PR touching workflows, check
  scripts, or the rules docs to a human merge. A pipeline that could
  auto-merge changes to its own gates would have no gates.

### What it earned the hard way

Every rule traces to an incident, cited in its docs. The ones that
shaped the most machinery: agents finishing whole builds and ending the
turn without pushing (deterministic checkpoint after agent exit); build
timeouts reporting `cancelled`, invisible to failure-keyed retries, so
claimed issues zombied and starved the queue (hourly groundskeeper);
escalated issues re-claimed by a fallback loop because one label was
left behind (clear both labels on escalate); three workflows parsing the
same review verdict with drifting regexes so an approved PR sat unmerged
forever (typed verdict token, stamped once); rescued work rebuilt from
scratch because the resume pointer was published on the wrong attempts
(deterministic resume pre-step); a draft-PR handshake that silently
disabled all reviews because `GITHUB_TOKEN`-created events never trigger
workflows (poll instead).

### Gaps

Its own reference documents four honestly (a consumed-but-never-created
override label, a documented-but-unset CI variable, hand-synced
CODEOWNERS, and the CI/CD reference itself not being a governance path).
Two observations to add: every LLM loop shares the single on/off secret,
so there is no per-loop enable short of the Actions UI (their docs note
this too); and the three long pipeline docs against 17 workflows carry
real drift risk, which they manage with a stated precedence rule
(workflow file wins) and tests that fail on cross-copy drift. Verdict:
this is a mature, incident-hardened design, and its playbook is the
right artifact to design from. The review below adopts its invariants
wholesale and its components selectively.

---

## 2. This repo, assessed

Against the playbook's §2, the five non-negotiable prerequisites:

| Prerequisite | State here | Gap |
|---|---|---|
| A CI gate that fails on broken code, on every PR | Strong. `validate.yml` runs the validator plus 28 regression tests on every PR, push, weekly cron, and dispatch. Pure Python, no services, seconds not minutes, near-zero flake surface | None |
| Branch protection with required checks | Documented as the target in [`platform-hardening.md`](platform-hardening.md); actual setting not verifiable from repo contents | **Verify**: `validate` required, author cannot approve own PR, force-push blocked |
| A written conventions doc | [`AGENTS.md`](../AGENTS.md) (ground rules for any agent) plus `CLAUDE.md`. Better than the source repo started with | None |
| A same-repo ownership signal | No convention yet; issues barely used | **Adopt** `Closes #N` and create the lane labels |
| Model credential + distinct bot identity | Not configured | **Add** `CLAUDE_CODE_OAUTH_TOKEN` secret; confirm the Claude GitHub App covers this repo |

Shape and culture facts that drive the component choices:

- **The gate is trivially cheap.** Seconds, no containers, no caches.
  Most of the source pipeline's gate machinery (service containers,
  embedding caches, DB-skip contracts) has no analog here.
- **Solo maintainer, low volume.** A few PRs a week. The playbook's own
  finding applies: a solo maintainer gets the most value per unit risk
  from review automation.
- **The work queue already exists in writing.** The design backlog in
  [`practical-guide-design.md`](practical-guide-design.md) §4 and the
  [`rollout-checklist.md`](rollout-checklist.md) Phase 3 backlog are
  well-specified, small, self-verifying items: exactly the input a build
  agent needs. Discovery loops (research, adversarial) are therefore
  unnecessary at the start: the playbook says to add them only when the
  pipeline is starved of specified work, and this one starts fed.
- **This is a public template repo.** Forks and template copies get any
  workflow files we add. The source pipeline's inert-gate pattern makes
  that safe (no secret, no runs), but it argues for a minimal footprint:
  adopt few workflows, each with a header comment saying what it is and
  that it is inert without the secret.
- **This repo is a governance layer.** Nearly everything outside
  `docs/` prose is load-bearing: the validator, schemas, registries,
  exception register, workflows. The governance-path list (paths no
  automation may ever merge) covers most of the tree, which mostly
  decides the auto-merge question by itself (§4).
- **Shared budget.** The pipeline would be the third consumer of one
  Max pool, after the production community bot and the source repo's own
  pipeline. The source repo's 2026-07-04 incident (a five-issue burst
  throttling every build into its timeout) is the cautionary tale;
  cadences and WIP here stay minimal.

---

## 3. The pipeline is a graph, so it gets a spec

The source pipeline describes itself as a label-driven state machine
and coordinates through tickets. In this repo's terms that is a `ticket`
runtime graph, and the discipline this repo teaches is that such a graph
gets a spec, registered agents, a contracted human gate, and a kill
switch. Practicing that on our own automation is the point: the pipeline
must clear the same bar we ask adopters to clear.

The mapping, concept for concept:

| Pipeline concept (source repo) | This repo's concept |
|---|---|
| The label state machine, issues as the bus | `runtime: ticket` (run = issue, gate = PR review) |
| `claude[bot]`, the one identity all agent loops share | One registered agent in [`registry/agents.yaml`](../registry/agents.yaml) |
| `github-actions[bot]`, the deterministic steps | The runtime itself, not an agent: it holds no model and makes no judgment calls, like the ticket runner |
| Per-run OIDC-minted App token, ~1h TTL | `credentials: kind: jit`, genuinely (this is what GE-CRED-STANDING asks for) |
| Remove the secret, all agent loops inert | `kill_switch.how`, and it is a real, tested, single action |
| Human merges every PR | The spec's one gate: `pr-merge-review`, `on_timeout: default_deny` (an unmerged PR just waits; deny is the safe direction) |
| Attempt caps (2 fix attempts, revise cap stops reviewer-vs-reviser loops) | `pathology_guards.max_debate_rounds: 2` |
| Review always runs as a cold session, never the builder | `pathology_guards.fresh_context_verifier: true` |
| Unparseable verdict routes nowhere, stalls visibly | `pathology_guards.arbitration_default: reject` |
| `needs-human` label, the terminal state of every loop | Gate escalation surface; the lane a human empties |
| Governance paths never auto-merged | The non-waivable spirit: automation must not weaken its own gates (`CLAUDE.md` already states it: never weaken the validator or CI to get green) |
| Outcome ledger: is each loop earning its tokens? | [`metrics/gate-health.md`](../metrics/gate-health.md) discipline; measurement instruments stay frozen, agents never write them |
| Auto-merge after weeks of boring | An autonomy increase to `oversight: sampling`, which GE-SAMPLING-ANCHOR permits only with external anchors. See §4; this is the model being *stricter* than the source repo's intuition, and machine-checked |

### The draft spec

What stage 2 would commit to `specs/graph-maintainers/` (with registry
entries in the same PR). Shown inline here because it is not yet
committable, for the honest reason given below it.

```yaml
---
spec: graph/v1
name: repo-build-pipeline
status: draft
team: graph-maintainers
owner: swampratnz
backup_owner: <second-human>
created: 2026-08-24
review_by: 2026-11-24

shape: shared
runtime: ticket

agents:
  - graph-pipeline-bot

autonomy:
  anchor_class: internal
  anchors: []
  oversight: full-gating
  sampling_rate: null

cost:
  cap_per_run_usd: 5
  alert_threshold_usd: 2.50
  cap_per_day_usd: 20

resources:
  reads: [graph-repo.main, graph-repo.issues]
  writes: [graph-repo.branches, graph-repo.pull-requests]

gates:
  - id: pr-merge-review
    class: quality
    surface: pr
    reviewers: [<second-human>]
    timeout_hours: 168
    on_timeout: default_deny

pathology_guards:
  max_debate_rounds: 2
  max_agent_group: 2
  fresh_context_verifier: true
  arbitration_default: reject

kill_switch:
  how: >
    Remove the CLAUDE_CODE_OAUTH_TOKEN repo secret (every agent loop goes
    inert); set graph-pipeline-bot to disabled in registry/agents.yaml;
    disable an individual workflow in the Actions UI for a single loop.
  authorized: [swampratnz]
---
```

Notes on deliberate choices:

- **One registered agent.** All agent loops authenticate as the same
  App identity, so registering per-loop agents would describe an
  identity separation that does not exist. The entry's purpose field
  names the loops it covers.
- **The spec's `writes` omit labels.** Lane labels are workflow-owned
  (the deterministic runtime), and the agent is granted no
  `gh issue edit`. The spec declaring only what the *agent* writes is
  the accurate record, and it preserves the audit-N4 property from the
  source repo.
- **Metrics stay frozen.** `graph-repo.metrics` (the `metrics/` tree)
  gets a `frozen: true` resource entry. The pipeline optimizes this
  repo, so the instruments measuring the repo's health are exactly what
  it must never write; any future spec declaring that write trips
  GE-FROZEN-WRITE, non-waivably. Outcome reporting goes to a tracking
  issue (the source repo's pattern), not to `metrics/`.
- **Cost caps are notional under subscription auth.** The enforced
  bounds are `--max-turns` and job timeouts (§6); the USD fields record
  intent, as the runtime section of every spec here already documents.

### The separation-of-duties collision, stated plainly

The [small-team path's](paths/small-team.md#the-separation-of-duties-math)
one-person row says it: solo, an active spec is not possible, and
honestly so. The schema requires a distinct `backup_owner`, and the owner
reviewing their own gate is GE-SELF-APPROVE, never waivable. This repo's
maintainer is one person, who would own the pipeline and also be the
merge-gate reviewer.

So by this repo's own published doctrine, the sanctioned solo mode is
option one of that row: **use the concepts (registry entry, caps, kill
switch, run records) and keep the spec `status: draft`**. The pipeline
runs; the spec records it honestly as not yet clearing the bar the repo
sets for active workflows. What upgrades it: one more human. At two
people the 2-person shape applies (owner + backup/reviewer, one
GE-BACKUP-APPROVE exception signed by an outside approver); at three it
is fully clean. Until then, one mitigating fact from the same page
applies: when the agent authors the work, the one human reviewer who did
not trigger the run already constitutes independent review of each
*change*, which is what branch protection's author-cannot-approve rule
encodes. The draft status is the honest record that spec-level
separation, not change-level review, is what is missing.

This is the single biggest obstacle the playbook's §9 asks for, and it
is a feature: the model, applied to our own automation, pushes back
exactly where it should.

---

## 4. Per-component verdicts

| Component | Verdict | Reason |
|---|---|---|
| Review agent (read-only, typed verdict) | **Adopt first** | Highest value per unit risk for a solo maintainer: a second reader on every PR, including the maintainer's own and other agents'. Reviews against `AGENTS.md`, validator semantics, and the house voice. Read-only tool grant; a deterministic step posts the comment |
| Build agent (with all four safeguards) | **Adopt** | The backlog is full of well-specified small items. Workflow-owned lane labels, incremental push, deterministic checkpoint, verify-else-escalate: all four, from day one; every one traces to a source-repo incident |
| Build retry | **Adopt with build** | Transient runner failures should not spend the maintainer's attention. Deterministic, free |
| Groundskeeper | **Adopt with build** | The zombie-lane sweep is what makes `status:building` mean something. Hourly, deterministic, free |
| Outcome reporting | **Adopt with build** | The recovered count is the pipeline's own health metric; without it, harness defects are invisible. Reports to a tracking issue |
| Autofix (CI-failure repair) | **Adopt after build settles** | With a seconds-fast deterministic gate, a red PR is a real defect in the change, the case autofix handles best. Cap 2, then `needs-human` |
| Revise (changes-requested repair) | **Adopt with autofix** | Once review and build both run, a green PR with a changes-requested verdict has no responder without it. Cap 2 |
| CI retry (blind rerun) | **Skip** | The gate is pure Python with near-zero flake surface. Revisit on the first month with more than one infrastructure-caused failure |
| Conflict resolver | **Skip for now** | WIP 1 and a solo human make conflicts rare. The append-point hotspots here (`registry/agents.yaml`, `governance/exceptions.yaml`) are touched by a minority of changes. Adopt if the queue ever runs concurrent builds |
| Branch janitor | **Skip** | GitHub's own "automatically delete head branches" setting covers the need at this scale |
| Changelog coverage + autofill | **Skip** | No changelog convention; per-spec promotion-history tables serve the role |
| Context pack + gate | **Skip** | The repo is small and `AGENTS.md` plus the README layout table already are the orientation map. A gated map earns its keep on large trees |
| Handoff notes (build → review) | **Skip initially** | Diffs here are small; the source repo itself treats the mechanism as a measured hypothesis. Revisit if review quality on build PRs disappoints |
| Discovery loops (research, adversarial) | **Skip initially** | The pipeline starts fed from a written backlog. Add only if it starves; the adversarial rubric would be `docs/plan.md` and the design records, the way `VISION.md` serves the source repo |
| Auto-merge | **Skip, anchor-gated** | Three independent reasons: the governance-path list covers most of this repo, leaving little eligible surface; solo operation keeps the spec draft, and autonomy increases belong to active specs; and auto-merge is `oversight: sampling`, which GE-SAMPLING-ANCHOR grants only with external anchors, and no frozen external instrument for this repo exists. If real external anchors ever exist (adoption metrics measured outside the repo), the promotion path in [`decision-rights.md`](../governance/decision-rights.md) applies. Until then the model itself says no, which is the correct answer |

---

## 5. Staged rollout

Each stage is one PR (or one platform action), verified before the next.
Rollback for every agent stage: remove the secret (all loops inert) or
disable the one workflow.

### Stage 0: foundations (no automation)

- Verify branch protection: `validate` required, author cannot approve
  own PR, force-push blocked (per [`platform-hardening.md`](platform-hardening.md)).
- Add the `CLAUDE_CODE_OAUTH_TOKEN` secret; confirm the Claude GitHub
  App covers this repo.
- Create the labels (port of the source repo's setup script, same
  vocabulary; see §6) and adopt `Closes #N` in contributions.
- Optional gate hardening, each a small PR and each an ideal first work
  item *for* the pipeline later: a voice check (fail on any em dash in
  tracked Markdown, mechanizing the house style the docs currently keep
  by discipline); the `--list-codes` flag plus a drift check between
  the validator and [`validator-errors.md`](validator-errors.md)
  (already on the design backlog); a test-count floor in the spirit of
  the source repo's security floor, so a deleted regression test cannot
  pass silently.
- **Verify:** the gate still fails on a deliberately broken spec (the
  [tutorial's](tutorial-first-workflow.md) break-it steps are the test).

### Stage 1: review agent

- Install the review workflow: read-only tool grant, typed verdict
  token (`LGTM` / `CHANGES_REQUESTED` / `NEEDS_HUMAN`) stamped by the
  workflow, fork PRs excluded by the absent secret.
- The review prompt's rubric, in order: does the change weaken the
  validator, CI, or a non-waivable rule (the `CLAUDE.md` red line);
  spec/registry coherence beyond what the validator can see; sourcing
  and honesty standards from the design records; house voice.
- **Verify:** open one PR with a deliberate rule violation and one
  clean PR; the verdicts must differ, and both must get a comment.

### Stage 2: build agent

- Install the build workflow with the four safeguards, plus build
  retry, groundskeeper, and outcome reporting. Commit the draft spec
  (§3) and the `graph-pipeline-bot` + resource registry entries in the
  same PR; the validator holds it to the same rules as any workflow.
- Seed the queue: file 3 to 5 backlog items as issues with acceptance
  criteria, label exactly one `status:approved`, and watch the whole
  run. There is no dry-run for this stage; one issue at a time is the
  rollout.
- **Verify:** three consecutive builds produce a mergeable PR that
  passes review; the groundskeeper escalates a deliberately abandoned
  claim.

### Stage 3: repair loops

- Autofix first, then revise. Cap 2 each, `needs-human` terminal,
  same-repo checks on the `workflow_run` trigger (the fork-safety
  invariant), checkpoint and verify steps included.
- **Verify:** one genuinely red build PR repaired; one changes-requested
  verdict addressed; one escalation observed by exhausting a cap.

### Stage 4: does not exist

Auto-merge is not a planned stage (§4). The written bar for revisiting:
a second human (spec goes pilot), then external anchors registered and
frozen, then the four-week evidence rule from
[`decision-rights.md`](../governance/decision-rights.md). All three, in
that order, by PR.

---

## 6. Parameters

| Parameter | Value here | Notes |
|---|---|---|
| Lane labels | `status:draft/approved/building/built/rejected` | Same vocabulary as the source repo; no existing labels collide |
| Stop label | `needs-human` | Hard stop for every loop; a human empties the lane |
| Pin-out label | `no-auto-fix` | Per-PR manual opt-out of repair loops |
| Ownership signal | `Closes #N` in the PR body | Distinguishes pipeline PRs from Dependabot bumps |
| Agent identity | `claude[bot]` (Claude GitHub App) | Registered as `graph-pipeline-bot` |
| Deterministic identity | `github-actions[bot]` | Must stay distinct; gates depend on it |
| Gate commands | `pip install -r requirements.txt && python3 scripts/validate.py && python3 -m unittest discover -s tests` | Identical in CI, agent workflows, and local runs |
| Service containers | none | The gate is pure Python |
| Required env | none | No config schema to satisfy |
| Governance paths (never auto-merged; extra review scrutiny) | `scripts/**`, `schemas/**`, `governance/**`, `registry/**`, `.github/**`, `AGENTS.md`, `CLAUDE.md`, `SECURITY.md`, `docs/validator-errors.md`, `requirements.txt` | Most of the tree outside `docs/` prose and `specs/`, which is the point |
| Attempt caps | 2 (autofix), 2 (revise), 3 (build attempts total), 0 (CI retry: skipped) | Matches `max_debate_rounds: 2` |
| Model | Sonnet, all loops | Pinned in workflow files; revisit per loop on evidence |
| Turn budgets | build 150, review 50, repair 100 | Sized down from the source repo's 300/60/200: smaller diffs, faster gate |
| Timeouts | build 60 min, review 15 min, repair 30 min | Generous so a pool-throttled run finishes slowly instead of dying mid-gate |
| Groundskeeper threshold | 2 h idle, hourly sweep | Must exceed the build timeout |
| WIP | 1 approved-and-building at a time | Solo review capacity, shared token pool |

---

## 7. Risks and honest limits

- **Spec-level separation of duties is unmet while solo.** Covered in
  §3; the spec stays draft and says so. This is the biggest limit, and
  it is the model working.
- **Third consumer of one token pool.** The pipeline shares the Max
  pool with the production community bot and the source repo's
  pipeline. Mitigations: WIP 1, no discovery loops, staggered
  approvals, generous timeouts. If contention shows up anyway, this
  pipeline yields (relax cadence or pause) before the production bot
  does.
- **The pipeline edits its own governor.** Build items will sometimes
  touch `scripts/validate.py`. The mitigations stack: the governance
  paths get extra review scrutiny (stage 1 rubric), the human merge
  gate holds for everything, the `CLAUDE.md` never-weaken rule binds
  every agent, and the regression suite plus the optional test-floor
  gate make silent weakening loud.
- **Prompt injection through issue text.** The build agent processes
  issue bodies; a hostile issue could try to steer it. Blast radius
  under this design: a PR a human reads, on a branch, with no label
  authority and no merge authority. The invariants that keep it there
  (no `gh issue edit`, identity separation, fork exclusion, human
  merge) are exactly the source repo's, adopted unchanged.
- **Template copies inherit the workflows.** Safe (inert without the
  secret) but potentially confusing. Every workflow file carries a
  header comment: what it is, what turns it on, and a pointer here.
- **Docs-vs-workflow drift.** This document is a design record, not a
  reference. If a workflow and this document disagree, the workflow
  file wins and the discrepancy is a bug to fix by PR, the same
  precedence rule the source repo states.

**Cost, order of magnitude.** At three builds a week: roughly 3 build
runs, 5 to 8 review runs (PRs plus revisions), and an occasional repair
run, all Sonnet, tens of turns each. Comfortably inside a Max pool the
production bot already headlines, provided WIP stays at 1. The weekly
outcome issue is the place this stops being an estimate.

---

## 8. What this design does not do

It creates no workflows, labels, secrets, or registry entries; every
stage above is a separate PR for the maintainer to approve, and stage 0
is platform work only the maintainer can do. It does not adopt the
source pipeline wholesale: eight of its components are skipped here with
reasons, and the count that matters is not how much automation runs but
whether each loop earns its tokens, which stage 2's outcome reporting
exists to answer. And it does not grant the pipeline any autonomy the
model would not grant an adopter: full gating, a draft spec while the
separation math is unmet, and an anchor-gated ceiling above it.
