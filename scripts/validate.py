#!/usr/bin/env python3
"""Validate GRAPH SPECs, registries, and the exception register against the
rules in docs/plan.md and SECURITY.md.

Run from the repo root: python3 scripts/validate.py
Exit code 0 = clean, 1 = errors. Warnings never fail the build.

Every error carries a GE-* code. Most errors can be temporarily waived by an
entry in governance/exceptions.yaml (named approver, expiry <= 90 days);
waived errors print as warnings. Two codes are never waivable:

  GE-FROZEN-WRITE  writes to a frozen measurement instrument
  GE-SELF-APPROVE  a spec owner reviewing/escalation-target of their own gates

Checks, mapped to the plan:
  structural   GE-SCHEMA, GE-FM, GE-NAME-DUP  frontmatter shape
  identity     GE-AGENT-*                     agents registered, active, owned,
                                              kill-switchable; JIT credentials
                                              (GE-CRED-STANDING); quarterly
                                              recertification (GE-AGENT-RECERT)
  humans       GE-OWNER-BACKUP, GE-HUMAN-ROLE owner != backup; owners/reviewers
                                              are people, not agent identities
  resources    GE-RES-UNREG, GE-FROZEN-WRITE, declared, frozen respected,
               GE-CONTENTION                  one writer per resource
  gates        GE-GATE-*, GE-SELF-APPROVE,    timeouts explicit, escalation
               GE-ESC-OWNER                   named, separation of duties
  autonomy     GE-SAMPLING-*, GE-ANCHOR-*     sampling needs external anchors
  cost         GE-COST-ALERT                  alert strictly below cap
  ownership    GE-ORPHAN                      review_by respected
  exceptions   GE-EXC-*                       register well-formed, not
                                              expired, not stale
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
CODEOWNERS_PATH = ROOT / ".github" / "CODEOWNERS"

ACTIVE_STATUSES = {"pilot", "promoted"}
NON_WAIVABLE = {"GE-FROZEN-WRITE", "GE-SELF-APPROVE"}
MAX_EXCEPTION_DAYS = 90

TODAY = datetime.date.today()

errors: list[str] = []
warnings: list[str] = []
# active exceptions: (target, code) -> exception id; targets a spec name or
# a repo-relative path. Populated before any check runs.
active_exceptions: dict[tuple[str, str], str] = {}
used_exceptions: set[str] = set()


def rel(path: Path | str) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


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
                f"exception {exc_id!r} targets non-waivable code {code} — "
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
                "days from grant — renew consciously instead")
            continue
        if expires < TODAY:
            err(EXCEPTIONS_PATH, "GE-EXC-EXPIRED",
                f"exception {exc_id!r} expired {expires} — remove it or "
                "renew it by PR; the underlying error is live again")
            continue
        active_exceptions[(str(entry["target"]), code)] = exc_id


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        err(path, "GE-FM", "missing YAML frontmatter (file must start with ---)")
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
        if isinstance(data.get(key), datetime.date):
            data[key] = data[key].isoformat()
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
                f"agent {agent_id!r} is not in registry/agents.yaml — "
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


def check_humans(path: Path, fm: dict, agents: dict[str, dict]) -> None:
    """Owner != backup, and role-holders are people, not agent identities."""
    name = fm.get("name")
    owner, backup = fm.get("owner"), fm.get("backup_owner")
    if owner and backup and owner == backup:
        err(path, "GE-OWNER-BACKUP",
            f"backup_owner {backup!r} is the owner — escalation and absence "
            "cover need a second person", target=name)
    roles = {("owner", owner), ("backup_owner", backup)}
    for gate in fm.get("gates") or []:
        gid = gate.get("id", "?")
        for r in gate.get("reviewers") or []:
            roles.add((f"gate {gid!r} reviewer", r))
        if gate.get("escalate_to"):
            roles.add((f"gate {gid!r} escalate_to", gate["escalate_to"]))
    for role, handle in roles:
        if handle and handle in agents:
            err(path, "GE-HUMAN-ROLE",
                f"{role} is {handle!r}, a registered agent identity — "
                "governance roles are held by humans (delegation, not "
                "impersonation)", target=name)


def check_resources(path: Path, fm: dict, resources: dict[str, dict]) -> None:
    name = fm.get("name")
    declared = fm.get("resources") or {}
    for direction in ("reads", "writes"):
        for res_id in declared.get(direction, []) or []:
            entry = resources.get(res_id)
            if entry is None:
                err(path, "GE-RES-UNREG",
                    f"resource {res_id!r} ({direction}) is not in "
                    "registry/resources.yaml", target=name)
                continue
            if direction == "writes" and entry.get("frozen"):
                err(path, "GE-FROZEN-WRITE",
                    f"writes frozen resource {res_id!r} — measurement "
                    "instruments are frozen; no optimizing agent holds "
                    "write access to what measures it", target=name)


def check_gates(path: Path, fm: dict) -> None:
    name = fm.get("name")
    owner = fm.get("owner")
    status = fm.get("status")
    gates = fm.get("gates") or []
    if status in ACTIVE_STATUSES and not gates:
        err(path, "GE-GATE-NONE",
            "active spec has no gates — even sampling oversight keeps "
            "100% gates on irreversible/external actions", target=name)
    seen_ids: set[str] = set()
    for gate in gates:
        gid = gate.get("id", "<missing-id>")
        if gid in seen_ids:
            err(path, "GE-GATE-DUP", f"duplicate gate id {gid!r}", target=name)
        seen_ids.add(gid)
        reviewers = gate.get("reviewers") or []
        if owner and owner in reviewers:
            err(path, "GE-SELF-APPROVE",
                f"gate {gid!r}: spec owner {owner!r} is a reviewer — "
                "authors cannot approve their own graph's outputs", target=name)
        if gate.get("on_timeout") == "escalate":
            target_h = gate.get("escalate_to")
            if not target_h:
                err(path, "GE-GATE-ESC",
                    f"gate {gid!r}: on_timeout escalate needs escalate_to",
                    target=name)
            elif target_h == owner:
                err(path, "GE-SELF-APPROVE",
                    f"gate {gid!r}: escalates to the spec owner — escalation "
                    "must not bypass separation of duties", target=name)


def check_autonomy(path: Path, fm: dict) -> None:
    name = fm.get("name")
    autonomy = fm.get("autonomy") or {}
    anchor_class = autonomy.get("anchor_class")
    anchors = autonomy.get("anchors") or []
    oversight = autonomy.get("oversight")
    if anchor_class == "external" and not anchors:
        err(path, "GE-ANCHOR-MISSING",
            "anchor_class external requires named anchors from the "
            "team's anchor table", target=name)
    if oversight == "sampling":
        if anchor_class != "external":
            err(path, "GE-SAMPLING-ANCHOR",
                "sampling oversight requires anchor_class external — "
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
                       "gate — confirm nothing this graph does is "
                       "externally visible")


def check_cost(path: Path, fm: dict) -> None:
    cost = fm.get("cost") or {}
    cap = cost.get("cap_per_run_usd")
    alert = cost.get("alert_threshold_usd")
    if isinstance(cap, (int, float)) and isinstance(alert, (int, float)) and alert >= cap:
        err(path, "GE-COST-ALERT",
            f"alert_threshold_usd ({alert}) must be below "
            f"cap_per_run_usd ({cap}) — the alert is the early warning",
            target=fm.get("name"))


def check_ownership(path: Path, fm: dict) -> None:
    review_by = as_date(fm.get("review_by"))
    if fm.get("review_by") is not None and review_by is None:
        err(path, "GE-ORPHAN", f"review_by {fm.get('review_by')!r} is not a date",
            target=fm.get("name"))
        return
    if review_by and review_by < TODAY:
        msg = (f"orphaned: review_by {review_by} has passed — re-verify the "
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
        for res_id in (fm.get("resources") or {}).get("writes", []) or []:
            writers.setdefault(res_id, []).append((path, fm))
    for res_id, spec_list in writers.items():
        if len(spec_list) > 1:
            names = ", ".join(fm.get("name", rel(p)) for p, fm in spec_list)
            for path, fm in spec_list:
                err(path, "GE-CONTENTION",
                    f"write contention on {res_id!r} with [{names}] — "
                    "two nodes writing the same resource need an edge, "
                    "not parallelism", target=fm.get("name"))


def check_agent_registry(agents: dict[str, dict]) -> None:
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
        ks = entry.get("kill_switch")
        if isinstance(ks, dict) and not ks.get("authorized"):
            err(AGENTS_PATH, "GE-REG",
                f"agent {agent_id!r} kill switch names no one authorized "
                "to pull it")
        creds = entry.get("credentials")
        if status == "active" and isinstance(creds, dict) \
                and creds.get("kind") != "jit":
            err(AGENTS_PATH, "GE-CRED-STANDING",
                f"agent {agent_id!r} has {creds.get('kind')!r} credentials — "
                "policy requires JIT/ephemeral (docs/platform-hardening.md); "
                "a standing credential needs an expiring exception")
        review_by = as_date(entry.get("review_by"))
        if status == "active" and review_by and review_by < TODAY:
            err(AGENTS_PATH, "GE-AGENT-RECERT",
                f"agent {agent_id!r} recertification lapsed {review_by} — "
                "re-verify owner, scopes, and kill switch, then bump "
                "review_by")


def main() -> int:
    try:
        from jsonschema import Draft202012Validator as validator_cls
    except ImportError:
        validator_cls = None
        warnings.append("WARNING jsonschema not installed — structural schema "
                        "checks skipped (pip install -r requirements.txt)")

    load_exceptions()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    agents = load_registry(AGENTS_PATH, "agents")
    resources = load_registry(RESOURCES_PATH, "resources")
    check_agent_registry(agents)

    if not CODEOWNERS_PATH.exists():
        warn(CODEOWNERS_PATH, "missing — review routing in "
             "governance/decision-rights.md is unenforced")

    specs: list[tuple[Path, dict]] = []
    names: dict[str, Path] = {}

    spec_files = sorted(p for p in SPEC_DIR.rglob("*.md")
                        if p.name not in ("TEMPLATE.md", "README.md"))
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
        check_structural(path, fm, schema, validator_cls)
        check_agents(path, fm, agents)
        check_humans(path, fm, agents)
        check_resources(path, fm, resources)
        check_gates(path, fm)
        check_autonomy(path, fm)
        check_cost(path, fm)
        check_ownership(path, fm)

    check_write_contention(specs)

    for (target, code), exc_id in active_exceptions.items():
        if exc_id not in used_exceptions:
            warn(EXCEPTIONS_PATH,
                 f"exception {exc_id!r} ({code} on {target!r}) matches no "
                 "current error — remove it to keep the register clean")

    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    print(f"\n{len(spec_files)} spec(s), {len(agents)} agent(s), "
          f"{len(resources)} resource(s), "
          f"{len(active_exceptions)} active exception(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
