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
    "CO", "AR", "AK", "AL", "WY", "WI", "WV", "VT", "UT", "TN", "SD", "RI", "OR", "OK", "OH",
    "ND", "NM", "NH", "MT", "NV", "NE", "ME", "MI", "IA", "KY", "LA", "ID", "MN", "MS",
    "IN", "MO", "SC",
}
# States with no fillable paper DVRO petition: AZ, IL, KS, and NJ require online
# e-filing submitted through a state court portal. We collect Tier 1, then return a
# `handoff` step (see `_shared_gates`) that routes the survivor to that portal,
# instead of assembling a form here. These never reach a `_<st>_step` or an assembler.
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
        # ID is in the doc's Q31-35 list, but Form CAO DV 1-1 has no respondent
        # physical-description block — omitted so the physical gate doesn't ask for what
        # the form can't carry. See vault.forms.idaho.
        "KY",
        # LA is in the doc's Q31-35 list, but Form LPOR B has no respondent
        # physical-description block (only the defendant's address/parish) — omitted so
        # the physical gate doesn't ask for what the form can't carry. See vault.forms.la.
        "ME",
        "MA",
        # MN is in the doc's Q31-35 list, but Form OFP102 carries only the respondent's
        # race/gender/DOB, not a height/weight/eyes/hair block — omitted so the physical
        # gate doesn't ask for what the form can't carry. See vault.forms.mn.
        "MS",
        "MO",
        "NE",
        # NH is in the doc's Q31-35 list, but Form NHJB-2050-DF has no respondent
        # physical-description block (only the defendant's name/DOB/sex/address) —
        # omitted so the physical gate doesn't ask for what the form can't carry.
        # See vault.forms.nh.
        "ND",
        "OH",
        "OK",
        "PA",
        # SC is in the doc's Q31-35 list, but Form SCCA 425 carries only the respondent's
        # DOB/race/sex, not a height/weight/eyes/hair block — omitted so the physical gate
        # doesn't ask for what the form can't carry. See vault.forms.sc.
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
        # ID, KY, LA, and MS are in the doc's Q41-43 list, but their actual forms have no
        # respondent vehicle block — Form CAO DV 1-1 (ID), AOC-275.1 (KY), LPOR B (LA),
        # and the MS 93-21-1 petition — omitted so the vehicle gate doesn't ask for what
        # the forms can't carry. See vault.forms.idaho / ky / la / ms.
        "ME",
        "MA",
        "MO",
        "NE",
        # NH is in the doc's Q41-43 list, but Form NHJB-2050-DF has no respondent
        # vehicle block — item 11's vehicle is the plaintiff's (a relief detail),
        # not a respondent identifier — omitted like the OK/TN carve-out above.
        # See vault.forms.nh.
        "ND",
        "OH",
        # OK, TN, and SC are in the doc's Q41-43 list, but their actual forms have no
        # respondent vehicle field — the OK / TN AOC / OP forms and SC's Form SCCA 425 —
        # omitted so the vehicle gate doesn't ask for what the forms can't carry.
        # See vault.forms.ok / tn / sc.
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
            in {
                "CA", "NY", "TX", "FL", "WA", "NC", "MA", "MD", "DE", "AR", "CT", "WI", "OR",
                "OH", "NM", "NV", "NE", "LA",
            }
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

    # New Mexico Petition for Order of Protection from Domestic Abuse (Form 4-961,
    # Family Violence Protection Act §§ 40-13-1 to 40-13-8 NMSA) — county/district,
    # drugs/alcohol + prior-abuse flags, and the item-6 (A-J) relief list. NM's
    # relief list is its own. Maps in vault.forms.nm.
    def _nm_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "nm.county" not in answers:
            return {
                "step": "nm.county",
                "prompt": "Which New Mexico county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "nm.judicial_district" not in answers:
            return {
                "step": "nm.judicial_district",
                "prompt": "Which judicial district is that? If you're not sure, you can skip it.",
                "schema": {"type": "string"},
            }
        if "nm.drugs_alcohol" not in answers:
            return {
                "step": "nm.drugs_alcohol",
                "prompt": "Did drugs or alcohol play a role in what happened?",
                "schema": {"type": "boolean"},
            }
        if "nm.prior_abuse" not in answers:
            return {
                "step": "nm.prior_abuse",
                "prompt": "Has there been abuse before this?",
                "schema": {"type": "boolean"},
            }
        if "nm.relief" not in answers:
            return {
                "step": "nm.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_contact_stay_away",  # A
                            "leave_residence",  # B(1)
                            "alternative_housing",  # B(2)
                            "no_property_disposal",  # C
                            "le_retrieve_belongings",  # D
                            "custody",  # E
                            "children_contact",  # F
                            "support",  # G
                            "pay_damages",  # H
                            "other",  # I
                            "surrender_firearms",  # J
                        ],
                    },
                },
            }
        nm_relief = answers.get("nm.relief", [])
        if "leave_residence" in nm_relief and "nm.residence_address" not in answers:
            return {
                "step": "nm.residence_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "le_retrieve_belongings" in nm_relief and "nm.retrieve_address" not in answers:
            return {
                "step": "nm.retrieve_address",
                "prompt": "What's the address where you'd retrieve your belongings?",
                "schema": {"type": "string"},
            }
        if "support" in nm_relief and "nm.support_types" not in answers:
            return {
                "step": "nm.support_types",
                "prompt": "Who should the support be for — the children, you, or both?",
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["children", "petitioner"]},
                },
            }
        if "children_contact" in nm_relief and "nm.children_contact" not in answers:
            return {
                "step": "nm.children_contact",
                "prompt": (
                    "Until the hearing, what contact (if any) should the other person have "
                    "with the children? Leave blank for no contact."
                ),
                "schema": {"type": "string"},
            }
        if "other" in nm_relief and "nm.other_relief" not in answers:
            return {
                "step": "nm.other_relief",
                "prompt": "What other relief would you like the court to consider?",
                "schema": {"type": "string"},
            }
        if "nm.respondent_in_jail" not in answers:
            return {
                "step": "nm.respondent_in_jail",
                "prompt": "Is the other person in jail right now, as far as you know?",
                "schema": {"type": "boolean"},
            }
        return None

    # North Dakota Petition for Civil Protection Order (N.D.C.C. Ch. 14-07.7) — a
    # combined petition for three order types (domestic-violence / sexual-assault /
    # disorderly-conduct). Respondent identifiers, county/district, the order
    # type(s), venue, and the discretionary relief. ND's relief list is its own.
    # Maps in vault.forms.nd.
    def _nd_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The North Dakota form has a respondent description. Their race, if you "
                    "know it — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their gender, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "nd.county" not in answers:
            return {
                "step": "nd.county",
                "prompt": "Which North Dakota county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "nd.judicial_district" not in answers:
            return {
                "step": "nd.judicial_district",
                "prompt": (
                    "Which judicial district is that? If you're not sure, you can skip it."
                ),
                "schema": {"type": "string"},
            }
        if "nd.order_types" not in answers:
            return {
                "step": "nd.order_types",
                "prompt": (
                    "What kind of protection are you asking for? Pick any that fit — the "
                    "court issues the one that gives you the most protection you qualify for."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "domestic_violence",  # DV protection order (family/household)
                            "sexual_assault",  # sexual assault restraining order
                            "disorderly_conduct",  # disorderly conduct restraining order
                        ],
                    },
                },
            }
        if "nd.venue" not in answers:
            return {
                "step": "nd.venue",
                "prompt": (
                    "Why are you filing in this county? Pick any: you live here, your child "
                    "lives here, they live here, or it happened here."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "live_here",
                            "child_lives_here",
                            "respondent_lives_here",
                            "conduct_here",
                            "other",
                        ],
                    },
                },
            }
        if "nd.relief" not in answers:
            return {
                "step": "nd.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "restrain_contact",  # no contact / acts of DV
                            "exclude_places",  # stay away from listed places
                            "prohibit_contact",  # prohibit contacting
                            "custody",  # temporary custody
                            "parenting_time",  # temporary parenting time
                            "surrender_firearms",  # surrender firearms/weapons
                            "protect_animals",  # protect animals
                            "stop_disorderly",  # stop disorderly conduct
                        ],
                    },
                },
            }
        nd_relief = answers.get("nd.relief", [])
        if "exclude_places" in nd_relief and "nd.exclude_places" not in answers:
            return {
                "step": "nd.exclude_places",
                "prompt": (
                    "Which places should they stay away from? Pick any — your home, work, "
                    "school, daycare, or somewhere else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["residence", "employment", "school", "daycare", "other"],
                    },
                },
            }
        if "exclude_places" in nd_relief and "nd.stay_away_feet" not in answers:
            return {
                "step": "nd.stay_away_feet",
                "prompt": "How many feet should they have to stay away from those places?",
                "schema": {"type": "string"},
            }
        if "surrender_firearms" in nd_relief and "nd.firearms_detail" not in answers:
            return {
                "step": "nd.firearms_detail",
                "prompt": (
                    "Which firearms or weapons should they surrender? Describe what you can "
                    "— or say 'unknown'."
                ),
                "schema": {"type": "string"},
            }
        if "protect_animals" in nd_relief and "nd.animals_detail" not in answers:
            return {
                "step": "nd.animals_detail",
                "prompt": "Which animal(s) need protecting? A name and description is enough.",
                "schema": {"type": "string"},
            }
        if "nd.notification" not in answers:
            return {
                "step": "nd.notification",
                "prompt": "Do you want to be notified when the other person is served the papers?",
                "schema": {"type": "boolean"},
            }
        return None

    # Ohio Petition for Domestic Violence Civil Protection Order (Form 10.01-D,
    # R.C. 3113.31) — county, the ex parte request, who needs protection, optional
    # item-7 factors, and the item-9 (a-n) relief list. OH's relief list is its
    # own. Maps in vault.forms.oh.
    def _oh_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "oh.county" not in answers:
            return {
                "step": "oh.county",
                "prompt": "Which Ohio county (Court of Common Pleas) will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "oh.ex_parte" not in answers:
            return {
                "step": "oh.ex_parte",
                "prompt": (
                    "Do you want an emergency (ex parte) order that can be granted right "
                    "away, before a full hearing?"
                ),
                "schema": {"type": "boolean"},
            }
        if "oh.who_needs_protection" not in answers:
            return {
                "step": "oh.who_needs_protection",
                "prompt": (
                    "Who needs protection? Pick any: you, your minor children, another "
                    "family or household member, or someone else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["me", "minor_children", "household_member", "other"],
                    },
                },
            }
        if "oh.aggravating_factors" not in answers:
            return {
                "step": "oh.aggravating_factors",
                "prompt": (
                    "This part is optional. Do any of these apply to the other person? "
                    "Pick any — or skip. (Leaving it blank doesn't mean the abuse didn't "
                    "happen.)"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "history_dv",  # history of DV / violent acts
                            "violating_orders",  # history of violating court orders
                            "mental_health",  # mental-health concerns
                            "threats_others",  # threats to other persons
                            "weapons_access",  # access to / use of deadly weapons
                            "substance_abuse",  # alcohol / drug abuse
                            "serious_injury",  # serious injury / forced sex / strangulation / etc.
                            "recent_separation",  # recent separation / breakup
                            "controlling_stalking",  # obsessive/controlling, stalking, isolating
                            "threats_kill",  # threats to kill self or others
                        ],
                    },
                },
            }
        if "oh.relief" not in answers:
            return {
                "step": "oh.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # (a)
                            "no_enter_locations",  # (b) not enter residence/school/work
                            "no_contact",  # (c)
                            "exclusive_residence",  # (d) leave/exclusive possession
                            "custody",  # (e) temporary parental rights
                            "parenting_time",  # (f) parenting-time conditions
                            "financial_support",  # (g)
                            "no_property_disposal",  # (h)
                            "take_pets",  # (i) take companion animals
                            "divide_property",  # (j)
                            "vehicle",  # (k) exclusive use of vehicle
                            "counseling",  # (l) batterer/substance counseling
                            "wireless_transfer",  # (m) wireless account separation
                            "additional",  # (n) additional provisions
                        ],
                    },
                },
            }
        oh_relief = answers.get("oh.relief", [])
        if "exclusive_residence" in oh_relief and "oh.residence_address" not in answers:
            return {
                "step": "oh.residence_address",
                "prompt": "What's the address of the residence you want exclusive possession of?",
                "schema": {"type": "string"},
            }
        if "take_pets" in oh_relief and "oh.pets_detail" not in answers:
            return {
                "step": "oh.pets_detail",
                "prompt": "Which companion animals or pets? A name and description is enough.",
                "schema": {"type": "string"},
            }
        if "divide_property" in oh_relief and "oh.property_detail" not in answers:
            return {
                "step": "oh.property_detail",
                "prompt": "How would you want household and personal property divided?",
                "schema": {"type": "string"},
            }
        if "vehicle" in oh_relief and "oh.vehicle_detail" not in answers:
            return {
                "step": "oh.vehicle_detail",
                "prompt": (
                    "Which motor vehicle do you need exclusive use of? A description is fine."
                ),
                "schema": {"type": "string"},
            }
        if "wireless_transfer" in oh_relief and "oh.wireless_detail" not in answers:
            return {
                "step": "oh.wireless_detail",
                "prompt": (
                    "Which wireless number(s) do you want moved into your name, and what's "
                    "their billing number if you know it?"
                ),
                "schema": {"type": "string"},
            }
        if "additional" in oh_relief and "oh.additional_provisions" not in answers:
            return {
                "step": "oh.additional_provisions",
                "prompt": "What additional provisions would you like the court to include?",
                "schema": {"type": "string"},
            }
        return None

    # New Hampshire Domestic Violence Petition (Form NHJB-2050-DF, RSA 173-B) —
    # respondent DOB/sex, a plaintiff demographic block (sex/race/ethnicity), the
    # court name, and the item-1 through item-15 relief list (protective orders 1-7
    # + additional orders 8-15) with its details, the financial-losses block, and
    # the other-court-actions block. NH's relief list is its own. The form has no
    # respondent physical/vehicle block, so NH is carved out of those gates. Maps
    # in vault.forms.nh.
    def _nh_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know the other person's date of birth? Skip if you don't.",
                "schema": {"type": "string"},
            }
        if "respondent.sex" not in answers:
            return {
                "step": "respondent.sex",
                "prompt": (
                    "The New Hampshire form notes the other person's sex (M/F), if you know it."
                ),
                "schema": {"type": "string"},
            }
        if "petitioner.sex" not in answers:
            return {
                "step": "petitioner.sex",
                "prompt": (
                    "The form also records a few things about you for the court record — all "
                    "optional. Your sex (M/F), if you'd like to put one — or skip."
                ),
                "schema": {"type": "string"},
            }
        if "petitioner.race" not in answers:
            return {
                "step": "petitioner.race",
                "prompt": (
                    "Your race, if you want to note one — or skip; the form has an "
                    "'unavailable' box."
                ),
                "schema": {"type": "string"},
            }
        if "petitioner.ethnicity" not in answers:
            return {
                "step": "petitioner.ethnicity",
                "prompt": "And ethnicity — Hispanic, non-Hispanic, or skip.",
                "schema": {"type": "string"},
            }
        if "nh.court_name" not in answers:
            return {
                "step": "nh.court_name",
                "prompt": (
                    "Which New Hampshire Circuit Court will you file in? The town or division "
                    "name is enough."
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "nh.relief" not in answers:
            return {
                "step": "nh.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse_contact",  # 1 restrain abuse / all contact
                            "stay_away",  # 2 premises / employment / school
                            "protect_others",  # 3 relatives / household members
                            "no_property_damage",  # 4 take / damage property
                            "surrender_firearms",  # 5 relinquish firearms / weapons
                            "custody",  # 6 temporary custody of children
                            "protect_animals",  # 7 animal no-contact / cruelty
                            "child_support",  # 8 child support payments
                            "visitation",  # 9 court-approved visitation plan
                            "exclusive_residence",  # 10 residence + furnishings
                            "exclusive_vehicle",  # 11 exclusive use of a vehicle
                            "animal_custody",  # 12 care / custody of an animal
                            "pay_losses",  # 13 pay for financial losses
                            "batterer_treatment",  # 14 treatment / counseling
                            "other",  # 15 other relief
                        ],
                    },
                },
            }
        nh_relief = answers.get("nh.relief", [])
        if "surrender_firearms" in nh_relief and "nh.firearms_detail" not in answers:
            return {
                "step": "nh.firearms_detail",
                "prompt": (
                    "Which firearms or other deadly weapons should they hand over? Describe "
                    "what you can — or say 'unknown'."
                ),
                "schema": {"type": "string"},
            }
        if "exclusive_residence" in nh_relief and "nh.residence_type" not in answers:
            return {
                "step": "nh.residence_type",
                "prompt": "The home you'd want exclusive use of — do you own it or rent it?",
                "schema": {"type": "string", "enum": ["own", "rent"]},
            }
        if "exclusive_residence" in nh_relief and "nh.residence_holder" not in answers:
            return {
                "step": "nh.residence_holder",
                "prompt": "Whose name is the home in — yours, theirs, or both?",
                "schema": {"type": "string"},
            }
        if "exclusive_vehicle" in nh_relief and "nh.vehicle_detail" not in answers:
            return {
                "step": "nh.vehicle_detail",
                "prompt": "Which vehicle do you need exclusive use of? A description is fine.",
                "schema": {"type": "string"},
            }
        if "pay_losses" in nh_relief and "nh.financial_losses" not in answers:
            return {
                "step": "nh.financial_losses",
                "prompt": (
                    "What did the abuse cost you that you'd want repaid? Pick any that fit."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "medical_dental_optical",
                            "lost_wages",
                            "lost_property",
                            "other",
                        ],
                    },
                },
            }
        if (
            "pay_losses" in nh_relief
            and "other" in answers.get("nh.financial_losses", [])
            and "nh.financial_losses_other" not in answers
        ):
            return {
                "step": "nh.financial_losses_other",
                "prompt": "What other financial loss would you want repaid?",
                "schema": {"type": "string"},
            }
        if "other" in nh_relief and "nh.other_relief" not in answers:
            return {
                "step": "nh.other_relief",
                "prompt": "What other relief would you like the court to consider?",
                "schema": {"type": "string"},
            }
        if "nh.court_actions" not in answers:
            return {
                "step": "nh.court_actions",
                "prompt": (
                    "Are you and the other person involved in any other court cases — divorce, "
                    "custody, a protective order, or something else? Pick any, or 'none'."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "divorce",
                            "custody",
                            "protective_order",
                            "none",
                            "other",
                        ],
                    },
                },
            }
        nh_court_actions = answers.get("nh.court_actions", [])
        has_other_case = bool(nh_court_actions) and nh_court_actions != ["none"]
        if has_other_case and "nh.court_list" not in answers:
            return {
                "step": "nh.court_list",
                "prompt": "Which court(s) are handling those? Skip if you're not sure.",
                "schema": {"type": "string"},
            }
        if has_other_case and "nh.represented_by_lawyer" not in answers:
            return {
                "step": "nh.represented_by_lawyer",
                "prompt": "Do you have a lawyer in any of those matters?",
                "schema": {"type": "boolean"},
            }
        return None

    # Montana Sworn Petition for Temporary Order of Protection (AGO Form OVS 3,
    # Mont. Code Ann. § 40-15-201) — court type + county, living situation, and the
    # item-1 through item-12 relief list with its details (stay-away feet/places,
    # firearms, possession, other-safety) plus the item-11 parenting choice. MT's
    # relief list is its own. The form has no respondent DOB / physical / vehicle
    # block, so MT is in none of those gates. Maps in vault.forms.mt.
    def _mt_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "mt.court_type" not in answers:
            return {
                "step": "mt.court_type",
                "prompt": (
                    "Montana protection orders can be filed in a few court types. Which fits "
                    "where you're filing?"
                ),
                "schema": {
                    "type": "string",
                    "enum": ["justice", "city", "municipal", "district", "tribal"],
                },
            }
        if "mt.county" not in answers:
            return {
                "step": "mt.county",
                "prompt": "Which Montana county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "mt.living_situation" not in answers:
            return {
                "step": "mt.living_situation",
                "prompt": (
                    "Where do things stand with living arrangements? Pick any that fit — they "
                    "don't live with me, we live together, or I've left a home we shared."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "respondent_not_with_me",
                            "live_with_respondent",
                            "left_residence",
                        ],
                    },
                },
            }
        mt_living = answers.get("mt.living_situation", [])
        if "left_residence" in mt_living and "mt.return_reason" not in answers:
            return {
                "step": "mt.return_reason",
                "prompt": (
                    "You left a home you shared — would you want to return? Pick any: to live "
                    "there, to get your belongings, or something else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["live_there", "get_belongings", "other"],
                    },
                },
            }
        if "mt.relief" not in answers:
            return {
                "step": "mt.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_violence",  # 1 no acts/threats of violence
                            "no_contact",  # 2 no harass / contact / communicate
                            "no_remove_children",  # 3 not take children from county/state
                            "stay_away",  # 4 stay-away distance + places
                            "firearms",  # 5 not possess firearms used/threatened
                            "no_property_damage",  # 6 not take/hide/damage property
                            "possession",  # 7 give petitioner possession/use of items
                            "peace_officer",  # 8 peace-officer help with possession
                            "counseling",  # 9 violence / chemical-dependency counseling
                            "other_safety",  # 10 other orders for safety / welfare
                            "other_relief",  # 12 other relief as just and proper
                        ],
                    },
                },
            }
        mt_relief = answers.get("mt.relief", [])
        if "stay_away" in mt_relief and "mt.stay_away_feet" not in answers:
            return {
                "step": "mt.stay_away_feet",
                "prompt": (
                    "How many feet should they have to stay away? The court can order up to 1500."
                ),
                "schema": {"type": "string"},
            }
        if "stay_away" in mt_relief and "mt.stay_away_places" not in answers:
            return {
                "step": "mt.stay_away_places",
                "prompt": (
                    "Which places should they stay away from? Pick any — you, the children, "
                    "your home, work, your vehicle, the children's school, or somewhere else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "me",
                            "minor_children",
                            "other_people",
                            "home",
                            "job",
                            "vehicle",
                            "school",
                            "other",
                        ],
                    },
                },
            }
        if "firearms" in mt_relief and "mt.firearms_relief_detail" not in answers:
            return {
                "step": "mt.firearms_relief_detail",
                "prompt": (
                    "Which firearms should they be ordered not to possess? Describe what you "
                    "can — or say 'unknown'."
                ),
                "schema": {"type": "string"},
            }
        if "possession" in mt_relief and "mt.possession_detail" not in answers:
            return {
                "step": "mt.possession_detail",
                "prompt": (
                    "What should they hand over to you — the home, a vehicle, other essentials? "
                    "List what you need, no matter who owns it."
                ),
                "schema": {"type": "string"},
            }
        if "other_safety" in mt_relief and "mt.other_safety_detail" not in answers:
            return {
                "step": "mt.other_safety_detail",
                "prompt": "What else should the court order for your safety and welfare?",
                "schema": {"type": "string"},
            }
        if answers.get("relationship.children_in_common") is True and "mt.parenting" not in answers:
            return {
                "step": "mt.parenting",
                "prompt": (
                    "About time with the children, pick the one that fits: it doesn't apply, "
                    "the stay-away orders are enough so no visits are needed, or you want a "
                    "temporary visitation schedule."
                ),
                "schema": {
                    "type": "string",
                    "enum": ["not_applicable", "protections_suffice", "visitation_appendix_a"],
                },
            }
        if "mt.other_protected" not in answers:
            return {
                "step": "mt.other_protected",
                "prompt": (
                    "Anyone else you'd want protected — by name, and how they're related to you "
                    "and the other person? Leave blank if it's just you."
                ),
                "schema": {"type": "string"},
            }
        if "mt.other_cases" not in answers:
            return {
                "step": "mt.other_cases",
                "prompt": (
                    "Any other court cases — divorce, custody, criminal — involving the two of "
                    "you? You can name them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Nevada Application for Protection Order Against Domestic Violence (© 2022
    # Nevada Supreme Court, NRS 33) — court type/county, who needs protection, the
    # abuse grounds, the item-10 temporary-protections list with its details, the
    # custody request, and the item-11 order length (45-day vs. extended) with its
    # extended-relief list. NV's relief list is its own. Maps in vault.forms.nv.
    def _nv_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "nv.court_type" not in answers:
            return {
                "step": "nv.court_type",
                "prompt": (
                    "Nevada filings go to District Court (in Washoe or Clark County, or against "
                    "a minor) or a Justice Court. Which fits where you're filing?"
                ),
                "schema": {"type": "string", "enum": ["district", "justice"]},
            }
        if answers.get("nv.court_type") == "justice" and "nv.township" not in answers:
            return {
                "step": "nv.township",
                "prompt": "Which township is that Justice Court in?",
                "schema": {"type": "string"},
            }
        if "nv.county" not in answers:
            return {
                "step": "nv.county",
                "prompt": "Which Nevada county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "nv.adverse_party_type" not in answers:
            return {
                "step": "nv.adverse_party_type",
                "prompt": "Is the person you need protection from an adult or a minor?",
                "schema": {"type": "string", "enum": ["adult", "minor"]},
            }
        if "nv.adverse_in_custody" not in answers:
            return {
                "step": "nv.adverse_in_custody",
                "prompt": "Is that person in jail or prison right now, as far as you know?",
                "schema": {"type": "boolean"},
            }
        if "nv.who_needs_protection" not in answers:
            return {
                "step": "nv.who_needs_protection",
                "prompt": (
                    "Who needs protection? Pick one or both: you, and/or your minor children."
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["me", "minor_children"]},
                },
            }
        if "nv.protection_reason" not in answers:
            return {
                "step": "nv.protection_reason",
                "prompt": (
                    "What's the reason for the request? Pick any that fit — the other person "
                    "harmed or threatened you, and/or harmed or threatened a child."
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["dv_against_me", "dv_against_child"]},
                },
            }
        if "nv.temp_protections" not in answers:
            return {
                "step": "nv.temp_protections",
                "prompt": (
                    "What would you like the judge to order right now? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "prohibited_activities",  # no threaten/injure/harass
                            "no_contact_me",  # no contact with you at all
                            "contact_me_parenting",  # contact you for parenting only
                            "no_contact_children",  # no contact with the children
                            "contact_children_parenting",  # limited contact with children
                            "current_residence",  # stay away from your residence
                            "personal_belongings",  # law-enforcement escort for belongings
                            "work",  # stay away from your workplace
                            "school_daycare",  # stay away from school / day care
                            "other_places",  # stay away from other places
                            "pets_safety",  # don't harm the pets/animals
                            "pets_possession",  # you keep the pets/animals
                        ],
                    },
                },
            }
        nv_temp = answers.get("nv.temp_protections", [])
        if "contact_me_parenting" in nv_temp and "nv.contact_me_method" not in answers:
            return {
                "step": "nv.contact_me_method",
                "prompt": (
                    "For parenting matters only, how should they be allowed to reach you? "
                    "Pick any: text, email, phone, in writing, or something else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["text", "email", "phone", "writing", "other"],
                    },
                },
            }
        if "personal_belongings" in nv_temp and "nv.belongings_address" not in answers:
            return {
                "step": "nv.belongings_address",
                "prompt": (
                    "What's the address where you'd retrieve your belongings, with a law-"
                    "enforcement escort?"
                ),
                "schema": {"type": "string"},
            }
        if "other_places" in nv_temp and "nv.other_places_detail" not in answers:
            return {
                "step": "nv.other_places_detail",
                "prompt": "Which other places should they stay away from, and why?",
                "schema": {"type": "string"},
            }
        if answers.get("relationship.children_in_common") is True and "nv.custody" not in answers:
            return {
                "step": "nv.custody",
                "prompt": (
                    "About the children, pick the one that fits: no visitation for now, "
                    "visitation on a schedule you'll describe, keep an existing order, or "
                    "you're not asking about custody here."
                ),
                "schema": {
                    "type": "string",
                    "enum": ["no_visitation", "visitation", "existing_order", "not_requested"],
                },
            }
        if (
            answers.get("nv.custody") == "visitation"
            and "nv.visitation_detail" not in answers
        ):
            return {
                "step": "nv.visitation_detail",
                "prompt": "What visitation schedule would you want?",
                "schema": {"type": "string"},
            }
        if "nv.order_length" not in answers:
            return {
                "step": "nv.order_length",
                "prompt": (
                    "The judge can issue a temporary order up to 45 days, or that plus an "
                    "extended order up to 2 years (which needs a hearing). Which would you like?"
                ),
                "schema": {"type": "string", "enum": ["temporary_45", "extended_2yr"]},
            }
        if answers.get("nv.order_length") == "extended_2yr" and "nv.extended_relief" not in answers:
            return {
                "step": "nv.extended_relief",
                "prompt": (
                    "For the extended order, is there anything else you'd want? Pick any — "
                    "or none. (Some of these may need a separate financial form.)"
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "rent_mortgage",
                            "household_support",
                            "child_support",
                            "lost_earnings",
                            "costs_fees",
                            "pets_arrangement",
                            "other",
                        ],
                    },
                },
            }
        if "nv.other_cases_detail" not in answers:
            return {
                "step": "nv.other_cases_detail",
                "prompt": (
                    "Any other court cases involving the two of you? If you know the type, "
                    "county, or case number, jot it down — or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Nebraska Petition and Affidavit to Obtain Domestic Abuse Protection Order
    # (Form DC 19:8, Neb. Rev. Stat. §§ 26-101 et seq.) — respondent DOB/race/sex
    # (the item-4 description), county/judge type, the item-7 relief list with its
    # details, and the item-6 prior-case detail. NE's relief list is its own. NE is
    # in the interpreter / physical / vehicle / minor gates. Maps in vault.forms.ne.
    def _ne_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
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
                    "The Nebraska form has a respondent description. Their race, if you know it "
                    "— or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "And their sex, if you know — or skip.",
                "schema": {"type": "string"},
            }
        if "ne.county" not in answers:
            return {
                "step": "ne.county",
                "prompt": "Which Nebraska county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ne.judge_type" not in answers:
            return {
                "step": "ne.judge_type",
                "prompt": (
                    "Would you like a District Court or County Court judge to preside? "
                    "(The court may not grant the request, and either is fine.)"
                ),
                "schema": {"type": "string", "enum": ["district", "county"]},
            }
        if "ne.relief" not in answers:
            return {
                "step": "ne.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_restraint",  # no restraint on the protected person(s)
                            "no_abuse",  # no harass/threaten/assault/disturb the peace
                            "no_contact",  # no telephoning/contacting/communicating
                            "exclude_residence",  # remove/exclude from a residence
                            "stay_away",  # stay away from listed location(s)
                            "no_firearm",  # no possessing/purchasing a firearm
                            "custody",  # temporary custody (up to 90 days)
                            "pet_possession",  # sole possession of household pets
                            "pet_protection",  # no contact/harm to household pets
                            "other",  # any other relief for safety/welfare
                        ],
                    },
                },
            }
        ne_relief = answers.get("ne.relief", [])
        if "exclude_residence" in ne_relief and "ne.residence_address" not in answers:
            return {
                "step": "ne.residence_address",
                "prompt": "What's the address of the residence you want them excluded from?",
                "schema": {"type": "string"},
            }
        if "stay_away" in ne_relief and "ne.stay_away_location" not in answers:
            return {
                "step": "ne.stay_away_location",
                "prompt": (
                    "Which location(s) should they stay away from? An address or description, "
                    "and how the place connects to you, helps."
                ),
                "schema": {"type": "string"},
            }
        if "custody" in ne_relief and "ne.custody_days" not in answers:
            return {
                "step": "ne.custody_days",
                "prompt": "How many days of temporary custody are you asking for? (Up to 90.)",
                "schema": {"type": "string"},
            }
        if "pet_possession" in ne_relief and "ne.pet_detail" not in answers:
            return {
                "step": "ne.pet_detail",
                "prompt": (
                    "Which pet(s) do you want to keep? A name, species, and short description "
                    "is enough."
                ),
                "schema": {"type": "string"},
            }
        if "other" in ne_relief and "ne.other_relief" not in answers:
            return {
                "step": "ne.other_relief",
                "prompt": "What other relief would you like the court to consider?",
                "schema": {"type": "string"},
            }
        if answers.get("prior_orders.exists") is True and "ne.prior_cases_detail" not in answers:
            return {
                "step": "ne.prior_cases_detail",
                "prompt": (
                    "For the other case(s) between you — if you know the court, date, type, or "
                    "case number, jot down what you can. Skip if you're not sure."
                ),
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
                "prompt": (
                    "Which household pet(s) need protecting? A name and description is enough."
                ),
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
                "prompt": (
                    "How much monthly spousal support are you asking for, and why is it needed?"
                ),
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
                "prompt": (
                    "Which Connecticut judicial district (or court location) will you file in?"
                ),
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

    # Maine Complaint for Protection from Abuse (Form PA-001, 19-A M.R.S. §§ 4101-4116) —
    # respondent dob/gender/race the PA-005 service sheet needs, the District Court town,
    # the §3 military-service note, the §4 relationship basis, the §10 temporary (ex parte)
    # election, the §11 weapons block, and the orders a-q relief list with its conditional
    # details. ME is in the shared physical/vehicle/minor gates (PA-005 carries those
    # identifiers). ME's relationship and relief lists are its own. Maps in vault.forms.me.
    def _me_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": (
                    "Do you know their date of birth? An approximate age is fine if you're "
                    "not sure."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their gender? You can skip this.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "Maine's form asks for their race. You can pick what fits, or skip — "
                    "Lea defaults to 'unknown'."
                ),
                "schema": {"type": "string"},
            }
        if "me.court_location" not in answers:
            return {
                "step": "me.court_location",
                "prompt": (
                    "Maine PFAs are filed in the District Court for a town. Which town will "
                    "you file in?"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "me.defendant_military" not in answers:
            return {
                "step": "me.defendant_military",
                "prompt": (
                    "Do you know if they're in the military right now? The form asks — and "
                    "'not sure' is a real answer."
                ),
                "schema": {
                    "type": "string",
                    "enum": ["in_service", "not_in_service", "unknown"],
                },
            }
        if "me.relationship_basis" not in answers:
            return {
                "step": "me.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a spouse or ex, a "
                    "co-parent, someone you live or lived with, a dating partner, a relative, "
                    "or because of something they did to you (stalking, sexual assault, "
                    "sharing private images, trafficking)."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "married",
                            "former_spouse",
                            "parent_of_child",
                            "minor_child_household",
                            "relative",
                            "sexual_partner",
                            "living_together",
                            "dating_partner",
                            "dependent_adult",
                            "sex_trafficking",
                            "condom_tampering",
                            "sexual_assault",
                            "stalking",
                            "image_dissemination",
                            "minor_exploitation",
                            "minor_harassment",
                        ],
                    },
                },
            }
        if "me.temporary_order" not in answers:
            return {
                "step": "me.temporary_order",
                "prompt": (
                    "Do you need protection right now, before they're notified? Pick what "
                    "fits: I'm in immediate danger, my children are in immediate danger, or "
                    "I'm not asking for a temporary order."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["self_danger", "children_danger", "not_requesting"],
                    },
                },
            }
        if "me.relief" not in answers:
            return {
                "step": "me.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stop_abuse",  # a
                            "no_contact",  # b
                            "no_enter_residence",  # c
                            "no_follow",  # d
                            "stay_distance",  # e
                            "no_weapons",  # f
                            "remove_images",  # g
                            "possession_residence",  # h
                            "possession_property_pets",  # i
                            "parental_rights",  # j
                            "defendant_contact",  # k
                            "counseling",  # l
                            "support",  # m
                            "monetary_relief",  # n
                            "trafficking_damages",  # o
                            "no_passport_tampering",  # p
                            "other",  # q
                        ],
                    },
                },
            }
        me_relief = answers.get("me.relief", [])
        if "possession_residence" in me_relief and "me.residence_address" not in answers:
            return {
                "step": "me.residence_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "possession_property_pets" in me_relief and "me.property_detail" not in answers:
            return {
                "step": "me.property_detail",
                "prompt": (
                    "What belongings or pets should you keep? You can name the animals too, "
                    "so the order protects them."
                ),
                "schema": {"type": "string"},
            }
        if "stay_distance" in me_relief and "me.stay_distance_detail" not in answers:
            return {
                "step": "me.stay_distance_detail",
                "prompt": (
                    "How far should they have to stay from you, or which specific place "
                    "should they keep away from?"
                ),
                "schema": {"type": "string"},
            }
        if "other" in me_relief and "me.relief_other_detail" not in answers:
            return {
                "step": "me.relief_other_detail",
                "prompt": "Anything else you'd like to ask the court for? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        if "me.weapon_access" not in answers:
            return {
                "step": "me.weapon_access",
                "prompt": (
                    "Do they have access to any weapons? Pick any: a firearm, a muzzle-loading "
                    "firearm, a bow or crossbow, or another dangerous weapon. Leave blank if "
                    "none or you don't know."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["firearm", "muzzle_loading", "bow_crossbow", "other_dangerous"],
                    },
                },
            }
        if answers.get("me.weapon_access") and "me.weapon_detail" not in answers:
            return {
                "step": "me.weapon_detail",
                "prompt": (
                    "Can you describe the weapon and where it's usually kept? Whatever you "
                    "know helps."
                ),
                "schema": {"type": "string"},
            }
        if "me.weapon_ever_used" not in answers:
            return {
                "step": "me.weapon_ever_used",
                "prompt": (
                    "Have they ever used a weapon to threaten or scare you? Yes or no is fine."
                ),
                "schema": {"type": "boolean"},
            }
        if answers.get("me.weapon_ever_used") is True and "me.weapon_used_detail" not in answers:
            return {
                "step": "me.weapon_used_detail",
                "prompt": "When you're ready, tell me what happened — in your own words.",
                "schema": {"type": "string"},
            }
        if "me.other_cases_detail" not in answers:
            return {
                "step": "me.other_cases_detail",
                "prompt": (
                    "Any other court cases — divorce, custody, criminal — involving the two "
                    "of you? You can name them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Michigan Petition for Personal Protection Order (Domestic Relationship) (Form CC 375,
    # MCL 600.2950/600.2950a) — the county/circuit, the §1 relationship basis, the §2
    # firearm-in-employment note, the §6 ex parte election, and the §5 relief list (items
    # a-l) with the §5e stalking sub-acts, §5j animal sub-acts, and conditional details.
    # CC 375 has no physical-description or vehicle block, so MI is in neither gate. MI's
    # relationship and relief lists are its own. Maps in vault.forms.mi.
    def _mi_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "mi.county" not in answers:
            return {
                "step": "mi.county",
                "prompt": "Which Michigan county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "mi.relationship" not in answers:
            return {
                "step": "mi.relationship",
                "prompt": (
                    "How are you connected to them? Pick any that fit — married now, married "
                    "before, a child together, a dating relationship, or you live or lived "
                    "in the same home."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "married",
                            "formerly_married",
                            "child_in_common",
                            "dating",
                            "cohabitants",
                        ],
                    },
                },
            }
        if "mi.respondent_carries_firearm" not in answers:
            return {
                "step": "mi.respondent_carries_firearm",
                "prompt": (
                    "Does their job require them to carry a firearm — police, military, "
                    "security? 'Not sure' is fine."
                ),
                "schema": {"type": "string", "enum": ["yes", "no", "unknown"]},
            }
        if "mi.ex_parte" not in answers:
            return {
                "step": "mi.ex_parte",
                "prompt": (
                    "Do you need the order right away, before they're notified? That's called "
                    "an ex parte order — for when waiting could put you in danger."
                ),
                "schema": {"type": "boolean"},
            }
        if "mi.relief" not in answers:
            return {
                "step": "mi.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "enter_my_property",  # a
                            "enter_other_property",  # b
                            "assault",  # c
                            "remove_children",  # d
                            "stalking",  # e
                            "interfere_property_removal",  # f
                            "threats",  # g
                            "interfere_employment",  # h
                            "access_records",  # i
                            "animal_abuse",  # j
                            "firearm",  # k
                            "other",  # l
                        ],
                    },
                },
            }
        mi_relief = answers.get("mi.relief", [])
        if "stalking" in mi_relief and "mi.stalking_acts" not in answers:
            return {
                "step": "mi.stalking_acts",
                "prompt": (
                    "Which of these have they done? Pick any: following or showing up where "
                    "you are, appearing at your work or home, sending mail or messages, calling "
                    "you, approaching you in public or private, coming onto your property, or "
                    "leaving things for you."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "following",
                            "appearing_workplace",
                            "sending_mail",
                            "contacting_phone",
                            "approaching",
                            "entering_property",
                            "placing_object",
                        ],
                    },
                },
            }
        if "animal_abuse" in mi_relief and "mi.animal_acts" not in answers:
            return {
                "step": "mi.animal_acts",
                "prompt": (
                    "Is this about an animal you own? Pick any: they've hurt or threatened it, "
                    "taken it, or are keeping it from you."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["injure", "remove", "retain"],
                    },
                },
            }
        if "enter_other_property" in mi_relief and "mi.other_property_address" not in answers:
            return {
                "step": "mi.other_property_address",
                "prompt": "What's the address of the property they should be kept away from?",
                "schema": {"type": "string"},
            }
        if "assault" in mi_relief and "mi.assault_names" not in answers:
            return {
                "step": "mi.assault_names",
                "prompt": (
                    "Who should be protected from being hurt? You can list yourself and anyone "
                    "else by name."
                ),
                "schema": {"type": "string"},
            }
        if "threats" in mi_relief and "mi.threat_names" not in answers:
            return {
                "step": "mi.threat_names",
                "prompt": "Who should they be ordered not to threaten? List the names.",
                "schema": {"type": "string"},
            }
        if "other" in mi_relief and "mi.relief_other_detail" not in answers:
            return {
                "step": "mi.relief_other_detail",
                "prompt": "Anything else you'd like to ask the court for? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        if "mi.other_cases_detail" not in answers:
            return {
                "step": "mi.other_cases_detail",
                "prompt": (
                    "Any other court cases — divorce, custody, criminal — involving the two "
                    "of you? You can name them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Iowa Petition for Relief from Domestic Abuse (Rule 17.10 Form 11, Iowa Code ch. 236)
    # — the county, the §5 defendant-minor flag, the §7 relationship basis, the §8 abuse
    # types, the §23 temporary/final order election and order checklist, the §20 possession
    # requests, the §22 counseling, and the §24 confidentiality requests. Form 11 has no
    # respondent physical/vehicle block, so IA is in neither gate. IA's relationship and
    # relief lists are its own. Maps in vault.forms.ia.
    def _ia_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "ia.county" not in answers:
            return {
                "step": "ia.county",
                "prompt": "Which Iowa county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ia.defendant_minor" not in answers:
            return {
                "step": "ia.defendant_minor",
                "prompt": (
                    "Is the other person 17 or younger? The form asks — 'not sure' is fine."
                ),
                "schema": {"type": "string", "enum": ["yes", "no", "unknown"]},
            }
        if "ia.relationship_basis" not in answers:
            return {
                "step": "ia.relationship_basis",
                "prompt": (
                    "How were you connected to them when this happened? Pick any that fit — "
                    "family or household living together, separated or divorced, parents of "
                    "the same child, family who lived together in the past year, or an intimate "
                    "relationship now or within the past year."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "family_living_together",
                            "separated_divorced",
                            "parents_same_child",
                            "family_not_living_together",
                            "intimate_relationship",
                        ],
                    },
                },
            }
        if "ia.abuse_types" not in answers:
            return {
                "step": "ia.abuse_types",
                "prompt": (
                    "How has the other person hurt or frightened you? Pick any: physically, "
                    "sexually, or by saying or doing something that made you afraid."
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["physical", "sexual", "threats"]},
                },
            }
        if "ia.order_request" not in answers:
            return {
                "step": "ia.order_request",
                "prompt": (
                    "Iowa has two kinds of orders: a temporary one right away (until a hearing "
                    "within 15 days), and a final one that lasts up to a year after a hearing. "
                    "Which would you like? You can ask for both."
                ),
                "schema": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["temporary", "final"]},
                },
            }
        if "ia.relief" not in answers:
            return {
                "step": "ia.relief",
                "prompt": (
                    "What would you like the judge to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stop_abuse",  # 1
                            "stay_away_me",  # 2
                            "stay_away_children",  # 3
                            "stay_away_home",  # 4
                            "stay_away_work_school",  # 5
                            "no_contact",  # 6
                            "possession_home",  # 7
                            "possession_car",  # 8
                            "custody_visitation",  # 9
                            "financial_support",  # 10
                            "no_firearms",  # 11
                            "possession_other",  # 12
                            "other",  # 13
                        ],
                    },
                },
            }
        ia_relief = answers.get("ia.relief", [])
        if "possession_home" in ia_relief and "ia.home_address" not in answers:
            return {
                "step": "ia.home_address",
                "prompt": "What's the address of the home, and why should you have it?",
                "schema": {"type": "string"},
            }
        if "financial_support" in ia_relief and "ia.support_detail" not in answers:
            return {
                "step": "ia.support_detail",
                "prompt": (
                    "How much monthly support do you need, and for what — rent, food, "
                    "childcare? You can include incomes if you know them."
                ),
                "schema": {"type": "string"},
            }
        if "other" in ia_relief and "ia.relief_other_detail" not in answers:
            return {
                "step": "ia.relief_other_detail",
                "prompt": "What else should the court order? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        if "ia.possession_requests" not in answers:
            return {
                "step": "ia.possession_requests",
                "prompt": (
                    "Is there anything you need to keep or take with you? Pick any: the "
                    "residence, a vehicle, a pet, identification or documents, or something "
                    "else. Leave blank if none."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["residence", "vehicle", "pet", "documents", "other"],
                    },
                },
            }
        ia_possession = answers.get("ia.possession_requests", [])
        if "residence" in ia_possession and "ia.residence_detail" not in answers:
            return {
                "step": "ia.residence_detail",
                "prompt": "What's the address, and why should you have the residence?",
                "schema": {"type": "string"},
            }
        if "vehicle" in ia_possession and "ia.vehicle_detail" not in answers:
            return {
                "step": "ia.vehicle_detail",
                "prompt": "What's the year, make, and model, and why should you have the vehicle?",
                "schema": {"type": "string"},
            }
        if "pet" in ia_possession and "ia.pet_detail" not in answers:
            return {
                "step": "ia.pet_detail",
                "prompt": (
                    "What's the pet's name and description, and why should you have them?"
                ),
                "schema": {"type": "string"},
            }
        if "ia.counseling" not in answers:
            return {
                "step": "ia.counseling",
                "prompt": (
                    "Would you like the court to order counseling for anyone? Pick any: no one, "
                    "you, the other person, or the children."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["no_one", "me", "defendant", "children"],
                    },
                },
            }
        if "ia.confidential_requests" not in answers:
            return {
                "step": "ia.confidential_requests",
                "prompt": (
                    "This file is public unless you ask the court to protect it. Pick any: seal "
                    "the file, remove your address, seal the children's names and addresses, or "
                    "something else. Leave blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["seal_file", "remove_address", "seal_children", "other"],
                    },
                },
            }
        return None

    # Kentucky Petition/Motion for Order of Protection (AOC-275.1, KRS 403/456) — the
    # respondent dob/sex/race the identifier box needs, the county, the §2 relationship
    # basis, the page-1 CAUTION flags, the emergency/ex-parte election, and the
    # Motion-for-Relief restraints with their details. KY is in the physical gate (the box
    # has a description) but carved out of the vehicle gate (no vehicle field). KY's
    # relationship and relief lists are its own. Maps in vault.forms.ky.
    def _ky_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know their date of birth? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their sex or gender? You can skip this.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The form asks for their race for the order entry. You can pick what fits, "
                    "or skip — Lea defaults to 'unknown'."
                ),
                "schema": {"type": "string"},
            }
        if "ky.county" not in answers:
            return {
                "step": "ky.county",
                "prompt": "Which Kentucky county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ky.relationship_basis" not in answers:
            return {
                "step": "ky.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — married or formerly "
                    "married, a child in common, living together now or before, a family "
                    "relationship (parent, child, grandparent, sibling), a dating relationship, "
                    "or none of those but they stalked or sexually assaulted you."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "married",
                            "formerly_married",
                            "unmarried_child_in_common",
                            "unmarried_living_together",
                            "parent",
                            "child",
                            "stepparent",
                            "grandparent",
                            "grandchild",
                            "adult_sibling",
                            "household_member_child_victim",
                            "dating_relationship",
                            "none_stalking",
                            "none_sexual_assault",
                        ],
                    },
                },
            }
        if "ky.caution" not in answers:
            return {
                "step": "ky.caution",
                "prompt": (
                    "A couple of safety flags for the officers: was a weapon involved, or do "
                    "you believe they're armed and dangerous? Pick any, or leave blank."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["weapon_involved", "armed_dangerous"],
                    },
                },
            }
        if "ky.ex_parte" not in answers:
            return {
                "step": "ky.ex_parte",
                "prompt": (
                    "Do you need an emergency order right away, before they're notified? That's "
                    "for when there's an immediate and present danger."
                ),
                "schema": {"type": "boolean"},
            }
        if "ky.relief" not in answers:
            return {
                "step": "ky.relief",
                "prompt": (
                    "What would you like the court to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_further_acts",
                            "no_contact",
                            "stay_away_distance",
                            "no_damage_property",
                            "vacate_residence",
                            "temporary_custody",
                            "child_support",
                            "possession_pets",
                            "retrieve_belongings",
                            "other",
                        ],
                    },
                },
            }
        ky_relief = answers.get("ky.relief", [])
        if "stay_away_distance" in ky_relief and "ky.stay_away_location" not in answers:
            return {
                "step": "ky.stay_away_location",
                "prompt": (
                    "Which place should they stay away from — your home, school, or work? "
                    "(Note: an address you give here is shared with the other person.)"
                ),
                "schema": {"type": "string"},
            }
        if "vacate_residence" in ky_relief and "ky.vacate_address" not in answers:
            return {
                "step": "ky.vacate_address",
                "prompt": "What's the address of the shared home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "other" in ky_relief and "ky.relief_other_detail" not in answers:
            return {
                "step": "ky.relief_other_detail",
                "prompt": "What else should the court order? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        return None

    # Louisiana Petition for Protection from Abuse (LPOR B, La. R.S. 46:2131) — the parish,
    # the §5 venue basis, the §6 relationship basis, the §8 abuse manner and danger
    # indicators, the §9 ex parte TRO relief, and the §10 other (rule-to-show-cause)
    # requests with their details. LPOR B has an interpreter request (so LA is in the
    # interpreter gate) but no respondent physical/vehicle block (carved out of both). LA's
    # lists are its own. Maps in vault.forms.la.
    def _la_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "la.parish" not in answers:
            return {
                "step": "la.parish",
                "prompt": "Which Louisiana parish will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "la.venue" not in answers:
            return {
                "step": "la.venue",
                "prompt": (
                    "Why is this the right parish to file in? Pick any that fit — it's where "
                    "you and they lived together, where the household is, where they live, "
                    "where the abuse happened, or where you live now."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "marital_domicile",
                            "household",
                            "defendant_resides",
                            "abuse_occurred",
                            "protected_resides",
                        ],
                    },
                },
            }
        if "la.relationship_basis" not in answers:
            return {
                "step": "la.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a current or former "
                    "spouse or dating partner, an intimate cohabitant, a parent or child "
                    "(including step or foster), a grandparent or grandchild, a child of their "
                    "partner, or a child who lived with them."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "spouse",
                            "dating_partner",
                            "intimate_cohabitant",
                            "parent_stepparent_foster",
                            "child_stepchild_foster",
                            "grandparent_ascendant",
                            "child_of_partner",
                            "grandchild_descendant",
                            "child_living_with",
                        ],
                    },
                },
            }
        if "la.abuse_types" not in answers:
            return {
                "step": "la.abuse_types",
                "prompt": (
                    "What has the other person done? Pick any that fit — and only what you're "
                    "comfortable marking. We can always come back to this."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "slapped",
                            "punched",
                            "choked",
                            "shoved",
                            "kicked",
                            "stalked",
                            "abused_pregnant",
                            "threatened_bodily_harm",
                            "threatened_life",
                            "threatened_weapon",
                            "sexually_abused",
                            "abused_children",
                            "abused_pets",
                            "other",
                        ],
                    },
                },
            }
        if "la.danger_indicators" not in answers:
            return {
                "step": "la.danger_indicators",
                "prompt": (
                    "A few questions that help the court understand the risk. Pick any that "
                    "are true: the abuse has gotten more frequent, it's gotten worse, you've "
                    "left during the past year, they own firearms, or they've threatened or "
                    "attempted suicide."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "more_often",
                            "more_severe",
                            "left_past_year",
                            "owns_firearms",
                            "suicide",
                        ],
                    },
                },
            }
        if "la.relief" not in answers:
            return {
                "step": "la.relief",
                "prompt": (
                    "What would you like the judge to order right away? Pick whatever fits — "
                    "there's no wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",  # a
                            "no_contact",  # b
                            "stay_away_residence",  # c
                            "stay_away_work_school",  # d
                            "no_damage_property",  # e
                            "use_residence",  # f
                            "possession_property",  # g
                            "no_transfer_property",  # h
                            "retrieve_belongings",  # i
                            "sheriff_accompany",  # j
                            "temporary_custody",  # k
                            "sheriff_custody",  # l
                            "no_interfere_custody",  # m
                        ],
                    },
                },
            }
        la_relief = answers.get("la.relief", [])
        if "stay_away_residence" in la_relief and "la.residence_address" not in answers:
            return {
                "step": "la.residence_address",
                "prompt": "What's the address they should be ordered to stay away from?",
                "schema": {"type": "string"},
            }
        if "use_residence" in la_relief and "la.use_residence_address" not in answers:
            return {
                "step": "la.use_residence_address",
                "prompt": "What's the address of the home you want to be allowed to use?",
                "schema": {"type": "string"},
            }
        if "possession_property" in la_relief and "la.property_detail" not in answers:
            return {
                "step": "la.property_detail",
                "prompt": (
                    "What property or pets should you keep? List each and where it is, if "
                    "you can."
                ),
                "schema": {"type": "string"},
            }
        if "la.other_requests" not in answers:
            return {
                "step": "la.other_requests",
                "prompt": (
                    "Is there anything more you'd like to ask the court for at the hearing? "
                    "Pick any — child or spousal support, counseling for the other person, "
                    "court costs or attorney's fees, medical care, ordering them to move out, "
                    "or something else. Leave blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "child_support",
                            "spousal_support",
                            "counseling",
                            "evaluation",
                            "court_costs",
                            "attorney_fees",
                            "evaluation_fees",
                            "expert_fees",
                            "medical_care",
                            "vacate",
                            "other",
                        ],
                    },
                },
            }
        if "other" in answers.get("la.other_requests", []) and "la.other_detail" not in answers:
            return {
                "step": "la.other_detail",
                "prompt": "What else should the court order? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        return None

    # Idaho Sworn Petition for Protection Order (CAO DV 1-1, I.C. § 39-6304 / § 18-7907) —
    # the county, the §6 petition type (DV / stalking / phone threats / protected-class),
    # the §2 relationship basis, and the §7 relief (stay-away / move-out / custody /
    # counseling / other) with its details. CAO DV 1-1 has no respondent physical/vehicle
    # block, so ID is in neither gate. ID's lists are its own. Maps in vault.forms.idaho.
    def _id_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "id.county" not in answers:
            return {
                "step": "id.county",
                "prompt": "Which Idaho county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "id.petition_type" not in answers:
            return {
                "step": "id.petition_type",
                "prompt": (
                    "What's this order for? Pick any that fit — domestic violence, stalking, "
                    "telephone threats, or threats based on your race, religion, or national "
                    "origin."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "domestic_violence",
                            "stalking",
                            "telephone_threats",
                            "protected_class_threats",
                        ],
                    },
                },
            }
        if "id.relationship_basis" not in answers:
            return {
                "step": "id.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a spouse or ex, living "
                    "together now or before, a child in common, an intimate partner, a parent, "
                    "a relative, a dating relationship now or before, or something else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "spouse",
                            "former_spouse",
                            "residing_together",
                            "previously_resided",
                            "child_in_common",
                            "intimate_partner",
                            "parent",
                            "related",
                            "dating",
                            "previously_dated",
                            "other",
                        ],
                    },
                },
            }
        if "id.relief" not in answers:
            return {
                "step": "id.relief",
                "prompt": (
                    "What would you like the judge to order? A no-contact order is included by "
                    "default. Pick any others that fit — stay away from places, move out, "
                    "custody, counseling, or something else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "stay_away",
                            "move_out",
                            "child_custody",
                            "treatment_counseling",
                            "other",
                        ],
                    },
                },
            }
        id_relief = answers.get("id.relief", [])
        if "stay_away" in id_relief and "id.stay_away_places" not in answers:
            return {
                "step": "id.stay_away_places",
                "prompt": (
                    "Which places should they stay away from? Pick any — your home, a "
                    "protected child's home, your work or school, the child's work or school, "
                    "the children's school or childcare, or somewhere else."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "my_residence",
                            "minor_residence",
                            "my_workplace_school",
                            "minor_workplace_school",
                            "childrens_school_childcare",
                            "other",
                        ],
                    },
                },
            }
        if "move_out" in id_relief and "id.move_out_address" not in answers:
            return {
                "step": "id.move_out_address",
                "prompt": "What's the address of the home you want them ordered to move from?",
                "schema": {"type": "string"},
            }
        if "treatment_counseling" in id_relief and "id.counseling_detail" not in answers:
            return {
                "step": "id.counseling_detail",
                "prompt": "What kind of treatment or counseling should they be ordered to do?",
                "schema": {"type": "string"},
            }
        if "other" in id_relief and "id.relief_other_detail" not in answers:
            return {
                "step": "id.relief_other_detail",
                "prompt": "What else should the court order? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        if "id.other_cases" not in answers:
            return {
                "step": "id.other_cases",
                "prompt": (
                    "Any other court cases or past protection orders involving the two of you? "
                    "You can describe them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Minnesota Petition for Order for Protection (OFP102, Minn. Stat. § 518B.01) — the
    # respondent dob/gender/race the form needs (OFP102 has no height/weight block, so the
    # physical gate is carved out), the county, the #7 relationship basis, the #13
    # immediate-danger statement, the #15 ex parte relief, and the #16-#22 relief-requiring-
    # a-hearing items with their details. MN's lists are its own. Maps in vault.forms.mn.
    def _mn_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know their date of birth? An approximate age is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their gender? You can skip this.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "Minnesota's form asks for their race (federal reporting). You can pick "
                    "what fits, or skip."
                ),
                "schema": {"type": "string"},
            }
        if "mn.county" not in answers:
            return {
                "step": "mn.county",
                "prompt": "Which Minnesota county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "mn.relationship_basis" not in answers:
            return {
                "step": "mn.relationship_basis",
                "prompt": (
                    "How do you know them? Pick any that fit — married or divorced, living "
                    "together now or before, a child (or unborn child) together, parent and "
                    "child, related by blood, or a significant romantic or sexual relationship."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "married",
                            "divorced",
                            "currently_live_together",
                            "used_to_live_together",
                            "child_together",
                            "unborn_child_together",
                            "parent_child",
                            "related_by_blood",
                            "romantic_sexual",
                        ],
                    },
                },
            }
        if "mn.immediate_danger" not in answers:
            return {
                "step": "mn.immediate_danger",
                "prompt": (
                    "Do you believe the abuse will continue and that you (or others you're "
                    "protecting) are in immediate danger? Yes or no is fine."
                ),
                "schema": {"type": "boolean"},
            }
        if "mn.relief" not in answers:
            return {
                "step": "mn.relief",
                "prompt": (
                    "What would you like the judge to order right away (no hearing needed)? "
                    "Pick whatever fits — there's no wrong answer."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_harm",  # a
                            "no_contact",  # b
                            "stay_away_home",  # c
                            "stay_away_work",  # d
                            "stay_away_other",  # e
                            "insurance",  # f
                            "pet_possession",  # g
                            "no_pet_abuse",  # h
                            "le_assist",  # i
                            "other",  # j
                        ],
                    },
                },
            }
        mn_relief = answers.get("mn.relief", [])
        if "stay_away_other" in mn_relief and "mn.other_location" not in answers:
            return {
                "step": "mn.other_location",
                "prompt": "What other location should they be ordered to stay away from?",
                "schema": {"type": "string"},
            }
        if "pet_possession" in mn_relief and "mn.pet_detail" not in answers:
            return {
                "step": "mn.pet_detail",
                "prompt": "Which pet or companion animal, and how should its care be handled?",
                "schema": {"type": "string"},
            }
        if "other" in mn_relief and "mn.relief_other_detail" not in answers:
            return {
                "step": "mn.relief_other_detail",
                "prompt": "What else should the court order right away? Describe it, or skip.",
                "schema": {"type": "string"},
            }
        if "mn.hearing_relief" not in answers:
            return {
                "step": "mn.hearing_relief",
                "prompt": (
                    "Some things need a hearing first. Would you like to ask for any? Pick any "
                    "— custody or parenting time, financial support, use of property, "
                    "restitution, counseling for the respondent, a firearms restriction, or a "
                    "longer (up to 50-year) order. Leave blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "custody_parenting",
                            "financial_support",
                            "property",
                            "restitution",
                            "counseling",
                            "firearms",
                            "extended_term",
                        ],
                    },
                },
            }
        if (
            "financial_support" in answers.get("mn.hearing_relief", [])
            and "mn.support_detail" not in answers
        ):
            return {
                "step": "mn.support_detail",
                "prompt": (
                    "For support — what do you need, and what are the incomes if you know them? "
                    "You can include child support, your living expenses, or medical support."
                ),
                "schema": {"type": "string"},
            }
        if "mn.other_cases" not in answers:
            return {
                "step": "mn.other_cases",
                "prompt": (
                    "Any other family, domestic-abuse, or harassment cases between the two of "
                    "you? You can describe them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Mississippi Petition for Domestic Abuse Protection Order (M.C.A. § 93-21-1) — the
    # respondent dob/sex/race the §4 identifier block needs, the county/court type, the
    # emergency-relief election, the §1 relationship basis, the §5 acts of abuse, the §4
    # caution flags, the §9 relief, and the Chancery/County-only relief. The §4 block has a
    # physical description (so MS is in the physical gate) but no vehicle block (carved out).
    # MS's lists are its own. Maps in vault.forms.ms.
    def _ms_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know their date of birth? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their sex? You can skip this.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The form asks for their race for the order entry. You can pick what fits, "
                    "or skip."
                ),
                "schema": {"type": "string"},
            }
        if "ms.county" not in answers:
            return {
                "step": "ms.county",
                "prompt": "Which Mississippi county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "ms.court_type" not in answers:
            return {
                "step": "ms.court_type",
                "prompt": (
                    "Which court are you filing in? Chancery and County courts can also handle "
                    "custody and support; Justice and Municipal courts handle the protection "
                    "order itself."
                ),
                "schema": {
                    "type": "string",
                    "enum": ["chancery", "county", "justice", "municipal"],
                },
            }
        if "ms.emergency_relief" not in answers:
            return {
                "step": "ms.emergency_relief",
                "prompt": (
                    "Do you need emergency relief right away, before a hearing? Yes or no is "
                    "fine."
                ),
                "schema": {"type": "boolean"},
            }
        if "ms.relationship_basis" not in answers:
            return {
                "step": "ms.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a current or former "
                    "spouse, lived together as spouses, a child in common, a current or former "
                    "dating partner, or related by blood or marriage and living together now "
                    "or before."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "current_former_spouse",
                            "lived_as_spouse",
                            "child_in_common",
                            "dating_partner",
                            "related_cohabit",
                        ],
                    },
                },
            }
        if "ms.abuse_acts" not in answers:
            return {
                "step": "ms.abuse_acts",
                "prompt": (
                    "What has the other person done? Pick any that fit — caused or tried to "
                    "cause bodily injury, placed you in fear of imminent serious injury, "
                    "criminal sexual conduct against a minor, stalking or cyber-stalking, or "
                    "sexual battery or rape."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "attempted_bodily_injury",
                            "physical_menace_fear",
                            "criminal_sexual_minor",
                            "stalking_cyberstalking",
                            "sexual_battery_rape",
                        ],
                    },
                },
            }
        if "ms.caution" not in answers:
            return {
                "step": "ms.caution",
                "prompt": (
                    "A few safety flags for the officers serving the papers. Pick any that "
                    "apply, or leave blank: armed and dangerous, escape risk, abuses drugs, "
                    "martial-arts trained, needs medication, or another condition."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "alcoholic",
                            "allergies",
                            "armed_dangerous",
                            "diabetic",
                            "epilepsy",
                            "escape_risk",
                            "explosive",
                            "hemophiliac",
                            "heart_condition",
                            "intl_flight_risk",
                            "abuse_drugs",
                            "martial_arts",
                            "medication",
                            "other",
                        ],
                    },
                },
            }
        if "ms.relief" not in answers:
            return {
                "step": "ms.relief",
                "prompt": (
                    "What would you like the court to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "prohibit_abuse",
                            "prohibit_contact",
                            "prohibit_distance",
                            "prohibit_property_transfer",
                            "sole_use_residence",
                            "le_possession_residence",
                            "le_possession_belongings",
                            "court_costs",
                            "other",
                        ],
                    },
                },
            }
        ms_relief = answers.get("ms.relief", [])
        if "sole_use_residence" in ms_relief and "ms.residence_address" not in answers:
            return {
                "step": "ms.residence_address",
                "prompt": "What's the address of the residence you want sole use of?",
                "schema": {"type": "string"},
            }
        if "le_possession_belongings" in ms_relief and "ms.belongings_location" not in answers:
            return {
                "step": "ms.belongings_location",
                "prompt": (
                    "Where would you need an officer's help to recover your belongings — the "
                    "shared residence, their residence, or somewhere else?"
                ),
                "schema": {"type": "string"},
            }
        if (
            answers.get("ms.court_type") in {"chancery", "county"}
            and "ms.chancery_relief" not in answers
        ):
            return {
                "step": "ms.chancery_relief",
                "prompt": (
                    "Since you're in Chancery or County court, you can also ask for custody or "
                    "support. Pick any — temporary custody/support, a visitation schedule, "
                    "monetary support, or restitution. Leave blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "custody_support",
                            "visitation",
                            "monetary_support",
                            "restitution",
                        ],
                    },
                },
            }
        if "ms.other_cases" not in answers:
            return {
                "step": "ms.other_cases",
                "prompt": (
                    "Any other protection petitions pending or orders already in place against "
                    "them? You can describe them, or skip."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Indiana Petition for an Order for Protection (OJA-PO-0100, I.C. 34-26-5) — the county,
    # the §3 respondent age, the §1 victim basis, the §2 relationship basis, the §5 venue,
    # the §7 acts, the §9 protective relief and after-hearing relief with their details.
    # OJA-PO-0100 has no respondent physical/vehicle block, so IN is in neither gate. IN's
    # lists are its own. Maps in vault.forms.indiana (package name — "IN" is a keyword).
    def _in_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "in.county" not in answers:
            return {
                "step": "in.county",
                "prompt": "Which Indiana county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "respondent.age" not in answers:
            return {
                "step": "respondent.age",
                "prompt": "About how old is the other person? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "in.victim_basis" not in answers:
            return {
                "step": "in.victim_basis",
                "prompt": (
                    "What brings you here? Pick any that fit — you're a victim of domestic or "
                    "family violence, a sex offense, stalking, or repeated harassment."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "dv_family_violence",
                            "sex_offense",
                            "stalking",
                            "repeated_harassment",
                        ],
                    },
                },
            }
        if "in.relationship_basis" not in answers:
            return {
                "step": "in.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a spouse or ex, lived "
                    "together in an intimate relationship, a child in common, dating, a sexual "
                    "relationship, related by blood/adoption/marriage, a guardian/ward/"
                    "custodian/foster relationship, or — if they're not family — stalking, a "
                    "sex offense, or repeated harassment."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "spouse",
                            "former_spouse",
                            "intimate_cohabitant",
                            "child_in_common",
                            "dating",
                            "sexual_relationship",
                            "related_blood_adoption",
                            "related_marriage",
                            "guardian",
                            "ward",
                            "custodian",
                            "foster_parent",
                            "minor_child_of_relationship",
                            "nonfamily_stalking",
                            "nonfamily_sex_offense",
                            "nonfamily_harassment",
                        ],
                    },
                },
            }
        if "in.venue" not in answers:
            return {
                "step": "in.venue",
                "prompt": (
                    "Why this county? Pick any — the respondent lives here, the incident "
                    "happened here, or you live here."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["respondent_lives", "incident_here", "i_live"],
                    },
                },
            }
        if "in.abuse_acts" not in answers:
            return {
                "step": "in.abuse_acts",
                "prompt": (
                    "What has the other person done? Pick any that fit — and only what you're "
                    "comfortable marking."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "attempted_harm",
                            "threatened_harm",
                            "caused_harm",
                            "fear_harm",
                            "forced_sexual",
                            "stalking",
                            "sex_offense",
                            "animal_cruelty",
                            "repeated_harassment",
                        ],
                    },
                },
            }
        if "in.relief" not in answers:
            return {
                "step": "in.relief",
                "prompt": (
                    "What would you like the judge to order? These can be granted right away. "
                    "Pick whatever fits — there's no wrong answer."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "prohibit_dv",
                            "prohibit_dv_household",
                            "no_tracking",
                            "no_contact",
                            "stay_away",
                            "stay_away_family_locations",
                            "evict",
                            "possession",
                            "no_animal_harm",
                            "exclusive_animal_care",
                            "additional_safety",
                            "no_firearm",
                            "surrender_firearm",
                            "wireless_transfer",
                        ],
                    },
                },
            }
        in_relief = answers.get("in.relief", [])
        if "stay_away" in in_relief and "in.stay_away_location" not in answers:
            return {
                "step": "in.stay_away_location",
                "prompt": "Which place should they stay away from — your home, school, or work?",
                "schema": {"type": "string"},
            }
        if "evict" in in_relief and "in.evict_address" not in answers:
            return {
                "step": "in.evict_address",
                "prompt": "What's the address of the home you want them ordered to leave?",
                "schema": {"type": "string"},
            }
        if "possession" in in_relief and "in.possession_detail" not in answers:
            return {
                "step": "in.possession_detail",
                "prompt": (
                    "What should you keep — the residence, a vehicle, or other personal items? "
                    "List what you need."
                ),
                "schema": {"type": "string"},
            }
        if "surrender_firearm" in in_relief and "in.firearm_detail" not in answers:
            return {
                "step": "in.firearm_detail",
                "prompt": "Which firearms or weapons should they surrender? Describe what you can.",
                "schema": {"type": "string"},
            }
        if "wireless_transfer" in in_relief and "in.wireless_detail" not in answers:
            return {
                "step": "in.wireless_detail",
                "prompt": "Which phone number(s) should be transferred to you, and the carrier?",
                "schema": {"type": "string"},
            }
        if "in.hearing_relief" not in answers:
            return {
                "step": "in.hearing_relief",
                "prompt": (
                    "Some things need a hearing first. Would you like to ask for any? Pick any "
                    "— parenting time arrangements, supervised or no parenting time, attorney "
                    "fees, rent or mortgage, child support, maintenance, or reimbursement for "
                    "expenses. Leave blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "parenting_time",
                            "supervised_parenting",
                            "deny_parenting",
                            "attorney_fees",
                            "rent",
                            "mortgage",
                            "child_support",
                            "maintenance",
                            "reimburse_expenses",
                        ],
                    },
                },
            }
        in_hearing = answers.get("in.hearing_relief", [])
        support_items = {"rent", "mortgage", "child_support", "maintenance", "reimburse_expenses"}
        if support_items & set(in_hearing) and "in.support_detail" not in answers:
            return {
                "step": "in.support_detail",
                "prompt": (
                    "For the financial requests — what amounts do you need, and for what "
                    "(rent, child support, expenses)? You can include documentation later."
                ),
                "schema": {"type": "string"},
            }
        return None

    # Missouri Petition for a Court Order of Protection - Adult (AA40, RSMo 455) — the
    # respondent age/sex/race the §A block needs, the county, the venue, the §A relationship
    # basis, the §B acts and ex-parte basis, the §C(1) relief, the §C(2) serious-danger
    # finding, and the §C(3-7) additional relief with details. The §A block has a physical
    # description (MO in the physical gate) and §B a vehicle question (MO in the vehicle
    # gate). MO's lists are its own. Maps in vault.forms.mo.
    def _mo_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.age" not in answers:
            return {
                "step": "respondent.age",
                "prompt": "About how old is the other person? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their sex? You can skip this.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "Missouri's form asks for their race or ethnicity. You can pick what fits, "
                    "or skip."
                ),
                "schema": {"type": "string"},
            }
        if "mo.county" not in answers:
            return {
                "step": "mo.county",
                "prompt": (
                    "Which Missouri county will you file in? "
                    "(St. Louis City counts as a county.)"
                ),
                "schema": {"type": "string", "minLength": 1},
            }
        if "mo.venue" not in answers:
            return {
                "step": "mo.venue",
                "prompt": (
                    "Why this county? Pick any — you live here, the abuse happened here, or "
                    "the respondent can be served here."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["i_live", "abuse_happened", "respondent_served"],
                    },
                },
            }
        if "mo.relationship_basis" not in answers:
            return {
                "step": "mo.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick any that fit — a spouse or ex, a "
                    "child in common, a continuing romantic/social relationship, lived together "
                    "(with or without intimacy), related by blood or marriage, or — if none of "
                    "those — stalking or sexual assault."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "spouse",
                            "former_spouse",
                            "child_in_common",
                            "continuing_social_romantic",
                            "resided_with_intimacy",
                            "resided_no_intimacy",
                            "related_blood",
                            "related_marriage",
                            "stalking",
                            "sexual_assault",
                        ],
                    },
                },
            }
        if "mo.abuse_acts" not in answers:
            return {
                "step": "mo.abuse_acts",
                "prompt": (
                    "What has the other person done? Pick any that fit — and only what you're "
                    "comfortable marking."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "caused_harm",
                            "fear_harm",
                            "coerced",
                            "stalked",
                            "harassed",
                            "sexually_assaulted",
                            "unlawfully_imprisoned",
                            "followed",
                            "abused_pet",
                            "threatened",
                        ],
                    },
                },
            }
        if "mo.ex_parte_basis" not in answers:
            return {
                "step": "mo.ex_parte_basis",
                "prompt": (
                    "For an emergency order right away, pick any that are true: I'm afraid of "
                    "the respondent, there's an immediate and present danger, there are other "
                    "good reasons, or I have evidence (photos, texts, messages)."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "afraid",
                            "immediate_danger",
                            "other_reasons",
                            "has_evidence",
                        ],
                    },
                },
            }
        if "mo.relief" not in answers:
            return {
                "step": "mo.relief",
                "prompt": (
                    "What would you like the court to order the respondent NOT to do? Pick "
                    "whatever fits — there's no wrong answer."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_dv",
                            "no_pet_abuse",
                            "no_enter_home",
                            "no_enter_school",
                            "no_enter_work",
                            "stay_distance",
                            "no_communicate",
                            "other",
                        ],
                    },
                },
            }
        mo_relief = answers.get("mo.relief", [])
        if "no_enter_school" in mo_relief and "mo.school_address" not in answers:
            return {
                "step": "mo.school_address",
                "prompt": "What's the address of your school?",
                "schema": {"type": "string"},
            }
        if "no_enter_work" in mo_relief and "mo.work_address" not in answers:
            return {
                "step": "mo.work_address",
                "prompt": "What's the address of your work?",
                "schema": {"type": "string"},
            }
        if "stay_distance" in mo_relief and "mo.stay_distance_feet" not in answers:
            return {
                "step": "mo.stay_distance_feet",
                "prompt": "How many feet should they have to stay away from you?",
                "schema": {"type": "string"},
            }
        if "mo.serious_danger" not in answers:
            return {
                "step": "mo.serious_danger",
                "prompt": (
                    "Do you want to ask for a longer order (2 to 10 years) because the "
                    "respondent poses a serious danger? Yes or no — we can revisit it."
                ),
                "schema": {"type": "boolean"},
            }
        if "mo.additional_relief" not in answers:
            return {
                "step": "mo.additional_relief",
                "prompt": (
                    "Anything more to ask for? Pick any — custody, child support or "
                    "maintenance, rent/mortgage or shelter or medical costs, court costs or "
                    "attorney fees, possession of property, counseling or substance-abuse "
                    "treatment, a pet, closing your voter address, or something else. Leave "
                    "blank to skip."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "custody",
                            "child_support",
                            "maintenance",
                            "rent_mortgage",
                            "shelter_costs",
                            "medical_costs",
                            "court_costs",
                            "attorney_fees",
                            "possession_property",
                            "prohibit_transfer",
                            "counseling",
                            "substance_abuse",
                            "auto_renew",
                            "wireless_transfer",
                            "pet_possession",
                            "voter_address",
                            "other",
                        ],
                    },
                },
            }
        mo_additional = answers.get("mo.additional_relief", [])
        if "custody" in mo_additional and "mo.custody_detail" not in answers:
            return {
                "step": "mo.custody_detail",
                "prompt": "For custody — which children, and what arrangement are you asking for?",
                "schema": {"type": "string"},
            }
        mo_support = {
            "child_support",
            "maintenance",
            "rent_mortgage",
            "shelter_costs",
            "medical_costs",
        }
        if mo_support & set(mo_additional) and "mo.support_detail" not in answers:
            return {
                "step": "mo.support_detail",
                "prompt": (
                    "For the financial requests — what amounts do you need, and how often "
                    "(weekly or monthly)?"
                ),
                "schema": {"type": "string"},
            }
        if "possession_property" in mo_additional and "mo.property_detail" not in answers:
            return {
                "step": "mo.property_detail",
                "prompt": "Which personal property should you keep? List the items.",
                "schema": {"type": "string"},
            }
        return None

    # South Carolina Petition for Family Court Order of Protection (SCCA 425) — the
    # respondent dob/race/sex the §4 block needs (SCCA 425 has no height/weight block, so
    # the physical gate is carved out), the county, the §1 venue, the §7 relationship basis,
    # and the §9 relief (items a-q) with details. SCCA 425 has no vehicle block (carved
    # out). SC's lists are its own. Maps in vault.forms.sc.
    def _sc_step(self, answers: dict[str, Any]) -> dict[str, Any] | None:
        if "respondent.dob" not in answers:
            return {
                "step": "respondent.dob",
                "prompt": "Do you know their date of birth? An estimate is fine.",
                "schema": {"type": "string"},
            }
        if "respondent.race" not in answers:
            return {
                "step": "respondent.race",
                "prompt": (
                    "The form asks for their race. You can pick what fits, or skip."
                ),
                "schema": {"type": "string"},
            }
        if "respondent.gender" not in answers:
            return {
                "step": "respondent.gender",
                "prompt": "How would you describe their sex? You can skip this.",
                "schema": {"type": "string"},
            }
        if "sc.county" not in answers:
            return {
                "step": "sc.county",
                "prompt": "Which South Carolina county will you file in?",
                "schema": {"type": "string", "minLength": 1},
            }
        if "sc.venue" not in answers:
            return {
                "step": "sc.venue",
                "prompt": (
                    "Why this county? Pick what fits — the abuse happened here, the respondent "
                    "lives here, they last lived with you here and you still live here, or none "
                    "of those but you live here and want the case transferred."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "abuse_occurred",
                            "respondent_lives",
                            "last_lived_here",
                            "transfer_request",
                        ],
                    },
                },
            }
        if "sc.relationship_basis" not in answers:
            return {
                "step": "sc.relationship_basis",
                "prompt": (
                    "How are you connected to them? Pick one or more — married, previously "
                    "married, a child in common, living together romantically (now or before), "
                    "or family members where sexual abuse is alleged."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "married",
                            "previously_married",
                            "child_in_common",
                            "live_together_romantic",
                            "formerly_lived_romantic",
                            "family_sexual_abuse",
                        ],
                    },
                },
            }
        if "sc.relief" not in answers:
            return {
                "step": "sc.relief",
                "prompt": (
                    "What would you like the court to order? Pick whatever fits — there's no "
                    "wrong answer and we can change it later."
                ),
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "no_abuse",
                            "stop_offensive",
                            "no_communicate",
                            "stay_away",
                            "custody",
                            "child_support",
                            "financial_support",
                            "exclusive_home",
                            "insurance",
                            "no_property_disposal",
                            "no_pet_harm",
                            "possession_property",
                            "le_assist",
                            "reimburse_fees",
                            "hearing_15_days",
                            "emergency_hearing_24h",
                            "other",
                        ],
                    },
                },
            }
        sc_relief = answers.get("sc.relief", [])
        if "stay_away" in sc_relief and "sc.stay_away_location" not in answers:
            return {
                "step": "sc.stay_away_location",
                "prompt": "Which place should they stay away from — your home, work, or school?",
                "schema": {"type": "string"},
            }
        if "custody" in sc_relief and "sc.custody_detail" not in answers:
            return {
                "step": "sc.custody_detail",
                "prompt": (
                    "For custody — which children, and do you want the respondent to have "
                    "visitation or not?"
                ),
                "schema": {"type": "string"},
            }
        if "exclusive_home" in sc_relief and "sc.home_address" not in answers:
            return {
                "step": "sc.home_address",
                "prompt": "What's the address of the home you want exclusive use of?",
                "schema": {"type": "string"},
            }
        sc_property = {"possession_property", "le_assist"}
        if (sc_property & set(sc_relief)) and "sc.property_detail" not in answers:
            return {
                "step": "sc.property_detail",
                "prompt": (
                    "Which personal property or pets should you keep, and do you need an "
                    "officer's help to get them?"
                ),
                "schema": {"type": "string"},
            }
        if "other" in sc_relief and "sc.relief_other_detail" not in answers:
            return {
                "step": "sc.relief_other_detail",
                "prompt": "What else should the court order? Describe it, or skip.",
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
        "OH": _oh_step,
        "ND": _nd_step,
        "NM": _nm_step,
        "NH": _nh_step,
        "MT": _mt_step,
        "NV": _nv_step,
        "NE": _ne_step,
        "ME": _me_step,
        "MI": _mi_step,
        "IA": _ia_step,
        "KY": _ky_step,
        "LA": _la_step,
        "ID": _id_step,
        "MN": _mn_step,
        "MS": _ms_step,
        "IN": _in_step,
        "MO": _mo_step,
        "SC": _sc_step,
    }


def determine_next_step(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Public entry point for the Vault intake state machine.

    Delegates to `IntakeStateMachine`; the signature and return contract are
    unchanged (called by `handle_intake_step` and the test-suite).
    """
    return IntakeStateMachine().next_step(jurisdiction, answers)
