#!/usr/bin/env python3
"""Validate GRAPH SPECs, registries, anchor tables, and the exception
register against the rules in docs/plan.md and SECURITY.md.

Run from the repo root: python3 scripts/validate.py
Exit code 0 = clean, 1 = errors. Warnings never fail the build.

Every error carries a GE-* code. Most errors can be temporarily waived by an
entry in governance/exceptions.yaml (named approver who is not the target
spec's owner or backup, expiry <= 90 days); waived errors print as warnings.
Two codes are never waivable:

  GE-FROZEN-WRITE  writes to a frozen measurement instrument
  GE-SELF-APPROVE  a spec owner reviewing/escalation-target of their own gates

Identity handles (owners, backups, reviewers, escalation targets, approvers)
are compared case-insensitively; GitHub handles are case-insensitive, so
`Alice` and `alice` are the same person here too.

Checks, mapped to the plan:
  structural   GE-SCHEMA, GE-FM, GE-NAME-DUP  frontmatter shape; every .md
                                              under specs/ except the exact
                                              top-level TEMPLATE.md/README.md
                                              is validated; there is no
                                              filename that dodges the rules
  identity     GE-AGENT-*                     agents registered, active, owned,
                                              kill-switchable; JIT credentials
                                              (GE-CRED-STANDING); quarterly
                                              recertification (GE-AGENT-RECERT)
  humans       GE-OWNER-BACKUP, GE-HUMAN-ROLE owner != backup; roles held by
                                              people, not agent identities
  resources    GE-RES-UNREG, GE-FROZEN-WRITE, declared, frozen respected,
               GE-CONTENTION                  one writer per resource
  gates        GE-GATE-*, GE-SELF-APPROVE,    timeouts explicit, escalation
               GE-BACKUP-APPROVE,             named and independent of the
               GE-ESC-REVIEWER                gate it escalates from,
                                              separation of duties for owner
                                              (non-waivable) and backup
                                              (waivable by exception)
  autonomy     GE-SAMPLING-*, GE-ANCHOR-*     external anchors must exist in
                                              the team's anchor table
                                              (governance/anchors/<team>.yaml)
                                              and be measured by a frozen,
                                              registered instrument
  cost         GE-COST-ALERT, GE-COST-DAY     alert strictly below cap; daily
                                              cap (if set) >= per-run cap
  ownership    GE-ORPHAN                      review_by respected
  exceptions   GE-EXC-*                       register well-formed, not
                                              expired, not stale, not
                                              self-approved
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "specs"
SCHEMA_PATH = ROOT / "schemas" / "graph-spec.schema.json"
AGENTS_PATH = ROOT / "registry" / "agents.yaml"
RESOURCES_PATH = ROOT / "registry" / "resources.yaml"
EXCEPTIONS_PATH = ROOT / "governance" / "exceptions.yaml"
ANCHORS_DIR = ROOT / "governance" / "anchors"
CODEOWNERS_PATH = ROOT / ".github" / "CODEOWNERS"

# Only these exact paths are exempt from spec validation. Exclusion is by
# full path, not filename: a TEMPLATE.md nested anywhere else under specs/
# is validated like any spec (and fails on its placeholder values).
EXCLUDED_SPEC_FILES = {SPEC_DIR / "TEMPLATE.md", SPEC_DIR / "README.md"}

ACTIVE_STATUSES = {"pilot", "promoted"}
NON_WAIVABLE = {"GE-FROZEN-WRITE", "GE-SELF-APPROVE"}
MAX_EXCEPTION_DAYS = 90

TODAY = datetime.date.today()

errors: list[str] = []
warnings: list[str] = []
# active exceptions: (target, code) -> exception id; targets a spec name or
# a repo-relative path. Populated before any check runs, pruned of
# self-approved entries once spec ownership is known.
active_exceptions: dict[tuple[str, str], str] = {}
exception_entries: list[dict] = []
used_exceptions: set[str] = set()


def norm(handle) -> str | None:
    """GitHub handles are case-insensitive; compare them that way."""
    return handle.casefold() if isinstance(handle, str) else handle


def rel(path: Path | str) -> str:
    # Always forward-slash: exception targets are written with "/", and this
    # value is both printed and used as an exception-match key. Path.relative_to
    # would yield "\" on Windows, so local runs would disagree with Linux CI.
    try:
        return Path(path).relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def err(path: Path | str, code: str, msg: str, target: str | None = None) -> None:
    """Record an error unless an active exception waives it (then warn)."""
    for key in ((target, code) if target else (None,), (rel(path), code)):
        if key in active_exceptions and code not in NON_WAIVABLE:
            exc_id = active_exceptions[key]
            used_exceptions.add(exc_id)
            warnings.append(f"WAIVED  {rel(path)}: [{code}] {msg} "
                            f"(exception {exc_id})")
            return
    errors.append(f"ERROR   {rel(path)}: [{code}] {msg}")


def warn(path: Path | str, msg: str) -> None:
    warnings.append(f"WARNING {rel(path)}: {msg}")


def as_date(value) -> datetime.date | None:
    # datetime is a subclass of date; take its date part so comparisons
    # against TODAY never raise.
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def load_exceptions() -> None:
    if not EXCEPTIONS_PATH.exists():
        warn(EXCEPTIONS_PATH, "exception register missing")
        return
    try:
        data = yaml.safe_load(EXCEPTIONS_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        err(EXCEPTIONS_PATH, "GE-EXC-INVALID", f"not valid YAML: {e}")
        return
    seen_ids: set[str] = set()
    for entry in data.get("exceptions", []) or []:
        if not isinstance(entry, dict):
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID", f"malformed entry: {entry!r}")
            continue
        exc_id = str(entry.get("id", "<missing-id>"))
        missing = [f for f in ("id", "target", "code", "reason",
                               "approved_by", "granted", "expires")
                   if not entry.get(f)]
        if missing:
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID",
                f"exception {exc_id!r} missing {missing}")
            continue
        if exc_id in seen_ids:
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID", f"duplicate id {exc_id!r}")
            continue
        seen_ids.add(exc_id)
        code = str(entry["code"])
        if code in NON_WAIVABLE:
            err(EXCEPTIONS_PATH, "GE-EXC-NONWAIVABLE",
                f"exception {exc_id!r} targets non-waivable code {code}; "
                "frozen instruments and separation of duties never bend")
            continue
        approvers = entry["approved_by"]
        if not isinstance(approvers, list) or not approvers:
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID",
                f"exception {exc_id!r}: approved_by must be a non-empty list")
            continue
        granted, expires = as_date(entry["granted"]), as_date(entry["expires"])
        if granted is None or expires is None:
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID",
                f"exception {exc_id!r}: granted/expires must be dates")
            continue
        if (expires - granted).days > MAX_EXCEPTION_DAYS:
            err(EXCEPTIONS_PATH, "GE-EXC-INVALID",
                f"exception {exc_id!r}: expiry exceeds {MAX_EXCEPTION_DAYS} "
                "days from grant; renew consciously instead")
            continue
        if expires < TODAY:
            err(EXCEPTIONS_PATH, "GE-EXC-EXPIRED",
                f"exception {exc_id!r} expired {expires}; remove it or "
                "renew it by PR; the underlying error is live again")
            continue
        exception_entries.append(entry)
        active_exceptions[(str(entry["target"]), code)] = exc_id


def prune_self_approved_exceptions(specs: list[tuple[Path, dict]],
                                   agents: dict[str, dict]) -> None:
    """An exception approved by a party the waiver benefits is void.

    Resolvable for every legal target form, not just spec names:
      - spec name        -> that spec's owner + backup_owner
      - agent id         -> that agent's owner (GE-CRED-STANDING / GE-AGENT-RECERT
                            are emitted with the agent id as target)
      - registry path    -> the union of ALL agent owners, so a coarse
                            file-level waiver of an agent rule can only be
                            approved by someone who owns no agent in it.
    A target with no resolvable interested party (e.g. a spec-name target on
    an agent-scoped code, which no longer matches anything) is left alone; the
    stale-exception warning surfaces it.
    """
    interested: dict[str, set[str]] = {}
    for _, fm in specs:
        name = fm.get("name")
        if isinstance(name, str):
            interested[name] = {norm(fm.get("owner")),
                                norm(fm.get("backup_owner"))} - {None}
    all_agent_owners: set[str] = set()
    for agent_id, entry in agents.items():
        owner = norm(entry.get("owner"))
        interested[agent_id] = {owner} - {None}
        if owner is not None:
            all_agent_owners.add(owner)
    interested[rel(AGENTS_PATH)] = all_agent_owners
    for entry in exception_entries:
        target = str(entry["target"])
        owners = interested.get(target)
        if not owners:
            continue
        bad = [a for a in entry["approved_by"] if norm(a) in owners]
        if bad:
            exc_id = str(entry["id"])
            err(EXCEPTIONS_PATH, "GE-EXC-SELF",
                f"exception {exc_id!r} approved by {bad}; a party the waiver "
                f"of {target!r} benefits cannot approve it; the waiver is void")
            active_exceptions.pop((target, str(entry["code"])), None)


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        err(path, "GE-FM", "missing YAML frontmatter; every .md under "
            "specs/ (except the top-level TEMPLATE.md) must be a valid spec")
        return None
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        err(path, "GE-FM", "unterminated YAML frontmatter")
        return None
    try:
        data = yaml.safe_load(parts[0].lstrip("-").lstrip("\n") or parts[0][3:])
    except yaml.YAMLError as e:
        err(path, "GE-FM", f"frontmatter is not valid YAML: {e}")
        return None
    if not isinstance(data, dict):
        err(path, "GE-FM", "frontmatter did not parse to a mapping")
        return None
    for key in ("created", "review_by"):
        value = data.get(key)
        if isinstance(value, datetime.datetime):
            data[key] = value.date().isoformat()
        elif isinstance(value, datetime.date):
            data[key] = value.isoformat()
    return data


def load_registry(path: Path, key: str) -> dict[str, dict]:
    if not path.exists():
        err(path, "GE-REG", "registry file missing")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        err(path, "GE-REG", f"not valid YAML: {e}")
        return {}
    out: dict[str, dict] = {}
    for entry in data.get(key, []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            err(path, "GE-REG", f"entry without an id: {entry!r}")
            continue
        if entry["id"] in out:
            err(path, "GE-REG", f"duplicate id {entry['id']!r}")
            continue
        out[entry["id"]] = entry
    return out


def load_anchor_tables(resources: dict[str, dict]) -> dict[str, dict[str, str]]:
    """governance/anchors/<team>.yaml -> {team: {anchor_id: instrument_id}}.

    The machine-readable side of the anchor tables: what makes
    anchor_class: external checkable instead of prose.
    """
    tables: dict[str, dict[str, str]] = {}
    if not ANCHORS_DIR.exists():
        return tables
    for path in sorted(ANCHORS_DIR.glob("*.yaml")):
        if path.name == "TEMPLATE.yaml":
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            err(path, "GE-ANCHOR-TABLE", f"not valid YAML: {e}")
            continue
        team = data.get("team")
        if not team:
            err(path, "GE-ANCHOR-TABLE", "missing 'team'")
            continue
        if team in tables:
            err(path, "GE-ANCHOR-TABLE", f"duplicate anchor table for team "
                f"{team!r}")
            continue
        anchors: dict[str, str] = {}
        for anchor in data.get("anchors", []) or []:
            if not isinstance(anchor, dict) or not anchor.get("id") \
                    or not anchor.get("instrument"):
                err(path, "GE-ANCHOR-TABLE",
                    f"anchor entries need id and instrument: {anchor!r}")
                continue
            aid, instrument = anchor["id"], anchor["instrument"]
            if aid in anchors:
                err(path, "GE-ANCHOR-TABLE", f"duplicate anchor id {aid!r}")
                continue
            res = resources.get(instrument)
            if res is None:
                err(path, "GE-ANCHOR-INSTRUMENT",
                    f"anchor {aid!r}: instrument {instrument!r} is not in "
                    "registry/resources.yaml")
            elif not res.get("frozen"):
                err(path, "GE-ANCHOR-INSTRUMENT",
                    f"anchor {aid!r}: instrument {instrument!r} is not "
                    "frozen; an anchor measured by an instrument the "
                    "optimizing side can write to is an internal metric")
            anchors[aid] = instrument
        tables[team] = anchors
    return tables


def check_structural(path: Path, fm: dict, schema: dict, validator_cls) -> None:
    if validator_cls is None:
        return
    name = fm.get("name")
    for e in validator_cls(schema).iter_errors(fm):
        loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
        err(path, "GE-SCHEMA", f"{loc}: {e.message}", target=name)


def check_agents(path: Path, fm: dict, agents: dict[str, dict]) -> None:
    name = fm.get("name")
    for agent_id in fm.get("agents", []) or []:
        entry = agents.get(agent_id)
        if entry is None:
            err(path, "GE-AGENT-UNREG",
                f"agent {agent_id!r} is not in registry/agents.yaml; "
                "register the identity before the spec merges", target=name)
            continue
        if entry.get("status") != "active" and fm.get("status") in ACTIVE_STATUSES:
            err(path, "GE-AGENT-INACTIVE",
                f"agent {agent_id!r} has status {entry.get('status')!r} "
                "but the spec is active", target=name)
        if not entry.get("owner"):
            err(path, "GE-AGENT-NOOWNER",
                f"agent {agent_id!r} has no human owner in the registry",
                target=name)
        if not entry.get("kill_switch"):
            err(path, "GE-AGENT-NOKILL",
                f"agent {agent_id!r} has no kill switch in the registry",
                target=name)


def check_humans(path: Path, fm: dict, agent_ids: set[str]) -> None:
    """Owner != backup, and role-holders are people, not agent identities."""
    name = fm.get("name")
    owner, backup = fm.get("owner"), fm.get("backup_owner")
    if owner and backup and norm(owner) == norm(backup):
        err(path, "GE-OWNER-BACKUP",
            f"backup_owner {backup!r} is the owner; escalation and absence "
            "cover need a second person", target=name)
    roles = [("owner", owner), ("backup_owner", backup)]
    for gate in fm.get("gates") or []:
        gid = gate.get("id", "?")
        for r in gate.get("reviewers") or []:
            roles.append((f"gate {gid!r} reviewer", r))
        if gate.get("escalate_to"):
            roles.append((f"gate {gid!r} escalate_to", gate["escalate_to"]))
    ks = fm.get("kill_switch")
    if isinstance(ks, dict):
        for a in ks.get("authorized") or []:
            roles.append(("kill_switch.authorized", a))
    for role, handle in roles:
        if handle and norm(handle) in agent_ids:
            err(path, "GE-HUMAN-ROLE",
                f"{role} is {handle!r}, a registered agent identity; "
                "governance roles are held by humans (delegation, not "
                "impersonation)", target=name)


def check_gates(path: Path, fm: dict) -> None:
    name = fm.get("name")
    owner, backup = norm(fm.get("owner")), norm(fm.get("backup_owner"))
    status = fm.get("status")
    gates = fm.get("gates") or []
    if status in ACTIVE_STATUSES and not gates:
        err(path, "GE-GATE-NONE",
            "active spec has no gates; even sampling oversight keeps "
            "100% gates on irreversible/external actions", target=name)
    seen_ids: set[str] = set()
    for gate in gates:
        gid = gate.get("id", "<missing-id>")
        if gid in seen_ids:
            err(path, "GE-GATE-DUP", f"duplicate gate id {gid!r}", target=name)
        seen_ids.add(gid)
        reviewers = [norm(r) for r in gate.get("reviewers") or []]
        if owner and owner in reviewers:
            err(path, "GE-SELF-APPROVE",
                f"gate {gid!r}: spec owner {fm.get('owner')!r} is a "
                "reviewer: authors cannot approve their own graph's outputs",
                target=name)
        if backup and backup in reviewers:
            err(path, "GE-BACKUP-APPROVE",
                f"gate {gid!r}: backup owner {fm.get('backup_owner')!r} is a "
                "reviewer; the backup operates the workflow when the owner "
                "is away and must not review it (waivable by exception for "
                "small teams)", target=name)
        if gate.get("on_timeout") == "escalate":
            target_h = gate.get("escalate_to")
            if not target_h:
                err(path, "GE-GATE-ESC",
                    f"gate {gid!r}: on_timeout escalate needs escalate_to",
                    target=name)
                continue
            if norm(target_h) == owner:
                err(path, "GE-SELF-APPROVE",
                    f"gate {gid!r}: escalates to the spec owner; escalation "
                    "must not bypass separation of duties", target=name)
            elif norm(target_h) == backup:
                err(path, "GE-BACKUP-APPROVE",
                    f"gate {gid!r}: escalates to the backup owner; same "
                    "conflict as the backup reviewing (waivable by exception "
                    "for small teams)", target=name)
            if norm(target_h) in reviewers:
                err(path, "GE-ESC-REVIEWER",
                    f"gate {gid!r}: escalates to {target_h!r}, already a "
                    "reviewer on this gate; a timeout would escalate to "
                    "the person who just timed out", target=name)


def check_resources(path: Path, fm: dict, resources: dict[str, dict]) -> None:
    name = fm.get("name")
    declared = fm.get("resources") or {}
    for direction in ("reads", "writes"):
        ids = declared.get(direction, []) or []
        dupes = {r for r in ids if ids.count(r) > 1}
        for d in sorted(dupes):
            warn(path, f"resource {d!r} listed more than once under "
                       f"{direction}")
        for res_id in ids:
            entry = resources.get(res_id)
            if entry is None:
                err(path, "GE-RES-UNREG",
                    f"resource {res_id!r} ({direction}) is not in "
                    "registry/resources.yaml", target=name)
                continue
            if direction == "writes" and entry.get("frozen"):
                err(path, "GE-FROZEN-WRITE",
                    f"writes frozen resource {res_id!r}: measurement "
                    "instruments are frozen; no optimizing agent holds "
                    "write access to what measures it", target=name)


def check_autonomy(path: Path, fm: dict,
                   anchor_tables: dict[str, dict[str, str]]) -> None:
    name = fm.get("name")
    team = fm.get("team")
    autonomy = fm.get("autonomy") or {}
    anchor_class = autonomy.get("anchor_class")
    anchors = autonomy.get("anchors") or []
    oversight = autonomy.get("oversight")
    if anchor_class == "external":
        if not anchors:
            err(path, "GE-ANCHOR-MISSING",
                "anchor_class external requires named anchors from the "
                "team's anchor table", target=name)
        table = anchor_tables.get(team)
        if table is None:
            err(path, "GE-ANCHOR-TABLE",
                f"anchor_class external but no anchor table for team "
                f"{team!r}; add governance/anchors/{team}.yaml "
                "(see TEMPLATE.yaml)", target=name)
        else:
            for anchor in anchors:
                if anchor not in table:
                    err(path, "GE-ANCHOR-UNREG",
                        f"anchor {anchor!r} is not in team {team!r}'s anchor "
                        "table; a workflow may only claim external anchors "
                        "the table defines and a frozen instrument measures",
                        target=name)
    if oversight == "sampling":
        if anchor_class != "external":
            err(path, "GE-SAMPLING-ANCHOR",
                "sampling oversight requires anchor_class external; "
                "internal metrics alone never justify autonomy increases",
                target=name)
        if not autonomy.get("sampling_rate"):
            err(path, "GE-SAMPLING-RATE",
                "sampling oversight requires a sampling_rate", target=name)
        for gate in fm.get("gates") or []:
            if gate.get("class") in ("irreversible", "external"):
                break
        else:
            warn(path, "sampling oversight with no irreversible/external "
                       "gate; confirm nothing this graph does is "
                       "externally visible")


def check_cost(path: Path, fm: dict) -> None:
    name = fm.get("name")
    cost = fm.get("cost") or {}
    cap = cost.get("cap_per_run_usd")
    alert = cost.get("alert_threshold_usd")
    day = cost.get("cap_per_day_usd")
    if isinstance(cap, (int, float)) and isinstance(alert, (int, float)) and alert >= cap:
        err(path, "GE-COST-ALERT",
            f"alert_threshold_usd ({alert}) must be below "
            f"cap_per_run_usd ({cap}); the alert is the early warning",
            target=name)
    if isinstance(cap, (int, float)) and isinstance(day, (int, float)) and day < cap:
        err(path, "GE-COST-DAY",
            f"cap_per_day_usd ({day}) is below cap_per_run_usd ({cap}); "
            "a day contains at least one run", target=name)


def check_ownership(path: Path, fm: dict) -> None:
    review_by = as_date(fm.get("review_by"))
    if fm.get("review_by") is not None and review_by is None:
        err(path, "GE-ORPHAN", f"review_by {fm.get('review_by')!r} is not a date",
            target=fm.get("name"))
        return
    if review_by and review_by < TODAY:
        msg = (f"orphaned: review_by {review_by} has passed; re-verify the "
               "owner or kill the spec (quarterly spec review)")
        if fm.get("status") in ACTIVE_STATUSES:
            err(path, "GE-ORPHAN", msg, target=fm.get("name"))
        else:
            warn(path, msg)


def check_write_contention(specs: list[tuple[Path, dict]]) -> None:
    writers: dict[str, list[tuple[Path, dict]]] = {}
    for path, fm in specs:
        if fm.get("status") not in ACTIVE_STATUSES:
            continue
        for res_id in set((fm.get("resources") or {}).get("writes", []) or []):
            writers.setdefault(res_id, []).append((path, fm))
    for res_id, spec_list in writers.items():
        if len(spec_list) > 1:
            names = ", ".join(fm.get("name", rel(p)) for p, fm in spec_list)
            for path, fm in spec_list:
                err(path, "GE-CONTENTION",
                    f"write contention on {res_id!r} with [{names}]; "
                    "two nodes writing the same resource need an edge, "
                    "not parallelism", target=fm.get("name"))


def check_agent_registry(agents: dict[str, dict]) -> None:
    agent_ids = {norm(a) for a in agents}
    for agent_id, entry in agents.items():
        for field in ("owner", "created", "status", "credentials",
                      "kill_switch", "review_by"):
            if not entry.get(field):
                err(AGENTS_PATH, "GE-REG",
                    f"agent {agent_id!r} missing {field!r}")
        status = entry.get("status")
        if status not in (None, "active", "disabled", "retired"):
            err(AGENTS_PATH, "GE-REG",
                f"agent {agent_id!r} has unknown status {status!r}")
        if norm(entry.get("owner")) in agent_ids:
            err(AGENTS_PATH, "GE-HUMAN-ROLE",
                f"agent {agent_id!r} is owned by {entry.get('owner')!r}, "
                "a registered agent identity; owners are humans")
        ks = entry.get("kill_switch")
        if isinstance(ks, dict):
            authorized = ks.get("authorized") or []
            if not authorized:
                err(AGENTS_PATH, "GE-REG",
                    f"agent {agent_id!r} kill switch names no one authorized "
                    "to pull it")
            for a in authorized:
                if norm(a) in agent_ids:
                    err(AGENTS_PATH, "GE-HUMAN-ROLE",
                        f"agent {agent_id!r} kill switch authorizes "
                        f"{a!r}, a registered agent identity; only humans "
                        "pull kill switches")
        creds = entry.get("credentials")
        if status == "active" and isinstance(creds, dict) \
                and creds.get("kind") != "jit":
            err(AGENTS_PATH, "GE-CRED-STANDING",
                f"agent {agent_id!r} has {creds.get('kind')!r} credentials; "
                "policy requires JIT/ephemeral (docs/platform-hardening.md); "
                "a standing credential needs an expiring exception",
                target=agent_id)
        review_by = as_date(entry.get("review_by"))
        if entry.get("review_by") is not None and review_by is None:
            err(AGENTS_PATH, "GE-REG",
                f"agent {agent_id!r} review_by {entry.get('review_by')!r} "
                "is not a date")
        elif status == "active" and review_by and review_by < TODAY:
            err(AGENTS_PATH, "GE-AGENT-RECERT",
                f"agent {agent_id!r} recertification lapsed {review_by}; "
                "re-verify owner, scopes, and kill switch, then bump "
                "review_by", target=agent_id)


def main() -> int:
    try:
        from jsonschema import Draft202012Validator as validator_cls
    except ImportError:
        validator_cls = None
        warnings.append("WARNING jsonschema not installed; structural schema "
                        "checks skipped (pip install -r requirements.txt)")

    load_exceptions()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    agents = load_registry(AGENTS_PATH, "agents")
    resources = load_registry(RESOURCES_PATH, "resources")
    anchor_tables = load_anchor_tables(resources)
    agent_ids = {norm(a) for a in agents}

    if not CODEOWNERS_PATH.exists():
        warn(CODEOWNERS_PATH, "missing; review routing in "
             "governance/decision-rights.md is unenforced")

    # Pass 1: parse every spec so exception self-approval can be resolved
    # before any waivable check consults the register.
    specs: list[tuple[Path, dict]] = []
    names: dict[str, Path] = {}
    spec_files = sorted(p for p in SPEC_DIR.rglob("*.md")
                        if p not in EXCLUDED_SPEC_FILES)
    for path in spec_files:
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        specs.append((path, fm))
        name = fm.get("name")
        if isinstance(name, str):
            if name in names:
                err(path, "GE-NAME-DUP",
                    f"duplicate spec name {name!r} (also in {rel(names[name])})")
            names[name] = path

    # Void self-approved exceptions BEFORE any waivable check runs; the
    # agent-registry checks (GE-CRED-STANDING, GE-AGENT-RECERT) are waivable
    # and must consult the pruned register, so they follow the prune.
    prune_self_approved_exceptions(specs, agents)
    check_agent_registry(agents)

    # Pass 2: checks (err() consults the pruned exception register).
    for path, fm in specs:
        check_structural(path, fm, schema, validator_cls)
        check_agents(path, fm, agents)
        check_humans(path, fm, agent_ids)
        check_resources(path, fm, resources)
        check_gates(path, fm)
        check_autonomy(path, fm, anchor_tables)
        check_cost(path, fm)
        check_ownership(path, fm)

    check_write_contention(specs)

    for (target, code), exc_id in active_exceptions.items():
        if exc_id not in used_exceptions:
            warn(EXCEPTIONS_PATH,
                 f"exception {exc_id!r} ({code} on {target!r}) matches no "
                 "current error; remove it to keep the register clean")

    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    print(f"\n{len(spec_files)} spec(s), {len(agents)} agent(s), "
          f"{len(resources)} resource(s), {len(anchor_tables)} anchor "
          f"table(s), {len(active_exceptions)} active exception(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
