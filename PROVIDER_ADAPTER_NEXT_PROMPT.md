Focus exclusively on the Overseer project in this current workspace.

Implement the OpenCode and terminal-native provider adapter (`overseer/provider.py`):
1. Create `overseer/provider.py` containing a provider helper, a registry of available models, and environment auto-detection.
2. Implement inspection logic so that if Overseer is invoked from an active terminal coding agent session (such as Claude Code, Codex, or OpenCode), it automatically detects and inherits that active CLI/LLM runner context rather than requiring hardcoded configuration.
3. Generate clean, safe argument vectors (argv) for headless execution (e.g., `opencode run --standalone --model <model> --format json --auto <instruction>`) without shell interpolation risks, ensuring correct workspace `$PWD` inheritance.
4. Integrate the provider into the factory execution flow so tasks can seamlessly leverage the inherited active session model.
5. Add comprehensive unit tests (testing with a mock binary on PATH and mocked environment markers) covering auto-detection, fallback handling, and argument generation.
6. Run python3 scripts/check and python3 scripts/check-doc-references to ensure 100% test pass rates and valid citations, update WORK_LOG.md, and commit clean.
