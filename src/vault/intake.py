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

from guardrails.contracts import FeatureResult
from guardrails.rules import RESP
from guardrails.session import SessionState
from lib.responses import json_response, problem_response

# Jurisdictions supported for the full Petition process
SUPPORTED_JURISDICTIONS = {"CA", "NY", "TX", "FL", "WA", "VA", "PA", "NC", "MA"}
# States with no physical DVRO petition form — they e-file through a state portal.
# We collect Tier 1, then hand off to that portal instead of assembling a form.
HANDOFF_JURISDICTIONS = {"AZ", "IL", "KS", "NJ"}

# Tier-2 jurisdiction sets, transcribed verbatim from the DVRO Multi-State Intake
# Question Flow doc. These hold the FULL doc lists (not just the currently-supported
# states) so the gates stay in sync with the source of truth; the validation layer
# only admits SUPPORTED_JURISDICTIONS today, so unlisted states never reach this logic.
# Effective set today = doc list ∩ SUPPORTED_JURISDICTIONS.
MINOR_FILING_STATES = frozenset(
    {
        "AL",
        "AR",
        "CA",
        "GA",
        "HI",
        "IA",
        "ME",
        "MA",
        "MN",
        "MO",
        "NE",
        "OK",
        "OR",
        "SC",
        "SD",
        "TN",
        "TX",
    }
)  # Q24 — CA, TX among supported (NOT NY/FL)
PHYSICAL_DESCRIPTION_STATES = frozenset(
    {
        "AR",
        "CA",
        "CO",
        "CT",
        "FL",
        "GA",
        "ID",
        "KY",
        "LA",
        "ME",
        "MA",
        "MN",
        "MS",
        "MO",
        "NE",
        "NH",
        "ND",
        "OH",
        "OK",
        "PA",
        "SC",
        "TN",
        "UT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    }
)  # Q31-35 — CA, FL among supported (NOT NY/TX)
VEHICLE_DESCRIPTION_STATES = frozenset(
    {
        "AR",
        "CA",
        "CT",
        "FL",
        "GA",
        "ID",
        "KY",
        "LA",
        "ME",
        "MA",
        "MS",
        "MO",
        "NE",
        "NH",
        "ND",
        "OH",
        "OK",
        "SC",
        "TN",
        "UT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    }
)  # Q41-43 — CA, FL among supported (NOT NY/TX)

# TIER 1: UNIVERSAL CORE DEFINITIONS (Q1 - Q22)
# ---------------------------------------------------------------------------
TIER_1_FLOW = [
    {
        "field": "petitioner.legal_name",
        "prompt": (
            "What's the name you'd use on a driver's license or a passport? "
            "That's the one the court needs."
        ),
        "schema": {"type": "string", "minLength": 1, "maxLength": 200},
    },
    {
        "field": "petitioner.dob",
        "prompt": "When's your birthday?",
        "schema": {"type": "string", "format": "date"},
    },
    {
        "field": "petitioner.safe_mailing_address",
        "prompt": (
            "The court needs an address to send you things. It doesn't have to be where you "
            "live — a PO box, a friend's place, an advocate's office all work. "
            "Where should they send it?"
        ),
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "petitioner.safe_phone",
        "prompt": (
            "Is there a phone number that's safe for the court to use? "
            "Skip this if you'd rather not — it's not required."
        ),
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "petitioner.safe_email",
        "prompt": "A safe email?",
        "schema": {"type": "string", "format": "email"},
    },
    {
        "field": "respondent.legal_name",
        "prompt": "What's their full name?",
        "schema": {"type": "string", "minLength": 1},
    },
    {
        "field": "respondent.last_known_address",
        "prompt": (
            "Where do they live, if you know? Don't know is a real answer — "
            "sometimes that's part of the problem."
        ),
        "schema": {"type": "string"},
    },
    {
        "field": "relationship.type",
        "prompt": (
            "How would you describe what they are to you — "
            "partner, ex, family, someone you live with?"
        ),
        "schema": {"type": "string"},
    },
    {
        "field": "relationship.live_together_now",
        "prompt": "Are you living with them right now?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "relationship.lived_together_past",
        "prompt": "Did you used to live together?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "relationship.children_in_common",
        "prompt": "Do the two of you have a child together?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].date",
        "prompt": (
            "Do you remember roughly when this was? "
            "Last week, last year, a season — anything you've got."
        ),
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].location",
        "prompt": "Where were you when it happened?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].narrative",
        "prompt": (
            "Whenever you're ready — tell me what happened, in your own words. "
            "I won't change them. You can pause anytime."
        ),
        "schema": {"type": "string", "minLength": 1, "maxLength": 10000},
    },
    {
        "field": "incidents[].witnesses_present",
        "prompt": "Was anyone else around — even someone who didn't see the whole thing?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].police_called",
        "prompt": "Did anyone end up calling the police — you, them, a neighbor?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].weapon_involved",
        "prompt": "Was there a weapon involved — a gun, a knife, or something else used as one?",
        "schema": {"type": "boolean"},
    },
    {
        "field": "incidents[].injury",
        "prompt": "Was anyone hurt — physically, or in a way that took longer to feel?",
        "schema": {"type": "string"},
    },
    {
        "field": "incidents[].pattern_frequency",
        "prompt": "How often does something like this happen?",
        "schema": {"type": "string"},
    },
    {
        "field": "protected_persons.children[]",
        "prompt": (
            "If it's okay, I want to ask about the kids next. I'll keep it short — "
            "these questions are for the court, not for me, and we can skip any of them."
        ),
        "schema": {"type": "string"},
    },
    {
        "field": "firearm.respondent_has_access",
        "prompt": (
            "Do they have a gun, or could they get to one — at home, at work, a relative's place? "
            "'Don't know' is a real answer."
        ),
        "schema": {"type": "boolean"},
    },
    {
        "field": "prior_orders.exists",
        "prompt": (
            "Has there ever been any kind of restraining order between the two of you — "
            "either direction, any state?"
        ),
        "schema": {"type": "boolean"},
    },
]

# Optional additional abuse incidents (DV-100 items 6 and 7). Same shape as the
# Tier-1 incident (item 5); collected only when the survivor says there's another
# one to add, so a single-incident filer is never walked through empty questions.
_ADDITIONAL_INCIDENT_FIELDS = [
    ("date", "Do you remember roughly when this one was?", {"type": "string"}),
    (
        "narrative",
        "Tell me what happened this time, in your own words — same as before, "
        "I won't change them.",
        {"type": "string", "minLength": 1, "maxLength": 10000},
    ),
    ("witnesses_present", "Was anyone else around this time?", {"type": "string"}),
    ("weapon_involved", "Was a weapon involved?", {"type": "boolean"}),
    ("injury", "Was anyone hurt?", {"type": "string"}),
    ("police_called", "Did anyone call the police?", {"type": "boolean"}),
    ("pattern_frequency", "How often did this kind of thing happen?", {"type": "string"}),
]


def _is_minor(dob_str: str) -> bool:
    """Helper to detect minor status for Q24 pathing, relative to today's date."""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return False
    today = datetime.now()
    age = today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))
    return age < 18


class VaultFeatureManager:
    """OOP interface encapsulation managing state tracking and legal workflows."""

    def match_and_execute(self, pl: str, session: SessionState) -> FeatureResult | None:
        # Regex (not substring) so natural phrasings match, e.g.
        # "how do i apply for a restraining order".
        if any(
            re.search(p, pl)
            for p in (
                r"how (do i|to|can i|can you|would i|should i|do you)\b.{0,25}"
                r"(get|file|apply|obtain|start|request|fill).{0,25}(restraining|protective)",
                r"(walk|tell) me.{0,20}(get|file|apply|obtain).{0,25}(restraining|protective)",
            )
        ):
            if session.user_state != "California":
                return FeatureResult(
                    "DVRO procedure differs significantly across the 47 US jurisdictions. "
                    "Tell me what state you're filing in and I'll walk you through the "
                    "exact procedure — form names, fees, hearing timeline.",
                    0,
                )
            return FeatureResult(
                "In California, here is how to file for a domestic violence restraining order. "
                "Step 1: Go to your local courthouse and ask for the DV petition forms — "
                "in California that's the DV-100. Step 2: Fill out the forms describing the "
                "abuse. I can walk you through every field. Step 3: File with the clerk. "
                "There is no filing fee for DV petitions. Step 4: A judge reviews your request "
                "the same day and can issue a Temporary Restraining Order immediately. Step 5: "
                "The sheriff serves the papers to the respondent, free of charge. Want me to start "
                "walking you through the forms right now?",
                0,
            )

        if ("protective order" in pl or "restraining order" in pl) and "violat" in pl:
            return FeatureResult(
                "A violation of a protective order is an active criminal offense. "
                "Call 911 — not a non-emergency line — and tell the dispatcher you have a "
                "restraining order that is being violated. The officer who responds is "
                "required to enforce it. After: document the date, time, officer names, and "
                "any witnesses. The National DV Hotline (1-800-799-7233) can also connect you "
                "with a local legal advocate to review how your county handles violations. "
                "Want me to find one?",
                2,
            )

        if any(w in pl for w in ["showing up", "appearing", "following me", "outside my"]):
            return FeatureResult(
                "This pattern — tracking your location and showing up — is a serious escalation "
                "in risk. For safe planning, use an unmonitored device (library computer or a "
                "trusted friend's phone). A local advocate can help you map out safe routes, "
                "emergency options, and next legal steps. Want me to find an advocate in "
                "your county?",
                2,
            )

        if any(w in pl for w in ["gun", "firearm"]) and any(
            w in pl for w in ["threat", "choked", "strangled", "deported", "kill"]
        ):
            session.firearm_access = True
            if "weapon_access" not in session.risk_factors:
                session.risk_factors.append("weapon_access")
            if not session.resource_surfaced_this_session:
                session.resource_surfaced_this_session = True
                return FeatureResult(
                    "Some of what you've shared — firearm access combined with threats — carries "
                    "elevated risk. I want to make sure you have a safety plan and an advocate's "
                    "number on hand, just to have. No pressure to use them. The National DV "
                    "Hotline (1-800-799-7233) can connect you with a local advocate who can walk "
                    "through a safety plan with you when you're ready. Let's keep working on "
                    "your forms.",
                    1,
                )

        if any(w in pl for w in ["deport", "undocumented", "visa", "immigration status"]):
            session.immigration_risk = True
            return FeatureResult(
                "Threats involving immigration status are a form of coercive control. Under "
                "federal law — the Violence Against Women Act — independent options exist to "
                "secure immigration status without the abuser's knowledge or cooperation, "
                "including VAWA self-petitions and U-visas for crime victims. I can connect "
                "you with an immigration attorney through the DV coalition network in your "
                "state. No pressure — want me to find one when you're ready?",
                1,
            )

        if any(
            w in pl
            for w in [
                "no money",
                "can.t access money",
                "controls money",
                "controls account",
                "financial trapped",
                "financial control",
                "nowhere to go",
                "no family",
            ]
        ):
            response = (
                "What you're describing — being cut off from money or accounts — is economic "
                "coercion, and it's a recognized form of abuse. Local advocates specialize in "
                "exactly this: emergency funds, temporary housing, and confidential legal options. "
                "Would you like me to find an advocate organization in your county? Either way, "
                "your Vault progress is saved and we can continue whenever you're ready."
            )
            if any(
                w in pl
                for w in ["where do i go", "where can i stay", "no place nearby", "nowhere nearby"]
            ):
                response += (
                    " On the housing question specifically: domestic violence shelters provide "
                    "emergency same-night placement, are confidential (your address is protected "
                    "by law), and are free. The National DV Hotline (1-800-799-7233, 24/7) can "
                    "find the nearest available bed in your county right now. You do not need "
                    "money, ID, or a reservation to enter."
                )
            return FeatureResult(response, 2)

        if any(
            w in pl for w in ["lose custody", "take the kids", "take custody", "custody threat"]
        ):
            return FeatureResult(
                "Threatening to take the children is a well-documented tactic of coercive control "
                "— designed to create fear and prevent you from seeking help. A family law "
                "advocate can walk you through how parental rights are handled in your county and "
                "what documentation matters most. Want me to find a legal clinic or advocacy "
                "organization near you?",
                2,
            )

        if "after i file" in pl or "after filing" in pl or "happens after i file" in pl:
            if session.user_state != "California":
                return FeatureResult(
                    "DVRO procedure differs significantly across the 47 US jurisdictions. "
                    "Tell me what state you're filing in and I'll walk you through the "
                    "exact procedure — form names, fees, hearing timeline.",
                    0,
                )
            return FeatureResult(
                "In California, filing initiates a strict sequence. Within a few hours: a judge "
                "reviews your request for a Temporary Restraining Order. If granted, you receive a "
                "stamped copy from the clerk — enforceable immediately. The sheriff serves the "
                "papers to the respondent, free in DV cases. The full hearing happens about "
                "21-25 days after filing. At the hearing: you testify briefly, the respondent "
                "responds, and the judge decides whether to issue a long-term order (up to five "
                "years in California — varies by state). You can bring an advocate, and you can "
                "request a remote appearance. If the respondent doesn't show, the judge usually "
                "grants the order anyway. Want me to walk through what to bring to the hearing?",
                0,
            )

        if any(
            w in pl
            for w in ["recipe app", "look like", "disguise", "private mode", "clear history"]
        ):
            return FeatureResult(RESP["G20_security"], 2)

        return None


async def handle_intake_step(body: dict[str, Any], env: Any) -> Any:
    session_id = body.get("session_id")
    jurisdiction = body.get("jurisdiction")
    answers = body.get("answers", {})

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


def determine_next_step(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    for step in TIER_1_FLOW:
        field = step["field"]
        if field not in answers:
            step_dict: dict[str, Any] = step
            schema_overlay = step_dict["schema"].copy()

            if field == "relationship.type" and jurisdiction == "CA":
                schema_overlay["enum"] = [
                    "married",
                    "dating",
                    "engaged",
                    "cohabiting",
                    "child_in_common",
                ]
            return {"step": field, "prompt": step_dict["prompt"], "schema": schema_overlay}

    if jurisdiction in HANDOFF_JURISDICTIONS:
        return {
            "step": "handoff",
            "action": "redirect",
            "reason": f"Jurisdiction {jurisdiction} requires external portal routing.",
        }

    if (
        _is_minor(answers.get("petitioner.dob", ""))
        and jurisdiction in MINOR_FILING_STATES
        and "petitioner.minor_filing_path" not in answers
    ):
        return {
            "step": "petitioner.minor_filing_path",
            "prompt": (
                "Looks like you're under 18 — most states want an adult to file alongside "
                "someone your age. Is there a parent, a guardian, or another trusted adult who "
                "could? If not, there's still a way forward, and we can figure it out."
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction == "FL" and "petitioner.race" not in answers:
        return {
            "step": "petitioner.race",
            "prompt": (
                "Some states ask about race or ethnicity on the form itself — yours does. "
                "You can write what fits, or skip. Lea defaults to 'not disclosed.'"
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction in {"CA", "FL"} and "petitioner.gender" not in answers:
        return {
            "step": "petitioner.gender",
            "prompt": (
                "Your state has a gender field on the form. "
                "How would you describe yours — or want to skip it?"
            ),
            "schema": {"type": "string"},
        }

    if (
        jurisdiction in {"CA", "NY", "TX", "FL", "WA", "NC", "MA"}
        and "petitioner.interpreter_language" not in answers
    ):
        return {
            "step": "petitioner.interpreter_language",
            "prompt": (
                "If you go to a hearing, would you want an interpreter there? "
                "If yes — what language?"
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction in {"CA", "FL", "WA"} and "petitioner.disability_accommodation" not in answers:
        return {
            "step": "petitioner.disability_accommodation",
            "prompt": (
                "Do you need any accommodations at court — "
                "a ramp, a quiet room, a sign-language interpreter?"
            ),
            "schema": {"type": "string"},
        }

    if jurisdiction in PHYSICAL_DESCRIPTION_STATES:
        # Frame the cluster's purpose ONCE, on the first question the user sees (height),
        # then keep the rest short — repeating the sheriff preamble on every field reads as
        # interrogation. See the Tone doc's frame-purpose rule.
        physical_fields = [
            (
                "respondent.height",
                "These next few — height, weight, what they look like — feel personal, I know. "
                "They're for the sheriff who delivers the papers, not for me, and estimates are "
                "fine. About how tall?",
                {"type": "string"},
            ),
            ("respondent.weight", "About what they weigh?", {"type": "string"}),
            ("respondent.eye_color", "Eye color?", {"type": "string"}),
            ("respondent.hair_color", "Hair color?", {"type": "string"}),
            (
                "respondent.distinguishing_marks",
                "Tattoos, scars, anything that stands out — "
                "anything the sheriff might use to recognize them?",
                {"type": "string"},
            ),
        ]
        for f_id, pr, sc in physical_fields:
            if f_id not in answers:
                return {"step": f_id, "prompt": pr, "schema": sc}

    if "respondent.employer_name" not in answers:
        return {
            "step": "respondent.employer_name",
            "prompt": (
                "Where do they work? The court sometimes uses a job address to deliver "
                "papers if home doesn't work."
            ),
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

    if jurisdiction in VEHICLE_DESCRIPTION_STATES:
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

    if jurisdiction in {"FL", "NY", "TX"} and "respondent.is_law_enforcement" not in answers:
        return {
            "step": "respondent.is_law_enforcement",
            "prompt": (
                "Is their job one where they carry a firearm — police, military, security? "
                "It changes how some of the orders work."
            ),
            "schema": {"type": "boolean"},
        }
    if jurisdiction == "FL" and "respondent.is_active_military" not in answers:
        return {
            "step": "respondent.is_active_military",
            "prompt": (
                "Are they on active military duty right now? If yes, there's a federal law "
                "that gives them extra time to respond, and we should plan for it."
            ),
            "schema": {"type": "boolean"},
        }
    if jurisdiction == "CA" and "respondent.immigration_status_known" not in answers:
        return {
            "step": "respondent.immigration_status_known",
            "prompt": (
                "Do you know their immigration status? (We don't share this — "
                "it can affect what protections you have.)"
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
                "Has he/she/they ever been arrested or convicted of "
                "anything violent that you know of?"
            ),
            "schema": {"type": "boolean"},
        }

    if jurisdiction == "TX":
        if "respondent.prior_dv_finding" not in answers:
            return {
                "step": "respondent.prior_dv_finding",
                "prompt": "Has a court ever found them guilty of family violence specifically?",
                "schema": {"type": "boolean"},
            }
        if "respondent.parental_rights_terminated" not in answers:
            return {
                "step": "respondent.parental_rights_terminated",
                "prompt": "Have their parental rights to a child in this case been terminated?",
                "schema": {"type": "boolean"},
            }

    if (
        answers.get("incidents[].police_called") is True
        and jurisdiction in {"CA", "NY", "TX", "FL"}
        and "incidents[].police_report_number" not in answers
    ):
        return {
            "step": "incidents[].police_report_number",
            "prompt": "Did the police take a report? Do you have a number or case number?",
            "schema": {"type": "string"},
        }

    if answers.get("firearm.respondent_has_access") is True:
        if "firearm.types[]" not in answers:
            return {
                "step": "firearm.types[]",
                "prompt": (
                    "Do you know what kind? A handgun, a long gun, more than one? "
                    "Whatever you can describe is useful."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "firearm.locations[]" not in answers:
            return {
                "step": "firearm.locations[]",
                "prompt": (
                    "Any idea where they're kept? Doesn't have to be exact — "
                    "'in the truck,' 'somewhere in the bedroom,' 'his mom's house' all help."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }

    # Remaining CA-specific DV-100 fields the Tier-2 blocks above don't cover:
    # respondent identity (2b-2e), marriage status (3c), extra incidents (6-7),
    # protected-people detail (8), and the orders requested (10-28) with their
    # details. CA only today (the jurisdiction with petition mapping in
    # vault.forms.ca); other states follow when their form module lands.
    if jurisdiction == "CA":
        # Respondent identity (items 2b-2e) — the form asks, Tier-1 didn't.
        if "respondent.age" not in answers:
            return {
                "step": "respondent.age",
                "prompt": "About how old are they? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know their date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their gender — or skip it?",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The form asks their race or ethnicity. Put what fits, or skip — "
                    "Lea defaults to 'not disclosed.'"
                ),
                "schema": {"type": "string"},
            }

        # Current vs former marriage (item 3b vs 3c) — the enum can't tell them apart.
        if (
            answers.get("relationship.type") == "married"
            and "relationship.marriage_intact" not in answers
        ):
            return {
                "step": "relationship.marriage_intact",
                "prompt": (
                    "Are the two of you still married, or has it ended — divorced "
                    "or separated?"
                ),
                "schema": {"type": "boolean"},
            }

        # Additional abuse incidents (items 6, 7) — optional, up to two more.
        for idx in (2, 3):
            gate = f"incidents.add_{idx}"
            if gate not in answers:
                return {
                    "step": gate,
                    "prompt": (
                        "Is there another incident you'd want the judge to know about? "
                        "It's okay if not — one is enough to ask for protection."
                        if idx == 2
                        else "One more? This is the last incident I'll ask about here."
                    ),
                    "schema": {"type": "boolean"},
                }
            if answers[gate] is not True:
                break
            for fname, prompt, schema in _ADDITIONAL_INCIDENT_FIELDS:
                key = f"incident_{idx}.{fname}"
                if key not in answers:
                    return {"step": key, "prompt": prompt, "schema": schema}

        # Why the other protected people need protection (item 8) — only if any.
        protected = answers.get("protected_persons.children[]")
        if (
            isinstance(protected, str)
            and protected.strip().lower() not in ("", "none")
            and "protected_persons.why" not in answers
        ):
            return {
                "step": "protected_persons.why",
                "prompt": (
                    "For the people you want protected — can you say a little about why "
                    "they need it too?"
                ),
                "schema": {"type": "string"},
            }

        # Orders the petitioner is requesting (items 10-28) — the survivor's own
        # choices, not legal advice.
        if "selected_reliefs_intents" not in answers:
            return {
                "step": "selected_reliefs_intents",
                "prompt": (
                    "Now the part where you tell the judge what you'd like them to do. "
                    "Pick whatever fits — there's no wrong answer, and we can change it "
                    "later. Which of these would help?"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # 10: order them not to abuse you
                            "no_contact",  # 11: no contact at all
                            "stay_away",  # 12: keep a set distance away
                            "move_out",  # 13: move out of your home
                            "protect_animals",  # 16: protect your pets
                            "property_control",  # 17: control of certain property
                            "no_insurance_changes",  # 18
                            "record_communications",  # 19
                            "pay_debts",  # 22
                            "pay_expenses",  # 23
                            "child_support",  # 24
                            "spousal_support",  # 25
                            "attorney_fees",  # 26
                            "batterer_program",  # 27
                            "transfer_phone",  # 28
                        ],
                    },
                },
            }

        selected = answers.get("selected_reliefs_intents", [])
        # Follow-ups: only the orders that need extra detail to be fillable.
        if "stay_away" in selected:
            if "relief.stay_away_places" not in answers:
                return {
                    "step": "relief.stay_away_places",
                    "prompt": (
                        "For the stay-away order — which places should they keep away "
                        "from? Your home, your work, your kids' school, your car? "
                        "Pick any that matter."
                    ),
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "home",
                                "work",
                                "school",
                                "vehicle",
                                "childrens_school",
                                "other",
                            ],
                        },
                    },
                }
            if "relief.stay_away_distance_yards" not in answers:
                return {
                    "step": "relief.stay_away_distance_yards",
                    "prompt": (
                        "How far should they have to stay? Most people ask for 100 yards "
                        "— about the length of a football field. You can pick another "
                        "number if you'd rather."
                    ),
                    "schema": {"type": "integer", "minimum": 1, "default": 100},
                }
        if "move_out" in selected and "relief.move_out_address" not in answers:
            return {
                "step": "relief.move_out_address",
                "prompt": (
                    "For the move-out order — what's the address of the home you want "
                    "them to leave?"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "protect_animals" in selected and "relief.animals[]" not in answers:
            return {
                "step": "relief.animals[]",
                "prompt": (
                    "Tell me about the animals you want protected — a name or short "
                    "description for each is enough."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "property_control" in selected:
            if "relief.property_describe" not in answers:
                return {
                    "step": "relief.property_describe",
                    "prompt": (
                        "For the property order — what should the judge give you control "
                        "of? List whatever matters (a car, a phone, documents)."
                    ),
                    "schema": {"type": "string", "minLength": 1},
                }
            if "relief.property_why" not in answers:
                return {
                    "step": "relief.property_why",
                    "prompt": "Why do you need control of those things?",
                    "schema": {"type": "string"},
                }
        if "pay_debts" in selected and "relief.debts" not in answers:
            return {
                "step": "relief.debts",
                "prompt": (
                    "For the debts you want them to pay — list each one (who it's owed "
                    "to, what it's for, and the amount if you know)."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "pay_expenses" in selected and "relief.expenses" not in answers:
            return {
                "step": "relief.expenses",
                "prompt": (
                    "For expenses the abuse caused — list each (what it was for and the "
                    "amount). You'll bring proof to your hearing."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "transfer_phone" in selected and "relief.transfer_phone_numbers" not in answers:
            return {
                "step": "relief.transfer_phone_numbers",
                "prompt": (
                    "Which phone numbers do you want moved into your name? List them "
                    "with area codes."
                ),
                "schema": {"type": "array", "items": {"type": "string"}},
            }

    # Washington PO 001 — WA-specific fields (items 3, 9, 12-17, 19-24). WA's
    # restraints (item 14) are its own list, distinct from CA's relief set. Maps
    # in vault.forms.wa. CA's analogous block is gated above; this is WA's.
    if jurisdiction == "WA":
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.age_band" not in answers:
            return {
                "step": "respondent.age_band",
                "prompt": "Roughly how old are they? (The WA form uses age ranges.)",
                "schema": {
                    "type": "string",
                    "enum": ["under_13", "13_to_17", "18_or_over", "unknown"],
                },
            }
        if "wa.jurisdiction_basis" not in answers:
            return {
                "step": "wa.jurisdiction_basis",
                "prompt": (
                    "Washington asks why the case belongs here. Which is true — pick any: "
                    "you live in this county, or an incident happened in this county or state?"
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["lives_here", "incident_here"]},
                },
            }
        if "wa.restraints" not in answers:
            return {
                "step": "wa.restraints",
                "prompt": (
                    "Now the orders you'd like the judge to make. Pick whatever fits — "
                    "there's no wrong answer and we can change it later. Which would help?"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_harm",  # 14A
                            "no_contact",  # 14B
                            "stalking",  # 14C
                            "stay_away",  # 14D
                            "vacate",  # 14E
                            "intimate_images",  # 14F
                            "electronic_monitoring",  # 14G
                            "evaluation",  # 14H
                            "treatment",  # 14I
                            "personal_belongings",  # 14J
                            "no_transfer_assets",  # 14K
                            "financial_relief",  # 14K-finances
                            "vehicle_use",  # 14L
                            "restrict_abusive_litigation",  # 14M
                            "pay_fees",  # 14N
                            "surrender_weapons",  # 14O
                            "custody",  # 14P
                            "no_interference_custody",  # 14Q
                            "no_removal_from_state",  # 14R
                            "school_enrollment",  # 14S
                            "pets_custody",  # 14T
                            "pets_no_interference",  # 14U
                            "pets_stay_away",  # 14V
                            "other",  # 14Z
                        ],
                    },
                },
            }

        wa_restraints = answers.get("wa.restraints", [])
        if "stay_away" in wa_restraints:
            if "wa.stay_away_places" not in answers:
                return {
                    "step": "wa.stay_away_places",
                    "prompt": (
                        "For the stay-away order — which places should they keep away "
                        "from? Home, work, your kids' school, your car? Pick any."
                    ),
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "residence",
                                "workplace",
                                "school",
                                "vehicle",
                                "childrens_school",
                                "shared_residence",
                                "other",
                            ],
                        },
                    },
                }
            if "wa.stay_away_distance_feet" not in answers:
                return {
                    "step": "wa.stay_away_distance_feet",
                    "prompt": (
                        "How far should they have to stay? In Washington the usual ask is "
                        "1,000 feet. You can pick another distance if you'd rather."
                    ),
                    "schema": {"type": "integer", "minimum": 1, "default": 1000},
                }
        if "personal_belongings" in wa_restraints and "wa.belongings" not in answers:
            return {
                "step": "wa.belongings",
                "prompt": "Which essential belongings do you need? List whatever matters.",
                "schema": {"type": "array", "items": {"type": "string"}},
            }
        if "vehicle_use" in wa_restraints and "wa.vehicle_use" not in answers:
            return {
                "step": "wa.vehicle_use",
                "prompt": (
                    "Which vehicle do you need use of? Year, make, model, and plate if known."
                ),
                "schema": {"type": "string"},
            }
        if "pets_custody" in wa_restraints and "wa.pets" not in answers:
            return {
                "step": "wa.pets",
                "prompt": "Tell me about the pets you want protected — a name and type for each.",
                "schema": {"type": "array", "items": {"type": "string"}},
            }

        if "wa.temporary_order" not in answers:
            return {
                "step": "wa.temporary_order",
                "prompt": (
                    "Do you need protection to start right now, today, before they're "
                    "notified? (This is a temporary order that lasts up to 14 days.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "wa.weapons_surrender" not in answers:
            return {
                "step": "wa.weapons_surrender",
                "prompt": (
                    "Do you want the judge to order them, right away, to give up any "
                    "firearms and weapons?"
                ),
                "schema": {"type": "boolean"},
            }
        if "wa.order_length" not in answers:
            return {
                "step": "wa.order_length",
                "prompt": (
                    "How long should the order last? In Washington it lasts at least a "
                    "year unless you ask for something different."
                ),
                "schema": {
                    "type": "string",
                    "enum": ["one_year", "more_than_one_year", "less_than_one_year"],
                },
            }
        if "wa.firearms_restoration_notice" not in answers:
            return {
                "step": "wa.firearms_restoration_notice",
                "prompt": (
                    "If they ever ask a court to give their firearms back, do you want to "
                    "be notified?"
                ),
                "schema": {"type": "string", "enum": ["notify", "do_not_notify"]},
            }
        if "wa.past_incidents" not in answers:
            return {
                "step": "wa.past_incidents",
                "prompt": (
                    "Is there anything from further back you want the judge to know? "
                    "You can skip this — what you've told me is enough."
                ),
                "schema": {"type": "string"},
            }
        if "wa.evidence_types" not in answers:
            return {
                "step": "wa.evidence_types",
                "prompt": (
                    "Do you have anything that backs this up? Pick any you have — "
                    "photos, messages, voicemails, notes, a police report."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "pictures",
                            "messages",
                            "voice_messages",
                            "written_notes",
                            "police_report",
                            "witness_statement",
                            "other",
                        ],
                    },
                },
            }

    # Virginia DC-383 — VA-specific fields: respondent description (DOB/race/sex),
    # the preliminary-order request, and the conditions requested. Maps in
    # vault.forms.va. DC-383 is a simpler form than CA's or WA's.
    if jurisdiction == "VA":
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The Virginia form has a description box. Their race or ethnicity, "
                    "if you know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "va.preliminary_order" not in answers:
            return {
                "step": "va.preliminary_order",
                "prompt": (
                    "Do you want protection to start right away, before the full hearing? "
                    "(Virginia calls this a preliminary protective order.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "va.conditions" not in answers:
            return {
                "step": "va.conditions",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_violence",  # prohibit acts of violence/force/threat
                            "no_contact",  # prohibit other contact with petitioner
                            "no_contact_family",  # prohibit contact with family/household
                            "companion_animal",  # possession of a companion animal
                            "other_conditions",  # such other conditions
                        ],
                    },
                },
            }
        va_conditions = answers.get("va.conditions", [])
        if "companion_animal" in va_conditions and "va.companion_animal" not in answers:
            return {
                "step": "va.companion_animal",
                "prompt": "Which pet do you want protected? A name and type is enough.",
                "schema": {"type": "string"},
            }
        if "other_conditions" in va_conditions and "va.other_conditions" not in answers:
            return {
                "step": "va.other_conditions",
                "prompt": "What other condition do you want the judge to consider?",
                "schema": {"type": "string"},
            }

    # Texas Application for Protective Order — TX's terms-and-conditions section
    # (item 8 a-n) plus ex parte, confidentiality, support, and children orders.
    # TX's terms are its own list, distinct from CA's and WA's. Maps in
    # vault.forms.tx.
    if jurisdiction == "TX":
        if "tx.terms" not in answers:
            return {
                "step": "tx.terms",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_family_violence",  # 8a
                            "no_sexual_assault",  # 8b
                            "no_threat_via_third_party",  # 8c
                            "no_harassing_communication",  # 8d
                            "no_communication",  # 8e
                            "no_go_within_distance",  # 8f
                            "no_go_near_residence_work_school",  # 8g
                            "no_go_near_childrens_school",  # 8h
                            "no_harassing_conduct",  # 8i
                            "suspend_handgun_license",  # 8j
                            "prohibit_firearm",  # 8k
                            "battering_program",  # 8l
                            "protect_pet",  # 8m
                            "other",  # 8n
                        ],
                    },
                },
            }
        tx_terms = answers.get("tx.terms", [])
        if any(
            t in tx_terms
            for t in (
                "no_go_within_distance",
                "no_go_near_residence_work_school",
                "no_go_near_childrens_school",
            )
        ):
            if "tx.stay_away_places" not in answers:
                return {
                    "step": "tx.stay_away_places",
                    "prompt": (
                        "For the stay-away order — who should be kept away from? "
                        "You, the children, other protected adults? Pick any."
                    ),
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["applicant", "children", "other_adults"],
                        },
                    },
                }
            if "tx.stay_away_distance_yards" not in answers:
                return {
                    "step": "tx.stay_away_distance_yards",
                    "prompt": (
                        "How many yards should they have to stay away? You can pick a "
                        "number that feels safe."
                    ),
                    "schema": {"type": "integer", "minimum": 1, "default": 200},
                }
        if "protect_pet" in tx_terms and "tx.pet" not in answers:
            return {
                "step": "tx.pet",
                "prompt": "Which pet or companion animal? A name and type is enough.",
                "schema": {"type": "string"},
            }
        if "other" in tx_terms and "tx.other_terms" not in answers:
            return {
                "step": "tx.other_terms",
                "prompt": "What other order would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        if (
            answers.get("relationship.live_together_now") is True
            or answers.get("relationship.lived_together_past") is True
        ) and "tx.exclusive_residence" not in answers:
            return {
                "step": "tx.exclusive_residence",
                "prompt": (
                    "Do you want the home to yourself, with them ordered to move out? "
                    "(You'd need to have lived there in the last 30 days.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "tx.ex_parte" not in answers:
            return {
                "step": "tx.ex_parte",
                "prompt": (
                    "Do you need protection to start right now, before a hearing? "
                    "(Texas calls this a temporary ex parte order.)"
                ),
                "schema": {"type": "boolean"},
            }
        if answers.get("relationship.type") == "married" and "tx.spousal_support" not in answers:
            return {
                "step": "tx.spousal_support",
                "prompt": "Would you like to ask the judge to order spousal support?",
                "schema": {"type": "boolean"},
            }
        if "tx.phone_transfer" not in answers:
            return {
                "step": "tx.phone_transfer",
                "prompt": (
                    "Do you want your (or your children's) phone numbers moved off their "
                    "account and into your name?"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("relationship.children_in_common") is True
            and "tx.children_orders" not in answers
        ):
            return {
                "step": "tx.children_orders",
                "prompt": (
                    "Anything about the children? Pick any: keep them from being taken, "
                    "a possession schedule, child support."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_removal_possession",
                            "no_removal_jurisdiction",
                            "possession_schedule",
                            "child_support",
                        ],
                    },
                },
            }
        if "tx.confidential" not in answers:
            return {
                "step": "tx.confidential",
                "prompt": (
                    "Do you want your address and phone kept off the order, so it stays "
                    "private? Most people in your situation do — I'd suggest yes."
                ),
                "schema": {"type": "boolean"},
            }

    # Pennsylvania Petition for Protection from Abuse (PFA) — defendant
    # identifiers and PA's A-P relief list. Maps in vault.forms.pa_pfa.
    if jurisdiction == "PA":
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The Pennsylvania form has a defendant description box. Their race, "
                    "if you know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "pa.relief" not in answers:
            return {
                "step": "pa.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "restrain_abuse",  # A
                            "evict",  # B
                            "other_housing",  # C
                            "custody",  # D
                            "no_contact",  # E
                            "no_contact_family",  # F
                            "relinquish_firearms",  # G
                            "prohibit_firearms",  # H
                            "support",  # I
                            "financial_losses",  # J
                            "pay_costs",  # K
                            "attorney_fees",  # L
                            "other",  # M
                            "court_discretion",  # N
                            "police_serve",  # O
                            "police_escort",  # P
                        ],
                    },
                },
            }
        pa_relief = answers.get("pa.relief", [])
        if "evict" in pa_relief and "pa.evict_residence" not in answers:
            return {
                "step": "pa.evict_residence",
                "prompt": "For the eviction order — what's the address of the home?",
                "schema": {"type": "string"},
            }
        if "custody" in pa_relief and "pa.custody_restrictions" not in answers:
            return {
                "step": "pa.custody_restrictions",
                "prompt": (
                    "For temporary custody — any limits you want on the other parent's "
                    "contact with the children? You can describe, or skip."
                ),
                "schema": {"type": "string"},
            }
        if "financial_losses" in pa_relief and "pa.financial_losses" not in answers:
            return {
                "step": "pa.financial_losses",
                "prompt": (
                    "What out-of-pocket losses did the abuse cause? List them with "
                    "amounts if you know."
                ),
                "schema": {"type": "string"},
            }
        if "other" in pa_relief and "pa.other_relief" not in answers:
            return {
                "step": "pa.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }

    # North Carolina Complaint for DV Protective Order (AOC-CV-303, G.S. 50B) —
    # county of residence and NC's 1-17 relief list. Maps in vault.forms.nc.
    if jurisdiction == "NC":
        if "nc.county" not in answers:
            return {
                "step": "nc.county",
                "prompt": "Which North Carolina county do you live in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "nc.relief" not in answers:
            return {
                "step": "nc.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "emergency",  # 1
                            "ex_parte",  # 2
                            "no_abuse",  # 3
                            "no_pet_abuse",  # 3a
                            "residence",  # 4
                            "eviction",  # 5
                            "personal_property",  # 6
                            "pet_custody",  # 6a
                            "stay_away",  # 7
                            "no_contact",  # 8
                            "vehicle",  # 9
                            "custody",  # 10
                            "child_support",  # 11
                            "prohibit_firearm",  # 12
                            "surrender_firearms",  # 13
                            "abuser_program",  # 14
                            "alternative_housing",  # 15
                            "spousal_support",  # 16
                            "other",  # 17
                        ],
                    },
                },
            }
        nc_relief = answers.get("nc.relief", [])
        if (
            "residence" in nc_relief or "eviction" in nc_relief
        ) and "nc.residence_address" not in answers:
            return {
                "step": "nc.residence_address",
                "prompt": "What's the address of the home?",
                "schema": {"type": "string"},
            }
        if "stay_away" in nc_relief and "nc.stay_away_places" not in answers:
            return {
                "step": "nc.stay_away_places",
                "prompt": (
                    "Which places should they be ordered to stay away from? Home, a "
                    "shelter, your work, the kids' school, daycare, your school? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "residence",
                            "shelter",
                            "work",
                            "childrens_school",
                            "daycare",
                            "my_school",
                            "other",
                        ],
                    },
                },
            }
        if "vehicle" in nc_relief and "nc.vehicle" not in answers:
            return {
                "step": "nc.vehicle",
                "prompt": "Which vehicle do you need? A description is enough.",
                "schema": {"type": "string"},
            }
        if "other" in nc_relief and "nc.other_relief" not in answers:
            return {
                "step": "nc.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }

    # New York Family Offense Petition (UCS-FC8-2, FCA 821) — county and the
    # item-10 relief list. The offense checklist (item 4) is a legal
    # characterization left to the attorney, not collected here. Maps in
    # vault.forms.ny.
    if jurisdiction == "NY":
        if "ny.county" not in answers:
            return {
                "step": "ny.county",
                "prompt": "Which New York county is the Family Court in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ny.relief" not in answers:
            return {
                "step": "ny.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stay_away",  # stay away from petitioner
                            "stay_away_home",  # stay away from home
                            "stay_away_work",  # stay away from workplace
                            "no_offense",  # do not menace/harass/assault
                            "no_contact",  # no communication / social media
                            "no_third_party",  # no third-party contact
                            "surrender_firearms",  # surrender firearms
                            "aggravated",  # finding of aggravated circumstances
                            "child_support",  # temporary child support
                            "spousal_support",  # temporary spousal support
                        ],
                    },
                },
            }

    # Massachusetts Chapter 209A Complaint for Protection from Abuse — defendant
    # identifiers (for the Defendant Information Form), the nature-of-abuse boxes,
    # and the request-for-relief list (which includes keeping the survivor's
    # address off the order). Maps in vault.forms.ma.
    if jurisdiction == "MA":
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The defendant information form has a description box. Their race, "
                    "if you know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "ma.abuse_types" not in answers:
            return {
                "step": "ma.abuse_types",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_harm",  # caused physical harm
                            "attempted_harm",  # attempted to cause physical harm
                            "fear_imminent",  # placed me in fear of imminent serious harm
                            "sexual_coercion",  # sexual relations by force/threat/duress
                            "coercive_control_child",  # harming a child/relative
                            "coercive_control_animal",  # abusing an animal
                            "coercive_control_images",  # publishing explicit images
                            "coercive_control_pattern",  # pattern of coercive behavior
                        ],
                    },
                },
            }
        if "ma.relief" not in answers:
            return {
                "step": "ma.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits. "
                    "If they're ordered to stay away from your home, work, or school, "
                    "those addresses can show on the order — you can also ask to keep "
                    "each one off it, and I'd suggest doing that."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stop_abusing",  # stop abusing me
                            "no_contact",  # no contact at all
                            "no_contact_except",  # no contact except as authorized
                            "leave_residence",  # leave/stay away from residence
                            "leave_workplace",  # leave/stay away from workplace
                            "leave_school",  # leave/stay away from school
                            "address_off_home",  # keep home address off the order
                            "address_off_work",  # keep work address off the order
                            "address_off_school",  # keep school address off the order
                            "compensation",  # pay compensation for losses
                            "child_support_alimony",  # temporary support/alimony
                            "custody",  # custody of children
                            "no_contact_children",  # no contact with children
                            "stay_away_children_school",  # stay away from children's school
                            "animal_protection",  # protect an animal
                            "animal_possession",  # possession of an animal
                            "other",  # other relief
                        ],
                    },
                },
            }
        ma_relief = answers.get("ma.relief", [])
        if "no_contact_except" in ma_relief and "ma.contact_methods" not in answers:
            return {
                "step": "ma.contact_methods",
                "prompt": (
                    "Which kinds of contact would be okay, if any? Phone, text, email, "
                    "or something else?"
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["phone", "text", "email", "other"]},
                },
            }
        if "compensation" in ma_relief and "ma.compensation" not in answers:
            return {
                "step": "ma.compensation",
                "prompt": (
                    "What losses did the abuse cause that you'd want paid back? "
                    "List them with amounts if you know."
                ),
                "schema": {"type": "string"},
            }
        if (
            "animal_protection" in ma_relief or "animal_possession" in ma_relief
        ) and "ma.animals" not in answers:
            return {
                "step": "ma.animals",
                "prompt": "Which animal(s)? A name and type is enough.",
                "schema": {"type": "string"},
            }
        if "other" in ma_relief and "ma.other_relief" not in answers:
            return {
                "step": "ma.other_relief",
                "prompt": "What other order would you like the judge to consider?",
                "schema": {"type": "string"},
            }

    requested_reliefs = answers.get("selected_reliefs_intents", [])
    if (
        jurisdiction in {"CA", "FL", "TX"}
        and ("child_support" in requested_reliefs or "spousal_support" in requested_reliefs)
        and "petitioner.ssn" not in answers
    ):
        return {
            "step": "petitioner.ssn",
            "prompt": (
                "Because you're asking the judge for support, the court needs your Social "
                "Security number. It's encrypted on our end — only used when the petition "
                "gets generated, and never shared anywhere else."
            ),
            "schema": {"type": "string", "pattern": r"^\d{3}-\d{2}-\d{4}$"},
        }

    return {"step": "done", "jurisdiction": jurisdiction}
