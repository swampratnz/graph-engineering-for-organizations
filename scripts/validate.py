#!/usr/bin/env python3
"""Validate GRAPH SPECs and registries against the rules in docs/plan.md.

Run from the repo root: python3 scripts/validate.py
Exit code 0 = clean, 1 = errors. Warnings never fail the build.

Checks, mapped to the plan:
  structural   - spec frontmatter matches schemas/graph-spec.schema.json
  identity     - every agent a spec references exists in registry/agents.yaml,
                 is active, and has an owner + kill switch (Phase 0)
  resources    - declared resources exist in registry/resources.yaml; no spec
                 writes a frozen resource (frozen measurement instruments); two
                 active specs writing the same resource is an error - they need
                 an edge, not parallelism (Phase 2)
  gates        - every gate has an explicit timeout behavior; escalation names
                 a target; the spec owner never reviews their own gates
                 (separation of duties); pilot/promoted specs have >= 1 gate;
                 irreversible/external gate classes survive sampling oversight
                 (Phase 3)
  autonomy     - sampling oversight requires external anchors; external anchor
                 class requires named anchors (design principles)
  cost         - alert threshold sits below the hard cap (Phase 0)
  ownership    - review_by in the past marks a spec orphaned: warning for
                 drafts, error for pilot/promoted (ownership decay is the
                 org-layer silent node failure)
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

ACTIVE_STATUSES = {"pilot", "promoted"}

errors: list[str] = []
warnings: list[str] = []


def err(path: Path | str, msg: str) -> None:
    errors.append(f"ERROR   {rel(path)}: {msg}")


def warn(path: Path | str, msg: str) -> None:
    warnings.append(f"WARNING {rel(path)}: {msg}")


def rel(path: Path | str) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        err(path, "missing YAML frontmatter (file must start with ---)")
        return None
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        err(path, "unterminated YAML frontmatter")
        return None
    try:
        data = yaml.safe_load(parts[0].lstrip("-").lstrip("\n") or parts[0][3:])
    except yaml.YAMLError as e:
        err(path, f"frontmatter is not valid YAML: {e}")
        return None
    if not isinstance(data, dict):
        err(path, "frontmatter did not parse to a mapping")
        return None
    for key in ("created", "review_by"):
        if isinstance(data.get(key), datetime.date):
            data[key] = data[key].isoformat()
    return data


def load_registry(path: Path, key: str) -> dict[str, dict]:
    if not path.exists():
        err(path, "registry file missing")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        err(path, f"not valid YAML: {e}")
        return {}
    out: dict[str, dict] = {}
    for entry in data.get(key, []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            err(path, f"entry without an id: {entry!r}")
            continue
        if entry["id"] in out:
            err(path, f"duplicate id {entry['id']!r}")
            continue
        out[entry["id"]] = entry
    return out


def check_structural(path: Path, fm: dict, schema: dict, validator_cls) -> bool:
    if validator_cls is None:
        return True  # jsonschema unavailable; cross-checks still run
    ok = True
    for e in validator_cls(schema).iter_errors(fm):
        loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
        err(path, f"schema: {loc}: {e.message}")
        ok = False
    return ok


def check_agents(path: Path, fm: dict, agents: dict[str, dict]) -> None:
    for agent_id in fm.get("agents", []) or []:
        entry = agents.get(agent_id)
        if entry is None:
            err(path, f"agent {agent_id!r} is not in registry/agents.yaml — "
                      "register the identity before the spec merges")
            continue
        if entry.get("status") != "active" and fm.get("status") in ACTIVE_STATUSES:
            err(path, f"agent {agent_id!r} has status {entry.get('status')!r} "
                      "but the spec is active")
        if not entry.get("owner"):
            err(path, f"agent {agent_id!r} has no human owner in the registry")
        if not entry.get("kill_switch"):
            err(path, f"agent {agent_id!r} has no kill switch in the registry")


def check_resources(path: Path, fm: dict, resources: dict[str, dict]) -> None:
    declared = fm.get("resources") or {}
    for direction in ("reads", "writes"):
        for res_id in declared.get(direction, []) or []:
            entry = resources.get(res_id)
            if entry is None:
                err(path, f"resource {res_id!r} ({direction}) is not in "
                          "registry/resources.yaml")
                continue
            if direction == "writes" and entry.get("frozen"):
                err(path, f"writes frozen resource {res_id!r} — measurement "
                          "instruments are frozen; no optimizing agent holds "
                          "write access to what measures it")


def check_gates(path: Path, fm: dict) -> None:
    owner = fm.get("owner")
    status = fm.get("status")
    gates = fm.get("gates") or []
    if status in ACTIVE_STATUSES and not gates:
        err(path, "active spec has no gates — even sampling oversight keeps "
                  "100% gates on irreversible/external actions")
    seen_ids: set[str] = set()
    for gate in gates:
        gid = gate.get("id", "<missing-id>")
        if gid in seen_ids:
            err(path, f"duplicate gate id {gid!r}")
        seen_ids.add(gid)
        reviewers = gate.get("reviewers") or []
        if owner and owner in reviewers:
            err(path, f"gate {gid!r}: spec owner {owner!r} is a reviewer — "
                      "authors cannot approve their own graph's outputs")
        if gate.get("on_timeout") == "escalate":
            target = gate.get("escalate_to")
            if not target:
                err(path, f"gate {gid!r}: on_timeout escalate needs escalate_to")
            elif target == owner:
                err(path, f"gate {gid!r}: escalates to the spec owner — "
                          "escalation must not bypass separation of duties")


def check_autonomy(path: Path, fm: dict) -> None:
    autonomy = fm.get("autonomy") or {}
    anchor_class = autonomy.get("anchor_class")
    anchors = autonomy.get("anchors") or []
    oversight = autonomy.get("oversight")
    if anchor_class == "external" and not anchors:
        err(path, "anchor_class external requires named anchors from the "
                  "team's anchor table")
    if oversight == "sampling":
        if anchor_class != "external":
            err(path, "sampling oversight requires anchor_class external — "
                      "internal metrics alone never justify autonomy increases")
        if not autonomy.get("sampling_rate"):
            err(path, "sampling oversight requires a sampling_rate")
        for gate in fm.get("gates") or []:
            if gate.get("class") in ("irreversible", "external"):
                break
        else:
            warn(path, "sampling oversight with no irreversible/external gate — "
                       "confirm nothing this graph does is externally visible")


def check_cost(path: Path, fm: dict) -> None:
    cost = fm.get("cost") or {}
    cap = cost.get("cap_per_run_usd")
    alert = cost.get("alert_threshold_usd")
    if isinstance(cap, (int, float)) and isinstance(alert, (int, float)) and alert >= cap:
        err(path, f"alert_threshold_usd ({alert}) must be below "
                  f"cap_per_run_usd ({cap}) — the alert is the early warning")


def check_ownership(path: Path, fm: dict, today: datetime.date) -> None:
    review_by = fm.get("review_by")
    if isinstance(review_by, str):
        try:
            review_by = datetime.date.fromisoformat(review_by)
        except ValueError:
            err(path, f"review_by {review_by!r} is not a date")
            return
    if not isinstance(review_by, datetime.date):
        return
    if review_by < today:
        msg = (f"orphaned: review_by {review_by} has passed — re-verify the "
               "owner or kill the spec (quarterly spec review)")
        if fm.get("status") in ACTIVE_STATUSES:
            err(path, msg)
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
            for path, _ in spec_list:
                err(path, f"write contention on {res_id!r} with [{names}] — "
                          "two nodes writing the same resource need an edge, "
                          "not parallelism")


def check_agent_registry(agents: dict[str, dict]) -> None:
    for agent_id, entry in agents.items():
        for field in ("owner", "created", "status", "credentials", "kill_switch"):
            if not entry.get(field):
                err(AGENTS_PATH, f"agent {agent_id!r} missing {field!r}")
        if entry.get("status") not in (None, "active", "disabled", "retired"):
            err(AGENTS_PATH, f"agent {agent_id!r} has unknown status "
                             f"{entry.get('status')!r}")
        ks = entry.get("kill_switch")
        if isinstance(ks, dict) and not ks.get("authorized"):
            err(AGENTS_PATH, f"agent {agent_id!r} kill switch names no one "
                             "authorized to pull it")


def main() -> int:
    try:
        from jsonschema import Draft202012Validator as validator_cls
    except ImportError:
        validator_cls = None
        warnings.append("WARNING jsonschema not installed — structural schema "
                        "checks skipped (pip install jsonschema)")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    agents = load_registry(AGENTS_PATH, "agents")
    resources = load_registry(RESOURCES_PATH, "resources")
    check_agent_registry(agents)

    today = datetime.date.today()
    specs: list[tuple[Path, dict]] = []
    names: dict[str, Path] = {}

    spec_files = sorted(p for p in SPEC_DIR.rglob("*.md")
                        if p.name != "TEMPLATE.md" and p.name != "README.md")
    for path in spec_files:
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        specs.append((path, fm))
        name = fm.get("name")
        if isinstance(name, str):
            if name in names:
                err(path, f"duplicate spec name {name!r} (also in {rel(names[name])})")
            names[name] = path
        check_structural(path, fm, schema, validator_cls)
        check_agents(path, fm, agents)
        check_resources(path, fm, resources)
        check_gates(path, fm)
        check_autonomy(path, fm)
        check_cost(path, fm)
        check_ownership(path, fm, today)

    check_write_contention(specs)

    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    print(f"\n{len(spec_files)} spec(s), {len(agents)} agent(s), "
          f"{len(resources)} resource(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
