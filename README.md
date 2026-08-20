# Graph Engineering for Organizations

The operational repo behind the [organizational implementation plan](docs/plan.md)
for running multi-agent graph workflows across an organization with multiple
humans in the loop. The plan calls for a spec repo where GRAPH SPECs are owned,
reviewed like code, and validated against the org's governance rules — this is
that repo.

## The idea in three sentences

Human review capacity, not model capability, is the binding constraint on
agent fleets — so humans are modeled as graph nodes with contracts (structured
input, approve/reject/modify output, explicit timeout behavior). Agent
autonomy scales with external anchor density, never with internal metrics.
Everything that enforces this — identity, gates, costs, frozen instruments,
ownership — is declared in versioned files here and checked by CI on every PR.

## New here? Three ways in

1. **See it used:** [`docs/walkthrough.md`](docs/walkthrough.md) — a
   three-person team putting one agent workflow under governance on a live
   repo, start to finish.
2. **Read the two reference specs**, which bracket the autonomy spectrum:
   [`weekly-release-review`](specs/example-team/weekly-release-review.md)
   (shared graph, every run human-gated) and
   [`dependency-update-triage`](specs/example-team/dependency-update-triage.md)
   (personal graph that *earned* 15% sampling oversight through four weeks
   of gate metrics and an external anchor — with 100% review kept on the
   irreversible step, and the promotion paper trail in the file).
3. **See how it runs:**
   [`docs/implementation-examples.md`](docs/implementation-examples.md) —
   the same gate contract on ticket-based state (no infrastructure),
   LangGraph, and Temporal, plus how sampling draws and how to wire the
   validator into any CI.

## Layout

| Path | What it is |
|------|------------|
| [`AGENTS.md`](AGENTS.md) | **Instructions for AI agents**: ground rules for working here, plus the step-by-step playbook for deploying this repo in an organization |
| [`SECURITY.md`](SECURITY.md) | Threat model, reporting paths, non-waivable rules |
| [`docs/plan.md`](docs/plan.md) | The canonical implementation plan |
| [`docs/practical-guide-design.md`](docs/practical-guide-design.md) | Decision record: research-backed design for the practical-guide layer (primer, tutorial, size-segmented adoption paths) |
| [`docs/walkthrough.md`](docs/walkthrough.md) | Plain-language tour: a small team using this on a live repo |
| [`docs/implementation-examples.md`](docs/implementation-examples.md) | Concrete runtimes: ticket-based, LangGraph, Temporal; sampling mechanics; CI wiring |
| [`docs/rollout-checklist.md`](docs/rollout-checklist.md) | Phase gates as checkable state, updated by PR |
| [`docs/platform-hardening.md`](docs/platform-hardening.md) | Branch protection, CI token scopes, credential issuance, frozen-instrument IAM — the platform settings that make the rules enforceable |
| [`docs/runbooks/`](docs/runbooks/) | Kill switch, incident response, quarterly spec review |
| [`specs/`](specs/) | GRAPH SPECs — one per workflow, YAML frontmatter + prose ([template](specs/TEMPLATE.md); reference examples: [full gating](specs/example-team/weekly-release-review.md), [earned sampling](specs/example-team/dependency-update-triage.md)) |
| [`registry/agents.yaml`](registry/agents.yaml) | Agent identity registry: owner, JIT credentials, kill switch, recertification date per agent |
| [`registry/resources.yaml`](registry/resources.yaml) | Shared resource registry, incl. frozen measurement instruments |
| [`governance/`](governance/) | [Decision rights](governance/decision-rights.md), per-team [anchor tables](governance/anchors/TEMPLATE.md), [exception register](governance/exceptions.yaml), [compliance mapping](governance/compliance-mapping.md) |
| [`schemas/`](schemas/) | JSON Schemas: [spec frontmatter](schemas/graph-spec.schema.json), [gate decisions](schemas/gate-decision.schema.json), [run records](schemas/run-record.schema.json) |
| [`workflows/`](workflows/) | Promoted workflow scripts (built into plugins; install, don't copy) |
| [`metrics/gate-health.md`](metrics/gate-health.md) | Metric definitions: gate latency, override rate, rubber-stamp detection, cost, anchor movement, review load |
| [`scripts/validate.py`](scripts/validate.py) | CI validator enforcing the rules below |

## What CI enforces

`python3 scripts/validate.py` runs on every PR (and weekly, so decay
surfaces without traffic). Every error carries a `GE-*` code. It fails the
build when:

- a spec references an agent that isn't registered, active, owned, and
  kill-switchable
- an active agent has **standing credentials** (policy is JIT/ephemeral) or
  a lapsed recertification date
- a spec writes a **frozen** resource (measurement instruments are frozen)
- two active specs write the same resource (they need an edge, not
  parallelism)
- a gate lacks a timeout behavior, or escalation names no one, targets the
  owner/backup, or targets someone already reviewing that gate
- a spec's **owner reviews their own gates** or is their escalation target
  (separation of duties, non-waivable); the **backup owner** likewise
  (waivable by exception for small teams)
- the owner and backup owner are the same person, or a governance role —
  including kill-switch authorization — is held by an agent identity
  instead of a human (all handle comparisons are case-insensitive, and the
  schema requires lowercase handles)
- sampling oversight is claimed without external anchors — internal metrics
  never justify autonomy
- a claimed external anchor isn't in the team's machine-readable anchor
  table (`governance/anchors/<team>.yaml`), or its measuring instrument
  isn't registered and frozen
- an exception was approved by the target spec's own owner or backup
- the cost alert threshold isn't below the hard cap
- an active spec is past its `review_by` date (orphaned — ownership decay is
  the org-layer silent node failure)
- the exception register is malformed, an exception has expired, or one
  targets a non-waivable rule

Out-of-compliance states are only sanctioned via
[`governance/exceptions.yaml`](governance/exceptions.yaml): named approver,
mandatory expiry (≤ 90 days), checked by CI. Two rules never bend: frozen
instrument writes and self-approval (see [`SECURITY.md`](SECURITY.md)).

## Adding a workflow

1. Copy [`specs/TEMPLATE.md`](specs/TEMPLATE.md) to `specs/<team>/<name>.md`
   and fill in every field. Register its agent(s) in `registry/agents.yaml`
   and any new resources in `registry/resources.yaml` in the same PR.
2. Open a PR. The [PR template](.github/pull_request_template.md) carries the
   spec-review checklist; CI validates the frontmatter and cross-file rules.
3. Status flows `draft → pilot → promoted` by PR, with the evidence rules in
   [`governance/decision-rights.md`](governance/decision-rights.md).
   Promoted scripts land in `workflows/` and ship as plugins.

## Setting this up in your organization

Point any AI agent (Claude Code or otherwise) at this repo and ask it to
help you deploy it — [`AGENTS.md`](AGENTS.md) contains the full playbook it
will follow: gathering your org's facts, staffing the roles, applying the
[platform hardening checklist](docs/platform-hardening.md), writing your
first anchor table and spec, and operating the pilot. The short human
version:

1. Copy/fork this repo; replace the placeholder handles in
   `.github/CODEOWNERS`.
2. Apply `docs/platform-hardening.md` (branch protection with the
   `validate` check, CODEOWNERS enforcement, read-only CI token).
3. Work through Phase 0 of `docs/rollout-checklist.md`.

For auditors and compliance teams:
[`governance/compliance-mapping.md`](governance/compliance-mapping.md) maps
the artifacts here to the EU AI Act, NIST AI RMF, ISO/IEC 42001, and SOC 2.

## Local validation

```sh
pip install -r requirements.txt
python3 scripts/validate.py
```
