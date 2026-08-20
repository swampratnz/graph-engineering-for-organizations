# Implementation examples

Concrete ways to run the graphs this repo governs. The spec is the contract;
these are interchangeable engines under it — chosen in order of pragmatism
(`docs/plan.md`, Phase 2), and you should not move down the list until the
current level has failed for a stated, written reason.

## Choosing a runtime

| Start here if… | Runtime | Move on only when |
|----------------|---------|-------------------|
| Always — any team size, no infrastructure | **Ticket-based state** (§1) | You need programmatic branching/state the issue tracker can't express, *written down as the reason* |
| Graphs need code: conditional edges, retries, structured state | **LangGraph + checkpointer** (§2) | Runs must survive worker crashes and multi-day waits at scale |
| Durability is the product requirement | **Temporal underneath** (§3) | — |

A reference implementation of the ticket runtime's record lifecycle
ships in this repo: `python3 scripts/ticket_runner.py --help` (start a
run, record gate decisions, close with a schema-valid run record) — use
it to execute the tutorial's manual run, or as the seed of your own
resume job.

## Runtime crosswalk

The gate contract (pause, structured human decision, timeout behavior,
resume) maps onto every major engine's primitive — adopt the spec layer
without changing engines:

| Engine | Gate/pause primitive | Durable state | Timeout handling |
|--------|---------------------|---------------|------------------|
| Ticket system (GitHub/Jira/Linear) | Assigned child issue + `/approve\|/reject\|/modify` reply | The issue thread | Scheduler watches open gates; applies spec's `on_timeout` |
| LangGraph | `interrupt()` at the gate node | Checkpointer (e.g. Postgres) | External scheduler resumes with `on_timeout` result |
| Temporal | Signal + `workflow.wait_condition(timeout=…)` | Event-sourced history | Native — timeout falls out of `wait_condition` |
| AWS Step Functions | `waitForTaskToken` callback | Execution state | State-machine timeout on the wait state |
| Microsoft Agent Framework | Workflow checkpoint + HITL approval | Checkpoint store | Framework timeout + resume |
| OpenAI Agents SDK | Tool-approval interrupts | Session/state store | Caller-managed |
| Claude Agent SDK | Permission callbacks (model asks) + hooks (deterministic gates that don't ask the model) | Session + your store | Caller-managed |
| GitHub Agentic Workflows / Actions | PR review or environment approval as the gate; "safe outputs" only | The PR/issue itself | Environment wait timers; branch protection |

Whatever the engine: the reviewer's decision is recorded per
`schemas/gate-decision.schema.json`, the run per
`schemas/run-record.schema.json` — identical records across engines is
what keeps override-rate and audit queries computable when you migrate.

## 1. Ticket-based state (start here)

No new infrastructure: your ticket system is the state store, the gate
surface, and the audit trail at once. Works with GitHub Issues/Projects,
Jira, or Linear.

**Run = parent issue.** Opened by the trigger (cron, webhook, or a human):

```markdown
Title: [run] weekly-release-review 2026-08-21 (run_id: wrr-2026-08-21)

Spec: specs/example-team/weekly-release-review.md @ a1b2c3d
Agent: example-release-bot
Status: running
Spend: $0.00 / cap $10.00
- [x] collect merged PRs
- [x] draft release summary + notes
- [ ] GATE release-go-no-go → #124
- [ ] publish notes
```

**Gate = child issue, assigned to the reviewer.** Contains the artifact and
the minimum context to judge it — never the worker agent's transcript:

```markdown
Title: [gate] release-go-no-go for wrr-2026-08-21 (assignee: @bob)

Artifact: release summary (below). Risk callouts: 2. Telemetry snapshot: green.
Reply with exactly one of:
  /approve <reason>
  /reject <reason>
  /modify <what you changed> <reason>
Timeout: 24h → escalates to @carol. Decision is recorded verbatim.
```

The reviewer's reply is parsed into a gate-decision record
(`schemas/gate-decision.schema.json`) and posted back on the parent issue;
the run resumes. On completion, the run record
(`schemas/run-record.schema.json`) is attached as the parent issue's closing
comment. Gate latency and override rate fall out of issue timestamps and the
parsed decisions — that's the whole metrics pipeline at this stage.

The "resume" can be as simple as a scheduled job that scans open runs for
resolved gates, or a webhook that re-invokes the agent with the run state.
Either way the state lives in the issue, not in a process.

## 2. LangGraph + checkpointer (when you need programmatic graphs)

`interrupt()` pauses at the gate node, the checkpointer persists exact
state, and the resume consumes no compute while waiting:

```python
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver

def gate_release_go_no_go(state):
    decision = interrupt({                      # pauses here; state persisted
        "gate_id": "release-go-no-go",
        "artifact": state["summary"],           # minimum context, not the transcript
    })
    record_gate_decision(state["run_id"], decision)   # audit plane
    if decision["decision"] != "approve":
        return Command(goto="halt")
    return state

# resume later — hours or days — from the exact node:
graph.invoke(
    Command(resume={"decision": "approve", "reason": "...", "decided_by": "bob"}),
    config={"configurable": {"thread_id": run_id}},
)
```

Timeout behavior lives outside the graph: a scheduler watches pending
interrupts and, past `timeout_hours`, resumes with the spec's `on_timeout`
result (`default_deny`) or reassigns (`escalate`). Side-effect nodes derive
idempotency keys from `(run_id, step_id)` before calling anything external.

## 3. Temporal underneath (when runs must survive crashes and multi-day waits)

Approval is a signal; the workflow blocks on a condition with the spec's
timeout; event-sourced history doubles as the audit trail:

```python
@workflow.defn
class WeeklyReleaseReview:
    def __init__(self):
        self.decision = None

    @workflow.signal
    def gate_decision(self, decision: dict):
        self.decision = decision

    @workflow.run
    async def run(self, params):
        summary = await workflow.execute_activity(draft_summary, params,
            start_to_close_timeout=timedelta(minutes=10))
        open_gate_ticket("release-go-no-go", summary)      # surface unchanged
        ok = await workflow.wait_condition(
            lambda: self.decision is not None,
            timeout=timedelta(hours=24))                   # spec's timeout_hours
        if not ok:
            self.decision = escalate_or_deny()             # spec's on_timeout
        if self.decision["decision"] == "approve":
            await workflow.execute_activity(publish_notes, summary,
                start_to_close_timeout=timedelta(minutes=5))
```

Note the human surface didn't change — still a ticket and a structured
reply. Temporal replaces the *durability* layer, not the gate contract.

## Sampling, concretely

For a spec with `oversight: sampling` (see
`specs/example-team/dependency-update-triage.md`): draw the sample at run
time with a seeded hash of `run_id` (auditable, not gameable by re-rolling),
route sampled artifacts through the same gate machinery as full review, and
record decisions identically — override rate must be computable across both
modes. Gates of class `irreversible`/`external` are never sampled; they keep
100% review whatever the spec's oversight mode.

## Wiring the validator into your CI

The enforcement layer is one script with two pinned dependencies:

```sh
pip install -r requirements.txt
python3 scripts/validate.py   # exit 0 = compliant
```

`.github/workflows/validate.yml` shows the reference setup: PRs, pushes to
main, a weekly schedule (so orphaned specs surface without traffic), and
`workflow_dispatch` as a keepalive. On other CI systems, run the same script
on the same triggers and make it a required check — then apply
`docs/platform-hardening.md` so the check can't be bypassed.
