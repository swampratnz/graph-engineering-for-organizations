# Runbook: agent incident response

For incidents involving an AI agent or workflow governed by this repo:
suspected credential compromise, an agent acting outside its spec, anomalous
spend, a gate bypassed, or a frozen instrument touched. Complements — does
not replace — the org's general security IR process; if one exists, this
slots in as the agent-specific annex.

## Severity

| Sev | Definition | Examples | First move |
|-----|-----------|----------|------------|
| **S1** | Credential compromise suspected, or an irreversible/externally visible action fired without its gate | Agent token used from unknown infra; payment/send/publish with no decision record | Kill switch, immediately, no approval needed |
| **S2** | Agent acting outside its spec, but gates held | Writes to an undeclared resource; spend past cap without runtime stop; gate resolved by an unauthorized person | Kill switch at DRI/security-owner discretion; halt new runs |
| **S3** | Governance signal, no active harm | Missed canary; rubber-stamp flags; orphaned spec found running; expired exception still relied on | Fix within the week; no kill needed |

When unsure between two severities, take the higher one.

## Response steps

1. **Stop the harm.** For S1/S2, execute `docs/runbooks/kill-switch.md` —
   credentials first, then in-flight runs. Stopping needs no approval;
   restarting does.
2. **Preserve evidence before touching anything else.** Snapshot: the run
   records and parent/child issues for affected runs, the agent's entries in
   the org audit log, the registry state (`git log` covers this repo), and
   spend records. For S1, export the audit log slice covering the
   credential's lifetime — threat #1 in `SECURITY.md` is only investigable
   from logs.
3. **Scope it.** From the resource declarations in the spec and the audit
   log: what could this identity reach, what did it actually touch, which
   runs are affected, did anything externally visible ship. Distrust the
   agent's own outputs as evidence; prefer the frozen instruments and
   third-party logs.
4. **Communicate.** S1: security owner notifies org leadership same day,
   plus any affected external parties per the org's disclosure obligations.
   S2: spec owner notifies the team and gate reviewers. All: note in the
   run's parent issue so the audit trail is self-contained.
5. **Regulatory check (S1, and S2 involving high-risk workflows).** If the
   workflow falls under the EU AI Act's high-risk provisions, serious
   incidents carry reporting obligations with deadlines — the security
   owner engages counsel the same day rather than deciding alone. The run
   records and audit plane are the evidence base
   (`governance/compliance-mapping.md`).
6. **Post-incident review, within one week.** Blameless, written, PR'd into
   the spec's Promotion history table. Must answer: which control failed or
   was missing (map to the `SECURITY.md` threat table), and what file in
   this repo changes so the same incident is caught earlier next time. An
   incident that produces no diff here is an unfinished review.
7. **Restart** only per the kill-switch runbook: root cause written, new
   credentials, security-owner-approved PR.

## Standing drills

- Kill-switch drill: quarterly (already in the quarterly review runbook).
- Tabletop: once a year, walk an S1 (compromised agent credential) end to
  end on paper with the security owner, one DRI, and one gate reviewer.
  Time step 1; findings PR'd like any post-incident review.
