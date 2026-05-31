"""Regression tests for the guardrails router.

Pins the load-bearing safety behavior so reordering the cascade or editing
trigger patterns surfaces as a test failure, not a runtime crisis.
"""

from __future__ import annotations

import pytest

from guardrails.router import (
    compute_risk_level,
    contains_quoted_speech,
    detect_tactics,
    enforce_trusted_friend_mode,
    process_message,
    validate_then_educate,
)
from guardrails.session import SessionState

# ---------------------------------------------------------------------------
# Tier-3 — these MUST always fire and MUST be uninterruptible
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "he's here",
        "he found me",
        "he has a gun and is going to kill me",
        "he watches my every move",
    ],
)
def test_g01_imminent_danger_returns_tier_3(prompt: str) -> None:
    result = process_message(prompt, SessionState())
    assert result["tier"] == 3
    assert "1-800-799-7233" in result["response"]


@pytest.mark.parametrize(
    "prompt",
    [
        "I'm thinking about suicide",
        "I want to die",
        "I'd rather be dead",
        "I want to hurt myself",
    ],
)
def test_g02_suicidal_ideation_returns_tier_3(prompt: str) -> None:
    result = process_message(prompt, SessionState())
    assert result["tier"] == 3
    assert "988" in result["response"]


def test_g03_child_safety_returns_tier_3() -> None:
    result = process_message("my kids saw him hit me last night", SessionState())
    assert result["tier"] == 3
    assert "1-800-422-4453" in result["response"]


def test_g04_strangulation_returns_tier_3_with_medical_eval_language() -> None:
    result = process_message("he choked me until I couldn't breathe", SessionState())
    assert result["tier"] == 3
    assert "medical evaluation" in result["response"].lower()


def test_g04_runs_before_g01_when_both_match() -> None:
    # G-04 strangulation must take precedence — needs its own medical-eval response
    result = process_message("he strangled me and said he would kill me", SessionState())
    assert result["tier"] == 3
    assert "SAFETY WARNING" in result["response"]
    assert "Strangulation" in result["response"]


def test_tier_3_cannot_be_downgraded_by_later_blocks() -> None:
    # A G-01 prompt that ALSO contains G-16 (couples therapy) keywords must still
    # return G-01's tier-3 response, not G-16's hard block.
    result = process_message(
        "he said he's going to kill me but maybe couples therapy could help",
        SessionState(),
    )
    assert result["tier"] == 3


# ---------------------------------------------------------------------------
# Hard refusals — bright lines
# ---------------------------------------------------------------------------


def test_g16_couples_therapy_is_blocked() -> None:
    result = process_message("should we try couples therapy?", SessionState())
    assert result["tier"] == 0
    assert "not appropriate" in result["response"].lower()


def test_g17_abuser_inner_life_speculation_is_blocked() -> None:
    result = process_message("why is he like this, did he have a hard childhood?", SessionState())
    assert result["tier"] == 0
    assert "speculat" in result["response"].lower()


def test_g18_burden_shift_is_blocked() -> None:
    result = process_message("have you tried setting clearer boundaries?", SessionState())
    assert result["tier"] == 0
    assert "responsibility" in result["response"].lower()


# ---------------------------------------------------------------------------
# G-07 validate-then-educate sequencing
# ---------------------------------------------------------------------------


def test_g09_first_turn_returns_validation_not_education() -> None:
    session = SessionState()
    result = process_message("I still love him", session)
    assert "trauma bonding" not in result["response"].lower()
    assert "makes complete sense" in result["response"].lower()


def test_g09_second_turn_returns_education() -> None:
    session = SessionState()
    process_message("I still love him", session)  # primes pending_education
    result = process_message("I still love him", session)  # second turn
    assert "trauma bonding" in result["response"].lower()


def test_validate_then_educate_helper_clears_pending_after_delivery() -> None:
    session = SessionState()
    msg1, session = validate_then_educate("validate text", "educate text", session)
    assert msg1 == "validate text"
    assert session.pending_education == "educate text"
    msg2, session = validate_then_educate("ignored", "ignored", session)
    assert msg2 == "educate text"
    assert session.pending_education is None


# ---------------------------------------------------------------------------
# Mode controls (G-11, G-12)
# ---------------------------------------------------------------------------


def test_g11_trusted_friend_mode_caps_at_five_sentences() -> None:
    text = "One. Two. Three. Four. Five. Six. Seven. Eight."
    out = enforce_trusted_friend_mode(text)
    assert out.count(".") == 5


def test_g11_trusted_friend_mode_strips_bullets() -> None:
    text = "- bullet one\n- bullet two"
    out = enforce_trusted_friend_mode(text)
    assert "-" not in out
    assert "bullet one" in out


# ---------------------------------------------------------------------------
# G-13 tactic detection
# ---------------------------------------------------------------------------


def test_detect_tactics_finds_darvo_and_gaslighting() -> None:
    found = detect_tactics(
        "he flipped it and turned it around — then said I'm crazy and making it up"
    )
    assert "DARVO" in found
    assert "gaslighting" in found


# ---------------------------------------------------------------------------
# G-14 risk scoring
# ---------------------------------------------------------------------------


def test_compute_risk_level_low_baseline() -> None:
    level, factors = compute_risk_level(SessionState(), "I want to learn my options")
    assert level == "Low"
    assert factors == []


def test_compute_risk_level_critical_with_strangulation_and_weapon() -> None:
    session = SessionState(strangulation_disclosed=True, firearm_access=True)
    level, _ = compute_risk_level(session, "I'm scared he'll kill me")
    assert level == "Critical"


# ---------------------------------------------------------------------------
# G-08 quoted-speech detection
# ---------------------------------------------------------------------------


def test_contains_quoted_speech_detects_double_quotes() -> None:
    assert contains_quoted_speech('he said "you ruined my life"')


def test_contains_quoted_speech_detects_curly_quotes() -> None:
    assert contains_quoted_speech("he said “you ruined my life”")


# ---------------------------------------------------------------------------
# G-19 quick-exit signal is in EVERY response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "hello",
        "he choked me",
        "I want to die",
        "should we try mediation",
        "what happens after I file",
    ],
)
def test_g19_quick_exit_always_signaled(prompt: str) -> None:
    result = process_message(prompt, SessionState())
    assert result["show_quick_exit"] is True


# ---------------------------------------------------------------------------
# G-20 monitoring detection preserves the SECURITY NOTICE label
# ---------------------------------------------------------------------------


def test_g20_security_notice_label_preserved() -> None:
    result = process_message("he has spyware on my phone", SessionState())
    assert "SECURITY NOTICE" in result["response"]
    assert result["tier"] == 2


# ---------------------------------------------------------------------------
# Feature-manager matchers — regex, not exact substring, so phrasing can vary
# ---------------------------------------------------------------------------


def test_restraining_order_how_to_matches_natural_phrasing() -> None:
    # "how do i apply for a restraining order" was missed by the substring matcher
    result = process_message("how do i apply for a restraining order", SessionState())
    assert result["tier"] == 0
    assert "what state you're filing in" in result["response"]


def test_trusted_friend_mode_activates_on_varied_phrasing() -> None:
    session = SessionState()
    process_message("could you switch to trusted friend mode", session)
    assert session.trusted_friend_mode is True


def test_restraining_order_violation_not_swallowed_by_how_to() -> None:
    # A violation question must reach the tier-2 violation branch, not the how-to branch
    result = process_message(
        "how do i report that he violated my restraining order", SessionState()
    )
    assert result["tier"] == 2
    assert "criminal offense" in result["response"].lower()
