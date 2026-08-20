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

## Layout

| Path | What it is |
|------|------------|
| [`docs/plan.md`](docs/plan.md) | The canonical implementation plan |
| [`docs/rollout-checklist.md`](docs/rollout-checklist.md) | Phase gates as checkable state, updated by PR |
| [`docs/runbooks/`](docs/runbooks/) | Kill switch, quarterly spec review |
| [`specs/`](specs/) | GRAPH SPECs — one per workflow, YAML frontmatter + prose ([template](specs/TEMPLATE.md), [reference example](specs/example-team/weekly-release-review.md)) |
| [`registry/agents.yaml`](registry/agents.yaml) | Agent identity registry: owner, JIT credentials, kill switch per agent |
| [`registry/resources.yaml`](registry/resources.yaml) | Shared resource registry, incl. frozen measurement instruments |
| [`governance/`](governance/) | [Decision rights](governance/decision-rights.md), per-team [anchor tables](governance/anchors/TEMPLATE.md) |
| [`schemas/`](schemas/) | JSON Schemas: [spec frontmatter](schemas/graph-spec.schema.json), [gate decisions](schemas/gate-decision.schema.json), [run records](schemas/run-record.schema.json) |
| [`workflows/`](workflows/) | Promoted workflow scripts (built into plugins; install, don't copy) |
| [`metrics/gate-health.md`](metrics/gate-health.md) | Metric definitions: gate latency, override rate, rubber-stamp detection, cost, anchor movement, review load |
| [`scripts/validate.py`](scripts/validate.py) | CI validator enforcing the rules below |

## What CI enforces

`python3 scripts/validate.py` runs on every PR (and weekly, so orphaned specs
surface without traffic). It fails the build when:

- a spec references an agent that isn't registered, active, owned, and
  kill-switchable
- a spec writes a **frozen** resource (measurement instruments are frozen)
- two active specs write the same resource (they need an edge, not
  parallelism)
- a gate lacks a timeout behavior, or escalation names no one
- a spec's **owner reviews their own gates** or is their escalation target
  (separation of duties)
- sampling oversight is claimed without external anchors — internal metrics
  never justify autonomy
- the cost alert threshold isn't below the hard cap
- an active spec is past its `review_by` date (orphaned — ownership decay is
  the org-layer silent node failure)

## Adding a workflow

1. Copy [`specs/TEMPLATE.md`](specs/TEMPLATE.md) to `specs/<team>/<name>.md`
   and fill in every field. Register its agent(s) in `registry/agents.yaml`
   and any new resources in `registry/resources.yaml` in the same PR.
2. Open a PR. The [PR template](.github/pull_request_template.md) carries the
   spec-review checklist; CI validates the frontmatter and cross-file rules.
3. Status flows `draft → pilot → promoted` by PR, with the evidence rules in
   [`governance/decision-rights.md`](governance/decision-rights.md).
   Promoted scripts land in `workflows/` and ship as plugins.

## Local validation

```sh
pip install pyyaml jsonschema
python3 scripts/validate.py
```
