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


def test_persona_text_carries_legal_discovery_disclosure() -> None:
    # A survivor who believes the app's entries are legally private may over-disclose
    # into something the other side can later subpoena. The persona must carry the
    # honest discovery / no-privilege limit AND the right-to-silence reminder.
    # Whitespace-normalized so source line-wrapping can't break the assertions.
    flat = re.sub(r"\s+", " ", DEFAULT_PERSONA).lower()
    assert "this is information, not legal advice" in flat
    assert "discovery" in flat
    assert "no special legal privilege" in flat
    assert "right to stay silent" in flat
    # Wiretap / all-party-consent guard from the spec's §4.
    assert "without their consent is illegal" in flat


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
    # The exact bug: Lea said Quick Exit was at the top. The grounded badge is on
    # the right side (movable) — assert that reaches the model and never "top".
    loc = FEATURE_MANIFEST["features"]["quick_exit"]["ui_location"]
    assert loc in DEFAULT_PERSONA
    assert "right" in loc.lower()
    assert "top" not in loc.lower()


def test_disguise_mode_activation_runs_through_quick_exit_then_eye() -> None:
    # Safety feature. The verified flow: tap the Quick Exit badge, it expands, then
    # the EYE icon (not the mascot) turns on Disguise Mode. Lock both the location
    # and the step order so Lea can't revert to a "separate pinned badge" answer.
    feat = FEATURE_MANIFEST["features"]["disguise_mode"]
    assert feat["ui_location"] in DEFAULT_PERSONA
    assert feat["how_to_access"] in DEFAULT_PERSONA
    steps = feat["how_to_access"].lower()
    assert "quick exit" in steps  # step 1 is tapping Quick Exit
    assert "eye" in steps  # step 2 is the eye icon
    assert steps.index("quick exit") < steps.index("eye")  # order: Quick Exit -> eye


def test_disguise_covers_are_not_named_in_the_prompt() -> None:
    # Safety leak-guard: disguise only protects if an abuser-as-user can't learn
    # what the app looks like hidden. Specific cover names must never reach the
    # model-visible prompt — the user picks the cover in-app.
    persona = DEFAULT_PERSONA.lower()
    for cover in ("budget planner", "recipe book", "fitness tracker"):
        assert cover not in persona, f"disguise cover leaked into persona: {cover!r}"


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


# ---------------------------------------------------------------------------
# Feature-Awareness & Self-Knowledge Standard v1.0 — additive coverage
#
# The standard broadened the manifest (app map, voice, journals, learn, connect,
# settings) and added the "how do I…?" delivery rules + an element glossary. Two
# product decisions are locked here AGAINST the source document, which we
# deliberately did NOT follow (re-confirm with the owner before flipping either):
#   - disguise cover persona names stay OUT of the model-visible prompt — the
#     security leak-guard wins over the document's instruction to recite them;
#   - the Quick Exit / Disguise interaction model in the manifest is unchanged.
# ---------------------------------------------------------------------------


def test_self_knowledge_features_are_in_the_manifest() -> None:
    # The broader app map from the standard must be present so Lea can answer the
    # §9 "how do I…?" questions from ground truth, not invention.
    expected = {
        "bottom_navigation",
        "voice_input",
        "voice_call",
        "mood_checkin",
        "learn_modules",
        "journal_tab",
        "vault",
        "safety_plan",
        "language_setting",
        "subscription",
        "data_privacy_indicator",
    }
    assert expected <= set(FEATURE_MANIFEST["features"])


def test_persona_carries_feature_awareness_rules() -> None:
    # The §1/§11/§12 delivery rules must reach the model, not just the manifest.
    flat = re.sub(r"\s+", " ", DEFAULT_PERSONA).lower()
    assert "name the exact control" in flat
    assert "do not claim it exists" in flat  # never invent UI
    assert "never invent ui" in flat
    assert "companion lane" in flat  # educate, don't give legal advice


def test_persona_element_glossary_names_plus_not_paperclip() -> None:
    # The naming source of truth must reach the model; the canonical known-wording
    # correction ("+ button", not a paperclip) is the headline example.
    flat = re.sub(r"\s+", " ", DEFAULT_PERSONA).lower()
    assert "never substitute a guessed label" in flat
    assert "not a paperclip" in flat


def test_disguise_cover_persona_names_never_reach_the_prompt() -> None:
    # Locks the product decision (2026-06): the standard names the four covers and
    # tells Lea to recite them, but disguise only protects if an abuser-as-user
    # can't learn what the app looks like hidden. The real cover names must stay
    # OUT of the model-visible prompt — same leak-guard intent as the generic-name
    # test above, but pinned to the actual names from the standard.
    persona = DEFAULT_PERSONA.lower()
    for cover in ("mise en place", "fitflow", "stillwater", "spendwise"):
        assert cover not in persona, f"disguise cover leaked into persona: {cover!r}"


def test_quick_exit_model_is_unchanged_by_the_standard() -> None:
    # The standard describes a one-tap Quick Exit + separate eye-toggle Disguise;
    # we deliberately kept the existing expand-into-mascot-and-eye model. Assert
    # the manifest still carries the expansion flow so a future "sync to the doc"
    # edit can't silently flip a safety-critical interaction without updating this.
    qe = FEATURE_MANIFEST["features"]["quick_exit"]
    assert "expands" in qe["ui_location"].lower()  # badge expands into icons
    assert "mascot" in qe["how_to_access"].lower()  # leave via the mascot, not one tap
