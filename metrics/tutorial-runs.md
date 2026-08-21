# Tutorial run log

The guide's own gate metric, instrumented. The measure: time from clone
to a green `validate.py` including the runner's own first spec, using
only [`docs/tutorial-first-workflow.md`](../docs/tutorial-first-workflow.md).
The target: a fresh human completes it unaided in ≤60 minutes
([design](../docs/practical-guide-design.md#6-how-well-know-the-guide-works)).

Add your run by PR: honest numbers only, blockers included, no tidying.
Human runs are the benchmark. Agent runs prove nothing blocks and catch
broken commands, but do not count toward the ≤60-minute target: agents
read faster and get lost differently than people.

| Date | Runner | Repo commit | Total time | Green incl. own spec? | Blockers | Notes |
|------|--------|-------------|------------|----------------------|----------|-------|
| 2026-08-21 | AI coding agent (blind evaluation) | 07cf223 | 2 min 28 s | yes | none | Windows 11 / Python 3.11; every documented output matched; agent speed, not a human benchmark |

**Status: the ≤60-minute human target is unmet** until the first human
row lands. Until then, treat the target as an aspiration this log
exists to test, not a claim.
