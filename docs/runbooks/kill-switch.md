# Runbook: kill switch

Stop needs no approval. Restart does. Practice this before you need it.

## Who may pull it

The security/identity owner or the spec's DRI, per the agent's
`kill_switch.authorized` list in `registry/agents.yaml`. If you're unsure
whether you're authorized and you believe an agent is misbehaving or
compromised: pull it anyway and page the security owner. A wrongly stopped
workflow costs hours; a compromised agent credential is the Salesloft-Drift
pattern — its activity is indistinguishable from legitimate use until you
look.

## Stop (no approval)

1. **Revoke credentials first.** Execute the agent's `kill_switch.how` from
   the registry entry — revoke the token/trust binding at the identity
   provider. Registry edits alone don't stop a running process.
2. **Halt in-flight runs.** Cancel the runtime's active runs for the spec
   (close the parent issue for ticket-based runs; terminate the
   LangGraph/Temporal execution otherwise). Mark run records `killed`.
3. **Record it.** PR (or direct commit in an emergency — this is the one
   allowed case) setting the agent's `status: disabled` in
   `registry/agents.yaml`, with when/who/why in the commit message.
4. **Notify** the spec owner, the gate reviewers with pending gates, and the
   security owner.

## Restart (approval required)

1. Root cause written into the spec's Promotion history table.
2. New credentials issued (never re-enable the revoked ones).
3. PR flipping `status: disabled → active`, approved by the security/identity
   owner. CI blocks active specs referencing disabled agents, so the spec
   stays effectively off until this merges.

## Quarterly drill

Once a quarter, pick one active agent and time steps 1-2 without warning the
owner. If revocation takes longer than minutes or requires tribal knowledge,
that's a finding for the quarterly spec review.
