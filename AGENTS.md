# Project instructions

## Shared optimizer and prompt-writing workflow

Follow `/home/kali/Projects/AGENTS.md`: use the `coder_optimization` playbook and
task/review guidance; assign a dedicated prompt-writing agent to read the latest
output and write the next bounded prompt, then have the primary agent execute
and verify it within the authorized scope. Preserve this project's specific
constraints and model requirements. This standing workflow supersedes older
wording that made optimizer guidance optional; it adds no runtime dependency.
