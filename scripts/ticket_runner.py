#!/usr/bin/env python3
"""Minimal reference runner for the ticket runtime.

Executes one run of a GRAPH SPEC as local files that mirror the
ticket-based runtime (docs/implementation-examples.md §1): a parent
"issue", one child "gate issue" per gate, and, the part that matters,
gate decisions and a closing run record validated against this repo's
schemas. It exists so the contract is executable end-to-end with zero
infrastructure; wiring the same lifecycle to real GitHub/Jira issues
changes the transport, not the records.

    python3 scripts/ticket_runner.py start  --spec specs/example-team/ci-failure-explainer.md
    python3 scripts/ticket_runner.py decide --run <run_id> --gate weekly-digest-review \
        --by bob --decision approve --reason "digest accurate, spot-checked two runs"
    python3 scripts/ticket_runner.py complete --run <run_id> --spend 0.42

State lives under runs/<run_id>/ (gitignored): parent.md (human view),
state.json (machine state), gate-*.md, gate decision JSONs, and
run-record.json on completion. Contract rules the runner enforces, same
as CI does statically: the spec owner never resolves a gate
(non-waivable), spend above the spec's cap forces status cap_exceeded,
and a decision without a reason doesn't validate.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def jsonable(value):
    """PyYAML parses bare dates as datetime.date; state is stored as JSON."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value


def load_spec(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        die(f"{path} has no YAML frontmatter; is it a GRAPH SPEC?")
    fm = yaml.safe_load(text.split("\n---", 2)[0].lstrip("-").lstrip("\n"))
    if not isinstance(fm, dict):
        die(f"{path}: frontmatter did not parse to a mapping")
    return jsonable(fm)


def make_validator(schema_name: str):
    """Build a Draft 2020-12 validator; inline the gate-decision $ref so
    run-record validation needs no resolver. Returns None if jsonschema
    is missing (mirrors scripts/validate.py's graceful degradation)."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("WARNING jsonschema not installed; records written without "
              "schema validation (pip install -r requirements.txt)")
        return None
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    if schema_name == "run-record.schema.json":
        gate = json.loads((SCHEMAS / "gate-decision.schema.json").read_text(encoding="utf-8"))
        gate = {k: v for k, v in gate.items() if k not in ("$schema", "$id")}
        schema["properties"]["gates"]["items"] = copy.deepcopy(gate)
    return Draft202012Validator(schema)


def validate_or_die(validator, instance: dict, what: str) -> None:
    if validator is None:
        return
    problems = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if problems:
        for e in problems:
            loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
            print(f"ERROR: {what} invalid at {loc}: {e.message}", file=sys.stderr)
        sys.exit(1)


def spec_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "uncommitted"


def run_dir(runs_root: Path, run_id: str) -> Path:
    # run_id becomes a directory name (it comes from --run-id or is derived
    # from the spec's frontmatter name), so it must stay a single component
    # inside runs_root. Reject path separators, a leading dot, and parent
    # references so a crafted id cannot mkdir/write outside runs/.
    if (not isinstance(run_id, str) or not run_id
            or "/" in run_id or "\\" in run_id or "\x00" in run_id
            or run_id.startswith(".")):
        die(f"invalid run id {run_id!r}: use a single path component with no "
            "separators or leading dot")
    root = runs_root.resolve()
    resolved = (runs_root / run_id).resolve()
    if resolved != root and root not in resolved.parents:
        die(f"run id {run_id!r} escapes the runs directory {runs_root}")
    return runs_root / run_id


def load_state(runs_root: Path, run_id: str) -> dict:
    path = run_dir(runs_root, run_id) / "state.json"
    if not path.exists():
        die(f"no run {run_id!r} under {runs_root}/; start it first")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(runs_root: Path, state: dict) -> None:
    d = run_dir(runs_root, state["run_id"])
    (d / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    render_parent(d, state)


def render_parent(d: Path, state: dict) -> None:
    fm, decided = state["spec_fm"], {g["gate_id"] for g in state["gates"]}
    lines = [
        f"Title: [run] {fm['name']} (run_id: {state['run_id']})",
        "",
        f"Spec: {state['spec_path']} @ {state['spec_version']}",
        f"Agent: {', '.join(fm.get('agents', []))}",
        f"Status: {state['status']}",
        f"Spend: ${state['spend_usd']:.2f} / cap ${fm['cost']['cap_per_run_usd']:.2f}",
        "- [x] do the work (you or your coding agent; paste the artifact here)",
    ]
    for g in fm.get("gates") or []:
        mark = "x" if g["id"] in decided else " "
        lines.append(f"- [{mark}] GATE {g['id']} → gate-{g['id']}.md")
    lines.append(f"- [{'x' if state['status'] != 'waiting_on_gate' else ' '}] "
                 "attach run record (complete)")
    (d / "parent.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_start(args) -> None:
    spec_path = Path(args.spec)
    fm = load_spec(spec_path)
    run_id = args.run_id or f"{fm['name']}-{datetime.date.today().isoformat()}"
    d = run_dir(args.runs_dir, run_id)
    if d.exists():
        die(f"run dir {d} already exists; pass --run-id for a distinct run")
    d.mkdir(parents=True)
    for g in fm.get("gates") or []:
        esc = (f"escalates to @{g['escalate_to']}" if g.get("on_timeout") == "escalate"
               else g.get("on_timeout", "default_deny"))
        (d / f"gate-{g['id']}.md").write_text(
            f"Title: [gate] {g['id']} for {run_id} "
            f"(assignee: @{', @'.join(g.get('reviewers', []))})\n\n"
            "Artifact: <paste the artifact and the minimum context to judge "
            "it; never the worker agent's full transcript>\n"
            "Reply by running:\n"
            f"  python3 scripts/ticket_runner.py decide --run {run_id} "
            f"--gate {g['id']} --by <you> --decision approve|reject|modify "
            "--reason \"...\"\n"
            f"Timeout: {g['timeout_hours']}h → {esc}.\n", encoding="utf-8")
    state = {
        "run_id": run_id, "spec_path": str(spec_path),
        "spec_version": spec_version(), "spec_fm": fm,
        "status": "waiting_on_gate" if fm.get("gates") else "running",
        "started_at": now(), "spend_usd": 0.0, "gates": [],
        "nodes": [{"step_id": "work", "kind": "agent", "started_at": now(),
                   "idempotency_key": f"{run_id}:work"}],
    }
    save_state(args.runs_dir, state)
    print(f"run {run_id} started: {d}/parent.md"
          + (f" and {len(fm.get('gates') or [])} gate file(s)" if fm.get("gates") else ""))


def cmd_decide(args) -> None:
    state = load_state(args.runs_dir, args.run)
    fm = state["spec_fm"]
    gate = next((g for g in fm.get("gates") or [] if g["id"] == args.gate), None)
    if gate is None:
        die(f"spec {fm['name']!r} has no gate {args.gate!r}")
    by = args.by.casefold()
    if args.timed_out:
        decision = {"run_id": state["run_id"], "gate_id": args.gate,
                    "decision": "reject", "timed_out": True,
                    "reason": f"timeout after {gate['timeout_hours']}h: "
                              f"{gate.get('on_timeout', 'default_deny')} per spec",
                    "decided_by": "timeout", "decided_at": now()}
    else:
        if by == str(fm.get("owner", "")).casefold():
            die(f"{args.by} owns this spec; authors never resolve their own "
                "gates (GE-SELF-APPROVE, non-waivable)")
        if by == str(fm.get("backup_owner", "")).casefold():
            print(f"WARNING: {args.by} is the backup owner; CI allows this "
                  "only under an exception with an outside approver "
                  "(docs/paths/small-team.md)")
        allowed = {r.casefold() for r in gate.get("reviewers", [])}
        if gate.get("escalate_to"):
            allowed.add(str(gate["escalate_to"]).casefold())
        if by not in allowed:
            die(f"{args.by} is not a reviewer (or escalation target) on gate "
                f"{args.gate!r}: {sorted(allowed)}")
        decision = {"run_id": state["run_id"], "gate_id": args.gate,
                    "decision": args.decision, "reason": args.reason,
                    "decided_by": args.by, "decided_at": now()}
        if args.modification:
            decision["modification"] = args.modification
        if args.escalated_from:
            decision["escalated_from"] = args.escalated_from
    validate_or_die(make_validator("gate-decision.schema.json"), decision,
                    f"gate decision for {args.gate!r}")
    state["gates"] = [g for g in state["gates"] if g["gate_id"] != args.gate] + [decision]
    state["nodes"].append({"step_id": f"gate-{args.gate}", "kind": "gate",
                           "started_at": now(), "finished_at": now()})
    d = run_dir(args.runs_dir, state["run_id"])
    (d / f"decision-{args.gate}.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if all(any(g["gate_id"] == s["id"] for g in state["gates"])
           for s in fm.get("gates") or []):
        state["status"] = "running"
    save_state(args.runs_dir, state)
    print(f"gate {args.gate}: {decision['decision']} by {decision['decided_by']} "
          f"(recorded, schema-valid)")


def cmd_complete(args) -> None:
    state = load_state(args.runs_dir, args.run)
    fm, cap = state["spec_fm"], state["spec_fm"]["cost"]["cap_per_run_usd"]
    undecided = [g["id"] for g in fm.get("gates") or []
                 if not any(d["gate_id"] == g["id"] for d in state["gates"])]
    if undecided and args.status == "completed":
        die(f"gate(s) {undecided} undecided; decide them (or record their "
            "timeout with --timed-out) before completing")
    status = args.status
    if args.spend > cap:
        print(f"WARNING: spend ${args.spend} exceeds cap ${cap}; status "
              "forced to cap_exceeded (the cap is a hard stop)")
        status = "cap_exceeded"
    rejected = any(d["decision"] == "reject" for d in state["gates"])
    if status == "completed" and rejected:
        status = "rejected"
    for n in state["nodes"]:
        n.setdefault("finished_at", now())
    record = {"run_id": state["run_id"], "spec": fm["name"],
              "spec_version": state["spec_version"],
              "agents": fm.get("agents", []),
              "started_at": state["started_at"], "finished_at": now(),
              "status": status, "nodes": state["nodes"],
              "gates": state["gates"], "spend_usd": args.spend}
    validate_or_die(make_validator("run-record.schema.json"), record, "run record")
    state.update(status=status, spend_usd=args.spend)
    d = run_dir(args.runs_dir, state["run_id"])
    (d / "run-record.json").write_text(json.dumps(record, indent=2) + "\n",
                                       encoding="utf-8")
    save_state(args.runs_dir, state)
    print(f"run {state['run_id']} closed: {status}, ${args.spend:.2f}; "
          f"schema-valid run record at {d / 'run-record.json'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-dir", type=Path, default=ROOT / "runs",
                   help="where run state lives (default: runs/, gitignored)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="open a run from a spec")
    s.add_argument("--spec", required=True)
    s.add_argument("--run-id")
    s.set_defaults(fn=cmd_start)
    s = sub.add_parser("decide", help="record a gate decision")
    s.add_argument("--run", required=True)
    s.add_argument("--gate", required=True)
    s.add_argument("--by", default="")
    s.add_argument("--decision", choices=["approve", "reject", "modify"])
    s.add_argument("--reason", default="")
    s.add_argument("--modification")
    s.add_argument("--escalated-from")
    s.add_argument("--timed-out", action="store_true",
                   help="record the gate resolving via its timeout behavior")
    s.set_defaults(fn=cmd_decide)
    s = sub.add_parser("complete", help="close the run with a run record")
    s.add_argument("--run", required=True)
    s.add_argument("--spend", type=float, default=0.0)
    s.add_argument("--status", default="completed",
                   choices=["completed", "rejected", "failed", "killed"])
    s.set_defaults(fn=cmd_complete)
    args = p.parse_args()
    if args.cmd == "decide" and not args.timed_out:
        if not args.by or not args.decision or not args.reason:
            p.error("decide needs --by, --decision, and --reason (the reason "
                    "is what makes review measurable)")
    args.fn(args)


if __name__ == "__main__":
    main()
