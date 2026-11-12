Focus exclusively on the Overseer project in this current workspace.

Implement autonomy increment 9 (The Unattended Loop):
1. Create or update the autonomous run loop (`overseer/loop.py` or equivalent integration) so that it drives the factory automatically.
2. For each iteration, the loop must use `overseer.provider.build_task` to construct the worker invocation, execute the run, read the worker report / evidence, and feed the next instruction automatically.
3. Ensure proper termination conditions, status tracking, and integration with the ledger and run evidence directories.
4. Add comprehensive unit tests in `tests/test_loop.py` (or `tests/test_factory.py`) covering multi-step autonomous execution and feedback processing.
5. Run python3 scripts/check and python3 scripts/check-doc-references to ensure 100% test pass rates and valid documentation citations, update WORK_LOG.md, and commit clean.
