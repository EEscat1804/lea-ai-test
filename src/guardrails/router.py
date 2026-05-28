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
from typing import Any

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
    LANGUAGE_COACH_SCRIPTS,
    RESP,
    RISK_FACTOR_TRIGGERS,
    TACTIC_PATTERNS,
)
from guardrails.session import SessionState

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

def enforce_trusted_friend_mode(text: str, session: SessionState | None = None) -> str:
    """G-11: prose only, max 5 sentences, no bullets, one question per turn."""
    if session and getattr(session, "response_mode", "") in ["Direct", "Gentle", "Strong", "Warm", "Crisis"]:
        return text

    text = re.sub(r"^\s*[-•*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n+", " ", text).strip()

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 5:
        text = " ".join(sentences[:5])

    question_count = text.count("?")
    if question_count > 1:
        parts = text.rsplit("?", question_count - 1)
        text = parts[0] + "?" + parts[-1].replace("?", ".")

    return text


CRISIS_PATTERN = r"\b(er|e\.r\.|emergenc[ye]|hospital[s]?|hoptal|hospitall|clinic|doctor[s]?|911|physician|icu|medic|paramedic|急診|醫院)\b"

def enforce_direct_constraints(text: str, prompt: str = "") -> str:
    """Direct Mode: Minimalist, raw directives. (Word Count: ~20-25)"""
    if re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text:
        return (
            "SAFETY WARNING: Go to the ER immediately for a medical evaluation. "
            "Strangulation causes hidden, fatal internal trauma. Call 911 or 1-800-799-7233 now."
        )
    
    # Existing standard fallback logic
    fillers = [r"^that's a really important question[^.]*\.", r"^i'm so relieved to hear[^.]*\.", r"^i hear you[^.]*\."]
    for pattern in fillers:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 3:
        text = " ".join(sentences[:3])
    return text

def enforce_gentle_constraints(text: str, prompt: str = "") -> str:
    """Gentle Mode: Soft pacing, double line breaks, low visual stress. (Word Count: ~65-70)"""
    if re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text:
        return (
            "Please take a deep breath. Your physical well-being is everything right now. Even if you feel fine physically, "
            "injuries from strangulation can cause internal trauma that isn't immediately visible to the eye.\n\n"
            "We highly recommend letting a professional at an emergency room evaluate you just to be completely safe. "
            "Whenever you are ready, gentle support is here 24/7 at 1-800-799-7233. Are you safe to talk right now?"
        )
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("Are you safe to talk right now?", "\n\nAre you safe to talk right now?")

def enforce_strong_constraints(text: str, prompt: str = "") -> str:
    """Strong Mode: Empowering active voice, high-agency framing. (Word Count: ~60-65)"""
    if re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text:
        return (
            "Listen to me carefully: you are facing a life-threatening situation. This is an assault, and your "
            "life matters. Demand an immediate medical evaluation at an ER—do not let anyone dismiss hidden internal trauma. "
            "Take control of your safety right now. Call 1-800-799-7233 immediately. "
            "Ensure you are in a secure location before continuing this conversation."
        )
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("Are you safe to talk right now?", "Ensure you are in a secure location before continuing this conversation.")

def enforce_warm_constraints(text: str, prompt: str = "") -> str:
    """Warm Mode: Rich narrative, prose-only companion tone, zero list blocks. (Word Count: ~85-95)"""
    if re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text:
        return (
            "I am so incredibly glad you reached out to me tonight, but I need you to know how precious your life is. "
            "What happened to you is dangerous, and I want to make sure you are truly safe. Please consider letting an ER doctor "
            "look after you, because internal injuries from this kind of harm don't always show up right away. "
            "There are gentle, caring experts waiting to hold space for you around the clock at 1-800-799-7233. "
            "Please take a gentle moment to make sure you are in a safe, quiet space where we can talk privately."
        )
    text = re.sub(r"\s+", " ", text).strip()
    return text

def enforce_crisis_constraints(text: str, prompt: str = "") -> str:
    """Crisis Mode: Strict tactical grounding, survival-first layout. (Word Count: ~50-55)"""
    if re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text:
        return (
            "EMERGENCY PROTOCOL ACTIVATED. Your life is in immediate danger. Internal trauma can be fatal. "
            "Go to the nearest Emergency Room (ER) right now. Medical professionals have protocols to protect you. "
            "Call 911 or 1-800-799-7233 immediately.\n\n"
            "CRITICAL: Focus on your physical environment right now. Find a safe room with a lock, or exit the building if you can. Are you safe to speak at this exact moment?"
        )
    text = re.sub(r"\s+", " ", text).strip()
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

    response_mode = getattr(session, "response_mode", "")
    
    if response_mode == "Direct":
        text = enforce_direct_constraints(text, prompt)
    elif response_mode == "Gentle":
        text = enforce_gentle_constraints(text, prompt)
    elif response_mode == "Strong":
        text = enforce_strong_constraints(text, prompt)
    elif response_mode == "Warm":
        text = enforce_warm_constraints(text, prompt)
    elif response_mode == "Crisis":
        text = enforce_crisis_constraints(text, prompt)
    elif session.trusted_friend_mode:
        text = enforce_trusted_friend_mode(text, session=session)
    elif not preserve_labels:
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
        re.search(r'["“”‘’].{3,100}["“”‘’]', prompt)
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
# G-15 LANGUAGE COACH
# ---------------------------------------------------------------------------


def generate_language_script(prompt: str, session: SessionState) -> str:
    """G-15: generate actual sentences based on who the user is talking to."""
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["police", "officer", "911", "cop"]):
        return LANGUAGE_COACH_SCRIPTS["police"] # type: ignore[no-any-return]
    if any(w in prompt_lower for w in ["clerk", "courthouse", "file", "filing"]):
        return LANGUAGE_COACH_SCRIPTS["clerk"] # type: ignore[no-any-return]
    if any(w in prompt_lower for w in ["judge", "hearing", "court", "testify"]):
        return LANGUAGE_COACH_SCRIPTS["judge"] # type: ignore[no-any-return]
    return (
        "To give you the right sentences, tell me who you're speaking to: "
        "police, a court clerk, a judge, or someone else? "
        "And what's the key thing you need to communicate?"
    )


# ---------------------------------------------------------------------------
# G-14 ASSESSMENT REPORT
# ---------------------------------------------------------------------------


def generate_assessment_report(prompt: str, session: SessionState) -> str:
    """G-14: compute and state an actual risk level with the factors that fired."""
    level, factors = compute_risk_level(session, prompt)
    session.risk_factors = factors

    if factors:
        factor_lines = "\n".join(f"  • {f.replace('_', ' ').capitalize()}" for f in factors)
    else:
        factor_lines = "  • No specific high-risk factors identified in session yet"

    return (
        f"Risk assessment based on what you've shared this session:\n\n"
        f"Risk Level: {level}\n\n"
        f"Factors present:\n{factor_lines}\n\n"
        f"This is not a clinical assessment — it is a structured summary of what you've disclosed. "
        f"A trained advocate can conduct a formal lethality assessment. "
        f"Would you like me to find one in your area?"
    )


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
        session.risk_factors.append("strangulation")
        session.tier3_fired_this_session = True
        return build_response(RESP["G04"], session, tier=3, preserve_labels=True)

    if matches_any(pl, G01_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G01"], session, tier=3, preserve_labels=True)

    if matches_any(pl, G02_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G02"], session, tier=3, preserve_labels=True)

    if matches_any(pl, G03_TRIGGERS):
        session.tier3_fired_this_session = True
        return build_response(RESP["G03_ack"], session, tier=3, preserve_labels=True)

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
        return build_response(RESP["G_predict_block"], session, tier=0)

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
        return build_response(RESP["G_third_party_block"], session, tier=0)

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
        return build_response(response, session, tier=2, preserve_labels=True)

    # -----------------------------------------------------------------------
    # G-16 / G-17 / G-18 — hard blocks
    # -----------------------------------------------------------------------
    if matches_any(pl, G16_TRIGGERS):
        return build_response(RESP["G16_block"], session, tier=0)

    if matches_any(pl, G17_TRIGGERS):
        return build_response(RESP["G17_block"], session, tier=0)

    if matches_any(pl, G18_TRIGGERS):
        return build_response(RESP["G18_block"], session, tier=0)

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
        return build_response(response, session, tier=0)

    if matches_any(pl, G10_TRIGGERS):
        return build_response(RESP["G10_reframe"], session, tier=0)

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
        return build_response(response_text, session, tier=0)

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
        return build_response(response_text, session, tier=0)

    # -----------------------------------------------------------------------
    # MODE ACTIVATIONS — G-11, G-12, G-15
    # -----------------------------------------------------------------------
    if matches_any(pl, [r"(trusted )?friend mode", r"talk (like|as) a friend"]):
        session.trusted_friend_mode = True
        session.expert_mode = False
        return build_response(RESP["G11_activate"], session, tier=0)

    if matches_any(pl, [r"expert mode", r"clinical mode"]):
        session.expert_mode = True
        session.trusted_friend_mode = False
        return build_response(RESP["G12_activate"], session, tier=0)

    if matches_any(
        pl,
        [
            r"language coach",
            r"give me (sentences|scripts?|words)",
            r"what (should|do) i say to (the )?(police|judge|clerk|court)",
            r"tell me (exactly )?what to say (to )?(the )?(police|judge|clerk|court)",
        ],
    ):
        session.language_coach_mode = True
        script = generate_language_script(pl, session)
        return build_response(script, session, tier=0)

    # -----------------------------------------------------------------------
    # G-13 tactic analysis on demand
    # -----------------------------------------------------------------------
    if matches_any(
        pl,
        [
            r"analyze.{0,20}(message|text|email)",
            r"flag.{0,10}(tactic|language)",
            r"(love.bombing|darvo|hoovering|gaslighting)",
        ],
    ):
        tactics = detect_tactics(pl)
        if tactics:
            lines = "\n".join(f"  • {tactic}: '{matched}'" for tactic, matched in tactics.items())
            response = (
                f"Tactics identified in what you shared:\n{lines}\n\n"
                f"Each of these is a deliberate method of control, not a relationship problem. "
                f"Would you like me to break down what any of these were designed to do?"
            )
        else:
            response = (
                "Send me the specific message or phrase you want to look at and I'll map "
                "the tactics present — love-bombing, DARVO, guilt induction, hoovering, and others."
            )
        return build_response(response, session, tier=0)

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
        report = generate_assessment_report(pl, session)
        return build_response(report, session, tier=0)

    # -----------------------------------------------------------------------
    # TIER 2 — depth responses (legal procedure, stalking, financial, custody, immigration)
    # -----------------------------------------------------------------------

    # Restraining-order how-to — Configurable state fallback (P1.2)
    if matches_any(
        pl,
        [
            r"how (do i|to) (get|file|apply for|obtain).{0,20}(restraining|protective) order",
            r"(can you |just )?(tell|help|walk) me.{0,10}(how to|what to do).{0,20}"
            r"(restraining|protective) order",
        ],
    ):
    
        if session.user_state != "California":
            return build_response(
                "DVRO procedure differs significantly across the 50 US jurisdictions. "
                "Tell me what state you're filing in and I'll walk you through the "
                "exact procedure — form names, fees, hearing timeline.",
                session, tier=0
            )
        
        return build_response(
            "In California, here is how to file for a domestic violence restraining order. "
            "Step 1: Go to your local courthouse and ask for the DV petition forms — in California that's the DV-100. "
            "Step 2: Fill out the forms describing the abuse. I can walk you through every field. "
            "Step 3: File with the clerk. There is no filing fee for DV petitions. "
            "Step 4: A judge reviews your request the same day and can issue a Temporary Restraining Order immediately. "
            "Step 5: The sheriff serves the papers to the respondent, free of charge. "
            "Want me to start walking you through the forms right now?",
            session,
            tier=0,
        )

    if matches_any(pl, [r"(protective|restraining) order"]) and matches_any(pl, [r"violat"]):
        return build_response(
            ("A violation of a protective order is an active criminal offense. "
            "Call 911 — not a non-emergency line — and tell the dispatcher you have a restraining "
            "order that is being violated. The officer who responds is required to enforce it. "
            "After: document the date, time, officer names, and any witnesses. "
            "The National DV Hotline (1-800-799-7233) can also connect you with a local legal "
            "advocate to review how your county handles violations. Want me to find one?"),
            session,
            tier=2,
        )

    if matches_any(pl, [r"(keeps? )?(showing up|appearing|following me|outside my)"]):
        return build_response(
            "This pattern — tracking your location and showing up — is a serious escalation in risk. "
            "For safe planning, use an unmonitored device (library computer or a trusted friend's "
            "phone). A local advocate can help you map out safe routes, emergency options, and "
            "next legal steps. Want me to find an advocate in your county?",
            session,
            tier=2,
        )

    if matches_any(pl, [r"\b(gun|firearm)\b"]) and matches_any(
        pl, [r"(threat|choked|strangled|deported|kill)"]
    ):
        session.firearm_access = True
        session.risk_factors.append("weapon_access")
        if not session.resource_surfaced_this_session:
            session.resource_surfaced_this_session = True
            return build_response(
                "Some of what you've shared — firearm access combined with threats — carries "
                "elevated risk. I want to make sure you have a safety plan and an advocate's "
                "number on hand, just to have. No pressure to use them. "
                "The National DV Hotline (1-800-799-7233) can connect you with a local advocate "
                "who can walk through a safety plan with you when you're ready. "
                "Let's keep working on your forms.",
                session,
                tier=1,
            )

    if matches_any(
        pl, [r"\bdeport\w*", r"\bundocumented\b", r"\bvisa\b", r"\bimmigration status\b"]
    ):
        session.immigration_risk = True
        return build_response(
            "Threats involving immigration status are a form of coercive control. "
            "Under federal law — the Violence Against Women Act — independent options exist "
            "to secure immigration status without the abuser's knowledge or cooperation, "
            "including VAWA self-petitions and U-visas for crime victims. "
            "I can connect you with an immigration attorney through the DV coalition network in "
            "your state. No pressure — want me to find one when you're ready?",
            session,
            tier=1,
        )

    if matches_any(
        pl,
        [
            r"(no|can.t access|controls).{0,15}(money|account|funds|finances)",
            r"financial(ly)? (trapped|dependent|control)",
            r"no (family|money).{0,30}(go|leave|nowhere)",
        ],
    ):
        response = (
            "What you're describing — being cut off from money or accounts — is economic coercion, "
            "and it's a recognized form of abuse. "
            "Local advocates specialize in exactly this: emergency funds, temporary housing, "
            "and confidential legal options. "
            "Would you like me to find an advocate organization in your county? "
            "Either way, your Vault progress is saved and we can continue whenever you're ready."
        )
        if matches_any(
            pl,
            [
                r"where (do i|can i|would i).{0,20}(go|stay|live)",
                r"no (family|place|where).{0,20}(nearby|to go|close)",
            ],
        ):
            response += (
                " On the housing question specifically: domestic violence shelters provide "
                "emergency same-night placement, are confidential (your address is protected by "
                "law), and are free. The National DV Hotline (1-800-799-7233, 24/7) can find the "
                "nearest available bed in your county right now. You do not need money, ID, or a "
                "reservation to enter."
            )
        return build_response(response, session, tier=2)

    if matches_any(
        pl,
        [
            r"(lose|take).{0,10}(the )?(kids?|children?|custody)",
            r"(threaten.{0,15}custody|custody.{0,15}threat)",
        ],
    ):
        return build_response(
            "Threatening to take the children is a well-documented tactic of coercive control — "
            "designed to create fear and prevent you from seeking help. "
            "A family law advocate can walk you through how parental rights are handled in your "
            "county and what documentation matters most. "
            "Want me to find a legal clinic or advocacy organization near you?",
            session,
            tier=2,
        )

    # Inside process_message() under Post-Filing Section (P1.2)
    if matches_any(
        pl, [r"what happens after (i )?fil(e|ing)", r"after (i )?fil(e|ing)"]
    ):
        
        if session.user_state != "California":
            return build_response(
                "DVRO procedure differs significantly across the 50 US jurisdictions. "
                "Tell me what state you're filing in and I'll walk you through the "
                "exact procedure — form names, fees, hearing timeline.",
                session, tier=0
            )


        return build_response(
                "In California, filing initiates a strict sequence. "
                "Within a few hours: a judge reviews your request for a Temporary Restraining Order. "
                "If granted, you receive a stamped copy from the clerk — enforceable immediately. "
                "The sheriff serves the papers to the respondent, free in DV cases. "
                "The full hearing happens about 21–25 days after filing. "
                "At the hearing: you testify briefly, the respondent responds, and the judge decides "
                "whether to issue a long-term order (up to five years in California — varies by state). "
                "You can bring an advocate, and you can request a remote appearance. "
                "If the respondent doesn't show, the judge usually grants the order anyway. "
                "Want me to walk through what to bring to the hearing?"
                ,
                session,
                tier=0,
            )

    if matches_any(
        pl, [r"(recipe app|look like|disguise|private.{0,10}mode|clear.{0,10}history)"]
    ):
        return build_response(RESP["G20_security"], session, tier=2, preserve_labels=True)

    # -----------------------------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------------------------
    return build_response(RESP["G_default"], session, tier=0)
