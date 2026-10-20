# Grok Build and Cursor installation result

## Authorized task and authorship
User confirmed official Grok Build coding terminal and added Cursor desktop setup. Dedicated /root/astra_next_prompt authored GROK_INSTALL_NEXT_PROMPT.md, requested gpt-6-astra/ultra; runtime model identity unconfirmed. Prompt snapshot/hash: /home/kali/Projects/Overseer/artifacts/devtools-install/20261019T031003Z/prompt.md and sha256.json. Primary agent read and executed it. Overseer directory has no Git repository; no starting commit claimed. Shared optimizer PLAYBOOK/TASK/REVIEW applied via this task/evidence record.

## Installed and checked
- Grok Build1.0.62 (1474f9cbdd91): /home/kali/.local/share/grok-build/1.0.62/grok; /home/kali/.local/bin/grok symlink. Official stable pointer https://x.ai/cli/stable and matching x.ai/cli/grok-1.0.62-linux-x86_64 artifact. Reviewed installer retained, but installed its exact official binary directly to avoid generic agent aliases and shell-profile edits.
- Cursor3.24.18 (be4c9e5350d77747b42cd467cbd3370a753d4640,x64): official https://cursor.com/download link https://api2.cursor.sh/updates/download/golden/linux-x64-deb/cursor/3.24. User-local extraction under /home/kali/.local/share/cursor/3.24.18; no system package installation. /home/kali/.local/bin/cursor points to vendor CLI; desktop entry /home/kali/.local/share/applications/cursor.desktop uses bundled icon.
- Eight version/help/login-help/fresh-shell/desktop-validation checks passed; exact commands, stdout/stderr and exit codes in checks.json and check-* files. Codex remains /home/kali/.local/bin/codex, version0.163.0; no generic agent alias created. No shell rc changes, services or Overseer config changes.
- Cursor was launched from the installed CLI into an isolated test profile without a repository argument. Visible welcome/onboarding screen inspected and captured in cursor-welcome.png. Early window-only captures were black; root capture showed splash then welcome. No rendering workaround or sandbox disablement was needed. Test window close requested after verification; existing default profile preserved.

## Limits and next user steps
Run `grok login` to authenticate, then `grok` from the desired workspace. Authentication/model access was not tested. Open Cursor from the applications menu or `cursor` and finish onboarding as needed. The welcome UI reports unavailable OS keyring; gnome-keyring-daemon is absent from PATH. Secure credential storage setup remains unresolved; no plaintext-storage workaround applied. No sign-in or AI prompt was initiated by this installation agent, no paid plan purchased and no model access claimed.

Overseer currently accepts codex/claude only (overseer/tmux.py and __main__.py). Grok/Cursor were not enrolled or added to automatic fallback. Provider integration and capacity fallback remain separate unfinished work, as does solver0006. This install task does not complete those broader objectives.

## Evidence, failures and rollback
Evidence directory: /home/kali/Projects/Overseer/artifacts/devtools-install/20261019T031003Z. Local SHA256 values identify downloaded bytes and prompt; no independently published signature/checksum was verified. Installer and downloaded artifacts retained. One setup helper assumed an icons directory and failed before desktop entry creation; corrected to vendor pixmaps icon. All final listed checks pass. No broad solver tests were needed.

Rollback: remove only the new ~/.local/bin/grok and cursor symlinks, new cursor.desktop entry, and the version directories listed above. Preserve ~/.config/Cursor and any authentication/user data. Updates require checking official releases and replacing these user-local versioned artifacts; package-manager auto-updates were not configured.
