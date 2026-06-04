import re

import pytest

from guardrails.session import SessionState
from persona.system_prompts import (
    DEFAULT_PERSONA,
    FEATURE_MANIFEST,
    FORBIDDEN_INTERNAL_TERMS,
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
# "About the app" knowledge — accurate, honest about privacy, no internals
#
# These tests assert against the DEFAULT_PERSONA *string* — they prove the
# instruction reaches Gemini, not that Lea's generated reply obeys it. The
# persona is the floor of the enforcement story, not the ceiling. A live-model
# adversarial probe (e.g. "is my chat fully private?", "describe the
# encryption") that asserts on the actual response is tracked as a follow-up,
# out of this PR's scope. The `test_persona_text_*` naming makes that boundary
# explicit so a green suite is never mistaken for verified behavior.
# ---------------------------------------------------------------------------


def test_persona_text_lists_app_features() -> None:
    # Lea should be able to answer "what is this app?" with real features.
    persona = DEFAULT_PERSONA.lower()
    assert "vault" in persona
    assert "journal" in persona


def test_persona_text_carries_honest_privacy_line() -> None:
    # Telling a survivor the app is fully private when it is not can lead them to
    # over-disclose. The persona must carry the honest limit AND forbid overclaiming.
    persona = DEFAULT_PERSONA.lower()
    assert "not fully end-to-end private" in persona
    assert "never tell a user the app cannot see their chat" in persona


def test_persona_text_points_to_on_device_safety_tools() -> None:
    persona = DEFAULT_PERSONA.lower()
    assert "quick-exit" in persona
    assert "disguise" in persona


def test_persona_text_excludes_internal_terms() -> None:
    # DEFAULT_PERSONA reaches Gemini and shapes user-facing replies. It must not
    # carry backend internals that could disclose security posture to an abuser.
    # Shares FORBIDDEN_INTERNAL_TERMS with src so the guard can't drift from any
    # future runtime output filter built on the same list.
    persona = DEFAULT_PERSONA.lower()
    for term in FORBIDDEN_INTERNAL_TERMS:
        assert term not in persona, f"internal term leaked into persona: {term!r}"


# ---------------------------------------------------------------------------
# Feature manifest — deterministic UI ground truth must reach the model
#
# Regression for the spatial-hallucination bug: Lea told users features were
# somewhere they aren't. The fix hard-codes each feature's location in
# FEATURE_MANIFEST and injects it into the persona. These assert the locations
# actually reach the prompt, so a future persona edit can't silently drop them.
# ---------------------------------------------------------------------------


def test_every_manifest_location_reaches_the_persona() -> None:
    for spec in FEATURE_MANIFEST["features"].values():
        assert spec["ui_location"] in DEFAULT_PERSONA


def test_every_manifest_access_step_reaches_the_persona() -> None:
    # "how to activate and access" is a named requirement — assert the steps,
    # not just the locations, reach the model.
    for spec in FEATURE_MANIFEST["features"].values():
        assert spec["how_to_access"] in DEFAULT_PERSONA


def test_quick_exit_location_is_grounded_not_top_of_screen() -> None:
    # The exact bug: Lea said Quick Exit was at the top. The grounded location is
    # the right-middle mascot badge — assert that reaches the model.
    loc = FEATURE_MANIFEST["features"]["quick_exit"]["ui_location"]
    assert loc in DEFAULT_PERSONA
    assert "right-middle" in loc.lower()
    # Safety-critical entry is pinned to one anchor, never "top", and never a
    # left-or-right range (review note): the key direction must be unambiguous.
    assert "top" not in loc.lower()
    assert " / " not in loc


def test_disguise_mode_is_grounded_to_the_eye_toggle() -> None:
    # Safety feature (shared/monitored device). Ground it to the eye toggle above
    # Quick Exit, per the in-app tooltip — not a guess, and never "top".
    loc = FEATURE_MANIFEST["features"]["disguise_mode"]["ui_location"]
    assert loc in DEFAULT_PERSONA
    assert "eye" in loc.lower()
    assert "quick exit" in loc.lower()


def test_every_feature_is_dated() -> None:
    # Drift guard: a new entry can't ship undated. `last_verified` makes
    # staleness visible in review (mobile-UI move -> bump the date), so the
    # manifest can't silently rot into confident-but-wrong locations.
    for name, spec in FEATURE_MANIFEST["features"].items():
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", spec["last_verified"]), (
            f"{name} has a missing or malformed last_verified date"
        )


def test_last_verified_metadata_does_not_leak_into_the_prompt() -> None:
    # last_verified is for maintainers, not the model — it must not reach Gemini.
    assert "last_verified" not in DEFAULT_PERSONA
    for spec in FEATURE_MANIFEST["features"].values():
        assert spec["last_verified"] not in DEFAULT_PERSONA


def test_manifest_survives_mode_composition() -> None:
    # The locations are a hard constraint, not a tone — they must stay in every
    # mode, not just the bare persona.
    for mode in sorted(MODE_GUIDANCE):
        prompt = compose_system_prompt("default", mode)
        for spec in FEATURE_MANIFEST["features"].values():
            assert spec["ui_location"] in prompt


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


@pytest.mark.parametrize("mode", sorted(MODE_GUIDANCE))
def test_compose_keeps_app_features_in_every_mode(mode: str) -> None:
    # startswith(DEFAULT_PERSONA) covers the About-the-app block transitively, but
    # a direct check means a future composition that reorders or trims the base
    # can't silently drop Lea's honest feature/privacy answer in some mode.
    prompt = compose_system_prompt("default", mode).lower()
    assert "vault" in prompt
    assert "journal" in prompt


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
