# Validator error reference

Every error `scripts/validate.py` can emit, by `GE-*` code: when it
trips, how to fix it, and whether an exception can waive it. The
validator's source is authoritative; this page is hand-maintained
against it (a `--list-codes` flag to mechanize the diff is on the
[design backlog](practical-guide-design.md#4-implementation-plan)).

**How waiving works:** most errors can be temporarily downgraded to
warnings by an entry in
[`governance/exceptions.yaml`](../governance/exceptions.yaml): named
approver (who is not a party the waiver benefits, resolved for spec,
agent, and registry-file targets alike), expiry ≤ 90 days, checked by
CI. **Never waivable**, and the validator refuses exceptions targeting
them: `GE-FROZEN-WRITE` and `GE-SELF-APPROVE` (frozen instruments and
separation of duties never bend), **and the whole `GE-EXC-*` family**:
an exception cannot waive a finding about the exception register itself,
or one actor could approve away the very check that catches their
self-approval ([SECURITY.md](../SECURITY.md)). When a self-approved
exception is voided, the error it targeted resurfaces as an error rather
than being swallowed, so the remediation signal is never lost.

## What the validator does not check

The validator proves the files are internally coherent. It is not a
runtime and it does not reach outside the repo, so these are checked by
the platform, the runtime, or human review, never by CI. Adopters should
read this as the honest boundary of the green checkmark:

- **That a handle is a real person, or holds the role it claims.** The
  validator compares strings; `security-owner` or a reviewer handle could
  be nobody. Personhood and role are enforced by PR review, CODEOWNERS +
  branch protection, and gate assignment ([FAQ](faq.md)); there is no
  machine roster of role-holders yet (a plausible `governance/roles.yaml`
  is unbuilt, called out here so its absence is explicit, not implied).
- **The real credential behind a `kind: jit` entry.** A standing token
  hiding behind a `jit` string passes; the
  [registry-vs-IAM reconciliation job](rollout-checklist.md#phase-3-backlog-scheduled-not-started)
  is the (unbuilt) control, and `docs/platform-hardening.md` is the
  interim.
- **That frozen-instrument write access is actually revoked** in the
  measuring system's own IAM (`platform-hardening.md`).
- **That the runtime honours** `cap_per_run_usd`, timeouts, `on_timeout`,
  the sampling rate, or idempotency keys. The spec declares intent; the
  engine enforces it (`AGENTS.md` Phase C.4).
- **The four-weeks-of-metrics evidence** for an autonomy increase: the
  validator checks `anchor_class: external` and defined anchors; the
  metrics half is a PR-description requirement
  ([decision-rights](../governance/decision-rights.md)).
- **Spec prose, or free-text fields** (`kill_switch.how`,
  `credentials.scope`, `issued_via`): shape is checked, content is not.
- **Prompt injection through processed data**: no spec fixes it; gate
  contracts and blast-radius limits are the mitigation
  ([enterprise path](paths/enterprise.md)).
- **Branch protection and CODEOWNERS enforcement themselves**: GitHub
  settings, not files. Without them everything here is advisory
  ([SECURITY.md](../SECURITY.md) hardening baseline).

## Structural

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-FM` | A `.md` under `specs/` (other than top-level `TEMPLATE.md`/`README.md`) has missing, unterminated, or invalid YAML frontmatter | Every file under `specs/` is a spec; give it valid frontmatter or move it out |
| `GE-SCHEMA` | Frontmatter violates [`schemas/graph-spec.schema.json`](../schemas/graph-spec.schema.json): missing required field, wrong enum, mixed-case handle | The message names the exact path (e.g. `gates/0: 'timeout_hours' is a required property`); fix that field |
| `GE-NAME-DUP` | Two specs share a `name` | Names are unique across `specs/`; rename one |

## Agent identity

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-AGENT-UNREG` | A spec references an agent id not in [`registry/agents.yaml`](../registry/agents.yaml) | Register the identity in the same PR; registration precedes credentials |
| `GE-AGENT-INACTIVE` | An active (pilot/promoted) spec references an agent whose status isn't `active` | Restart the agent per [decision rights](../governance/decision-rights.md) (approval required) or deactivate the spec |
| `GE-AGENT-NOOWNER` | Agent entry has no human owner | Name one person, not a team alias |
| `GE-AGENT-NOKILL` | Agent entry has no kill switch | Add `kill_switch.how` plus named `authorized` holders |
| `GE-CRED-STANDING` | An active agent's `credentials.kind` isn't `jit` | Move to OIDC exchange or per-agent App tokens ([hardening](platform-hardening.md)); a standing credential needs an expiring exception |
| `GE-AGENT-RECERT` | An active agent's `review_by` has passed | Re-verify owner, scopes, and kill switch; bump the date (quarterly review) |
| `GE-REG` | A registry file is malformed: missing/duplicate ids, missing required fields, unknown status, kill switch authorizing no one, non-date `review_by` | Fix the named entry |

## Humans and separation of duties

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-OWNER-BACKUP` | `backup_owner` is the owner | Two different people; absence cover needs a second human |
| `GE-HUMAN-ROLE` | A governance role (owner, backup, reviewer, escalation, kill-switch holder) is a registered *agent* identity | Roles are held by humans: delegation, never impersonation |
| `GE-SELF-APPROVE` | The spec owner is a reviewer or escalation target on their own gate | **Never waivable.** A different human reviews; see the [separation table](paths/small-team.md#the-separation-of-duties-math) for who can hold what at your size |
| `GE-BACKUP-APPROVE` | The backup owner is a reviewer or escalation target | Waivable for small teams, and at 2 people the exception's approver must be an *outside* human (`GE-EXC-SELF` voids owner/backup approvals) |
| `GE-ESC-REVIEWER` | A gate escalates to someone already reviewing that gate | Escalation needs a fresh person; or use `default_deny` |
| `GE-GATE-ESC` | `on_timeout: escalate` with no `escalate_to` | Name the person, or switch to `default_deny`/`reroute` |
| `GE-GATE-NONE` | An active spec has no gates | Add at least one gate, or return the spec to `draft` |
| `GE-GATE-DUP` | Two gates share an id within a spec | Rename one |

## Resources

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-RES-UNREG` | A spec reads/writes a resource not in [`registry/resources.yaml`](../registry/resources.yaml) | Register it in the same PR |
| `GE-FROZEN-WRITE` | A spec declares a write on a `frozen: true` resource | **Never waivable.** Measurement instruments stay outside the optimizing loop; remove the write |
| `GE-CONTENTION` | Two active specs write the same resource | Two writers need an edge, not parallelism: merge the specs, sequence them, or split the resource |

## Autonomy and anchors

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-SAMPLING-ANCHOR` | `oversight: sampling` without `anchor_class: external` | Internal metrics never justify autonomy: earn anchors first, or stay full-gating |
| `GE-SAMPLING-RATE` | Sampling without a `sampling_rate` | State the rate (e.g. `0.15`) |
| `GE-ANCHOR-MISSING` | `anchor_class: external` with an empty `anchors` list | Name anchors from the team's table |
| `GE-ANCHOR-TABLE` | No (or malformed) `governance/anchors/<team>.yaml` for a team claiming external anchors | Create it from [TEMPLATE.yaml](../governance/anchors/TEMPLATE.yaml) |
| `GE-ANCHOR-UNREG` | A spec claims an anchor id its team's table doesn't define | Add the anchor to the table (with its frozen instrument) or drop the claim |
| `GE-ANCHOR-INSTRUMENT` | An anchor's instrument isn't registered, or isn't frozen | Register the instrument with `frozen: true`; an anchor measured by something the optimizing side can write is an internal metric |

## Cost and ownership

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-COST-ALERT` | `alert_threshold_usd` ≥ `cap_per_run_usd` | The alert is the early warning; set it strictly below the cap |
| `GE-COST-DAY` | `cap_per_day_usd` < `cap_per_run_usd` | A day contains at least one run; raise the daily cap or lower the per-run cap |
| `GE-ORPHAN` | An active spec's `review_by` has passed (or isn't a date) | Re-confirm ownership and bump the date, or kill the spec; ownership decay is the org-layer silent node failure |

## Exception register

These report defects in the register itself. Fix the register rather
than reaching for another exception:

| Code | Trips when | Fix |
|------|-----------|-----|
| `GE-EXC-INVALID` | An entry is malformed: missing fields, bad dates, duplicate id, empty approver list, or expiry more than 90 days from grant | Complete the entry per the template comments in [`exceptions.yaml`](../governance/exceptions.yaml) |
| `GE-EXC-EXPIRED` | An entry's `expires` has passed | Remove it, or renew it consciously by PR; the underlying error is live again |
| `GE-EXC-NONWAIVABLE` | An entry targets `GE-FROZEN-WRITE`, `GE-SELF-APPROVE`, or any `GE-EXC-*` code | Delete it; these never bend, and an exception cannot waive a finding about the register itself ([SECURITY.md](../SECURITY.md)) |
| `GE-EXC-SELF` | An entry is approved by the target spec's own owner or backup | The waiver is void; an independent approver (security/identity owner or shared-services maintainer) must sign it |

Warnings (never fail the build, still worth reading): a resource listed
twice in one spec, sampling with no irreversible/external gate, an
exception matching no current error, a missing CODEOWNERS file, an
orphaned non-active spec, and `jsonschema` not installed (which skips
`GE-SCHEMA` checks; install the pinned requirements).
