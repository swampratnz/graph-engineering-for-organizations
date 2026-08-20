# What

<!-- One paragraph: what changes and why. -->

## Spec review checklist

<!-- Delete sections that don't apply. Specs are reviewed like code. -->

For a new or changed GRAPH SPEC:

- [ ] Owner and backup owner are real people who agreed to it
- [ ] Every agent referenced is registered in `registry/agents.yaml` with scoped JIT credentials and a tested kill switch
- [ ] Every resource touched is in `registry/resources.yaml`; no writes to frozen instruments
- [ ] Every gate has reviewers (not the owner), a timeout, and an explicit timeout behavior
- [ ] Gate inputs are artifact + minimum context, not the worker's full chat
- [ ] Side-effect nodes have idempotency keys derived from `(run_id, step_id)`
- [ ] Cost cap and alert threshold are set and defensible

Security (all PRs):

- [ ] No secrets, tokens, or credential material anywhere in the diff (registries describe credentials, never contain them)
- [ ] No weakening of `scripts/validate.py`, CI, or CODEOWNERS without security-owner review
- [ ] Any new exception in `governance/exceptions.yaml` has a reason, a named approver, and an expiry ≤ 90 days

For an autonomy increase (gate removed, cap widened, sampling enabled):

- [ ] Anchor coverage demonstrated (external anchors from the team's anchor table, outcomes in run records)
- [ ] Four weeks of gate metrics attached: latency, override rate in band, no rubber-stamp flags
- [ ] `irreversible`/`external` gate classes keep 100% review
- [ ] Approved by shared services AND the security/identity owner
