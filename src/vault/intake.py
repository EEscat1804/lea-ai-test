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

from datetime import datetime
from typing import Any

from lib.responses import json_response, problem_response

# Jurisdictions supported for the full Petition process
SUPPORTED_JURISDICTIONS = {"CA", "NY", "TX", "FL"}
# Jurisdictions that must be forced to halt and handoff after collecting Tier 1
HANDOFF_JURISDICTIONS = {"IL"}

# TIER 1: UNIVERSAL CORE DEFINITIONS (Q1 - Q22)
# ---------------------------------------------------------------------------
TIER_1_FLOW = [
    {
        "field": "petitioner.legal_name",
        "prompt": "What name should I use for the court? Your full legal name.",
        "schema": {"type": "string", "minLength": 1, "maxLength": 200},
    },
    {
        "field": "petitioner.dob",
        "prompt": "When were you born?",
        "schema": {"type": "string", "format": "date"},
    },
    {
        "field": "petitioner.safe_mailing_address",
        "prompt": (
            "Where can the court send mail safely? "
            "A PO box or a friend's address is fine."
        ),
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "petitioner.safe_phone",
        "prompt": "A safe number to reach you?",
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "petitioner.safe_email",
        "prompt": "A safe email?",
        "schema": {"type": "string", "format": "email"},
    },
    {
        "field": "respondent.legal_name",
        "prompt": "What's his/her/their full name?",
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "respondent.last_known_address",
        "prompt": "Where do they live, if you know?",
        "schema": {"type": "string"},
    },
    {
        "field": "relationship.type",
        "prompt": "How do you know each other?",
        "schema": {"type": "string"},
    },
    {
        "field": "relationship.live_together_now",
        "prompt": "Do you live with them right now?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "relationship.lived_together_past",
        "prompt": "Did you used to live together?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "relationship.children_in_common",
        "prompt": "Do you have a child together?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].date",
        "prompt": "When did this happen? An estimate is okay.",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].location",
        "prompt": "Where were you?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].narrative",
        "prompt": "In your own words, what happened?",
        "schema": {"type": "string", "minLength": 1, "maxLength": 10000},
    },
    {
        "field": "incidents[].witnesses_present",
        "prompt": "Was anyone else there?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].police_called",
        "prompt": "Did anyone call the police?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].weapon_involved",
        "prompt": "Was there a weapon?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].injury",
        "prompt": "Were you or anyone hurt?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].pattern_frequency",
        "prompt": "How often does something like this happen?",
        "schema": {"type": "string"},
    },
    {
        "field": "protected_persons.children[]",
        "prompt": "Are there kids you want kept safe?",
        "schema": {"type": "string"},
    },
    {
        "field": "firearm.respondent_has_access",
        "prompt": "Does he/she/they have a gun, or access to one?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "prior_orders.exists",
        "prompt": (
            "Have you ever had a restraining order before — "
            "against them, or them against you?"
        ),
        "schema": {"type": "boolean"},
    },
]


def _is_minor(dob_str: str) -> bool:
    """Helper to detect minor status for Q24 pathing based on 2026 anchor date."""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
        # Fixed SIM300: Yoda condition resolved
        age = 2026 - dob.year - ((dob.month, dob.day) > (5, 27))
        return age < 18
    except ValueError:
        return False


async def handle_intake_step(body: dict[str, Any], env: Any) -> Any:
    session_id = body.get("session_id")
    jurisdiction = body.get("jurisdiction")
    answers = body.get("answers", {})

    # Fixed N806: Lowercase variable configuration
    all_allowed = SUPPORTED_JURISDICTIONS | HANDOFF_JURISDICTIONS

    if not isinstance(session_id, str) or not session_id:
        return problem_response(400, "bad_request", "session_id is required")
    if jurisdiction not in all_allowed:
        return problem_response(
            400,
            "unsupported_jurisdiction",
            f"jurisdiction must be one of {sorted(all_allowed)}",
        )
    if not isinstance(answers, dict):
        return problem_response(400, "bad_request", "answers must be an object")

    next_step = determine_next_step(jurisdiction, answers)
    return json_response(next_step)


def determine_next_step(
    jurisdiction: str, answers: dict[str, Any]
) -> dict[str, Any]:
    # 1. Evaluate Tier 1 sequentially
    for step in TIER_1_FLOW:
        field = step["field"]
        if field not in answers:
            schema_overlay = step["schema"].copy()
            if field == "relationship.type" and jurisdiction == "CA":
                schema_overlay["enum"] = [
                    "married",
                    "dating",
                    "engaged",
                    "cohabiting",
                    "child_in_common",
                ]
            return {
                "step": field,
                "prompt": step["prompt"],
                "schema": schema_overlay,
            }

    # 2. Tier 1 complete -> Jurisdiction Gate
    if jurisdiction in HANDOFF_JURISDICTIONS:
        return {
            "step": "handoff",
            "action": "redirect",
            "reason": (
                f"Jurisdiction {jurisdiction} requires "
                "external portal routing."
            ),
        }

    # 3. Tier 2: Jurisdiction-Aware Overlays

    # Q24: Minor Filing Path
    # Fixed SIM102: Combined nested if structures
    if (
        _is_minor(answers.get("petitioner.dob", ""))
        and jurisdiction in {"CA", "NY", "TX", "FL"}
        and "petitioner.minor_filing_path" not in answers
    ):
        return {
            "step": "petitioner.minor_filing_path",
            "prompt": (
                "You're under 18 — is there an adult who can file with you, "
                "or do you want to file alone?"
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction == "FL" and "petitioner.race" not in answers:
        return {
            "step": "petitioner.race",
            "prompt": (
                "What is your race? This is a required court demographic "
                "field, but you can skip if uncomfortable."
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction in {"CA", "FL"} and "petitioner.gender" not in answers:
        return {
            "step": "petitioner.gender",
            "prompt": "How do you describe your gender? You can skip.",
            "schema": {"type": "string"},
        }

    if (
        jurisdiction in {"CA", "NY", "TX", "FL"}
        and "petitioner.interpreter_language" not in answers
    ):
        return {
            "step": "petitioner.interpreter_language",
            "prompt": "Do you need an interpreter for court? Which language?",
            "schema": {"type": "string"},
        }

    if (
        jurisdiction in {"CA", "FL"}
        and "petitioner.disability_accommodation" not in answers
    ):
        return {
            "step": "petitioner.disability_accommodation",
            "prompt": (
                "Do you need any accommodations at court — a ramp, "
                "a quiet room, a sign-language interpreter?"
            ),
            "schema": {"type": "string"},
        }

    # Respondent Physical Description Overlay (Q31-Q35)
    if jurisdiction in {"CA", "NY", "TX", "FL"}:
        prefix = (
            "The sheriff uses this to find them when they deliver "
            "the papers. Estimates are fine. "
        )
        physical_fields = [
            (
                "respondent.height",
                prefix + "About how tall? An estimate is fine.",
                {"type": "string"},
            ),
            (
                "respondent.weight",
                prefix + "About what weight?",
                {"type": "string"},
            ),
            (
                "respondent.eye_color",
                prefix + "Eye color?",
                {"type": "string"},
            ),
            (
                "respondent.hair_color",
                prefix + "Hair color?",
                {"type": "string"},
            ),
            (
                "respondent.distinguishing_marks",
                prefix + "Any tattoos, scars, or other marks the sheriff?",
                {"type": "string"},
            ),
        ]
        for f_id, prompt, schema in physical_fields:
            if f_id not in answers:
                return {"step": f_id, "prompt": prompt, "schema": schema}

    # Respondent Employer Info Overlay (Q38-Q40)
    if "respondent.employer_name" not in answers:
        return {
            "step": "respondent.employer_name",
            "prompt": "Where do they work, if you know?",
            "schema": {"type": "string"},
        }
    if "respondent.employer_address" not in answers:
        return {
            "step": "respondent.employer_address",
            "prompt": "What's the work address?",
            "schema": {"type": "string"},
        }
    if jurisdiction == "FL" and "respondent.employer_hours" not in answers:
        return {
            "step": "respondent.employer_hours",
            "prompt": "Working hours?",
            "schema": {"type": "string"},
        }

    # Respondent Vehicle Info Overlay (Q41-Q43)
    if jurisdiction in {"CA", "NY", "TX", "FL"}:
        if "respondent.vehicle_make_model" not in answers:
            return {
                "step": "respondent.vehicle_make_model",
                "prompt": "Do they drive? What kind of car?",
                "schema": {"type": "string"},
            }
        if "respondent.vehicle_color" not in answers:
            return {
                "step": "respondent.vehicle_color",
                "prompt": "Color?",
                "schema": {"type": "string"},
            }
        if "respondent.vehicle_plate" not in answers:
            return {
                "step": "respondent.vehicle_plate",
                "prompt": "License plate, if you know?",
                "schema": {"type": "string"},
            }

    # High-Risk / Background Check Overlays
    if (
        jurisdiction in {"FL", "NY", "TX"}
        and "respondent.is_law_enforcement" not in answers
    ):
        return {
            "step": "respondent.is_law_enforcement",
            "prompt": (
                "Are they a police officer, military, or do "
                "they carry a gun for work?"
            ),
            "schema": {"type": "boolean"},
        }
    if jurisdiction == "FL" and "respondent.is_active_military" not in answers:
        return {
            "step": "respondent.is_active_military",
            "prompt": "Are they currently in the military, active duty?",
            "schema": {"type": "boolean"},
        }
    if (
        jurisdiction == "CA"
        and "respondent.immigration_status_known" not in answers
    ):
        return {
            "step": "respondent.immigration_status_known",
            "prompt": (
                "Do you know their immigration status? (We don't "
                "share this — it can affect what protections you have.)"
            ),
            "schema": {"type": "boolean"},
        }
    if (
        jurisdiction in {"CA", "NY", "TX", "FL"}
        and "respondent.prior_criminal_history" not in answers
    ):
        return {
            "step": "respondent.prior_criminal_history",
            "prompt": (
                "Has he/she/they ever been arrested or convicted "
                "of anything violent that you know of?"
            ),
            "schema": {"type": "boolean"},
        }

    # TX Specific Background Overlays (Q48, Q49)
    if jurisdiction == "TX":
        if "respondent.prior_dv_finding" not in answers:
            return {
                "step": "respondent.prior_dv_finding",
                "prompt": (
                    "Has a court ever found them guilty of family "
                    "violence specifically?"
                ),
                "schema": {"type": "boolean"},
            }
        if "respondent.parental_rights_terminated" not in answers:
            return {
                "step": "respondent.parental_rights_terminated",
                "prompt": (
                    "Have their parental rights to a child in this "
                    "case been terminated?"
                ),
                "schema": {"type": "boolean"},
            }

    # 4. Conditional Triggers

    # Q50: Police Report Connection Interception
    # Fixed SIM102: Combined nested if structures
    if (
        answers.get("incidents[].police_called") is True
        and jurisdiction in {"CA", "NY", "TX", "FL"}
        and "incidents[].police_report_number" not in answers
    ):
        return {
            "step": "incidents[].police_report_number",
            "prompt": (
                "Did the police take a report? Do you have a "
                "number or case number?"
            ),
            "schema": {"type": "string"},
        }

    # Q64, Q65: Firearm Overlay
    if answers.get("firearm.respondent_has_access") is True:
        if "firearm.types[]" not in answers:
            return {
                "step": "firearm.types[]",
                "prompt": "Do you know what kind? A handgun, a rifle?",
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "firearm.locations[]" not in answers:
            return {
                "step": "firearm.locations[]",
                "prompt": "Where are they kept, if you know?",
                "schema": {"type": "array", "items": {"type": "string"}},
            }

    # 5. Q118: Terminal Support Gate
    # Fixed SIM102: Combined nested if structures
    requested_reliefs = answers.get("selected_reliefs_intents", [])
    if (
        jurisdiction in {"CA", "FL", "TX"}
        and (
            "child_support" in requested_reliefs
            or "spousal_support" in requested_reliefs
        )
        and "petitioner.ssn" not in answers
    ):
        return {
            "step": "petitioner.ssn",
            "prompt": (
                "(For child or spousal support, the court needs your "
                "SSN. Encrypted, never shared.)"
            ),
            "schema": {
                "type": "string",
                "pattern": r"^\d{3}-\d{2}-\d{4}$",
            },
        }

    return {"step": "done", "jurisdiction": jurisdiction}