# Claude Code project instructions

Follow `AGENTS.md` — it contains the ground rules for any AI agent working
in this repository and the setup playbook for deploying it in an
organization.

Quick facts:

- Validate before pushing: `pip install -r requirements.txt && python3 scripts/validate.py` (exit 0 required).
- All changes via PR; never weaken the validator or CI to get green — rule
  relaxations go through `governance/exceptions.yaml` with a human approver
  and an expiry.
- Never commit secrets; registries describe credentials, they never contain
  them.
- `frozen: true` resources never gain write access, and that rule is
  non-waivable.
