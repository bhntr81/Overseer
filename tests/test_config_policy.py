"""Regression guard for the P0-B efficiency policy baked into config.json.

These assert the operator's standing policy (audit DEVELOPMENT_ENVIRONMENT_AUDIT.md,
P0-B, 2026-10-30), not library behavior: Sonnet is the default implementation
model, Opus stays available for explicit selection, the unattended daily cap is
small, the credit fallback still reaches the free tier, and the continuation
prompt is handoff-first while keeping the OVERSEER status contract intact.
"""
from pathlib import Path

from overseer.__main__ import settings
from overseer.modelchoice import providers, next_hop

CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def _config():
    return settings(CONFIG)


def test_claude_default_is_sonnet_with_opus_available():
    config = _config()
    claude = next(p for p in providers(config) if p["id"] == "claude")
    ids = [m["id"] for m in claude["models"]]
    assert ids[0] == "sonnet", "Sonnet must be the default (first) claude model"
    assert "opus" in ids, "Opus must remain available for explicit selection"


def test_unattended_daily_cap_is_small():
    assert _config()["max_per_day"] <= 4


def test_credit_fallback_reaches_free_tier():
    config = _config()
    assert config["fallback_policy"]["zero_credit"], "a zero-credit tier must exist"
    assert next_hop(config, "credit_exhausted", "claude") == "opencode"


def test_continuation_prompt_is_handoff_first_and_bounded():
    reply = _config()["reply"]
    assert len(reply) <= 1000 and "\n" not in reply
    assert "SESSION_HANDOFF.md" in reply, "prompt should prefer the concise handoff"
    assert "not whole" in reply or "not in full" in reply, "prompt should discourage whole-file re-reads"


def test_continuation_prompt_keeps_status_contract():
    reply = _config()["reply"]
    for marker in ("OVERSEER_REPORT", "OVERSEER_STEP_DONE", "OVERSEER_DONE", "OVERSEER_NEEDS_INPUT"):
        assert marker in reply, f"status contract marker {marker} must be preserved"
