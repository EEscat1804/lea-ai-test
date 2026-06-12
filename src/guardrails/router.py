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

from guardrails.contracts import FeatureResult
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
    G21_DOCUMENT_TRIGGERS,
    G21_RECORDING_TRIGGERS,
    IMPLICIT_CRISIS_TRIGGERS,
    NAME_REQUEST_TRIGGERS,
    NO_DIAGNOSIS_LABELS,
    RELATIONAL_ABUSE_PATTERNS,
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
    def match_and_execute(self, pl: str, session: SessionState) -> FeatureResult | None: ...


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


def build_response(
    text: str,
    session: SessionState,
    tier: int = 0,
    prompt: str = "",  # Capture the incoming prompt
) -> dict[str, Any]:
    """Central response builder. Returns a dict that's the lea-ai HTTP contract."""
    if session.expert_mode:
        text = pair_clinical_terms(text)

    # Route formatting cleanly to the shared module-level Persona OOP Feature Manager.
    # apply_mode_constraints handles whitespace normalization per response_mode, so no
    # separate prose-cleanup pass is needed here.
    text = PERSONA_MANAGER.apply_mode_constraints(text, session, prompt)

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
    """G-07: validation FIRST, then the substance — in the SAME turn.

    Product directive (2026-05): a user must never have to send a follow-up
    message just to get the answer they already asked for. We preserve the
    validate-before-educate ORDER (validation leads), but deliver the education
    immediately after it in one response rather than deferring it to turn 2.

    `pending_education` is cleared (and no longer set) so nothing carries over.
    """
    session.pending_education = None
    return f"{validation} {education}", session


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
    return bool(re.search(r'["“”‘’].{3,100}["“”‘’]', prompt))


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
# RELATIONAL-ABUSE NAMING — G-13b
# ---------------------------------------------------------------------------


def name_relational_abuse(prompt: str) -> list[str]:
    """G-13b: return canonical labels for any relational-abuse pattern described.

    Order follows `RELATIONAL_ABUSE_PATTERNS` (dict insertion order) so the
    composed naming response is deterministic. Empty list when nothing matches.
    """
    return [
        label
        for label, (pattern, _clause) in RELATIONAL_ABUSE_PATTERNS.items()
        if re.search(pattern, prompt, re.IGNORECASE)
    ]


def _join_clauses(clauses: list[str]) -> str:
    """Join naming clauses into natural prose: 'a', 'a and b', 'a, b, and c'."""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def compose_naming_response(labels: list[str]) -> str:
    """G-13b: name the pattern(s), validate, refuse to diagnose where relevant.

    Structure is ordered so the no-diagnosis disclaimer lands BEFORE the closing
    check-in — it must survive any downstream sentence-cap in `apply_mode_constraints`.
    """
    joined = _join_clauses([RELATIONAL_ABUSE_PATTERNS[label][1] for label in labels])
    parts = [
        "I want to name what I'm hearing, because putting language to it can help you "
        "trust your own read on it.",
        f"What you're describing sounds like {joined}.",
    ]
    if any(label in NO_DIAGNOSIS_LABELS for label in labels):
        parts.append(
            "I'm naming behaviors and traits here, not giving a diagnosis — I can't and "
            "won't label anyone with a personality disorder from a description."
        )
    parts.append(
        "That's a real pattern, and your discomfort with it makes sense — "
        "you're not overthinking it."
    )
    parts.append("How are you holding up as you tell me this?")
    return " ".join(parts)


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
        return build_response(RESP["G04"], session, tier=3, prompt=user_prompt)

    if matches_any(pl, G01_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G01"], session, tier=3, prompt=user_prompt)

    if matches_any(pl, G02_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G02"], session, tier=3, prompt=user_prompt)

    if matches_any(pl, G03_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G03_ack"], session, tier=3, prompt=user_prompt)

    # Implicit-crisis safety net — default-to-safe per CLAUDE.md. Catches harm
    # language that no explicit G-01..G-04 pattern matched. Runs AFTER the
    # explicit checks so those keep their specific (medical/suicide/child) copy.
    # Uses word-boundary regex (see IMPLICIT_CRISIS_TRIGGERS) rather than substring
    # matching, which over-fired on benign messages like "I blocked his number".
    if matches_any(pl, IMPLICIT_CRISIS_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G01"], session, tier=3, prompt=user_prompt)

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
            # Real survivors ask about the outcome, not "my case": custody, the order,
            # the house, their chances. Lea must meet these with honest "I can't predict,
            # but here's what helps" — not a generic non-answer (found via safety eval).
            r"will i (win|lose|keep|get to keep)\b",
            r"(win|lose|keep) (custody|the kids|my kids|the house|the case)",
            r"what are my (chances|odds)",
            r"do i have a (good |strong )?(case|chance)",
            r"(good|strong|decent) chance",
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
    # G-21 evidence hygiene — discovery-aware guidance (Tier 0)
    #
    # Runs AFTER Tier-3 crisis and the bright-line blocks so it can never
    # override safety routing. Steers a user about to record someone, or to log
    # "everything," toward lower-risk, legally-safer evidence. This is guidance,
    # not enforcement: lea-ai is stateless and cannot block a write — the
    # structural archive-minimization protection is lea-be-core's to own.
    # -----------------------------------------------------------------------
    if matches_any(pl, G21_RECORDING_TRIGGERS):
        return build_response(RESP["G21_recording"], session, tier=0, prompt=user_prompt)

    if matches_any(pl, G21_DOCUMENT_TRIGGERS):
        return build_response(RESP["G21_document"], session, tier=0, prompt=user_prompt)

    # -----------------------------------------------------------------------
    # POLYMORPHIC DECOUPLED DISPATCH LOOP (Anti-Superfile Architecture)
    # -----------------------------------------------------------------------
    for feature in FEATURE_REGISTRY:
        result = feature.match_and_execute(pl, session)
        if result is not None:
            return build_response(
                result.text,
                session,
                tier=result.tier,
                prompt=user_prompt,
            )

    # -----------------------------------------------------------------------
    # G-20 device security — physical stalking append-on if both present
    # -----------------------------------------------------------------------
    if matches_any(pl, G20_TRIGGERS):
        response = RESP["G20_security"]
        if matches_any(pl, [r"(keeps? )?(showing up|appearing|following me|outside my)"]):
            response += (
                " Separately — the pattern of him physically showing up where you are is a "
                "serious escalation that goes beyond the phone. This level of physical tracking "
                "is dangerous. A local advocate can help you map safe routes, document the "
                "pattern for a court filing, and connect you with emergency options. "
                "Want me to find one in your county?"
            )
        return build_response(response, session, tier=2, prompt=user_prompt)

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

    # -----------------------------------------------------------------------
    # G-13b relational-abuse naming — name the pattern, especially when asked.
    # Sits at the END of the cascade: every Tier-3 crisis and hard block above
    # has already taken precedence. Tier 0; never overrides safety routing.
    # -----------------------------------------------------------------------
    labels = name_relational_abuse(pl)
    if labels:
        return build_response(compose_naming_response(labels), session, tier=0, prompt=user_prompt)
    if matches_any(pl, NAME_REQUEST_TRIGGERS):
        return build_response(RESP["G_name_invite"], session, tier=0, prompt=user_prompt)

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
    text = " ".join(sentences[:5]) if len(sentences) > 5 else " ".join(sentences)

    # 4. Cap at one question per turn (mirrors apply_mode_constraints)
    question_count = text.count("?")
    if question_count > 1:
        parts = text.rsplit("?", question_count - 1)
        text = parts[0] + "?" + parts[-1].replace("?", ".")
    return text
