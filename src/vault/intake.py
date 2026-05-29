"""Vault intake state machine.

The Vault is LEA's structured DV-survivor petition flow. A user walks through
jurisdiction-specific questions (47 US jurisdictions per the DVRO Multi-State
Intake Question Flow) and the answers are assembled into a court-ready DVRO
petition by `src.vault.petition`.

Owners: Pranav, Aaron. This module owns the *state* of intake; lea-be-core
persists the encrypted answers and serves the resulting document.

Stateless contract:
- Request:  { session_id, jurisdiction, current_step?, answers: {...} }
- Response: { next_step | done, prompt?, schema?, validation_errors? }
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from lib.responses import json_response, problem_response
from guardrails.session import SessionState
from guardrails.rules import RESP

# Jurisdictions supported for the full Petition process
SUPPORTED_JURISDICTIONS = {"CA", "NY", "TX", "FL"}
# Jurisdictions that must be forced to halt and handoff after collecting Tier 1
HANDOFF_JURISDICTIONS = {"IL"}

# TIER 1: UNIVERSAL CORE DEFINITIONS (Q1 - Q22)
# ---------------------------------------------------------------------------
TIER_1_FLOW = [
    {"field": "petitioner.legal_name", "prompt": "What name should I use for the court? Your full legal name.", "schema": {"type": "string", "minLength": 1, "maxLength": 200}},
    {"field": "petitioner.dob", "prompt": "When were you born?", "schema": {"type": "string", "format": "date"}},
    {"field": "petitioner.safe_mailing_address", "prompt": "Where can the court send mail safely? A PO box or a friend's address is fine.", "schema": {"type": "string", "minLength": 1}},
    {"field": "petitioner.safe_phone", "prompt": "A safe number to reach you?", "schema": {"type": "string", "minLength": 1}},
    {"field": "petitioner.safe_email", "prompt": "A safe email?", "schema": {"type": "string", "format": "email"}},
    {"field": "respondent.legal_name", "prompt": "What's his/her/their full name?", "schema": {"type": "string", "minLength": 1}},
    {"field": "respondent.last_known_address", "prompt": "Where do they live, if you know?", "schema": {"type": "string"}},
    {"field": "relationship.type", "prompt": "How do you know each other?", "schema": {"type": "string"}},
    {"field": "relationship.live_together_now", "prompt": "Do you live with them right now?", "schema": {"type": "boolean"}},
    {"field": "relationship.lived_together_past", "prompt": "Did you used to live together?", "schema": {"type": "boolean"}},
    {"field": "relationship.children_in_common", "prompt": "Do you have a child together?", "schema": {"type": "boolean"}},
    {"field": "incidents[].date", "prompt": "When did this happen? An estimate is okay.", "schema": {"type": "string"}},
    {"field": "incidents[].location", "prompt": "Where were you?", "schema": {"type": "string"}},
    {"field": "incidents[].narrative", "prompt": "In your own words, what happened?", "schema": {"type": "string", "minLength": 1, "maxLength": 10000}},
    {"field": "incidents[].witnesses_present", "prompt": "Was anyone else there?", "schema": {"type": "string"}},
    {"field": "incidents[].police_called", "prompt": "Did anyone call the police?", "schema": {"type": "boolean"}},
    {"field": "incidents[].weapon_involved", "prompt": "Was there a weapon?", "schema": {"type": "boolean"}},
    {"field": "incidents[].injury", "prompt": "Were you or anyone hurt?", "schema": {"type": "string"}},
    {"field": "incidents[].pattern_frequency", "prompt": "How often does something like this happen?", "schema": {"type": "string"}},
    {"field": "protected_persons.children[]", "prompt": "Are there kids you want kept safe?", "schema": {"type": "string"}},
    {"field": "firearm.respondent_has_access", "prompt": "Does he/she/they have a gun, or access to one?", "schema": {"type": "boolean"}},
    {"field": "prior_orders.exists", "prompt": "Have you ever had a restraining order before — against them, or them against you?", "schema": {"type": "boolean"}},
]


def _is_minor(dob_str: str) -> bool:
    """Helper to detect minor status for Q24 pathing based on 2026 anchor date."""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
        age = 2026 - dob.year - ((dob.month, dob.day) > (5, 27))
        return age < 18
    except ValueError:
        return False


class VaultFeatureManager:
    """OOP interface encapsulation managing state tracking and legal workflows."""

    def match_and_execute(self, pl: str, session: SessionState) -> tuple[str, int, bool] | tuple[str, int] | None:
        # -----------------------------------------------------------------------
        # TIER 2 — depth responses (legal procedure, stalking, financial, custody, immigration)
        # -----------------------------------------------------------------------

        # Restraining-order how-to — Configurable state fallback (P1.2)
        if any(w in pl for w in [
            "how do i get a restraining order", 
            "how to file a restraining order", 
            "how to apply for a restraining order", 
            "how to obtain a restraining order", 
            "tell me how to file a restraining order", 
            "walk me how to file a restraining order", 
            "how to protective order"
        ]):
            if session.user_state != "California":
                return (
                    "DVRO procedure differs significantly across the 50 US jurisdictions. "
                    "Tell me what state you're filing in and I'll walk you through the "
                    "exact procedure — form names, fees, hearing timeline.",
                    0,
                )
            return (
                "In California, here is how to file for a domestic violence restraining order. "
                "Step 1: Go to your local courthouse and ask for the DV petition forms — in California that's the DV-100. "
                "Step 2: Fill out the forms describing the abuse. I can walk you through every field. "
                "Step 3: File with the clerk. There is no filing fee for DV petitions. "
                "Step 4: A judge reviews your request the same day and can issue a Temporary Restraining Order immediately. "
                "Step 5: The sheriff serves the papers to the respondent, free of charge. "
                "Want me to start walking you through the forms right now?",
                0,
            )

        if "protective order" in pl or "restraining order" in pl:
            if "violat" in pl:
                return (
                    "A violation of a protective order is an active criminal offense. "
                    "Call 911 — not a non-emergency line — and tell the dispatcher you have a restraining "
                    "order that is being violated. The officer who responds is required to enforce it. "
                    "After: document the date, time, officer names, and any witnesses. "
                    "The National DV Hotline (1-800-799-7233) can also connect you with a local legal "
                    "advocate to review how your county handles violations. Want me to find one?",
                    2,
                )

        if any(w in pl for w in ["showing up", "appearing", "following me", "outside my"]):
            return (
                "This pattern — tracking your location and showing up — is a serious escalation in risk. "
                "For safe planning, use an unmonitored device (library computer or a trusted friend's "
                "phone). A local advocate can help you map out safe routes, emergency options, and "
                "next legal steps. Want me to find an advocate in your county?",
                2,
            )

        if any(w in pl for w in ["gun", "firearm"]) and any(w in pl for w in ["threat", "choked", "strangled", "deported", "kill"]):
            session.firearm_access = True
            if "weapon_access" not in session.risk_factors:
                session.risk_factors.append("weapon_access")
            if not session.resource_surfaced_this_session:
                session.resource_surfaced_this_session = True
                return (
                    "Some of what you've shared — firearm access combined with threats — carries "
                    "elevated risk. I want to make sure you have a safety plan and an advocate's "
                    "number on hand, just to have. No pressure to use them. "
                    "The National DV Hotline (1-800-799-7233) can connect you with a local advocate "
                    "who can walk through a safety plan with you when you're ready. "
                    "Let's keep working on your forms.",
                    1,
                )

        if any(w in pl for w in ["deport", "undocumented", "visa", "immigration status"]):
            session.immigration_risk = True
            return (
                "Threats involving immigration status are a form of coercive control. "
                "Under federal law — the Violence Against Women Act — independent options exist "
                "to secure immigration status without the abuser's knowledge or cooperation, "
                "including VAWA self-petitions and U-visas for crime victims. "
                "I can connect you with an immigration attorney through the DV coalition network in "
                "your state. No pressure — want me to find one when you're ready?",
                1,
            )

        if any(w in pl for w in ["no money", "can.t access money", "controls money", "controls account", "financial trapped", "financial control", "nowhere to go", "no family"]):
            response = (
                "What you're describing — being cut off from money or accounts — is economic coercion, "
                "and it's a recognized form of abuse. "
                "Local advocates specialize in exactly this: emergency funds, temporary housing, "
                "and confidential legal options. "
                "Would you like me to find an advocate organization in your county? "
                "Either way, your Vault progress is saved and we can continue whenever you're ready."
            )
            if any(w in pl for w in ["where do i go", "where can i stay", "no place nearby", "nowhere nearby"]):
                response += (
                    " On the housing question specifically: domestic violence shelters provide "
                    "emergency same-night placement, are confidential (your address is protected by "
                    "law), and are free. The National DV Hotline (1-800-799-7233, 24/7) can find the "
                    "nearest available bed in your county right now. You do not need money, ID, or a "
                    "reservation to enter."
                )
            return response, 2

        if any(w in pl for w in ["lose custody", "take the kids", "take custody", "custody threat"]):
            return (
                "Threatening to take the children is a well-documented tactic of coercive control — "
                "designed to create fear and prevent you from seeking help. "
                "A family law advocate can walk you through how parental rights are handled in your "
                "county and what documentation matters most. "
                "Want me to find a legal clinic or advocacy organization near you?",
                2,
            )

        # Inside process_message() under Post-Filing Section (P1.2)
        if "after i file" in pl or "after filing" in pl or "happens after i file" in pl:
            if session.user_state != "California":
                return (
                    "DVRO procedure differs significantly across the 50 US jurisdictions. "
                    "Tell me what state you're filing in and I'll walk you through the "
                    "exact procedure — form names, fees, hearing timeline.",
                    0,
                )
            return (
                "In California, filing initiates a strict sequence. "
                "Within a few hours: a judge reviews your request for a Temporary Restraining Order. "
                "If granted, you receive a stamped copy from the clerk — enforceable immediately. "
                "The sheriff serves the papers to the respondent, free in DV cases. "
                "The full hearing happens about 21–25 days after filing. "
                "At the hearing: you testify briefly, the respondent responds, and the judge decides "
                "whether to issue a long-term order (up to five years in California — varies by state). "
                "You can bring an advocate, and you can request a remote appearance. "
                "If the respondent doesn't show, the judge usually grants the order anyway. "
                "Want me to walk through what to bring to the hearing?",
                0,
                True,
            )

        if any(w in pl for w in ["recipe app", "look like", "disguise", "private mode", "clear history"]):
            return RESP["G20_security"], 2, True

        return None


async def handle_intake_step(body: dict[str, Any], env: Any) -> Any:
    session_id = body.get("session_id")
    jurisdiction = body.get("jurisdiction")
    answers = body.get("answers", {})

    all_allowed = SUPPORTED_JURISDICTIONS | HANDOFF_JURISDICTIONS

    if not isinstance(session_id, str) or not session_id:
        return problem_response(400, "bad_request", "session_id is required")
    if jurisdiction not in all_allowed:
        return problem_response(400, "unsupported_jurisdiction", f"jurisdiction must be one of {sorted(all_allowed)}")
    if not isinstance(answers, dict):
        return problem_response(400, "bad_request", "answers must be an object")

    next_step = determine_next_step(jurisdiction, answers)
    return json_response(next_step)


def determine_next_step(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    # 1. Evaluate Tier 1 sequentially
    for step in TIER_1_FLOW:
        field = step["field"]
        if field not in answers:
            step_dict: dict[str, Any] = step
            schema_overlay = step_dict["schema"].copy()
            
            if field == "relationship.type" and jurisdiction == "CA":
                schema_overlay["enum"] = ["married", "dating", "engaged", "cohabiting", "child_in_common"]
            return {"step": field, "prompt": step_dict["prompt"], "schema": schema_overlay}

    # 2. Tier 1 complete -> Jurisdiction Gate
    if jurisdiction in HANDOFF_JURISDICTIONS:
        return {"step": "handoff", "action": "redirect", "reason": f"Jurisdiction {jurisdiction} requires external portal routing."}

    # 3. Tier 2: Jurisdiction-Aware Overlays

    # Q24: Minor Filing Path
    if _is_minor(answers.get("petitioner.dob", "")) and jurisdiction in {"CA", "NY", "TX", "FL"} and "petitioner.minor_filing_path" not in answers:
        return {"step": "petitioner.minor_filing_path", "prompt": "You're under 18 — is there an adult who can file with you, or do you want to file alone?", "schema": {"type": "string"}}

    if jurisdiction == "FL" and "petitioner.race" not in answers:
        return {"step": "petitioner.race", "prompt": "What is your race? This is a required court demographic field, but you can skip if uncomfortable.", "schema": {"type": "string"}}

    if jurisdiction in {"CA", "FL"} and "petitioner.gender" not in answers:
        return {"step": "petitioner.gender", "prompt": "How do you describe your gender? You can skip.", "schema": {"type": "string"}}

    if jurisdiction in {"CA", "NY", "TX", "FL"} and "petitioner.interpreter_language" not in answers:
        return {"step": "petitioner.interpreter_language", "prompt": "Do you need an interpreter for court? Which language?", "schema": {"type": "string"}}

    if jurisdiction in {"CA", "FL"} and "petitioner.disability_accommodation" not in answers:
        return {"step": "petitioner.disability_accommodation", "prompt": "Do you need any accommodations at court — a ramp, a quiet room, a sign-language interpreter?", "schema": {"type": "string"}}

    # Respondent Physical Description Overlay (Q31-Q35)
    if jurisdiction in {"CA", "NY", "TX", "FL"}:
        prefix = "The sheriff uses this to find them when they deliver the papers. Estimates are fine. "
        physical_fields = [
            ("respondent.height", prefix + "About how tall? An estimate is fine.", {"type": "string"}),
            ("respondent.weight", prefix + "About what weight?", {"type": "string"}),
            ("respondent.eye_color", prefix + "Eye color?", {"type": "string"}),
            ("respondent.hair_color", prefix + "Hair color?", {"type": "string"}),
            ("respondent.distinguishing_marks", prefix + "Any tattoos, scars, or other marks the sheriff?", {"type": "string"}),
        ]
        for f_id, pr, sc in physical_fields:
            if f_id not in answers:
                return {"step": f_id, "prompt": pr, "schema": sc}

    # Respondent Employer Info Overlay (Q38-Q40)
    if "respondent.employer_name" not in answers:
        return {"step": "respondent.employer_name", "prompt": "Where do they work, if you know?", "schema": {"type": "string"}}
    if "respondent.employer_address" not in answers:
        return {"step": "respondent.employer_address", "prompt": "What's the work address?", "schema": {"type": "string"}}
    if jurisdiction == "FL" and "respondent.employer_hours" not in answers:
        return {"step": "respondent.employer_hours", "prompt": "Working hours?", "schema": {"type": "string"}}

    # Respondent Vehicle Info Overlay (Q41-Q43)
    if jurisdiction in {"CA", "NY", "TX", "FL"}:
        if "respondent.vehicle_make_model" not in answers:
            return {"step": "respondent.vehicle_make_model", "prompt": "Do they drive? What kind of car?", "schema": {"type": "string"}}
        if "respondent.vehicle_color" not in answers:
            return {"step": "respondent.vehicle_color", "prompt": "Color?", "schema": {"type": "string"}}
        if "respondent.vehicle_plate" not in answers:
            return {"step": "respondent.vehicle_plate", "prompt": "License plate, if you know?", "schema": {"type": "string"}}

    # High-Risk / Background Check Overlays
    if jurisdiction in {"FL", "NY", "TX"} and "respondent.is_law_enforcement" not in answers:
        return {"step": "respondent.is_law_enforcement", "prompt": "Are they a police officer, military, or do they carry a gun for work?", "schema": {"type": "boolean"}}
    if jurisdiction == "FL" and "respondent.is_active_military" not in answers:
        return {"step": "respondent.is_active_military", "prompt": "Are they currently in the military, active duty?", "schema": {"type": "boolean"}}
    if jurisdiction == "CA" and "respondent.immigration_status_known" not in answers:
        return {"step": "respondent.immigration_status_known", "prompt": "Do you know their immigration status? (We don't share this — it can affect what protections you have.)", "schema": {"type": "boolean"}}
    if jurisdiction in {"CA", "NY", "TX", "FL"} and "respondent.prior_criminal_history" not in answers:
        return {"step": "respondent.prior_criminal_history", "prompt": "Has he/she/they ever been arrested or convicted of anything violent that you know of?", "schema": {"type": "boolean"}}

    # TX Specific Background Overlays (Q48, Q49)
    if jurisdiction == "TX":
        if "respondent.prior_dv_finding" not in answers:
            return {"step": "respondent.prior_dv_finding", "prompt": "Has a court ever found them guilty of family violence specifically?", "schema": {"type": "boolean"}}
        if "respondent.parental_rights_terminated" not in answers:
            return {"step": "respondent.parental_rights_terminated", "prompt": "Have their parental rights to a child in this case been terminated?", "schema": {"type": "boolean"}}

    # 4. Conditional Triggers

    # Q50: Police Report Connection Interception
    if answers.get("incidents[].police_called") is True and jurisdiction in {"CA", "NY", "TX", "FL"} and "incidents[].police_report_number" not in answers:
        return {"step": "incidents[].police_report_number", "prompt": "Did the police take a report? Do you have a number or case number?", "schema": {"type": "string"}}

    # Q64, Q65: Firearm Overlay
    if answers.get("firearm.respondent_has_access") is True:
        if "firearm.types[]" not in answers:
            return {"step": "firearm.types[]", "prompt": "Do you know what kind? A handgun, a rifle?", "schema": {"type": "array", "items": {"type": "string"}},}
        if "firearm.locations[]" not in answers:
            return {"step": "firearm.locations[]", "prompt": "Where are they kept, if you know?", "schema": {"type": "array", "items": {"type": "string"}},}

    # 5. Q118: Terminal Support Gate
    requested_reliefs = answers.get("selected_reliefs_intents", [])
    if jurisdiction in {"CA", "FL", "TX"} and ("child_support" in requested_reliefs or "spousal_support" in requested_reliefs) and "petitioner.ssn" not in answers:
        return {"step": "petitioner.ssn", "prompt": "(For child or spousal support, the court needs your SSN. Encrypted, never shared.)", "schema": {"type": "string", "pattern": r"^\d{3}-\d{2}-\d{4}$"}}

    return {"step": "done", "jurisdiction": jurisdiction}