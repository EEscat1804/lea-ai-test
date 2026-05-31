import pytest

from guardrails.session import SessionState
from persona.system_prompts import (
    DEFAULT_PERSONA,
    MODE_GUIDANCE,
    RESPONSE_MODES,
    PersonaFeatureManager,
    compose_system_prompt,
    get_persona_prompt,
)


def test_default_persona_is_returned() -> None:
    assert get_persona_prompt("default") == DEFAULT_PERSONA


def test_unknown_persona_falls_back_to_default() -> None:
    assert get_persona_prompt("nonexistent") == DEFAULT_PERSONA


def test_default_persona_mentions_legal_advice_guardrail() -> None:
    """Regression: if someone edits the persona and drops the legal-advice
    guardrail, this test fails. Don't remove unless you've replaced the
    guardrail with an equivalent rule elsewhere."""
    assert "legal advice" in DEFAULT_PERSONA.lower()


def test_default_persona_mentions_emergency_resources() -> None:
    """Regression: crisis-routing rule must stay in the persona."""
    assert "emergency" in DEFAULT_PERSONA.lower()


# ---------------------------------------------------------------------------
# Per-mode voices — each mode must reach Gemini, and NONE may drop a safety rail
# ---------------------------------------------------------------------------


def test_every_response_mode_has_a_voice() -> None:
    # Every selectable response_mode must have generative guidance, or that mode
    # silently behaves like the bare persona.
    for mode in RESPONSE_MODES:
        assert mode in MODE_GUIDANCE


@pytest.mark.parametrize("mode", sorted(MODE_GUIDANCE))
def test_compose_keeps_safety_rails_in_every_mode(mode: str) -> None:
    prompt = compose_system_prompt("default", mode)
    # The mode voice is added...
    assert MODE_GUIDANCE[mode] in prompt
    # ...on TOP of the persona, never replacing its rails.
    assert "legal advice" in prompt.lower()
    assert "emergency" in prompt.lower()
    assert prompt.startswith(DEFAULT_PERSONA)


def test_compose_unknown_or_empty_mode_returns_bare_persona() -> None:
    assert compose_system_prompt("default", "") == DEFAULT_PERSONA
    assert compose_system_prompt("default", "NotARealMode") == DEFAULT_PERSONA


def test_distinct_modes_produce_distinct_prompts() -> None:
    gentle = compose_system_prompt("default", "Gentle")
    strong = compose_system_prompt("default", "Strong")
    crisis = compose_system_prompt("default", "Crisis")
    assert gentle != strong != crisis
    assert "Gentle" in gentle and "Strong" in strong and "Crisis" in crisis


# ---------------------------------------------------------------------------
# Trauma-informed post-processing — Gentle never interrogates
# ---------------------------------------------------------------------------


def test_gentle_mode_caps_to_a_single_question() -> None:
    mgr = PersonaFeatureManager()
    session = SessionState(response_mode="Gentle")
    text = "Are you okay? Do you feel safe? What happened? Do you want help?"
    out = mgr.apply_mode_constraints(text, session, prompt="")
    assert out.count("?") == 1  # one gentle question, the rest softened
    # words are softened, not dropped
    assert "feel safe" in out
    assert "want help" in out
