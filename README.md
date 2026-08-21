# Graph Engineering for Organizations

**Graph engineering** is designing and running AI-agent workflows as
explicit graphs, with the humans, budgets, and rules as versioned,
CI-checked files. This repo is a practical guide to it **and** the
operational repo you fork to do it: GRAPH SPECs reviewed like code, agent
and resource registries, human gates with contracts, and a validator that
fails the build when the governance stops being coherent. In effect, *a
linter for your agent fleet's governance*. It is **not an agent-building
framework**: you bring your own engine (LangGraph, Temporal, Step
Functions, plain GitHub Actions; see the
[crosswalk](docs/implementation-examples.md#runtime-crosswalk)), and
this repo is the contract and enforcement layer above it. (And not graph
databases; see
[the primer](docs/what-is-graph-engineering.md#the-name-and-its-neighbors).)

## The idea in three sentences

Human review capacity, not model capability, is the binding constraint on
agent fleets, so humans are modeled as graph nodes with contracts (structured
input, approve/reject/modify output, explicit timeout behavior). Agent
autonomy scales with external anchor density, never with internal metrics.
Everything that enforces this (identity, gates, costs, frozen instruments,
ownership) is declared in versioned files here and checked by CI on every PR.

## Is this for you?

| Probably not yet | Fork it |
|------------------|---------|
| You're **one person** experimenting on a laptop. Separation of duties needs a second human, so learn an engine first (LangGraph, CrewAI, the Claude Agent SDK) and bring the concepts back when a second person or a real workload arrives | You're **two or more people** with even one recurring agent workflow. The minimum footprint is three files and one CI check, about [an hour](docs/tutorial-first-workflow.md), and [most machinery stays dormant](docs/paths/small-team.md) at small scale |
| You're building a one-off demo with no side effects | Agents touch anything real (money, production, customer-visible output, your dependencies), or you're about to let them |
| Nothing here will ever be audited, and nobody else's money is involved | Security or legal is blocking AI adoption. This repo *is* the evidence pack that unblocks it, produced as a by-product of running |

Governance isn't the thing to defer: registering agent #1 takes minutes;
inventorying agent #10 after the fact takes an investigation
([why](docs/faq.md)).

## Start here: three doors

| You want to… | Go to | Time |
|--------------|-------|------|
| **Understand it**: what this is, why, with evidence | [What is graph engineering?](docs/what-is-graph-engineering.md) · [FAQ](docs/faq.md) · [Glossary](docs/glossary.md) | ~15 min |
| **Try it**: fork, break the rules on purpose, get your own first spec validating | [Tutorial: your first governed workflow](docs/tutorial-first-workflow.md) | ~1 hour |
| **Adopt it**: a sequenced path for your size | [Small team (2–10)](docs/paths/small-team.md) · [Enterprise](docs/paths/enterprise.md) · [The full plan](docs/plan.md) | ongoing |

Prefer to watch before doing? [`docs/walkthrough.md`](docs/walkthrough.md)
follows a three-person team putting one workflow under governance, start
to finish. The three reference specs under
[`specs/example-team/`](specs/example-team/) are the autonomy ladder's
live rungs: [suggest-only](specs/example-team/ci-failure-explainer.md) →
[act behind a gate](specs/example-team/weekly-release-review.md) →
[earned sampling](specs/example-team/dependency-update-triage.md).

## Layout

| Path | What it is |
|------|------------|
| [`AGENTS.md`](AGENTS.md) | **Instructions for AI agents**: ground rules for working here, plus the step-by-step playbook for deploying this repo in an organization |
| [`SECURITY.md`](SECURITY.md) | Threat model, reporting paths, non-waivable rules |
| [`docs/what-is-graph-engineering.md`](docs/what-is-graph-engineering.md) | The primer: definition, the term's history and collisions, benefits with evidence, honest limits |
| [`docs/tutorial-first-workflow.md`](docs/tutorial-first-workflow.md) | Hands-on tutorial: fork → break it → your own validated spec, ~1 hour |
| [`docs/paths/`](docs/paths/) | Adoption paths: [small team](docs/paths/small-team.md), [enterprise](docs/paths/enterprise.md) |
| [`docs/faq.md`](docs/faq.md) · [`docs/glossary.md`](docs/glossary.md) | Objections answered · one home per term |
| [`docs/plan.md`](docs/plan.md) | The canonical implementation plan |
| [`docs/practical-guide-design.md`](docs/practical-guide-design.md) | Decision record: research-backed design for the practical-guide layer (primer, tutorial, size-segmented adoption paths) |
| [`docs/walkthrough.md`](docs/walkthrough.md) | Plain-language tour: a small team using this on a live repo |
| [`docs/implementation-examples.md`](docs/implementation-examples.md) | Runtime decision table and crosswalk; concrete runtimes: ticket-based, LangGraph, Temporal; sampling mechanics; CI wiring |
| [`docs/validator-errors.md`](docs/validator-errors.md) | Reference: every `GE-*` error code, with meaning, fix, and waivability |
| [`docs/rollout-checklist.md`](docs/rollout-checklist.md) | Phase gates as checkable state, updated by PR |
| [`docs/platform-hardening.md`](docs/platform-hardening.md) | Branch protection, CI token scopes, credential issuance, frozen-instrument IAM. The platform settings that make the rules enforceable |
| [`docs/runbooks/`](docs/runbooks/) | Kill switch, incident response, quarterly spec review |
| [`specs/`](specs/) | GRAPH SPECs, one per workflow: YAML frontmatter + prose ([template](specs/TEMPLATE.md); reference examples above) |
| [`registry/agents.yaml`](registry/agents.yaml) | Agent identity registry: owner, JIT credentials, kill switch, recertification date per agent |
| [`registry/resources.yaml`](registry/resources.yaml) | Shared resource registry, incl. frozen measurement instruments |
| [`governance/`](governance/) | [Decision rights](governance/decision-rights.md), per-team [anchor tables](governance/anchors/TEMPLATE.md), [exception register](governance/exceptions.yaml), [compliance mapping](governance/compliance-mapping.md) |
| [`schemas/`](schemas/) | JSON Schemas: [spec frontmatter](schemas/graph-spec.schema.json), [gate decisions](schemas/gate-decision.schema.json), [run records](schemas/run-record.schema.json) |
| [`workflows/`](workflows/) | Promoted workflow scripts (built into plugins; install, don't copy) |
| [`metrics/gate-health.md`](metrics/gate-health.md) | Metric definitions: gate latency, override rate, rubber-stamp detection, cost, anchor movement, review load |
| [`scripts/validate.py`](scripts/validate.py) | CI validator enforcing the rules below |
| [`scripts/ticket_runner.py`](scripts/ticket_runner.py) | Minimal reference runner for the ticket runtime; executes a spec's run/gate/record lifecycle against the schemas |

## What CI enforces

`python3 scripts/validate.py` runs on every PR (and weekly, so decay
surfaces without traffic). Every error carries a `GE-*` code
([full reference](docs/validator-errors.md)). It fails the build when:

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
- the owner and backup owner are the same person, or a governance role
  (including kill-switch authorization) is held by an agent identity
  instead of a human (all handle comparisons are case-insensitive, and the
  schema requires lowercase handles)
- sampling oversight is claimed without external anchors; internal metrics
  never justify autonomy
- a claimed external anchor isn't in the team's machine-readable anchor
  table (`governance/anchors/<team>.yaml`), or its measuring instrument
  isn't registered and frozen
- an exception was approved by the target spec's own owner or backup
- the cost alert threshold isn't below the hard cap
- an active spec is past its `review_by` date (orphaned; ownership decay is
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

Start from the path for your size, [small team
(2–10)](docs/paths/small-team.md) or
[enterprise](docs/paths/enterprise.md); each sequences what to do now
and what to defer. Point any AI agent (Claude Code or otherwise) at this
repo and ask it to help you deploy it; [`AGENTS.md`](AGENTS.md) contains
the full playbook it will follow: gathering your org's facts, staffing
the roles, applying the [platform hardening
checklist](docs/platform-hardening.md), writing your first anchor table
and spec, and operating the pilot. The short human version:

1. Copy/fork this repo (or use "Use this template"); replace the
   placeholder handles in `.github/CODEOWNERS`.
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

## License

[Apache-2.0](LICENSE). Fork it, adapt it, deploy it in your organization.
