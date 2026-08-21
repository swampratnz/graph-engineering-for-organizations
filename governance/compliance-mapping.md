# Compliance mapping

Where this repo's artifacts line up with the frameworks an enterprise audit
will ask about. This is a mapping aid for auditors and implementers; it is
**not legal advice and not a conformity claim**. Whether a given workflow is
in scope (e.g. "high-risk" under the EU AI Act) is a legal determination the
org makes with counsel; this table shows which artifact answers which
requirement once it is.

## EU AI Act (high-risk provisions, provider/deployer obligations)

| Requirement (paraphrased) | Where it lives here |
|---------------------------|---------------------|
| Risk management system across the lifecycle (Art. 9) | `SECURITY.md` threat model; pathology guards as platform defaults (spec frontmatter); quarterly review runbook |
| Record-keeping / automatic logs (Art. 12) | Run records (`schemas/run-record.schema.json`): nodes, models, gate decisions with who/when/why, spend, anchor outcomes; ticket threads as the durable store |
| Transparency to deployers (Art. 13) | The GRAPH SPEC itself: declared resources, gates, caps, autonomy class, owner |
| Human oversight, with real ability to intervene (Art. 14) | Human node contract (gates with structured decisions + timeouts); kill switch stop-without-approval; override-rate band and rubber-stamp detection proving oversight is real (`metrics/gate-health.md`) |
| Accuracy, robustness, cybersecurity (Art. 15) | Idempotency requirements; frozen instruments; JIT credential enforcement; platform hardening checklist |
| Serious incident reporting (Art. 73) | `docs/runbooks/incident-response.md` step 5, evidenced by run records |
| Identity/registration through the lifecycle | `registry/agents.yaml`: identity, owner, lifecycle states active→disabled→retired, recertification dates |

## NIST AI RMF

| Function | Where it lives here |
|----------|---------------------|
| **GOVERN** | `governance/decision-rights.md` (roles, decision rights); `governance/exceptions.yaml` (documented risk acceptance with expiry); CODEOWNERS routing |
| **MAP** | GRAPH SPECs (context, resources, autonomy class); anchor tables (what "good" externally means) |
| **MEASURE** | `metrics/gate-health.md` (latency, override rate, rubber-stamping, cost, anchor movement, review load) |
| **MANAGE** | Rollout checklist phase gates; kill-switch and incident runbooks; quarterly review; autonomy-increase evidence rules |

## ISO/IEC 42001 (AI management system)

| Clause theme | Where it lives here |
|--------------|---------------------|
| Leadership, roles, responsibilities (5) | Decision rights; named owner + backup on every spec and agent |
| Planning, risk & opportunity (6) | Threat model; anchor tables; phase gates |
| Support & resources (7) | Platform hardening; cost plumbing requirements |
| Operation & lifecycle controls (8) | Spec lifecycle draft→pilot→promoted→killed by PR; validator as operational control |
| Performance evaluation (9) | Gate health metrics; quarterly spec review |
| Improvement (10) | Post-incident review requiring a diff in this repo; canary findings |

## SOC 2 (common criteria, where agent workflows touch in-scope systems)

| Criteria theme | Where it lives here |
|----------------|---------------------|
| Logical access (CC6) | Agent identity registry, JIT credentials, scoped access, recertification |
| Change management (CC8) | Everything-by-PR + branch protection + required `validate` check |
| Risk mitigation & incident response (CC7/CC9) | Threat model; incident runbook; kill-switch drills |

## Keeping this honest

This file changes in the same PR as any control it references. At the
quarterly review, spot-check one row per framework: pull the artifact and
confirm it still does what the row claims. A mapping row without a living
artifact behind it is the compliance version of a rubber-stamped gate.
