Focus exclusively on the Overseer project in this current workspace.

Implement autonomy increment 10 (Escalation Route):
1. Update the factory and orchestration pipeline so that tasks requiring human intervention, major structural decisions, or Claude-level escalation can be routed cleanly to the active terminal session or operator interface without breaking automation flow.
2. Ensure proper handling of escalation payloads, status flags, and ledger state transitions when an attempt hits an escalation boundary.
3. Add comprehensive unit tests covering escalation routing, state serialization, and recovery.
4. Run python3 scripts/check and python3 scripts/check-doc-references to ensure 100% test pass rates and valid documentation citations, update WORK_LOG.md, and commit clean.
