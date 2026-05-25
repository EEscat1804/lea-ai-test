from persona.system_prompts import DEFAULT_PERSONA, get_persona_prompt


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
