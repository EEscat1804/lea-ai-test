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
from collections.abc import Callable
from datetime import datetime
from typing import Any, ClassVar

from guardrails.contracts import FeatureResult
from guardrails.rules import RESP
from guardrails.session import SessionState
from lib.responses import json_response, problem_response

# Jurisdictions supported for the full Petition process
SUPPORTED_JURISDICTIONS = {
    "CA", "NY", "TX", "FL", "WA", "VA", "PA", "NC", "MA", "MD", "HI", "GA", "DE", "DC", "CT",
    "CO", "AR", "AK", "AL", "WY", "WI", "WV", "VT", "UT", "TN", "SD", "RI", "OR", "OK",
}
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
        "SC",
        # OK and TN are in the doc's Q41-43 list, but their actual AOC / OP forms have
        # no vehicle field — omitted so the vehicle gate doesn't ask for what the form
        # can't carry. See vault.forms.ok and vault.forms.tn.
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


class IntakeStateMachine:
    """OOP wrapper around the Vault intake state machine.

    `next_step` reproduces the documented pure-function contract
    `(jurisdiction, answers) -> next question`, dispatching each jurisdiction's
    block to a `_<xx>_step` method via `_STATE_STEPS`. Tier-1 and the shared
    Tier-2 gates stay shared methods; the SSN gate runs last, as before.
    Behavior is identical to the previous flat `determine_next_step`; the public
    function below delegates here so the call contract is unchanged.
    """

    def next_step(self, jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
        tier1 = self._tier1(jurisdiction, answers)
        if tier1 is not None:
            return tier1
        gated = self._shared_gates(jurisdiction, answers)
        if gated is not None:
            return gated
        handler = self._STATE_STEPS.get(jurisdiction)
        if handler is not None:
            state_step = handler(self, answers)
            if state_step is not None:
                return state_step
        ssn = self._ssn_gate(jurisdiction, answers)
        if ssn is not None:
            return ssn
        return {"step": "done", "jurisdiction": jurisdiction}

    def _tier1(self, jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    def _shared_gates(
        self, jurisdiction: str, answers: dict[str, Any]
    ) -> dict[str, Any] | None:
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
            jurisdiction
            in {"CA", "NY", "TX", "FL", "WA", "NC", "MA", "MD", "DE", "AR", "CT", "WI", "OR"}
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

        if (
            jurisdiction in {"CA", "FL", "WA", "WV"}
            and "petitioner.disability_accommodation" not in answers
        ):
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
                    "They're for the sheriff who delivers the papers, not for me, and "
                    "estimates are fine. About how tall?",
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
            jurisdiction in {"CA", "NY", "TX", "FL", "AR"}
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
        return None

    # Remaining CA-specific DV-100 fields the Tier-2 blocks above don't cover:
    # respondent identity (2b-2e), marriage status (3c), extra incidents (6-7),
    # protected-people detail (8), and the orders requested (10-28) with their
    # details. CA only today (the jurisdiction with petition mapping in
    # vault.forms.ca); other states follow when their form module lands.
    def _ca_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Washington PO 001 — WA-specific fields (items 3, 9, 12-17, 19-24). WA's
    # restraints (item 14) are its own list, distinct from CA's relief set. Maps
    # in vault.forms.wa. CA's analogous block is gated above; this is WA's.
    def _wa_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Virginia DC-383 — VA-specific fields: respondent description (DOB/race/sex),
    # the preliminary-order request, and the conditions requested. Maps in
    # vault.forms.va. DC-383 is a simpler form than CA's or WA's.
    def _va_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Texas Application for Protective Order — TX's terms-and-conditions section
    # (item 8 a-n) plus ex parte, confidentiality, support, and children orders.
    # TX's terms are its own list, distinct from CA's and WA's. Maps in
    # vault.forms.tx.
    def _tx_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Pennsylvania Petition for Protection from Abuse (PFA) — defendant
    # identifiers and PA's A-P relief list. Maps in vault.forms.pa_pfa.
    def _pa_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # North Carolina Complaint for DV Protective Order (AOC-CV-303, G.S. 50B) —
    # county of residence and NC's 1-17 relief list. Maps in vault.forms.nc.
    def _nc_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # New York Family Offense Petition (UCS-FC8-2, FCA 821) — county and the
    # item-10 relief list. The offense checklist (item 4) is a legal
    # characterization left to the attorney, not collected here. Maps in
    # vault.forms.ny.
    def _ny_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Massachusetts Chapter 209A Complaint for Protection from Abuse — defendant
    # identifiers (for the Defendant Information Form), the nature-of-abuse boxes,
    # and the request-for-relief list (which includes keeping the survivor's
    # address off the order). Maps in vault.forms.ma.
    def _ma_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    # Maryland Petition for Protection from Domestic Violence (CC-DC-DV-001,
    # FL § 4-504) — respondent description (for the CC-DC-DV-001A addendum), the
    # acts-of-abuse checklist, and the relief list. Maps in vault.forms.md.
    def _md_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "Maryland has a description addendum. Their race, if you know it "
                    "— or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "md.abuse_acts" not in answers:
            return {
                "step": "md.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "kicking",
                            "punching",
                            "choking_strangling",
                            "slapping",
                            "shooting",
                            "rape_sexual",
                            "hitting_object",
                            "stabbing",
                            "shoving",
                            "threats",
                            "mental_injury_child",
                            "detaining",
                            "stalking",
                            "biting",
                            "revenge_porn",
                            "other",
                        ],
                    },
                },
            }
        if "md.relief" not in answers:
            return {
                "step": "md.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits. "
                    "(You don't have to give an address if listing it would put you "
                    "at more risk.)"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # not to abuse or threaten
                            "no_contact",  # not to contact or harass
                            "stay_away_residence",  # not go to residence
                            "stay_away_school",  # not go to school
                            "stay_away_childcare",  # not go to child care
                            "stay_away_workplace",  # not go to workplace
                            "leave_home",  # leave the home / possession
                            "surrender_firearms",  # turn over firearms
                            "counseling",  # go to counseling
                            "emergency_maintenance",  # emergency family maintenance
                            "custody",  # custody of children
                            "vehicle",  # use/possession of vehicle
                            "pet_possession",  # temporary possession of pets
                            "other",  # additional relief
                        ],
                    },
                },
            }
        md_relief = answers.get("md.relief", [])
        if "other" in answers.get("md.abuse_acts", []) and "md.abuse_other" not in answers:
            return {
                "step": "md.abuse_other",
                "prompt": "You picked 'other' — can you say what happened in a few words?",
                "schema": {"type": "string"},
            }
        if "leave_home" in md_relief and "md.home_address" not in answers:
            return {
                "step": "md.home_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "counseling" in md_relief and "md.counseling_type" not in answers:
            return {
                "step": "md.counseling_type",
                "prompt": "What kind of counseling — domestic violence, drug/alcohol, or other?",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["domestic_violence", "drug_alcohol", "other"],
                    },
                },
            }
        if "vehicle" in md_relief and "md.vehicle" not in answers:
            return {
                "step": "md.vehicle",
                "prompt": "Which vehicle? A description is enough.",
                "schema": {"type": "string"},
            }
        if "pet_possession" in md_relief and "md.pets" not in answers:
            return {
                "step": "md.pets",
                "prompt": "Which pet(s)? A name and type is enough.",
                "schema": {"type": "string"},
            }
        if "other" in md_relief and "md.other_relief" not in answers:
            return {
                "step": "md.other_relief",
                "prompt": "What other order would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        return None

    # Hawai'i Petition for an Order for Protection (1F-P-752A, HRS ch. 586) —
    # the acts-of-abuse checklist, the harm-type classification, the section II
    # relief requests, and order duration. Maps in vault.forms.hi.
    def _hi_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "hi.abuse_acts" not in answers:
            return {
                "step": "hi.abuse_acts",
                "prompt": (
                    "Which of these describe what they did (or threatened)? Pick any "
                    "that fit — you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "choke",
                            "force_sex",
                            "grab",
                            "hit",
                            "kick",
                            "slap",
                            "punch",
                            "push",
                            "shove",
                            "other",
                        ],
                    },
                },
            }
        if "other" in answers.get("hi.abuse_acts", []) and "hi.abuse_other" not in answers:
            return {
                "step": "hi.abuse_other",
                "prompt": "You picked 'other' — can you say what happened in a few words?",
                "schema": {"type": "string"},
            }
        if "hi.harm_types" not in answers:
            return {
                "step": "hi.harm_types",
                "prompt": (
                    "And how would you describe the harm? Pick any that fit — physical "
                    "harm, a threat of harm, psychological abuse, property damage, or a "
                    "pattern of control."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_harm",
                            "threat_imminent",
                            "psychological",
                            "property_damage",
                            "coercive_control",
                        ],
                    },
                },
            }
        if "hi.relief" not in answers:
            return {
                "step": "hi.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_contact",  # no contact / threaten / abuse
                            "no_residence",  # not enter/visit residence
                            "no_property_damage",  # no property damage
                            "no_psych_abuse",  # no psychological abuse
                            "no_contact_work",  # no contact at workplace
                            "no_contact_children_school",  # no contact at children's school
                            "protect_animals",  # protect animals
                            "vacate",  # vacate residence
                            "custody_visitation",  # temporary custody/visitation
                            "no_visitation",  # prohibit visitation
                            "supervised_visitation",  # supervised visitation
                            "dv_intervention",  # DV intervention services
                        ],
                    },
                },
            }
        if "hi.duration" not in answers:
            return {
                "step": "hi.duration",
                "prompt": (
                    "How long should the protective order last? You can say something "
                    "like '6 months' or '1 year' — the judge can adjust it."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Georgia Petition for Family Violence Protective Order (SC-26, O.C.G.A.
    # § 19-13) — respondent identifiers (for the sealed fact sheet), county, and
    # GA's relief list (which includes keeping the address confidential). Maps in
    # vault.forms.ga.
    def _ga_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "Georgia has a sealed fact sheet for the police. Their race, if you "
                    "know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "ga.county" not in answers:
            return {
                "step": "ga.county",
                "prompt": "Which Georgia county do you live in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ga.relief" not in answers:
            return {
                "step": "ga.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits. "
                    "Keeping your address confidential is one of the options, and "
                    "I'd suggest it."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # stop abusing/harassing
                            "no_contact",  # no direct/indirect contact
                            "stay_away_distance",  # stay 100 yards away
                            "vacate",  # vacate residence
                            "exclusive_residence",  # exclusive use of residence
                            "pay_rent",  # pay rent/mortgage/utilities
                            "alternate_housing",  # provide alternate housing
                            "stay_away_places",  # stay away from residence/work/school
                            "custody",  # temporary custody
                            "no_visitation",  # limit/no visitation
                            "child_support",  # child support
                            "financial_support",  # financial support
                            "attorney_fees",  # costs and attorney's fees
                            "address_confidential",  # keep address confidential
                            "property_restraint",  # no disposing of property
                            "utility_insurance_restraint",  # no cutting utilities/insurance
                            "vehicle",  # exclusive use of vehicle
                            "remove_property",  # permission to remove property
                            "drug_evaluation",  # drug/alcohol evaluation
                            "fvip",  # family violence intervention program
                            "return_property",  # return property
                            "reimburse",  # reimburse damages/expenses
                            "additional",  # additional relief
                        ],
                    },
                },
            }
        ga_relief = answers.get("ga.relief", [])
        if (
            "vacate" in ga_relief or "exclusive_residence" in ga_relief
        ) and "ga.residence_address" not in answers:
            return {
                "step": "ga.residence_address",
                "prompt": "What's the address of the home?",
                "schema": {"type": "string"},
            }
        if "vehicle" in ga_relief and "ga.vehicle" not in answers:
            return {
                "step": "ga.vehicle",
                "prompt": "Which vehicle? Make, model, year if you know.",
                "schema": {"type": "string"},
            }
        if "return_property" in ga_relief and "ga.return_property_desc" not in answers:
            return {
                "step": "ga.return_property_desc",
                "prompt": "Which property do you want returned to you?",
                "schema": {"type": "string"},
            }
        if "additional" in ga_relief and "ga.other_relief" not in answers:
            return {
                "step": "ga.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        return None

    # West Virginia Domestic Violence Petition for Temporary Emergency Protective
    # (TEPO) Order (MDVTPET, W. Va. Code § 48-27) — respondent identifiers, county,
    # the item-8 acts checklist, the requested PO duration (with § 505 reasons),
    # and WV's permissive-relief list. WV's relief list is its own. Maps in
    # vault.forms.wv.
    def _wv_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The West Virginia form has a respondent description for the DV registry. "
                    "Their race, if you know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "wv.county" not in answers:
            return {
                "step": "wv.county",
                "prompt": "Which West Virginia county (Magistrate Court) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "wv.abuse_acts" not in answers:
            return {
                "step": "wv.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_harm",  # caused/attempted physical harm
                            "fear_physical_harm",  # in fear of physical harm
                            "fear_by_harassment",  # fear via harassment/stalking/psych abuse
                            "sexual_assault",  # sexually assaulted/abused
                            "held_confined",  # held/confined/detained/abducted
                        ],
                    },
                },
            }
        if "wv.po_duration" not in answers:
            return {
                "step": "wv.po_duration",
                "prompt": (
                    "After the hearing, how long would you like the protective order to last? "
                    "90 days, 180 days, one year, or longer than a year?"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["90_day", "180_day", "1_year", "longer_than_1_year"],
                },
            }
        if answers.get("wv.po_duration") in ("1_year", "longer_than_1_year") and (
            "wv.duration_reasons" not in answers
        ):
            return {
                "step": "wv.duration_reasons",
                "prompt": (
                    "For an order that long, the court looks at certain factors. Pick any "
                    "that are true — we can add detail later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "violated_prior_po",  # materially violated a prior PO
                            "two_plus_pos",  # 2+ POs in five years
                            "dv_conviction",  # conviction for DV battery/assault
                            "stalking_violation",  # § 61-2-9(a) violation
                            "totality",  # totality of the circumstances
                            "violated_existing_po",  # materially violated existing PO
                            "violated_divorce_order",  # violated PO in a final divorce order
                        ],
                    },
                },
            }
        if "wv.permissive_relief" not in answers:
            return {
                "step": "wv.permissive_relief",
                "prompt": (
                    "What else would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # 1 — refrain from abusing me/children
                            "no_enter_workplace",  # 2 — not enter school/business/work
                            "no_contact",  # 3 — refrain from contacting/harassing
                            "custody",  # 4 — temporary custody of children
                            "visitation_changes",  # 5 — changes in visitation
                            "le_accompany_children",  # LE accompany to get children
                            "le_enter_residence",  # consent for LE to enter shared residence
                        ],
                    },
                },
            }
        if (
            "visitation_changes" in answers.get("wv.permissive_relief", [])
            and "wv.visitation_detail" not in answers
        ):
            return {
                "step": "wv.visitation_detail",
                "prompt": "What changes to visitation would you want? Be specific.",
                "schema": {"type": "string"},
            }
        return None

    # Wisconsin Petition for TRO and/or Injunction Hearing (Domestic Abuse)
    # (CV-402, § 813.12 Wis. Stats.) — respondent identifiers, county, imminent
    # danger, and WI's relief (TRO items 1a-f, mirrored as injunction items 2a-f,
    # plus items 4-7). WI's relief list is its own. Maps in vault.forms.wi.
    def _wi_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The Wisconsin form has a respondent description. Their race, if you "
                    "know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "wi.county" not in answers:
            return {
                "step": "wi.county",
                "prompt": "Which Wisconsin county (Circuit Court) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "wi.imminent_danger" not in answers:
            return {
                "step": "wi.imminent_danger",
                "prompt": (
                    "Do you believe you're in immediate danger of physical harm? "
                    "(Wisconsin needs this for an emergency restraining order.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "wi.relief" not in answers:
            return {
                "step": "wi.relief",
                "prompt": (
                    "What would you like the judge to order the other person to do? Pick "
                    "whatever fits — this applies to both the emergency order and the "
                    "longer injunction."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # a — refrain from acts/threats of abuse
                            "avoid_residence",  # b — avoid the residence
                            "no_contact",  # c — avoid contacting
                            "no_pet_harm",  # d — not harm a household pet
                            "allow_pet_retrieval",  # e — allow retrieving a household pet
                            "other",  # f — other
                        ],
                    },
                },
            }
        if "other" in answers.get("wi.relief", []) and "wi.relief_other" not in answers:
            return {
                "step": "wi.relief_other",
                "prompt": "What other behavior do you want the judge to order them to stop?",
                "schema": {"type": "string"},
            }
        if "wi.injunction_duration" not in answers:
            return {
                "step": "wi.injunction_duration",
                "prompt": (
                    "A Wisconsin injunction lasts up to four years. Want a shorter period? "
                    "If so, how long? (Leave blank for four years.)"
                ),
                "schema": {"type": "string"},
            }
        if "wi.additional_requests" not in answers:
            return {
                "step": "wi.additional_requests",
                "prompt": (
                    "A few more options — pick any: move your phone numbers to you; a longer "
                    "order if there's serious risk of homicide or sexual assault; a permanent "
                    "order if they've been convicted of sexual assault against you; or have "
                    "the sheriff help you get back into your home."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "wireless_transfer",  # 4 — transfer phone numbers
                            "extended_10yr",  # 5 — up to 10 years (homicide/SA risk)
                            "permanent",  # 6 — permanent (SA conviction)
                            "sheriff_assist",  # 7 — sheriff assist with residence
                        ],
                    },
                },
            }
        return None

    # Wyoming Petition for Domestic Violence Order of Protection (PO DV Form 03,
    # W.S. § 35-21-101 to 112) — respondent identifiers, county/judicial district,
    # respondent probation, and WY's paragraph-11 relief list (A-T). WY's relief
    # list is its own. Maps in vault.forms.wy.
    def _wy_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The Wyoming form has a respondent description. Their race, if you "
                    "know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "wy.county" not in answers:
            return {
                "step": "wy.county",
                "prompt": "Which Wyoming county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "wy.judicial_district" not in answers:
            return {
                "step": "wy.judicial_district",
                "prompt": (
                    "Which judicial district is that? If you're not sure, you can skip it — "
                    "the clerk can fill it in."
                ),
                "schema": {"type": "string"},
            }
        if "wy.respondent_probation" not in answers:
            return {
                "step": "wy.respondent_probation",
                "prompt": "Is the other person on probation right now for domestic violence?",
                "schema": {"type": "boolean"},
            }
        if "wy.relief" not in answers:
            return {
                "step": "wy.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "personal_conduct",  # A
                            "no_contact",  # B
                            "medical_expenses",  # C
                            "stay_away",  # D
                            "no_guns",  # E
                            "property_no_disposal",  # F
                            "property_possession",  # G
                            "property_services",  # H
                            "alternative_housing",  # I
                            "pets",  # J
                            "transfer_wireless",  # K
                            "custody_visitation",  # L
                            "no_abduct",  # M
                            "no_alcohol_drugs",  # N
                            "supervised_visitation",  # O
                            "travel_restrictions",  # P
                            "support",  # Q
                            "attorney_fees",  # R
                            "appoint_attorney",  # S
                            "other_assistance",  # T
                        ],
                    },
                },
            }
        wy_relief = answers.get("wy.relief", [])
        if "stay_away" in wy_relief and "wy.stay_away_distance" not in answers:
            return {
                "step": "wy.stay_away_distance",
                "prompt": "How far should they have to stay from you? You can give a distance.",
                "schema": {"type": "string"},
            }
        if "stay_away" in wy_relief and "wy.stay_away_places" not in answers:
            return {
                "step": "wy.stay_away_places",
                "prompt": (
                    "Which places should they stay away from? Pick any — your home, work, "
                    "school, place of worship, and the same for your children."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "my_home",
                            "my_work",
                            "my_school",
                            "my_worship",
                            "children_home",
                            "children_work",
                            "children_school",
                            "children_worship",
                            "other",
                        ],
                    },
                },
            }
        if "property_possession" in wy_relief and "wy.property_possession_detail" not in answers:
            return {
                "step": "wy.property_possession_detail",
                "prompt": (
                    "Which home, vehicle, or essential belongings do you need sole use of? "
                    "List whatever matters."
                ),
                "schema": {"type": "string"},
            }
        if "pets" in wy_relief and "wy.pets_detail" not in answers:
            return {
                "step": "wy.pets_detail",
                "prompt": "Which household pet(s) need protecting? A name and description is enough.",
                "schema": {"type": "string"},
            }
        if "transfer_wireless" in wy_relief and "wy.wireless_numbers" not in answers:
            return {
                "step": "wy.wireless_numbers",
                "prompt": "Which wireless phone number(s) do you want transferred into your name?",
                "schema": {"type": "string"},
            }
        if "custody_visitation" in wy_relief and "wy.custody_to" not in answers:
            return {
                "step": "wy.custody_to",
                "prompt": (
                    "Who should have temporary custody of the children — you, or someone "
                    "else (name them)?"
                ),
                "schema": {"type": "string"},
            }
        if "custody_visitation" in wy_relief and "wy.visitation_terms" not in answers:
            return {
                "step": "wy.visitation_terms",
                "prompt": (
                    "What visitation (if any) should the other person have? You can leave "
                    "this blank."
                ),
                "schema": {"type": "string"},
            }
        if "supervised_visitation" in wy_relief and "wy.supervised_detail" not in answers:
            return {
                "step": "wy.supervised_detail",
                "prompt": (
                    "Who should supervise visitation? A name and phone number of the agency "
                    "or person."
                ),
                "schema": {"type": "string"},
            }
        if "support" in wy_relief and "wy.support_detail" not in answers:
            return {
                "step": "wy.support_detail",
                "prompt": (
                    "What support are you asking for — monthly child support, spousal "
                    "support, a share of childcare or medical costs? List what fits."
                ),
                "schema": {"type": "string"},
            }
        if "other_assistance" in wy_relief and "wy.other_assistance" not in answers:
            return {
                "step": "wy.other_assistance",
                "prompt": "What other help would protect you and your children?",
                "schema": {"type": "string"},
            }
        if "wy.appearance" not in answers:
            return {
                "step": "wy.appearance",
                "prompt": (
                    "For the hearing, would you rather appear in person at the courthouse, "
                    "or by phone/computer?"
                ),
                "schema": {"type": "string", "enum": ["in_person", "virtual"]},
            }
        return None

    # Alabama Petition for Protection from Abuse (Form C-2, Ala. Code § 30-5-1
    # et seq.) — the county, the request type, the section-II acts checklist, the
    # VII ex parte relief and VIII final relief lists. AL's acts and relief lists
    # are its own. Maps in vault.forms.al.
    def _al_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "al.county" not in answers:
            return {
                "step": "al.county",
                "prompt": "Which Alabama county (Circuit Court) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "al.request_type" not in answers:
            return {
                "step": "al.request_type",
                "prompt": (
                    "What are you asking for? A protection order, an emergency order, or a "
                    "change to an order you already have? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "protection_order",
                            "emergency_order",
                            "change_current_order",
                            "change_emergency_order",
                        ],
                    },
                },
            }
        if "al.abuse_acts" not in answers:
            return {
                "step": "al.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "threatened_confine",
                            "fear_serious_injury",
                            "sex_by_force",
                            "kidnapped",
                            "trespassed",
                            "tortured_child",
                            "stole",
                            "reckless_conduct",
                            "tortured_child_multiple",
                            "exposed_child_drugs",
                            "injured",
                            "tried_acts",
                            "threatened_injure",
                            "stalked",
                            "set_fire",
                            "restrained",
                            "other",
                        ],
                    },
                },
            }
        if "al.ex_parte_relief" not in answers:
            return {
                "step": "al.ex_parte_relief",
                "prompt": (
                    "What would you like the judge to order right away (before a hearing)? "
                    "Pick whatever fits — we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "enjoin_abuse",  # 1
                            "restrain_harass",  # 2
                            "no_contact_300ft",  # 3
                            "custody",  # 4
                            "no_interfere_removal",  # 5
                            "no_remove_children",  # 6
                            "exclude_residence",  # 7
                            "possession_auto_effects",  # 8
                            "prohibit_property_disposal",  # 9
                            "other_safety",  # 10
                        ],
                    },
                },
            }
        if "al.final_relief" not in answers:
            return {
                "step": "al.final_relief",
                "prompt": (
                    "And for the final hearing (a longer-term order), anything else? "
                    "Pick whatever fits."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "visitation",  # 11
                            "attorney_fees",  # 12
                            "possession_residence_evict",  # 13
                            "child_support",  # 14
                            "vehicle_possession",  # 15
                            "incorporate_order",  # 16
                            "surrender_firearms",  # 17
                            "le_accompany",  # 18
                            "other_final",  # 19
                        ],
                    },
                },
            }
        al_ex_parte = answers.get("al.ex_parte_relief", [])
        al_final = answers.get("al.final_relief", [])
        if (
            "exclude_residence" in al_ex_parte or "possession_residence_evict" in al_final
        ) and "al.residence_basis" not in answers:
            return {
                "step": "al.residence_basis",
                "prompt": (
                    "Who owns or rents the home you live in — you, them, or both of you? "
                    "And is it owned or rented?"
                ),
                "schema": {
                    "type": "string",
                    "enum": [
                        "owned_plaintiff",
                        "owned_defendant",
                        "owned_both",
                        "rented_plaintiff",
                        "rented_defendant",
                        "rented_both",
                    ],
                },
            }
        if "prohibit_property_disposal" in al_ex_parte and "al.property_description" not in answers:
            return {
                "step": "al.property_description",
                "prompt": "Which mutually owned or leased property do you want protected?",
                "schema": {"type": "string"},
            }
        if "other_safety" in al_ex_parte and "al.other_ex_parte" not in answers:
            return {
                "step": "al.other_ex_parte",
                "prompt": "What other safety relief would you like the judge to order right away?",
                "schema": {"type": "string"},
            }
        if "visitation" in al_final and "al.visitation_type" not in answers:
            return {
                "step": "al.visitation_type",
                "prompt": (
                    "For the children's visitation — do you want a visitation schedule, "
                    "no visitation, or supervised visitation?"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["visitation", "deny_visitation", "supervised"],
                },
            }
        if "visitation" in al_final and "al.visitation_terms" not in answers:
            return {
                "step": "al.visitation_terms",
                "prompt": "What visitation arrangement would you want? Be specific.",
                "schema": {"type": "string"},
            }
        if "vehicle_possession" in al_final and "al.vehicle_description" not in answers:
            return {
                "step": "al.vehicle_description",
                "prompt": "Which vehicle do you need? A description is enough.",
                "schema": {"type": "string"},
            }
        if "other_final" in al_final and "al.other_final" not in answers:
            return {
                "step": "al.other_final",
                "prompt": "What other relief would you like the judge to consider at the hearing?",
                "schema": {"type": "string"},
            }
        return None

    # Alaska Petition for Domestic Violence Protective Order (DV-100, AS
    # 18.66.100-.990) — court location, the 20-day/long-term order type, the
    # short-term (§5) and long-term (§6) protections, and law-enforcement
    # assistance (§9). AK's protection lists are its own. Maps in vault.forms.ak.
    def _ak_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": (
                    "Do you know the other person's date of birth? An estimate is okay, "
                    "or skip."
                ),
                "schema": {"type": "string"},
            }
        if "ak.court_location" not in answers:
            return {
                "step": "ak.court_location",
                "prompt": (
                    "Which Alaska court location will you file at — for example, Anchorage, "
                    "Fairbanks, or Juneau?"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "ak.order_type" not in answers:
            return {
                "step": "ak.order_type",
                "prompt": (
                    "What kind of order do you want? A 20-day emergency (ex parte) order "
                    "can start right away; a long-term order lasts a year after a hearing. "
                    "If you might need more than 20 days, pick both."
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["ex_parte", "long_term"]},
                },
            }
        if "ak.children_in_household" not in answers:
            return {
                "step": "ak.children_in_household",
                "prompt": "Are there children in your household?",
                "schema": {"type": "boolean"},
            }
        if "ak.protections" not in answers:
            return {
                "step": "ak.protections",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_dv",  # 5a — no DV/stalking/harassment
                            "no_contact",  # 5b — no contact
                            "stay_away_residence",  # 5c — stay away from where I live
                            "stay_away_locations",  # 5d — stay away from listed places
                            "no_vehicle_interference",  # 5e — not interfere with my vehicle
                            "no_controlled_substances",  # 5f — no controlled substances
                            "possession_residence",  # 5g(1) — possession of the residence
                            "possession_vehicle",  # 5g(2) — possession of the vehicle
                            "possession_personal_items",  # 5g(3) — essential personal items
                            "spousal_support",  # 5h — spousal support
                            "no_property_disposal",  # 5i — not sell/dispose of property
                            "other_short_term",  # 5j — other short-term protection
                        ],
                    },
                },
            }
        ak_protections = answers.get("ak.protections", [])
        if "no_contact" in ak_protections and "ak.contact_exceptions" not in answers:
            return {
                "step": "ak.contact_exceptions",
                "prompt": (
                    "Should any contact be allowed, and how — email, an attorney, a third "
                    "person? Leave blank for no contact at all."
                ),
                "schema": {"type": "string"},
            }
        if "stay_away_locations" in ak_protections and "ak.stay_away_locations" not in answers:
            return {
                "step": "ak.stay_away_locations",
                "prompt": (
                    "Which places should they stay away from — your school, your kids' "
                    "school, your job, somewhere else? Add how far, if you have a distance "
                    "in mind."
                ),
                "schema": {"type": "string"},
            }
        if "possession_residence" in ak_protections and "ak.residence_address" not in answers:
            return {
                "step": "ak.residence_address",
                "prompt": "What's the address of the residence you need possession of?",
                "schema": {"type": "string"},
            }
        if "possession_vehicle" in ak_protections and "ak.vehicle_description" not in answers:
            return {
                "step": "ak.vehicle_description",
                "prompt": "Which vehicle? A description and license plate, if you know it.",
                "schema": {"type": "string"},
            }
        if "possession_personal_items" in ak_protections and "ak.personal_items" not in answers:
            return {
                "step": "ak.personal_items",
                "prompt": (
                    "Which essential belongings do you need? List whatever matters — keys, "
                    "clothes, medicine, documents, pets, and so on."
                ),
                "schema": {"type": "string"},
            }
        if "spousal_support" in ak_protections and "ak.spousal_support" not in answers:
            return {
                "step": "ak.spousal_support",
                "prompt": "How much monthly spousal support are you asking for, and why is it needed?",
                "schema": {"type": "string"},
            }
        if "other_short_term" in ak_protections and "ak.other_short_term" not in answers:
            return {
                "step": "ak.other_short_term",
                "prompt": "What other short-term protection would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        ak_order_type = answers.get("ak.order_type", [])
        if "long_term" in ak_order_type and "ak.long_term_protections" not in answers:
            return {
                "step": "ak.long_term_protections",
                "prompt": (
                    "A long-term order can include a few more things. Pick any that fit "
                    "(these can't be in the 20-day order)."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_weapon",  # 6a — no deadly weapon/firearm
                            "surrender_firearm",  # 6b — surrender firearms
                            "pay_costs",  # 6c — pay filing costs/fees
                            "pay_expenses",  # 6d — pay expenses caused by the DV
                            "batterers_program",  # 6e — batterers' rehabilitation program
                            "substance_treatment",  # 6e — substance abuse treatment
                            "other_long_term",  # 6f — other long-term protection
                        ],
                    },
                },
            }
        ak_long = answers.get("ak.long_term_protections", [])
        if "pay_expenses" in ak_long and "ak.expenses" not in answers:
            return {
                "step": "ak.expenses",
                "prompt": (
                    "What expenses did the abuse cause that you'd want paid back — medical, "
                    "counseling, shelter, repairs? List them with amounts if you know."
                ),
                "schema": {"type": "string"},
            }
        if "other_long_term" in ak_long and "ak.other_long_term" not in answers:
            return {
                "step": "ak.other_long_term",
                "prompt": "What other long-term protection would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        if answers.get("ak.children_in_household") is True and "ak.custody" not in answers:
            return {
                "step": "ak.custody",
                "prompt": "Do you want temporary custody of the children?",
                "schema": {"type": "boolean"},
            }
        if answers.get("ak.children_in_household") is True and "ak.child_support" not in answers:
            return {
                "step": "ak.child_support",
                "prompt": "Do you want to ask the judge to order child support?",
                "schema": {"type": "boolean"},
            }
        if "ak.le_assistance" not in answers:
            return {
                "step": "ak.le_assistance",
                "prompt": (
                    "Do you want the court to order police to help with anything? Pick any: "
                    "taking back your home, vehicle, or belongings; helping with custody; or "
                    "going with them once to get their things."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "possession_residence",  # 9a
                            "possession_vehicle",  # 9b
                            "possession_personal_items",  # 9c
                            "child_custody_assist",  # 9d
                            "recover_items",  # 9e
                        ],
                    },
                },
            }
        return None

    # Arkansas Petition and Affidavit for an Order of Protection (A.C.A.
    # § 9-15-101 et seq.) — respondent identifiers, the county, and AR's item-8
    # ex parte order provisions. AR's relief list is its own. Maps in
    # vault.forms.ar.
    def _ar_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The Arkansas form has a respondent description for law enforcement. "
                    "Their race, if you know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "ar.county" not in answers:
            return {
                "step": "ar.county",
                "prompt": "Which Arkansas county (Circuit Court) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ar.relief" not in answers:
            return {
                "step": "ar.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "exclude_residence",  # exclude respondent from the residence
                            "exclude_workplace",  # exclude from work/school/other
                            "no_contact",  # prohibit contact (except conditions)
                            "no_phone_disconnect",  # not disconnect phone numbers
                            "custody",  # temporary custody of minor children
                            "child_support",  # require child support
                            "spousal_support",  # require spousal support
                            "exclude_address",  # exclude petitioner's address from notice
                            "pay_fees",  # filing/service/court costs/attorney fees
                        ],
                    },
                },
            }
        ar_relief = answers.get("ar.relief", [])
        if "exclude_residence" in ar_relief and "ar.residence_address" not in answers:
            return {
                "step": "ar.residence_address",
                "prompt": "What's the address of the home you want them excluded from?",
                "schema": {"type": "string"},
            }
        if "exclude_residence" in ar_relief and "ar.residence_owner" not in answers:
            return {
                "step": "ar.residence_owner",
                "prompt": (
                    "Who owns or rents that home — you, them, both of you, or neither?"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["petitioner", "respondent", "both", "neither"],
                },
            }
        if "exclude_workplace" in ar_relief and "ar.workplace" not in answers:
            return {
                "step": "ar.workplace",
                "prompt": (
                    "Which place of work, school, or other location should they be kept "
                    "from? Name and address."
                ),
                "schema": {"type": "string"},
            }
        if "no_contact" in ar_relief and "ar.contact_conditions" not in answers:
            return {
                "step": "ar.contact_conditions",
                "prompt": (
                    "Should any contact be allowed, and under what conditions? "
                    "Leave blank for no contact at all."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Colorado Complaint/Motion for Civil Protection Order (JDF 402, C.R.S.
    # § 13-14-101 et seq.) — the county, the statutory basis (item 1), imminent
    # danger (item 5), and CO's item-7 relief list (a-i). CO's basis and relief
    # lists are its own. Maps in vault.forms.co.
    def _co_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "co.county" not in answers:
            return {
                "step": "co.county",
                "prompt": "Which Colorado county do you live or work in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "co.basis" not in answers:
            return {
                "step": "co.basis",
                "prompt": (
                    "Which of these describe what you experienced? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "domestic_abuse",  # § 13-14-101(2)
                            "stalking",  # § 18-3-602
                            "sexual_assault",  # § 18-3-402(1)
                            "unlawful_sexual_contact",  # § 18-3-404
                            "elder_at_risk",  # § 26-3.1-101(1) and (7)
                            "physical_assault",  # physical assault, threat, or other
                        ],
                    },
                },
            }
        if "co.imminent_danger" not in answers:
            return {
                "step": "co.imminent_danger",
                "prompt": (
                    "Why do you feel you're in danger right now? Pick any that fit."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "harm_life_health",  # harm to life/health if not restrained
                            "harm_if_not_excluded",  # harm if not excluded from the home
                        ],
                    },
                },
            }
        if "co.relief" not in answers:
            return {
                "step": "co.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # 7a — refrain from contact/harass/injure/stalk/...
                            "no_contact",  # 7b — no contact at all
                            "limited_contact",  # 7b alt — limited contact (specify)
                            "exclude_home",  # 7c — excluded from my home
                            "stay_away",  # 7d — stay a set distance from places
                            "custody_no_contact_children",  # 7e — no contact + care/control
                            "custody_parenting_time",  # 7e alt — care/control + parenting time
                            "protect_animals",  # 7f — protect animals
                            "firearm_relinquish",  # 7g — no firearm + relinquish (DV order)
                            "no_interference",  # 7h — no interference at work/school
                            "other",  # 7i — other
                        ],
                    },
                },
            }
        co_relief = answers.get("co.relief", [])
        if "limited_contact" in co_relief and "co.limited_contact_terms" not in answers:
            return {
                "step": "co.limited_contact_terms",
                "prompt": "What limited contact would be okay, if any? Be specific.",
                "schema": {"type": "string"},
            }
        if "exclude_home" in co_relief and "co.home_address" not in answers:
            return {
                "step": "co.home_address",
                "prompt": "What's the address of the home you want them excluded from?",
                "schema": {"type": "string"},
            }
        if "stay_away" in co_relief and "co.stay_away_distance_yards" not in answers:
            return {
                "step": "co.stay_away_distance_yards",
                "prompt": (
                    "How far should they have to stay — in yards? You can pick a number "
                    "that feels safe."
                ),
                "schema": {"type": "integer", "minimum": 1, "default": 100},
            }
        if "stay_away" in co_relief and "co.stay_away_places" not in answers:
            return {
                "step": "co.stay_away_places",
                "prompt": (
                    "Which places should they stay away from? Home, work, school, "
                    "somewhere else? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["home", "work", "school", "other"],
                    },
                },
            }
        if "custody_parenting_time" in co_relief and "co.parenting_time_terms" not in answers:
            return {
                "step": "co.parenting_time_terms",
                "prompt": (
                    "What parenting-time and decision-making arrangement would you want "
                    "for the other parent? Be specific."
                ),
                "schema": {"type": "string"},
            }
        if "protect_animals" in co_relief and "co.animal_arrangements" not in answers:
            return {
                "step": "co.animal_arrangements",
                "prompt": (
                    "Which animal(s) need protecting, and what should happen with their "
                    "possession and care?"
                ),
                "schema": {"type": "string"},
            }
        if "other" in co_relief and "co.other_relief" not in answers:
            return {
                "step": "co.other_relief",
                "prompt": "What other relief would you like the court to consider?",
                "schema": {"type": "string"},
            }
        return None

    # Connecticut Application for Relief from Abuse (JD-FM-137, C.G.S. § 46b-15
    # et al.) — respondent identifiers, the judicial district, and CT's coded
    # relief conditions (CT01-CT31) plus custody/visitation and ex parte. CT's
    # relief list is its own. Maps in vault.forms.ct.
    def _ct_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The Connecticut form has a respondent description. Their race, if you "
                    "know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex/gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "ct.judicial_district" not in answers:
            return {
                "step": "ct.judicial_district",
                "prompt": "Which Connecticut judicial district (or court location) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ct.relief" not in answers:
            return {
                "step": "ct.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # CT01 — not assault/threaten/abuse/harass/follow/stalk
                            "stay_away_home",  # CT03 — stay away from home/residence
                            "no_contact",  # CT05 — no contact in any manner
                            "respondent_retrieve_belongings",  # CT14
                            "applicant_retrieve_belongings",  # CT15
                            "stay_100_yards",  # CT16 — stay 100 yards away
                            "protect_children",  # CT19 — order protect minor children
                            "protect_animals",  # CT31 — order protect animals
                            "custody",  # CT20 — temporary custody
                            "further_order",  # item 3 — further order
                        ],
                    },
                },
            }
        ct_relief = answers.get("ct.relief", [])
        if "custody" in ct_relief and "ct.visitation" not in answers:
            return {
                "step": "ct.visitation",
                "prompt": (
                    "For custody — do you want the other parent to have visitation on terms "
                    "you set, or no visitation at all?"
                ),
                "schema": {"type": "string", "enum": ["with_visitation", "without_visitation"]},
            }
        if (
            answers.get("ct.visitation") == "with_visitation"
            and "ct.visitation_terms" not in answers
        ):
            return {
                "step": "ct.visitation_terms",
                "prompt": "What visitation terms would you want?",
                "schema": {"type": "string"},
            }
        if "further_order" in ct_relief and "ct.further_order_detail" not in answers:
            return {
                "step": "ct.further_order_detail",
                "prompt": "What else would you like the court to order?",
                "schema": {"type": "string"},
            }
        if "ct.ex_parte" not in answers:
            return {
                "step": "ct.ex_parte",
                "prompt": (
                    "Do you need protection to start right now, before a hearing — because "
                    "there's an immediate and present danger? (Connecticut calls this ex "
                    "parte relief.)"
                ),
                "schema": {"type": "boolean"},
            }
        return None

    # Washington, D.C. Petition and Affidavit for Civil Protection Order (CPO,
    # D.C. Code § 16-1001 et seq.) — the DC nexus questions (the court's basis to
    # hear the case) and the item 1-16 relief list. DC's relief list is its own.
    # Maps in vault.forms.dc.
    def _dc_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "dc.petitioner_dc_nexus" not in answers:
            return {
                "step": "dc.petitioner_dc_nexus",
                "prompt": (
                    "Do you live, work, or go to school in Washington, D.C.? "
                    "(The court asks so it can make sure it's able to hear your case.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "dc.incident_in_dc" not in answers:
            return {
                "step": "dc.incident_in_dc",
                "prompt": "Did any of what happened take place in Washington, D.C.?",
                "schema": {"type": "boolean"},
            }
        if "dc.relief" not in answers:
            return {
                "step": "dc.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # 1 — not abuse/threaten/stalk/harass
                            "stay_away",  # 2 — stay away
                            "no_contact",  # 3 — no contact
                            "custody",  # 4 — temporary custody
                            "visitation",  # 5 — respondent visitation if protected
                            "child_support",  # 6 — child support (DC guideline)
                            "vacate",  # 7 — vacate the home
                            "spousal_support",  # 8 — financial assistance / spousal support
                            "property_possession",  # 9 — possession of jointly owned property
                            "health_insurance",  # 10 — no removal from health insurance
                            "reimburse",  # 11 — reimburse costs/damage
                            "counseling",  # 12 — counseling program
                            "police_assistance",  # 13 — order police to assist
                            "attorney_fees",  # 14 — attorney's fees and costs
                            "other",  # 15 — other relief
                            "emergency_tpo",  # 16 — emergency Temporary Protection Order
                        ],
                    },
                },
            }
        dc_relief = answers.get("dc.relief", [])
        if "stay_away" in dc_relief and "dc.stay_away_places" not in answers:
            return {
                "step": "dc.stay_away_places",
                "prompt": (
                    "For the stay-away order — what should they keep away from? "
                    "Pick any that matter."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "person",
                            "work",
                            "home",
                            "vehicle",
                            "childrens_school",
                            "other_places",
                            "other_persons",
                        ],
                    },
                },
            }
        dc_stay_away = answers.get("dc.stay_away_places", [])
        if "other_places" in dc_stay_away and "dc.stay_away_other_places" not in answers:
            return {
                "step": "dc.stay_away_other_places",
                "prompt": "Which other places do you want them to stay away from?",
                "schema": {"type": "string"},
            }
        if "other_persons" in dc_stay_away and "dc.stay_away_other_persons" not in answers:
            return {
                "step": "dc.stay_away_other_persons",
                "prompt": "Which other people should they stay away from? Names are enough.",
                "schema": {"type": "string"},
            }
        if "no_contact" in dc_relief and "dc.contact_methods" not in answers:
            return {
                "step": "dc.contact_methods",
                "prompt": (
                    "Which kinds of contact should be off limits? Phone, writing, "
                    "online/social media, or any contact at all? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["telephone", "writing", "electronic", "any_manner"],
                    },
                },
            }
        if "vacate" in dc_relief and "dc.vacate_home_basis" not in answers:
            return {
                "step": "dc.vacate_home_basis",
                "prompt": (
                    "For the order to make them leave the home — whose name is on the "
                    "lease or deed? Just you, the two of you together, or you with "
                    "someone else?"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["own_alone", "own_together", "own_with_other"],
                },
            }
        if "property_possession" in dc_relief and "dc.property_description" not in answers:
            return {
                "step": "dc.property_description",
                "prompt": "Which jointly owned property do you need? List whatever matters.",
                "schema": {"type": "string"},
            }
        if "reimburse" in dc_relief and "dc.damaged_property" not in answers:
            return {
                "step": "dc.damaged_property",
                "prompt": (
                    "What costs or damage do you want paid back — medical bills, damaged "
                    "property, other expenses? List them with amounts if you know."
                ),
                "schema": {"type": "string"},
            }
        if "counseling" in dc_relief and "dc.counseling_types" not in answers:
            return {
                "step": "dc.counseling_types",
                "prompt": (
                    "What kind of counseling should they be ordered into? Pick any: "
                    "alcohol, drugs, domestic violence, parenting, family violence."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "alcohol",
                            "drug",
                            "domestic_violence",
                            "parenting",
                            "family_violence",
                            "other",
                        ],
                    },
                },
            }
        if "police_assistance" in dc_relief and "dc.police_actions" not in answers:
            return {
                "step": "dc.police_actions",
                "prompt": (
                    "How should the police help? Pick any: stand by while they leave the "
                    "home, make sure they hand over keys, come with you to get your "
                    "belongings, or help deliver the court papers."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stand_by_vacate",
                            "turn_over_keys",
                            "recover_belongings",
                            "assist_service",
                        ],
                    },
                },
            }
        if "other" in dc_relief and "dc.other_relief" not in answers:
            return {
                "step": "dc.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        return None

    # Delaware Petition for Order of Protection from Abuse (Family Court Form 450,
    # 10 Del. C. § 1041 et seq.) — the county (DE has three), the respondent's DE
    # residency basis for jurisdiction, the acts-of-abuse checklist (a-k), and the
    # protective + ancillary relief list. DE's abuse and relief lists are its own.
    # Maps in vault.forms.de.
    def _de_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "de.county" not in answers:
            return {
                "step": "de.county",
                "prompt": "Which Delaware county will you file in?",
                "schema": {"type": "string", "enum": ["new_castle", "kent", "sussex"]},
            }
        if "de.respondent_is_de_resident" not in answers:
            return {
                "step": "de.respondent_is_de_resident",
                "prompt": (
                    "Does the other person live in Delaware? (The court asks so it can "
                    "make sure it's able to hear your case.)"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("de.respondent_is_de_resident") is False
            and "de.de_connection" not in answers
        ):
            return {
                "step": "de.de_connection",
                "prompt": (
                    "Since they don't live in Delaware — how is what happened connected to "
                    "Delaware? For example, did any of it happen here, or did they call, "
                    "text, or message you while you were in Delaware?"
                ),
                "schema": {"type": "string"},
            }
        if "de.abuse_acts" not in answers:
            return {
                "step": "de.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_injury",  # a — physical injury / sexual offense
                            "fear_of_injury",  # b — fear of physical injury / sexual offense
                            "property_damage",  # c — damage/take property, incl. legal docs
                            "alarming_conduct",  # d — alarming/distressing conduct
                            "trespassing",  # e — trespassing on property
                            "child_abuse",  # f — child abuse
                            "unlawful_imprisonment",  # g — imprisonment/kidnapping/coercion
                            "financial_dependency",  # h — economic abuse
                            "other_threatening",  # i — other threatening/harmful conduct
                            "animal_cruelty",  # j — injury/cruelty to a companion animal
                            "human_trafficking",  # k — human trafficking
                        ],
                    },
                },
            }
        if "de.relief" not in answers:
            return {
                "step": "de.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # prohibit any act of abuse
                            "stay_away",  # stay away from petitioner / home / work
                            "no_contact",  # no contact by any means
                            "exclusive_residence",  # exclusive use of the residence
                            "compensation",  # pay compensation for losses
                            "custody",  # temporary custody of the children
                            "child_support",  # temporary child support
                            "spousal_support",  # support for the petitioner
                            "reimburse_expenses",  # reimburse expenses/fees/costs
                            "personal_property",  # possession of personal property
                            "companion_animal",  # care/custody of a companion animal
                            "return_documents",  # return legal/financial documents
                            "dv_evaluation",  # DV treatment evaluation
                            "other",  # other relief
                        ],
                    },
                },
            }
        de_relief = answers.get("de.relief", [])
        if "stay_away" in de_relief and "de.stay_away_places" not in answers:
            return {
                "step": "de.stay_away_places",
                "prompt": (
                    "For the stay-away order — what should they keep away from? "
                    "You, your home, your workplace? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["petitioner", "home", "workplace", "other"],
                    },
                },
            }
        if (
            "other" in answers.get("de.stay_away_places", [])
            and "de.stay_away_other" not in answers
        ):
            return {
                "step": "de.stay_away_other",
                "prompt": "Which other place should they be ordered to stay away from?",
                "schema": {"type": "string"},
            }
        if "exclusive_residence" in de_relief and "de.residence_address" not in answers:
            return {
                "step": "de.residence_address",
                "prompt": "What's the address of the home you want for yourself?",
                "schema": {"type": "string"},
            }
        if "compensation" in de_relief and "de.compensation_losses" not in answers:
            return {
                "step": "de.compensation_losses",
                "prompt": (
                    "What losses did the abuse cause that you'd want paid back? "
                    "List them with amounts if you know."
                ),
                "schema": {"type": "string"},
            }
        if "reimburse_expenses" in de_relief and "de.reimburse_expenses" not in answers:
            return {
                "step": "de.reimburse_expenses",
                "prompt": "Which expenses, fees, or costs should they reimburse you for?",
                "schema": {"type": "string"},
            }
        if "personal_property" in de_relief and "de.personal_property" not in answers:
            return {
                "step": "de.personal_property",
                "prompt": (
                    "Which personal property do you need — a vehicle, keys, anything "
                    "else? List whatever matters."
                ),
                "schema": {"type": "string"},
            }
        if "companion_animal" in de_relief and "de.companion_animal" not in answers:
            return {
                "step": "de.companion_animal",
                "prompt": "Which companion animal? A name and type is enough.",
                "schema": {"type": "string"},
            }
        if "return_documents" in de_relief and "de.return_documents" not in answers:
            return {
                "step": "de.return_documents",
                "prompt": "Which legal or financial documents do you want returned?",
                "schema": {"type": "string"},
            }
        if "other" in de_relief and "de.other_relief" not in answers:
            return {
                "step": "de.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        if "de.extended_duration" not in answers:
            return {
                "step": "de.extended_duration",
                "prompt": (
                    "A Delaware protective order usually lasts up to two years. Do you "
                    "want to ask the judge to make it last longer — up to a permanent order?"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("de.extended_duration") is True
            and "de.aggravating_factors" not in answers
        ):
            return {
                "step": "de.aggravating_factors",
                "prompt": (
                    "To ask for longer protection, the court looks at certain factors. "
                    "Pick any that are true — you can add detail later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_injury_caused",  # 1 — physical/serious physical injury
                            "deadly_weapon",  # 2 — deadly weapon / dangerous instrument
                            "repeated_violations",  # 3 — repeated violations of prior orders
                            "prior_convictions",  # 4 — prior convictions for crimes against me
                            "family_exposure",  # 5 — exposed family/household to injury
                            "ongoing_danger",  # 6 — other acts of immediate/ongoing danger
                        ],
                    },
                },
            }
        return None

    # Utah Request for Protective Order (Utah Code 78B-7-601 et seq.; District
    # Court). The form has no printed form number. It carries a "Describe
    # Respondent" block (sex/race/DOB + the shared physical description),
    # respondent vehicle, a violent-past and probation/parole question, an item-6
    # imminent-fear declaration, and a large items 8-25 relief checklist (personal
    # conduct through guardian-ad-litem) with sub-detail. UT is in the shared
    # PHYSICAL_DESCRIPTION_STATES and VEHICLE_DESCRIPTION_STATES sets, so those
    # gates run above; this block adds the rest. UT's relief list is its own. Maps
    # in vault.forms.ut.
    def _ut_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": (
                    "The form asks for the other person's date of birth. "
                    "Write what you know — 'unknown' is fine if you don't."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "The form asks the other person's sex. What should it say?",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "It also asks their race. You can write what fits, or 'unknown.'"
                ),
                "schema": {"type": "string"},
            }
        if "ut.county" not in answers:
            return {
                "step": "ut.county",
                "prompt": (
                    "Which Utah county will you file in? (Usually the one you live in — "
                    "the court sorts out the district number.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "ut.respondent_violent_past" not in answers:
            return {
                "step": "ut.respondent_violent_past",
                "prompt": (
                    "Has the other person used weapons or been violent in the past? "
                    "'Don't know' is a real answer."
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("ut.respondent_violent_past") is True
            and "ut.respondent_violent_detail" not in answers
        ):
            return {
                "step": "ut.respondent_violent_detail",
                "prompt": "Can you describe that — what happened, and any weapons?",
                "schema": {"type": "string"},
            }
        if "ut.respondent_probation" not in answers:
            return {
                "step": "ut.respondent_probation",
                "prompt": "Is the other person on probation or parole, as far as you know?",
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("ut.respondent_probation") is True
            and "ut.respondent_probation_detail" not in answers
        ):
            return {
                "step": "ut.respondent_probation_detail",
                "prompt": (
                    "If you know it — the probation/parole agency, the officer's name, "
                    "and a phone number?"
                ),
                "schema": {"type": "string"},
            }
        if "ut.fear_imminent" not in answers:
            return {
                "step": "ut.fear_imminent",
                "prompt": (
                    "Apart from what you've already told me, are you afraid the other person "
                    "is likely to physically harm you very soon?"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("ut.fear_imminent") is True
            and "ut.fear_imminent_detail" not in answers
        ):
            return {
                "step": "ut.fear_imminent_detail",
                "prompt": (
                    "Tell me why, in your own words — what makes you afraid it'll happen soon?"
                ),
                "schema": {"type": "string"},
            }
        if "ut.relief" not in answers:
            return {
                "step": "ut.relief",
                "prompt": (
                    "Now the orders you'd like to ask the judge for. Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "personal_conduct",  # 8 — no violence/abuse
                            "no_contact",  # 9 — no contact in any way
                            "contact_mediation",  # 10 — contact only during mediation
                            "stay_away",  # 11 — stay away from places/people
                            "no_weapons",  # 12 — no guns/weapons
                            "property_control_petitioner",  # 13 — petitioner controls home/car
                            "property_control_services",  # 14 — no interfering with services
                            "no_harming_pets",  # 15 — no harming pets
                            "transfer_wireless",  # 16 — transfer wireless numbers
                            "custody",  # 17 — child custody & parent-time
                            "no_alcohol_drugs",  # 18 — no alcohol/drugs before visitation
                            "supervised_visitation",  # 19 — supervised parent-time
                            "travel_restrictions",  # 20 — no taking children out of UT
                            "support_expenses",  # 21 — child/spousal support & expenses
                            "other_assistance",  # 22 — other orders needed
                            "law_enforcement_assist",  # 23 — order to law enforcement
                            "investigate_child_abuse",  # 24 — refer to DCFS
                            "guardian_children",  # 25 — appoint guardian ad litem
                        ],
                    },
                },
            }
        ut_relief = answers.get("ut.relief", [])
        if "stay_away" in ut_relief and "ut.stay_away_distance" not in answers:
            return {
                "step": "ut.stay_away_distance",
                "prompt": (
                    "For the stay-away order — how far away should they have to keep from you? "
                    "Whatever distance you'd want is fine."
                ),
                "schema": {"type": "string"},
            }
        if "stay_away" in ut_relief and "ut.stay_away_locations" not in answers:
            return {
                "step": "ut.stay_away_locations",
                "prompt": (
                    "Which places should they stay away from? Pick any. (The court can't keep "
                    "them from a place you both work, go to school, or worship — but tell us "
                    "anyway and a judge will weigh it.)"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["home", "work", "school", "worship", "other"],
                    },
                },
            }
        if (
            "other" in answers.get("ut.stay_away_locations", [])
            and "ut.stay_away_other" not in answers
        ):
            return {
                "step": "ut.stay_away_other",
                "prompt": "Which other place should they be ordered to stay away from?",
                "schema": {"type": "string"},
            }
        if "no_weapons" in ut_relief and "ut.weapons_detail" not in answers:
            return {
                "step": "ut.weapons_detail",
                "prompt": (
                    "Are there particular weapons the order should name? "
                    "List any you know about, or skip."
                ),
                "schema": {"type": "string"},
            }
        if (
            "property_control_petitioner" in ut_relief
            and "ut.property_home_address" not in answers
        ):
            return {
                "step": "ut.property_home_address",
                "prompt": "What's the address of the home you want for yourself?",
                "schema": {"type": "string"},
            }
        if (
            "property_control_petitioner" in ut_relief
            and "ut.property_belongings" not in answers
        ):
            return {
                "step": "ut.property_belongings",
                "prompt": (
                    "Which car or essential belongings do you need control of? "
                    "List whatever matters."
                ),
                "schema": {"type": "string"},
            }
        if "custody" in ut_relief and "ut.custody_to" not in answers:
            return {
                "step": "ut.custody_to",
                "prompt": (
                    "Who should have temporary custody of the children — you, or someone else?"
                ),
                "schema": {"type": "string", "enum": ["petitioner", "other"]},
            }
        if answers.get("ut.custody_to") == "other" and "ut.custody_other_name" not in answers:
            return {
                "step": "ut.custody_other_name",
                "prompt": "Who is that person? A name is enough.",
                "schema": {"type": "string"},
            }
        if "custody" in ut_relief and "ut.parent_time" not in answers:
            return {
                "step": "ut.parent_time",
                "prompt": (
                    "What parent-time (visitation) should the other person get, if any? "
                    "Describe what you think is safe."
                ),
                "schema": {"type": "string"},
            }
        if (
            "supervised_visitation" in ut_relief
            and "ut.supervised_visitation_detail" not in answers
        ):
            return {
                "step": "ut.supervised_visitation_detail",
                "prompt": (
                    "Who should supervise the visits — an agency or a person? "
                    "A name and phone number, if you have them."
                ),
                "schema": {"type": "string"},
            }
        if "support_expenses" in ut_relief and "ut.support_types" not in answers:
            return {
                "step": "ut.support_types",
                "prompt": (
                    "Which kinds of support or expenses should the judge order? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "child_support",  # 21a
                            "spousal_support",  # 21b
                            "income_withholding",  # 21c
                            "childcare_half",  # 21d — 50% childcare
                            "medical_half",  # 21e — 50% medical
                            "abuse_medical",  # 21f — abuse-related medical costs
                        ],
                    },
                },
            }
        ut_support = answers.get("ut.support_types", [])
        if "child_support" in ut_support and "ut.child_support_amount" not in answers:
            return {
                "step": "ut.child_support_amount",
                "prompt": (
                    "How much monthly child support are you asking for, if you have a number?"
                ),
                "schema": {"type": "string"},
            }
        if "spousal_support" in ut_support and "ut.spousal_support_amount" not in answers:
            return {
                "step": "ut.spousal_support_amount",
                "prompt": "And how much monthly spousal support?",
                "schema": {"type": "string"},
            }
        if "transfer_wireless" in ut_relief and "ut.wireless_numbers" not in answers:
            return {
                "step": "ut.wireless_numbers",
                "prompt": (
                    "Which wireless phone number(s) should be transferred to you? "
                    "List the numbers the other person currently holds the account for."
                ),
                "schema": {"type": "string"},
            }
        if "law_enforcement_assist" in ut_relief and "ut.law_enforcement_tasks" not in answers:
            return {
                "step": "ut.law_enforcement_tasks",
                "prompt": (
                    "What should law enforcement help with? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "control_property",  # 23a
                            "obtain_custody",  # 23b
                            "remove_belongings",  # 23c
                        ],
                    },
                },
            }
        if "other_assistance" in ut_relief and "ut.other_assistance_detail" not in answers:
            return {
                "step": "ut.other_assistance_detail",
                "prompt": "What other orders would help keep you and others safe?",
                "schema": {"type": "string"},
            }
        return None

    # Vermont Complaint for Relief from Abuse (form 400-00150C, 15 V.S.A. § 1101
    # et seq.) — the Superior Court Family Division unit, the existing-proceedings
    # matrix, an acts-of-abuse checklist (item 1), and TWO distinct relief lists:
    # Emergency Relief and Final Order (which differ — Final adds living expenses,
    # child support, and pet possession; Emergency has pet no-cruelty instead). VT
    # has no physical/vehicle/interpreter/disability fields, so none of the shared
    # Tier-2 gates apply. VT's acts and relief lists are its own. Maps in
    # vault.forms.vt.
    def _vt_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "vt.unit" not in answers:
            return {
                "step": "vt.unit",
                "prompt": (
                    "Vermont's Family Division is organized by county. "
                    "Which one will you file in — usually the one you live in?"
                ),
                "schema": {
                    "type": "string",
                    "enum": [
                        "addison",
                        "bennington",
                        "caledonia",
                        "chittenden",
                        "essex",
                        "franklin",
                        "grand_isle",
                        "lamoille",
                        "orange",
                        "orleans",
                        "rutland",
                        "washington",
                        "windham",
                        "windsor",
                    ],
                },
            }
        if "vt.existing_proceedings" not in answers:
            return {
                "step": "vt.existing_proceedings",
                "prompt": (
                    "Are there any other court cases — open or finished — involving you, the "
                    "other person, or your children? Pick any that apply, or leave it empty."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "divorce_separation",
                            "civil_union_dissolution",
                            "relief_from_abuse",
                            "criminal",
                            "parentage",
                            "guardianship",
                            "juvenile_dcf",
                        ],
                    },
                },
            }
        if (
            answers.get("vt.existing_proceedings")
            and "vt.existing_proceedings_where" not in answers
        ):
            return {
                "step": "vt.existing_proceedings_where",
                "prompt": "Which state and county is that case (or those cases) in?",
                "schema": {"type": "string"},
            }
        if "vt.abuse_acts" not in answers:
            return {
                "step": "vt.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_harm",  # attempted to cause or caused physical harm
                            "fear_serious_harm",  # fear of imminent serious physical harm
                            "child_abuse",  # abused the child(ren) named above
                            "stalking",  # stalked (form cites 12 V.S.A. 5131(6))
                            "sexual_assault",  # sexually assaulted (form cites 15 V.S.A. 5131(5))
                        ],
                    },
                },
            }
        if "stalking" in answers.get("vt.abuse_acts", []) and "vt.stalking_dates" not in answers:
            return {
                "step": "vt.stalking_dates",
                "prompt": (
                    "For the stalking, the form asks for the dates it happened. "
                    "What dates do you remember? Anything you've got is fine."
                ),
                "schema": {"type": "string"},
            }
        children = answers.get("protected_persons.children[]")
        has_children = isinstance(children, str) and children.strip().lower() not in ("", "none")
        if has_children and "vt.includes_children" not in answers:
            return {
                "step": "vt.includes_children",
                "prompt": (
                    "Do you want the order to protect your children too, not just you?"
                ),
                "schema": {"type": "boolean"},
            }
        if "vt.defendant_incarcerated" not in answers:
            return {
                "step": "vt.defendant_incarcerated",
                "prompt": (
                    "Is the other person in jail or prison right now for a violent crime? "
                    "'Don't know' is a real answer — this just changes some timing."
                ),
                "schema": {"type": "boolean"},
            }
        if "vt.public_assistance" not in answers:
            return {
                "step": "vt.public_assistance",
                "prompt": (
                    "Has either of you ever received public assistance — like Reach Up, "
                    "SNAP, or Medicaid? The form asks."
                ),
                "schema": {"type": "string", "enum": ["plaintiff", "defendant", "neither"]},
            }
        if "vt.emergency_relief" not in answers:
            return {
                "step": "vt.emergency_relief",
                "prompt": (
                    "First, the emergency orders — what you'd want the judge to do right away, "
                    "before any hearing. Pick whatever fits; we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # not abuse + not interfere with personal liberty
                            "refrain_stalking_sa",  # refrain from stalking / sexually assaulting
                            "leave_residence",  # leave residence + sole possession to plaintiff
                            "parental_rights",  # temporary parental rights & responsibilities
                            "no_pet_cruelty",  # refrain from cruelly treating pets
                            "stay_away",  # remain a set distance away
                            "no_contact",  # may not contact in any way
                            "other",  # other emergency relief
                        ],
                    },
                },
            }
        if "vt.final_relief" not in answers:
            return {
                "step": "vt.final_relief",
                "prompt": (
                    "Now the final order — what you'd want after a hearing, for the longer "
                    "term. Pick whatever fits."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # not abuse + not interfere with personal liberty
                            "refrain_stalking_sa",  # refrain from stalking / sexually assaulting
                            "leave_residence",  # leave residence + sole possession to plaintiff
                            "parental_rights",  # temporary parental rights & responsibilities
                            "pet_possession",  # possession & control of pets to plaintiff
                            "stay_away",  # remain a set distance away
                            "no_contact",  # may not contact in any way
                            "living_expenses",  # temporary living expenses
                            "child_support",  # temporary child support
                            "other",  # other final relief
                        ],
                    },
                },
            }
        vt_emergency = answers.get("vt.emergency_relief", [])
        vt_final = answers.get("vt.final_relief", [])
        if (
            ("stay_away" in vt_emergency or "stay_away" in vt_final)
            and "vt.stay_away_distance" not in answers
        ):
            return {
                "step": "vt.stay_away_distance",
                "prompt": (
                    "For the stay-away order — how far away should they have to keep? "
                    "Courts often use a number of feet; whatever you'd want is fine."
                ),
                "schema": {"type": "string"},
            }
        if (
            ("leave_residence" in vt_emergency or "leave_residence" in vt_final)
            and "vt.residence_address" not in answers
        ):
            return {
                "step": "vt.residence_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if (
            ("leave_residence" in vt_emergency or "leave_residence" in vt_final)
            and "vt.residence_tenure" not in answers
        ):
            return {
                "step": "vt.residence_tenure",
                "prompt": "Is that home owned, or rented/leased?",
                "schema": {"type": "string", "enum": ["owned", "rented_leased"]},
            }
        if (
            ("leave_residence" in vt_emergency or "leave_residence" in vt_final)
            and "vt.residence_in_name" not in answers
        ):
            return {
                "step": "vt.residence_in_name",
                "prompt": "Whose name is it in?",
                "schema": {
                    "type": "string",
                    "enum": ["plaintiff", "defendant", "both", "other"],
                },
            }
        if "other" in vt_emergency and "vt.emergency_other" not in answers:
            return {
                "step": "vt.emergency_other",
                "prompt": "What other emergency relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        if "other" in vt_final and "vt.final_other" not in answers:
            return {
                "step": "vt.final_other",
                "prompt": "What other final relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        return None

    # South Dakota Petition and Affidavit for a Protection Order (Domestic Abuse)
    # (Form UJS-091A / -091AJ juvenile, SDCL ch. 25-10) — county, the acts-of-abuse
    # checklist, prior-PO and weapon history (yes/no/don't-know), and the items 1-11
    # relief list plus the ex-parte (immediate TPO) request. SD is in the shared
    # MINOR_FILING_STATES set (the form has a juvenile version + under-18 path) but
    # not the physical/vehicle sets (the form describes neither). SD's relief list
    # is its own. Maps in vault.forms.sd.
    def _sd_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "sd.county" not in answers:
            return {
                "step": "sd.county",
                "prompt": (
                    "Which South Dakota county will you file in? (Usually the one you live in.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "sd.existing_custody_order" not in answers:
            return {
                "step": "sd.existing_custody_order",
                "prompt": (
                    "Is there already a custody order — in South Dakota or any other state — "
                    "for your children with the other person?"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("sd.existing_custody_order") is True
            and "sd.custody_order_details" not in answers
        ):
            return {
                "step": "sd.custody_order_details",
                "prompt": "Which county and case number is that custody order, if you know it?",
                "schema": {"type": "string"},
            }
        if "sd.abuse_acts" not in answers:
            return {
                "step": "sd.abuse_acts",
                "prompt": (
                    "Which of these describe what happened? Pick any that fit — "
                    "you can choose more than one."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "caused_harm",  # caused physical harm / bodily injury
                            "attempted_harm",  # attempted to cause physical harm
                            "inflicted_fear",  # fear of imminent physical harm
                            "violated_po",  # violated a protection order
                            "followed",  # willfully/repeatedly followed (stalking)
                            "harassing_conduct",  # course of conduct that alarmed/harassed
                            "credible_threat",  # credible threat of death/great bodily injury
                            "harassing_communication",  # repeated harassing communication
                            "crime_of_violence",  # committed a crime of violence
                        ],
                    },
                },
            }
        if "sd.respondent_arrested" not in answers:
            return {
                "step": "sd.respondent_arrested",
                "prompt": "Was the other person arrested for this incident?",
                "schema": {"type": "string", "enum": ["yes", "no", "dont_know"]},
            }
        if "sd.respondent_in_jail" not in answers:
            return {
                "step": "sd.respondent_in_jail",
                "prompt": "As far as you know, is the other person in jail right now?",
                "schema": {"type": "string", "enum": ["yes", "no", "dont_know"]},
            }
        if "sd.respondent_violated_po" not in answers:
            return {
                "step": "sd.respondent_violated_po",
                "prompt": "Has the other person ever violated a protection order?",
                "schema": {"type": "string", "enum": ["yes", "no", "dont_know"]},
            }
        if (
            answers.get("sd.respondent_violated_po") == "yes"
            and "sd.violated_po_whom" not in answers
        ):
            return {
                "step": "sd.violated_po_whom",
                "prompt": "Who was that protection order protecting?",
                "schema": {"type": "string"},
            }
        if "sd.respondent_convicted_po" not in answers:
            return {
                "step": "sd.respondent_convicted_po",
                "prompt": (
                    "Has the other person ever been found guilty of violating a protection order?"
                ),
                "schema": {"type": "string", "enum": ["yes", "no", "dont_know"]},
            }
        if (
            answers.get("sd.respondent_convicted_po") == "yes"
            and "sd.convicted_po_details" not in answers
        ):
            return {
                "step": "sd.convicted_po_details",
                "prompt": (
                    "If you know it — who it protected, the date of the conviction, and the "
                    "county and state?"
                ),
                "schema": {"type": "string"},
            }
        if "sd.respondent_threatened_weapon" not in answers:
            return {
                "step": "sd.respondent_threatened_weapon",
                "prompt": "Has the other person ever threatened anyone with a weapon?",
                "schema": {"type": "string", "enum": ["yes", "no", "dont_know"]},
            }
        if "sd.relief" not in answers:
            return {
                "step": "sd.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "restrain_abuse",  # 1 — restrain from abuse/threats/stalking
                            "set_duration",  # 2 — order for a period (up to 5 years)
                            "exclude_residence",  # 3 — exclude respondent from residence
                            "stay_away",  # 4 — stay-away distance from persons/places
                            "custody",  # 5 — temporary custody of children
                            "visitation",  # 6 — temporary visitation for respondent
                            "support",  # 7 — child/spousal support
                            "parenting_classes",  # 8 — parenting classes (SDCL 25-10-5)
                            "counseling",  # 9 — respondent obtain counseling
                            "no_contact",  # 10 — no contact, direct or indirect
                            "other",  # 11 — other relief
                        ],
                    },
                },
            }
        sd_relief = answers.get("sd.relief", [])
        if "set_duration" in sd_relief and "sd.duration" not in answers:
            return {
                "step": "sd.duration",
                "prompt": (
                    "How long would you like the order to last? South Dakota allows up to "
                    "five years."
                ),
                "schema": {"type": "string"},
            }
        if "exclude_residence" in sd_relief and "sd.residence_address" not in answers:
            return {
                "step": "sd.residence_address",
                "prompt": (
                    "What's the address of the residence you want the other person kept out of?"
                ),
                "schema": {"type": "string"},
            }
        if "stay_away" in sd_relief and "sd.stay_away_distance" not in answers:
            return {
                "step": "sd.stay_away_distance",
                "prompt": (
                    "For the stay-away order — how far away should they have to keep? "
                    "Whatever distance you'd want is fine."
                ),
                "schema": {"type": "string"},
            }
        if "stay_away" in sd_relief and "sd.stay_away_targets" not in answers:
            return {
                "step": "sd.stay_away_targets",
                "prompt": "What should they stay away from? Pick any.",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["petitioner", "children", "residence", "employment", "other"],
                    },
                },
            }
        if (
            "other" in answers.get("sd.stay_away_targets", [])
            and "sd.stay_away_other" not in answers
        ):
            return {
                "step": "sd.stay_away_other",
                "prompt": "Which other place should they be ordered to stay away from?",
                "schema": {"type": "string"},
            }
        if "visitation" in sd_relief and "sd.visitation_detail" not in answers:
            return {
                "step": "sd.visitation_detail",
                "prompt": (
                    "What visitation should the other person get, if any? Describe what you "
                    "think is safe — supervised, an existing order, or something else."
                ),
                "schema": {"type": "string"},
            }
        if "support" in sd_relief and "sd.support_types" not in answers:
            return {
                "step": "sd.support_types",
                "prompt": "Which kind of support should the judge order? Pick any.",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["child_support", "spousal_support"],
                    },
                },
            }
        sd_support = answers.get("sd.support_types", [])
        if "child_support" in sd_support and "sd.child_support_amount" not in answers:
            return {
                "step": "sd.child_support_amount",
                "prompt": (
                    "How much monthly child support are you asking for, if you have a number?"
                ),
                "schema": {"type": "string"},
            }
        if "spousal_support" in sd_support and "sd.spousal_support_amount" not in answers:
            return {
                "step": "sd.spousal_support_amount",
                "prompt": "And how much monthly spousal support?",
                "schema": {"type": "string"},
            }
        if "counseling" in sd_relief and "sd.counseling_detail" not in answers:
            return {
                "step": "sd.counseling_detail",
                "prompt": "What kind of counseling should the other person be ordered to get?",
                "schema": {"type": "string"},
            }
        if "other" in sd_relief and "sd.other_relief" not in answers:
            return {
                "step": "sd.other_relief",
                "prompt": "What other relief would help keep you and others safe?",
                "schema": {"type": "string"},
            }
        if "sd.ex_parte" not in answers:
            return {
                "step": "sd.ex_parte",
                "prompt": (
                    "Do you want to ask for an immediate temporary order now, before any "
                    "hearing and without notice to the other person?"
                ),
                "schema": {"type": "boolean"},
            }
        if answers.get("sd.ex_parte") is True and "sd.ex_parte_reasons" not in answers:
            return {
                "step": "sd.ex_parte_reasons",
                "prompt": (
                    "Why do you need protection right now, before a hearing? What immediate "
                    "harm are you worried about if you have to wait?"
                ),
                "schema": {"type": "string"},
            }
        return None

    # Tennessee Petition for Order of Protection and Order for Hearing (Form
    # #OP2018-1, TCA § 36-3-601 et seq.) — county, the describe-respondent identity
    # (sex/race/DOB on top of the shared physical block), and TN's items 7-19
    # relief checklist with sub-detail, plus the ex-parte (TPO) request. TN is in
    # the shared PHYSICAL_DESCRIPTION_STATES and MINOR_FILING_STATES sets (both
    # match the form); it was omitted from VEHICLE_DESCRIPTION_STATES (the form has
    # no vehicle field). TN's relief list is its own. Maps in vault.forms.tn.
    def _tn_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "The form asks the other person's sex. What should it say?",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": "It also asks their race. You can write what fits, or skip.",
                "schema": {"type": "string"},
            }
        if "tn.county" not in answers:
            return {
                "step": "tn.county",
                "prompt": (
                    "Which Tennessee county will you file in? (Usually the one you live in.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "tn.relief" not in answers:
            return {
                "step": "tn.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_contact",  # 7 — no contact
                            "stay_away",  # 8 — stay away from places
                            "personal_conduct",  # 9 — no property damage / harming animals
                            "temporary_custody",  # 10 — temporary custody of children
                            "child_support",  # 11 — reasonable child support
                            "spousal_support",  # 12 — spousal support (if married)
                            "move_out",  # 13 — move out / provide other housing
                            "counseling",  # 14 — batterers' / counseling program
                            "no_firearms",  # 15 — no firearms
                            "animals",  # 16 — custody/control of animals
                            "costs_fees",  # 17 — costs, fees, litigation taxes
                            "transfer_wireless",  # 18 — transfer wireless number(s)
                            "other",  # 19 — other orders (general relief)
                        ],
                    },
                },
            }
        tn_relief = answers.get("tn.relief", [])
        if "no_contact" in tn_relief and "tn.no_contact_who" not in answers:
            return {
                "step": "tn.no_contact_who",
                "prompt": "Who should the no-contact order cover? Pick any.",
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["me", "children"]},
                },
            }
        if "stay_away" in tn_relief and "tn.stay_away_places" not in answers:
            return {
                "step": "tn.stay_away_places",
                "prompt": (
                    "For the stay-away order — what should they keep away from? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["home", "workplace", "anywhere"],
                    },
                },
            }
        if "personal_conduct" in tn_relief and "tn.personal_conduct_types" not in answers:
            return {
                "step": "tn.personal_conduct_types",
                "prompt": (
                    "Which of these should the personal-conduct order include? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["property_utilities", "animals"],
                    },
                },
            }
        if "move_out" in tn_relief and "tn.move_out_choice" not in answers:
            return {
                "step": "tn.move_out_choice",
                "prompt": (
                    "For the housing order — should they move out of the home, or provide "
                    "you other suitable housing (if you're married)?"
                ),
                "schema": {"type": "string", "enum": ["move_out", "provide_housing"]},
            }
        if "transfer_wireless" in tn_relief and "tn.wireless_numbers" not in answers:
            return {
                "step": "tn.wireless_numbers",
                "prompt": (
                    "Which wireless phone number(s) should be transferred to you? "
                    "List the numbers the other person currently holds the account for."
                ),
                "schema": {"type": "string"},
            }
        if "other" in tn_relief and "tn.other_relief" not in answers:
            return {
                "step": "tn.other_relief",
                "prompt": "What other orders would help keep you and others safe?",
                "schema": {"type": "string"},
            }
        if "tn.ex_parte" not in answers:
            return {
                "step": "tn.ex_parte",
                "prompt": (
                    "Do you want to ask for an immediate temporary order now, before any "
                    "hearing? (In Tennessee that's an Ex Parte Order of Protection.)"
                ),
                "schema": {"type": "boolean"},
            }
        return None

    # Florida Petition for Injunction for Protection Against Domestic Violence
    # (Fla. Sup. Ct. Approved Family Law Form 12.980(a), Fla. Stat. § 741.30) —
    # the county/circuit to file in and the relief requested. FL's earlier Tier-2
    # blocks (race, gender, interpreter, disability, physical description,
    # vehicle, employer + hours, law-enforcement/military, prior criminal) are
    # gated above; this is FL's relief list, its own set. Maps in vault.forms.fl.
    def _fl_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "fl.county" not in answers:
            return {
                "step": "fl.county",
                "prompt": "Which Florida county will you file in? (Usually the one you live in.)",
                "schema": {"type": "string", "minLength": 1},
            }
        if "fl.relief" not in answers:
            return {
                "step": "fl.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_dv",  # not commit any acts of domestic violence
                            "no_contact",  # no contact, directly or indirectly
                            "exclusive_residence",  # exclusive use of dwelling / vacate
                            "parenting_plan",  # temporary parenting plan / timesharing
                            "child_support",  # temporary child support
                            "spousal_support",  # temporary support for the petitioner
                            "batterers_program",  # complete a batterers' intervention program
                            "surrender_firearms",  # surrender firearms and ammunition
                            "other",  # other relief the court deems necessary
                        ],
                    },
                },
            }
        fl_relief = answers.get("fl.relief", [])
        if "exclusive_residence" in fl_relief and "fl.residence_address" not in answers:
            return {
                "step": "fl.residence_address",
                "prompt": "What's the address of the home you share (or shared) with them?",
                "schema": {"type": "string"},
            }
        if "other" in fl_relief and "fl.other_relief" not in answers:
            return {
                "step": "fl.other_relief",
                "prompt": "What other relief would you like the judge to consider?",
                "schema": {"type": "string"},
            }
        return None

    # Rhode Island Complaint for an Order of Protection (FC-79, Family Court) —
    # the county and case type, the defendant's DOB, RI's §7 abuse checklist and
    # its relief list, plus the motion for an immediate ex parte order. RI's abuse
    # and relief lists are its own. FC-79 has no respondent-description or vehicle
    # block, so RI is NOT in PHYSICAL_DESCRIPTION_STATES/VEHICLE_DESCRIPTION_STATES.
    # Maps in vault.forms.ri.
    def _ri_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "ri.county" not in answers:
            return {
                "step": "ri.county",
                "prompt": (
                    "Which Rhode Island Family Court division will you file in? "
                    "(Usually the county where you live.)"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["Newport", "Washington", "Kent", "Providence/Bristol"],
                },
            }
        if "ri.case_type" not in answers:
            return {
                "step": "ri.case_type",
                "prompt": (
                    "What kind of protection is this about? Pick whatever fits — "
                    "we can adjust it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "domestic_abuse",
                            "sexual_exploitation",
                            "sexual_abuse",
                            "domestic_abuse_juvenile",
                        ],
                    },
                },
            }
        if "ri.former_residence" not in answers:
            return {
                "step": "ri.former_residence",
                "prompt": (
                    "Is there a home you've left to get away from them? If so, what was the "
                    "address? You can skip this — it's only if it helps your case."
                ),
                "schema": {"type": "string"},
            }
        if "ri.abuse_types" not in answers:
            return {
                "step": "ri.abuse_types",
                "prompt": (
                    "Which of these describes what happened? Pick any that fit — "
                    "you don't have to relive the details, just check what's true."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "weapon",  # threatened/harmed with a weapon
                            "attempted_harm",  # attempted physical harm
                            "caused_harm",  # caused physical harm
                            "fear_imminent",  # placed in fear of imminent harm
                            "sexual_force",  # involuntary sexual relations by force
                            "attempted_sexual",  # attempted involuntary sexual relations
                            "stalking",  # stalked / cyberstalked / harassed
                            "sexual_exploitation",  # sexually exploited / trafficked children
                        ],
                    },
                },
            }
        if "weapon" in answers.get("ri.abuse_types", []) and "ri.weapon_detail" not in answers:
            return {
                "step": "ri.weapon_detail",
                "prompt": "What was the weapon?",
                "schema": {"type": "string"},
            }
        if "ri.relief" not in answers:
            return {
                "step": "ri.relief",
                "prompt": (
                    "What would you like the court to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_contact",  # restrain / enjoin from contact
                            "surrender_firearms",  # surrender all firearms (72 hours)
                            "vacate",  # vacate / remain out of household
                            "no_utility_disruption",  # no terminating utility service
                            "custody",  # temporary custody of minor children
                            "child_support",  # child support (up to 90 days)
                            "pets",  # safety/welfare of household animals
                        ],
                    },
                },
            }
        ri_relief = answers.get("ri.relief", [])
        if "vacate" in ri_relief and "ri.vacate_address" not in answers:
            return {
                "step": "ri.vacate_address",
                "prompt": "What's the address of the home you want them to leave?",
                "schema": {"type": "string"},
            }
        if "custody" in ri_relief and "ri.custody_children" not in answers:
            return {
                "step": "ri.custody_children",
                "prompt": (
                    "Which children should the temporary-custody order cover? "
                    "A first name and age for each is enough."
                ),
                "schema": {"type": "string"},
            }
        if "pets" in ri_relief and "ri.pets_detail" not in answers:
            return {
                "step": "ri.pets_detail",
                "prompt": (
                    "Tell me about the animals you want protected — "
                    "a name and type is enough."
                ),
                "schema": {"type": "string"},
            }
        if "ri.ex_parte" not in answers:
            return {
                "step": "ri.ex_parte",
                "prompt": (
                    "Do you want to ask for an immediate temporary order now, before any "
                    "hearing? (In Rhode Island that's a Temporary Ex Parte Order of Protection, "
                    "and the court sets a hearing within 21 days.)"
                ),
                "schema": {"type": "boolean"},
            }
        return None

    # Oregon FAPA Petition for Restraining Order to Prevent Abuse (ORS 107.700,
    # Circuit Court) — the county, the defendant's DOB (the form needs the
    # respondent's age), OR's §4 abuse grounds (within the past 180 days), the §6
    # imminent-danger declaration, and OR's discretionary relief (firearms,
    # move-out, emergency money, animals, custody assistance). OR's abuse and
    # relief lists are its own. The FAPA petition has no respondent-description or
    # vehicle block, so OR is NOT in PHYSICAL_DESCRIPTION_STATES/
    # VEHICLE_DESCRIPTION_STATES; it IS in the interpreter set. Maps in
    # vault.forms.oregon (named `oregon`, not `or`, since `or` is a keyword).
    def _or_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "or.county" not in answers:
            return {
                "step": "or.county",
                "prompt": (
                    "Which Oregon county will you file in? (Usually the county where you live.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "or.abuse_types" not in answers:
            return {
                "step": "or.abuse_types",
                "prompt": (
                    "Has any of this happened in about the last six months? Pick any that "
                    "fit — you don't have to relive the details, just check what's true."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_injury",  # caused me physical injury
                            "attempted_injury",  # tried to cause physical injury
                            "fear_imminent",  # made me fear imminent injury
                            "sexual_force",  # sexual relations against my will by force/threat
                        ],
                    },
                },
            }
        if "or.imminent_danger" not in answers:
            return {
                "step": "or.imminent_danger",
                "prompt": (
                    "Oregon asks whether you're in danger of being hurt again soon. "
                    "Do you feel that you are?"
                ),
                "schema": {"type": "boolean"},
            }
        if (
            answers.get("or.imminent_danger") is True
            and "or.imminent_danger_explain" not in answers
        ):
            return {
                "step": "or.imminent_danger_explain",
                "prompt": (
                    "What makes you afraid they'll hurt you again soon? A sentence or two "
                    "in your own words is enough."
                ),
                "schema": {"type": "string"},
            }
        if "or.relief" not in answers:
            return {
                "step": "or.relief",
                "prompt": (
                    "What would you like the court to order, beyond telling them to stop? "
                    "Pick whatever fits — there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "firearms_prohibit",  # 7 — no firearms / ammunition
                            "move_out",  # 10 — move out of the residence
                            "emergency_money",  # 11 — one-time emergency payment
                            "animals",  # 12 — award companion/service animals
                            "custody_assistance",  # 19 — peace-officer help with custody
                        ],
                    },
                },
            }
        or_relief = answers.get("or.relief", [])
        if "move_out" in or_relief and "or.move_out_basis" not in answers:
            return {
                "step": "or.move_out_basis",
                "prompt": (
                    "For the move-out order — which of these are true about the home? Pick any."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["sole_name", "joint_own", "joint_lease", "spouse_rdp"],
                    },
                },
            }
        if "emergency_money" in or_relief and "or.emergency_amount" not in answers:
            return {
                "step": "or.emergency_amount",
                "prompt": (
                    "For the emergency money — what one-time amount would you ask them to pay?"
                ),
                "schema": {"type": "string"},
            }
        if "emergency_money" in or_relief and "or.emergency_reason" not in answers:
            return {
                "step": "or.emergency_reason",
                "prompt": "What's the money for?",
                "schema": {"type": "string"},
            }
        if "animals" in or_relief and "or.animals_detail" not in answers:
            return {
                "step": "or.animals_detail",
                "prompt": (
                    "Tell me about the animals you want awarded to you — a name and type "
                    "for each is enough."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Oklahoma AOC Petition for Protective Order (22 O.S. 60.1, District Court) —
    # the describe-defendant identity (sex/race/DOB), the county, the §2
    # jurisdiction statement, OK's §3 actions, the §6 emergency-ex-parte election,
    # and OK's items 1-15 relief list. OK's actions and relief lists are its own.
    # OK is in PHYSICAL_DESCRIPTION_STATES (the form has a Defendant Identifiers
    # block) but was removed from VEHICLE_DESCRIPTION_STATES (the AOC form has no
    # vehicle field). Maps in vault.forms.ok.
    def _ok_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "The form asks the other person's sex. What should it say?",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": "It also asks their race. You can write what fits, or skip.",
                "schema": {"type": "string"},
            }
        if "ok.county" not in answers:
            return {
                "step": "ok.county",
                "prompt": (
                    "Which Oklahoma county will you file in? (Usually the one you live in.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "ok.jurisdiction_basis" not in answers:
            return {
                "step": "ok.jurisdiction_basis",
                "prompt": (
                    "Oklahoma asks why the case belongs in this county. Which is true — "
                    "pick any: you live here, they live here, or the abuse happened here?"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "petitioner_resident",
                            "defendant_resident",
                            "abuse_in_county",
                        ],
                    },
                },
            }
        if "ok.actions" not in answers:
            return {
                "step": "ok.actions",
                "prompt": (
                    "Which of these has the other person done? Pick any that fit — "
                    "you don't have to relive the details, just check what's true."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "physical_harm",  # caused/attempted physical harm
                            "threatened_harm",  # threatened imminent physical harm
                            "harassed",  # harassed
                            "stalked",  # stalked
                            "crime",  # rape/sodomy/sex offense/kidnapping/ABDW/child abuse/murder
                            "adult_crime",  # other crime against an adult victim
                        ],
                    },
                },
            }
        if "ok.ex_parte" not in answers:
            return {
                "step": "ok.ex_parte",
                "prompt": (
                    "Do you need protection to start right now, before a hearing, because "
                    "you're in immediate danger? (Oklahoma calls this an Emergency Ex Parte "
                    "Order.)"
                ),
                "schema": {"type": "boolean"},
            }
        if "ok.relief" not in answers:
            return {
                "step": "ok.relief",
                "prompt": (
                    "What would you like the court to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_contact",  # 1
                            "no_abuse",  # 2
                            "no_fear_conduct",  # 3
                            "move_out",  # 4
                            "le_remove_defendant",  # 5
                            "civil_standby",  # 6
                            "minor_defendant_leave",  # 7
                            "suspend_visitation",  # 8
                            "counseling",  # 9
                            "protect_animals",  # 10
                            "gps_monitoring",  # 11
                            "transfer_utilities",  # 12
                            "surrender_firearms",  # 13
                            "pay_court_costs",  # 14
                            "attorney_fees",  # 15
                        ],
                    },
                },
            }
        ok_relief = answers.get("ok.relief", [])
        if "move_out" in ok_relief and "ok.move_out_address" not in answers:
            return {
                "step": "ok.move_out_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "civil_standby" in ok_relief and "ok.civil_standby_address" not in answers:
            return {
                "step": "ok.civil_standby_address",
                "prompt": (
                    "For the civil standby — what's the address where an officer would meet "
                    "you to get your things safely?"
                ),
                "schema": {"type": "string"},
            }
        if "transfer_utilities" in ok_relief and "ok.transfer_detail" not in answers:
            return {
                "step": "ok.transfer_detail",
                "prompt": (
                    "Which utilities or phone numbers should be moved into your name? "
                    "List whatever applies."
                ),
                "schema": {"type": "string"},
            }
        if "attorney_fees" in ok_relief and "ok.attorney_fees_amount" not in answers:
            return {
                "step": "ok.attorney_fees_amount",
                "prompt": "If you know the attorney's-fees amount to ask for, what is it?",
                "schema": {"type": "string"},
            }
        if "ok.additional_relief" not in answers:
            return {
                "step": "ok.additional_relief",
                "prompt": (
                    "Anything else you'd like to ask the court for? You can describe it, "
                    "or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    def _ssn_gate(
        self, jurisdiction: str, answers: dict[str, Any]
    ) -> dict[str, Any] | None:
        # FL collects the survivor's chosen orders as `fl.relief`, not the CA-style
        # `selected_reliefs_intents`, so the support→SSN gate must read both.
        requested_reliefs = answers.get("selected_reliefs_intents", [])
        fl_relief = answers.get("fl.relief", [])
        if (
            jurisdiction in {"CA", "FL", "TX"}
            and (
                "child_support" in requested_reliefs
                or "spousal_support" in requested_reliefs
                or "child_support" in fl_relief
                or "spousal_support" in fl_relief
            )
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
        return None

    _STATE_STEPS: ClassVar[
        dict[str, Callable[[IntakeStateMachine, dict[str, Any]], dict[str, Any] | None]]
    ] = {
        "CA": _ca_step,
        "WA": _wa_step,
        "VA": _va_step,
        "TX": _tx_step,
        "PA": _pa_step,
        "NC": _nc_step,
        "NY": _ny_step,
        "MA": _ma_step,
        "MD": _md_step,
        "HI": _hi_step,
        "GA": _ga_step,
        "WV": _wv_step,
        "WI": _wi_step,
        "WY": _wy_step,
        "AL": _al_step,
        "AK": _ak_step,
        "AR": _ar_step,
        "CO": _co_step,
        "CT": _ct_step,
        "DC": _dc_step,
        "DE": _de_step,
        "UT": _ut_step,
        "VT": _vt_step,
        "SD": _sd_step,
        "TN": _tn_step,
        "FL": _fl_step,
        "RI": _ri_step,
        "OR": _or_step,
        "OK": _ok_step,
    }


def determine_next_step(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Public entry point for the Vault intake state machine.

    Delegates to `IntakeStateMachine`; the signature and return contract are
    unchanged (called by `handle_intake_step` and the test-suite).
    """
    return IntakeStateMachine().next_step(jurisdiction, answers)
