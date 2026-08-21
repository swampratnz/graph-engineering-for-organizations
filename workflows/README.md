# Workflow scripts

Executable workflow scripts promoted from good runs (Phase 1). A script lands
here only alongside a GRAPH SPEC in `specs/`; the spec is the contract, the
script is one implementation of it.

Layout:

```
workflows/
  <team>/
    <spec-name>/
      workflow.md|.js|.py     # the runnable artifact (Claude workflow script,
                              # LangGraph graph, Temporal workflow, ...)
      README.md               # how to run it, links to its spec
```

Rules:

- **Install, don't copy.** Cross-team consumption happens via the plugin
  marketplace (namespaced, versioned, SHA-pinned), not by copying files
  between repos. This directory is the source the plugin is built from.
- Cross-cutting workflows (review standards, security checks, deploy
  patterns) live under `workflows/shared-services/` and are owned by the
  shared services maintainer; app-specific context stays in the app's own
  repository.
- A script whose spec is `deprecated` or `killed` gets deleted in the same
  PR that changes the spec status.
- Side-effect nodes derive idempotency keys from `(run_id, step_id)`; a
  script that can't safely retry a side effect doesn't get promoted.
