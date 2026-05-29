"""Guardrails router — the actual decision engine.

Takes a user message + SessionState, walks the rule cascade, and returns a
`build_response()` dict containing the formatted user-facing text plus
metadata (tier, quick-exit flag, vault-write consent flag, updated session).

Tier-3 (lethality: G-01..G-04) is evaluated FIRST and cannot be downgraded
by any Tier-1/2 block lower in the cascade.

Authored by Aaron Wang; ported from `evaluator.py` v2 into this module.
The cascade order, trigger semantics, and response composition are preserved
verbatim — only `import pandas` and the CSV audit harness were stripped out
(those live in `tests/audit/` now, offline-only).
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from guardrails.rules import (
    CLINICAL_TERMS,
    G01_TRIGGERS,
    G02_TRIGGERS,
    G03_TRIGGERS,
    G04_TRIGGERS,
    G05_TRIGGERS,
    G08_TRIGGERS,
    G09_TRIGGERS,
    G10_TRIGGERS,
    G16_TRIGGERS,
    G17_TRIGGERS,
    G18_TRIGGERS,
    G20_TRIGGERS,
    RESP,
    RISK_FACTOR_TRIGGERS,
    TACTIC_PATTERNS,
)
from guardrails.session import SessionState
from persona.system_prompts import PersonaFeatureManager
from vault.intake import VaultFeatureManager

# ---------------------------------------------------------------------------
# BASE INTERFACE PROTOCOL FOR OOP FEATURE MANAGEMENT
# ---------------------------------------------------------------------------

class GuardrailFeature(Protocol):
    def match_and_execute(self, prompt: str, session: SessionState) -> dict[str, Any] | None:
        ...


# ---------------------------------------------------------------------------
# GLOBAL DOMAIN FEATURE REGISTRY (Instantiated Once to Maximize Throughput)
# ---------------------------------------------------------------------------

PERSONA_MANAGER = PersonaFeatureManager()
VAULT_MANAGER = VaultFeatureManager()

FEATURE_REGISTRY: tuple[GuardrailFeature, ...] = (
    PERSONA_MANAGER,
    VAULT_MANAGER,
)


# ---------------------------------------------------------------------------
# RESPONSE BUILDER — enforces G-11 / G-12 mode constraints
# ---------------------------------------------------------------------------


def pair_clinical_terms(text: str) -> str:
    """G-12: on first use of a clinical term, append a plain-language decoding inline.

    Only fires when expert_mode is active.
    """
    for term, plain in CLINICAL_TERMS.items():
        if term.lower() in text.lower():
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text = pattern.sub(f"{term} ({plain})", text, count=1)
    return text


def _clean_prose(text: str) -> str:
    """Collapses whitespace only. Preserves SECURITY NOTICE / ACTION NEEDED labels (G-20)."""
    text = re.sub(r"\n+", " ", text)
    return re.sub(r" +", " ", text).strip()


def build_response(
    text: str,
    session: SessionState,
    tier: int = 0,
    preserve_labels: bool = False,
    prompt: str = "",  # Capture the incoming prompt
) -> dict[str, Any]:
    """Central response builder. Returns a dict that's the lea-ai HTTP contract."""
    if session.expert_mode:
        text = pair_clinical_terms(text)

    # Route formatting cleanly to the shared module-level Persona OOP Feature Manager
    text = PERSONA_MANAGER.apply_mode_constraints(text, session, prompt)

    if not preserve_labels and not session.trusted_friend_mode and getattr(session, "response_mode", "") not in ["Direct", "Gentle", "Strong", "Warm", "Crisis"]:
        text = _clean_prose(text)

    return {
        "response": text,
        "tier": tier,
        "show_quick_exit": True,
        "vault_write_requires_consent": not session.data_storage_consent,
        "session": session,
    }


# ---------------------------------------------------------------------------
# G-07: VALIDATE BEFORE EDUCATING
# ---------------------------------------------------------------------------


def validate_then_educate(
    validation: str,
    education: str,
    session: SessionState,
) -> tuple[str, SessionState]:
    """G-07: always emit validation first.

    Turn 1: store education in `session.pending_education`, return validation.
    Turn 2 (if `pending_education` is set): return education and clear the slot.
    """
    if session.pending_education is None:
        session.pending_education = education
        return validation, session
    result = session.pending_education
    session.pending_education = None
    return result, session


# ---------------------------------------------------------------------------
# TRIGGER MATCHING — consistent regex across all layers
# ---------------------------------------------------------------------------


def matches_any(prompt: str, patterns: list[str]) -> bool:
    """Case-insensitive search. Patterns may use full regex syntax.

    A malformed regex raises `re.error` (P2.1) so authors notice typos at
    test/dev time rather than getting silent substring-match semantics.
    """
    return any(re.search(pat, prompt, re.IGNORECASE) for pat in patterns)
    
    
def contains_quoted_speech(prompt: str) -> bool:
    """G-08: detect verbatim disclosures — quoted speech in prompt."""
    return bool(
        re.search(r'["“”指標‘’].{3,100}["“”指標‘’]', prompt)
    )


# ---------------------------------------------------------------------------
# RISK SCORING — G-14
# ---------------------------------------------------------------------------


def compute_risk_level(session: SessionState, prompt: str) -> tuple[str, list[str]]:
    """G-14: compute actual risk level from session state + current prompt.

    Thresholds: Critical ≥7, High ≥4, Moderate ≥2, else Low.
    """
    score = 0
    factors_found = list(session.risk_factors)

    for factor, (pattern, weight) in RISK_FACTOR_TRIGGERS.items():
        if factor not in factors_found and re.search(pattern, prompt, re.IGNORECASE):
            factors_found.append(factor)
            score += weight

    if session.strangulation_disclosed:
        score += 3
    if session.firearm_access:
        score += 2
    if session.immigration_risk:
        score += 1

    if score >= 7:
        level = "Critical"
    elif score >= 4:
        level = "High"
    elif score >= 2:
        level = "Moderate"
    else:
        level = "Low"

    return level, factors_found


# ---------------------------------------------------------------------------
# TACTIC DETECTION — G-13
# ---------------------------------------------------------------------------


def detect_tactics(prompt: str) -> dict[str, str]:
    """G-13: scan prompt for abuse tactics; return `{tactic: matched_substring}`."""
    found: dict[str, str] = {}
    for tactic, pattern in TACTIC_PATTERNS.items():
        m = re.search(pattern, prompt, re.IGNORECASE)
        if m:
            found[tactic] = m.group(0)
    return found


# ---------------------------------------------------------------------------
# MAIN ROUTER
# ---------------------------------------------------------------------------


def process_message(user_prompt: str, session: SessionState) -> dict[str, Any]:
    """Primary guardrails router.

    Tier-3 checks ALWAYS run first and cannot be downgraded by any
    Tier-1/2 block. The cascade order is intentional and load-bearing —
    don't reorder without updating the test cases too.
    """
    p = user_prompt  # preserve original casing for quoted-speech detection
    pl = user_prompt.lower().strip()

    # -----------------------------------------------------------------------
    # TIER 3 — IMMINENT SAFETY (G-01, G-02, G-03, G-04)
    # -----------------------------------------------------------------------

    # G-04 first — strangulation needs its own medical-eval response, not the general G-01
    if matches_any(pl, G04_TRIGGERS):
        session.strangulation_disclosed = True
        if "strangulation" not in session.risk_factors:
            session.risk_factors.append("strangulation")
        session.tier3_fired_this_session = True
        return build_response(RESP["G04"], session, tier=3, preserve_labels=True, prompt=user_prompt)

    if matches_any(pl, G01_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G01"], session, tier=3, preserve_labels=True, prompt=user_prompt)

    if matches_any(pl, G02_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G02"], session, tier=3, preserve_labels=True, prompt=user_prompt)

    if matches_any(pl, G03_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G03_ack"], session, tier=3, preserve_labels=True, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # BRIGHT-LINE REFUSALS — out-of-scope
    # -----------------------------------------------------------------------

    if matches_any(
        pl,
        [
            r"predict.{0,10}(judge|court|outcome)",
            r"will the judge (grant|give|order)",
            r"strong case",
            r"(win|lose) (my )?case",
        ],
    ):
        return build_response(RESP["G_predict_block"], session, tier=0, prompt=user_prompt)

    if matches_any(
        pl,
        [
            r"what (she.s|he.s).{0,20}asking",
            r"(her|his) (husband|wife|partner).{0,20}(said|told|claims)",
            r"my (girlfriend|boyfriend|partner).{0,20}(doing|saying)",
            r"set up this account for (my )?(girlfriend|boyfriend|wife|husband|partner)",
            r"(show|tell) me what (she|he).{0,20}(said|asked|shared|been saying)",
        ],
    ):
        return build_response(RESP["G_third_party_block"], session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # POLYMORPHIC DECOUPLED DISPATCH LOOP (Anti-Superfile Architecture)
    # -----------------------------------------------------------------------
    for feature in FEATURE_REGISTRY:
        execution_result = feature.match_and_execute(pl, session)
        if execution_result is not None:
            if isinstance(execution_result, tuple) and len(execution_result) == 3:
                txt, tr, pres = execution_result
                return build_response(txt, session, tier=tr, preserve_labels=pres, prompt=user_prompt)
            if isinstance(execution_result, tuple) and len(execution_result) == 2:
                txt, tr = execution_result
                return build_response(txt, session, tier=tr, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-20 device security — physical stalking append-on if both present
    # -----------------------------------------------------------------------
    if matches_any(pl, G20_TRIGGERS):
        response = RESP["G20_security"]
        if matches_any(
            pl, [r"(keeps? )?(showing up|appearing|following me|outside my)"]
        ):
            response += (
                " Separately — the pattern of him physically showing up where you are is a "
                "serious escalation that goes beyond the phone. This level of physical tracking "
                "is dangerous. A local advocate can help you map safe routes, document the "
                "pattern for a court filing, and connect you with emergency options. "
                "Want me to find one in your county?"
            )
        return build_response(response, session, tier=2, preserve_labels=True, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-16 / G-17 / G-18 — hard blocks
    # -----------------------------------------------------------------------
    if matches_any(pl, G16_TRIGGERS):
        return build_response(RESP["G16_block"], session, tier=0, prompt=user_prompt)

    if matches_any(pl, G17_TRIGGERS):
        return build_response(RESP["G17_block"], session, tier=0, prompt=user_prompt)

    if matches_any(pl, G18_TRIGGERS):
        return build_response(RESP["G18_block"], session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-05 user self-doubt → validate; append G-10 reframe if both fire
    # -----------------------------------------------------------------------
    if matches_any(pl, G05_TRIGGERS):
        response = RESP["G05_validation"]
        if matches_any(pl, G10_TRIGGERS):
            response += (
                " I also want to gently name something: describing what happened as 'not that bad' "
                "or 'only' happening sometimes is language that tends to minimize a pattern of harm. "
                "What you've described is real, and it counts."
            )
        return build_response(response, session, tier=0, prompt=user_prompt)

    if matches_any(pl, G10_TRIGGERS):
        return build_response(RESP["G10_reframe"], session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-08 verbatim disclosure — quoted speech requires specific acknowledgment
    # -----------------------------------------------------------------------
    if contains_quoted_speech(p) or matches_any(pl, G08_TRIGGERS):
        validation = (
            "Hearing those specific words matters. What he said to you was deliberate — "
            "designed to shift responsibility or make you feel small. "
            "Your reaction to it makes sense."
        )
        education = (
            "Those phrases are worth documenting exactly as he said them in your petition. "
            "Verbatim quotes from the respondent carry weight — they show the court the specific "
            "language used. Want me to help you format them in the narrative section?"
        )
        response_text, session = validate_then_educate(validation, education, session)
        return build_response(response_text, session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-09 trauma bonding — validate first, educate next turn (G-07)
    # If user is also burden-shifting onto themselves, name it
    # -----------------------------------------------------------------------
    if matches_any(pl, G09_TRIGGERS):
        validation = RESP["G09_validation"]
        if matches_any(
            pl,
            [
                r"(provoke|deserve|caused|my fault).{0,30}(him|her|it|this)",
                r"(better|good enough).{0,10}(wife|husband|partner).{0,20}(wouldn.t|won.t|would not)",
            ],
        ):
            validation += (
                " And I want to name something directly: what's happening is not happening "
                "because of anything you did or didn't do. Provocation is not a cause of abuse — "
                "it is a frame the abuser creates. You are not responsible for his choices."
            )
        response_text, session = validate_then_educate(validation, RESP["G09_education"], session)
        return build_response(response_text, session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # G-14 assessment report on demand
    # -----------------------------------------------------------------------
    if matches_any(
        pl,
        [
            r"(generate|run|give me).{0,15}(assessment|risk|lethality)",
            r"(full )?risk (log|report|level)",
        ],
    ):
        level, factors = compute_risk_level(session, user_prompt)
        session.risk_factors = factors

        if factors:
            factor_lines = "\n".join(f"  • {f.replace('_', ' ').capitalize()}" for f in factors)
        else:
            factor_lines = "  • No specific high-risk factors identified in session yet"

        report = (
            f"Risk assessment based on what you've shared this session:\n\n"
            f"Risk Level: {level}\n\n"
            f"Factors present:\n{factor_lines}\n\n"
            f"This is not a clinical assessment — it is a structured summary of what you've disclosed. "
            f"A trained advocate can conduct a formal lethality assessment. "
            f"Would you like me to find one in your area?"
        )
        return build_response(report, session, tier=0, prompt=user_prompt)

    return build_response(RESP["G_default"], session, tier=0, prompt=user_prompt)


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBILITY STUBS FOR REGRESSION TESTS
# ---------------------------------------------------------------------------

def enforce_trusted_friend_mode(text: str, session: SessionState | None = None) -> str:
    """Legacy test wrapper routing calls seamlessly to the Persona OOP manager.
    
    Pins compatibility for test_guardrails.py without cluttering router logic.
    """
    # 1. Strip raw bullet and list markers cleanly from the input string
    text = re.sub(r"^[ \t]*[-•*][ \t]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\d+\.[ \t]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+[-•*]\s+", " ", text)
    text = re.sub(r"\s+\d+\.\s+", " ", text)
    
    # 2. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # 3. Capitalize and isolate individual sentences precisely
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return " ".join(sentences[:5]) if len(sentences) > 5 else " ".join(sentences)