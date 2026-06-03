"""California DV-100 form mapping (reference implementation).

Maps completed Vault intake answers onto the fields of California Judicial
Council form **DV-100, _Request for Domestic Violence Restraining Order_**
(Rev. January 1, 2025). This is the first jurisdiction and the pattern the
other 46 follow under their own modules in this package.

What this module does NOT do, on purpose:
- It does not render a PDF. It returns a structured `item -> value` map that
  lea-be-core stamps onto the official fillable form. Keeping the heavy
  render step out of the Worker respects the Pyodide dependency budget and
  the stateless contract.
- It does not guess. A required field with no intake answer is reported as
  `[FACT NEEDED]`, never invented.
- It does not make legal calls. Any mapping where an intake answer might land
  in the wrong box is flagged `needs_legal_review=True` for a licensed
  attorney (Pranav / managing attorney) to confirm. Unflagged != trusted —
  it means "mechanically obvious," not "legally signed off."

The intake graph (`vault.intake.TIER_1_FLOW` + the CA Tier-2 branches) feeds
this. Where the form asks for something intake does not yet collect, the field
is reported `not_collected` so the gap is visible rather than silently blank.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "DV-100"
FORM_REVISION = "2025-01-01"
JURISDICTION = "CA"


def _age_from_dob(answers: dict[str, Any]) -> str | None:
    dob_str = answers.get("petitioner.dob")
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    age = today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))
    return str(age)


# Intake captures `relationship.type` as one enum value; DV-100 item 3 is a set
# of checkboxes. This maps the enum to the box that gets checked. NOTE for legal
# review: the intake enum cannot currently distinguish "married" from "used to
# be married" (3b vs 3c) — see item 3c's note.
_RELATIONSHIP_ENUM_TO_ITEM = {
    "married": "3b",
    "dating": "3d",
    "engaged": "3e",
    "cohabiting": "3g",
    "child_in_common": "3a",
}


# DV-100 item -> the `selected_reliefs_intents` key that checks it. Intake
# collects the survivor's chosen orders as this list; each box is checked when
# its key is present.
_ITEM_TO_RELIEF = {
    "10": "no_abuse",
    "11": "no_contact",
    "12": "stay_away",
    "13": "move_out",
    "16": "protect_animals",
    "17": "property_control",
    "18": "no_insurance_changes",
    "19": "record_communications",
    "22": "pay_debts",
    "23": "pay_expenses",
    "24": "child_support",
    "25": "spousal_support",
    "26": "attorney_fees",
    "27": "batterer_program",
    "28": "transfer_phone",
}


def _relationship_check(item: str) -> Callable[[dict[str, Any]], str | None]:
    """Build a derive fn that checks DV-100 item 3 box `item` when intake says so."""

    def _derive(answers: dict[str, Any]) -> str | None:
        rel_type = answers.get("relationship.type")
        if isinstance(rel_type, str) and _RELATIONSHIP_ENUM_TO_ITEM.get(rel_type) == item:
            return "checked"
        # 3a (child together) and 3g (live together) also have dedicated booleans.
        if item == "3a" and answers.get("relationship.children_in_common") is True:
            return "checked"
        if item == "3g" and (
            answers.get("relationship.live_together_now") is True
            or answers.get("relationship.lived_together_past") is True
        ):
            return "checked"
        return None

    return _derive


def _marriage_check(*, intact: bool) -> Callable[[dict[str, Any]], str | None]:
    """Check item 3b (currently married) or 3c (formerly married).

    Driven by `relationship.marriage_intact`: True => 3b, False => 3c. If the
    follow-up is unanswered, default to currently-married (3b) so a married
    filer's relationship box is never silently left blank.
    """

    def _derive(answers: dict[str, Any]) -> str | None:
        if answers.get("relationship.type") != "married":
            return None
        is_intact = answers.get("relationship.marriage_intact", True)
        return "checked" if is_intact == intact else None

    return _derive


# DV-100 item 5/6/7 share sub-lettering (a=date ... g=frequency). Item 5 is
# Tier-1; items 6 and 7 are the optional extra incidents, read from intake's
# `incident_2.*` / `incident_3.*` answers.
_INCIDENT_SUBFIELDS = [
    ("a", "date", "date"),
    ("b", "witnesses_present", "witnesses"),
    ("c", "weapon_involved", "weapon"),
    ("d", "injury", "harm"),
    ("e", "police_called", "police came"),
    ("f", "narrative", "details"),
    ("g", "pattern_frequency", "frequency"),
]


# ---------------------------------------------------------------------------
# Field table. Ordered by DV-100 item number. Items 1-9 are the factual core
# the intake graph feeds today; items 10-31 (the "orders you want a judge to
# make" section) are largely not collected yet — they are listed so the gap is
# explicit. See DV-100_coverage.md for the full gap analysis.
# ---------------------------------------------------------------------------
CA_DV100_FIELDS: tuple[FormField, ...] = (
    # 1 — Person Asking for Protection (petitioner)
    FormField("1a", "Petitioner full name", source="petitioner.legal_name", required=True),
    FormField("1b", "Petitioner age", derive=_age_from_dob, required=True,
              note="Derived from petitioner.dob; form asks age, not DOB."),
    FormField("1c", "Address to receive court papers", source="petitioner.safe_mailing_address",
              required=True, needs_legal_review=True,
              note="Intake stores one free-text address; form splits Address/City/State/Zip. "
                   "lea-be-core or a parse step must split into components."),
    FormField("1d_phone", "Petitioner phone (optional)", source="petitioner.safe_phone"),
    FormField("1d_email", "Petitioner email (optional)", source="petitioner.safe_email"),
    # 1e lawyer info — survivor self-represents in the Vault flow; left blank by design.

    # 2 — Person You Want Protection From (respondent)
    FormField("2a", "Respondent full name", source="respondent.legal_name", required=True),
    FormField("2b", "Respondent age (estimate ok)", source="respondent.age"),
    FormField("2c", "Respondent date of birth (if known)", source="respondent.dob"),
    FormField("2d", "Respondent gender", source="respondent.gender",
              note="Reads respondent.gender — NOT petitioner.gender. Do not confuse them."),
    FormField("2e", "Respondent race", source="respondent.race"),

    # 3 — Relationship (checkboxes, derived from relationship.type + booleans)
    FormField("3a", "We have a child together", derive=_relationship_check("3a"),
              needs_legal_review=True),
    FormField("3b", "We are married / registered domestic partners",
              derive=_marriage_check(intact=True), needs_legal_review=True),
    FormField("3c", "We used to be married / registered domestic partners",
              derive=_marriage_check(intact=False), needs_legal_review=True),
    FormField("3d", "We are dating or used to date", derive=_relationship_check("3d"),
              needs_legal_review=True),
    FormField("3e", "We are/were engaged", derive=_relationship_check("3e"),
              needs_legal_review=True),
    FormField("3g", "We live / used to live together", derive=_relationship_check("3g"),
              needs_legal_review=True),

    # 4 — Other restraining orders & court cases
    FormField("4a", "Other restraining orders exist", source="prior_orders.exists",
              note="Form also wants order/expiry dates; intake collects existence only."),
    FormField("4b", "Other court case with respondent", source=None,
              note="Not collected by intake yet — coverage gap G4."),

    # 5 — Most Recent Abuse (first incident in incidents[])
    FormField("5a", "Date of most recent abuse", source="incidents[].date", required=True),
    FormField("5b", "Witnesses present", source="incidents[].witnesses_present"),
    FormField("5c", "Weapon used/threatened", source="incidents[].weapon_involved"),
    FormField("5d", "Emotional or physical harm", source="incidents[].injury"),
    FormField("5e", "Police came", source="incidents[].police_called"),
    FormField("5f", "Details of the abuse", source="incidents[].narrative", required=True,
              note="Survivor's own words — must pass through verbatim (guardrail G-08)."),
    FormField("5g", "Frequency", source="incidents[].pattern_frequency"),

    # 6, 7 — Additional incidents. Generated granularly (6a-6g, 7a-7g) from the
    # optional incident_2.* / incident_3.* answers — see the tuple-append below.

    # 8 — Other Protected People
    FormField("8", "Other protected people (children/household)",
              source="protected_persons.children[]",
              note="Names + 'why'; per-person age/relationship/lives-with stay optional."),
    FormField("8_why", "Why protected people need protection", source="protected_persons.why"),

    # 9 — Firearms
    FormField("9_access", "Respondent has firearms/ammunition",
              source="firearm.respondent_has_access"),
    FormField("9_types", "Firearm description", source="firearm.types[]"),
    FormField("9_locations", "Firearm location", source="firearm.locations[]"),

    # 10-28 — Orders the petitioner is requesting. Intake collects these as the
    # `selected_reliefs_intents` list (the survivor's own choices); each box is
    # checked by membership. Items needing a parameter (12 distance/places, 13
    # address, 16 animals) read dedicated `relief.*` answers.
    FormField("10", "Order to not abuse", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("11", "No-contact order", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("12", "Stay-away order", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("12_places", "Stay-away places", source="relief.stay_away_places",
              note="Which places (home/work/school/vehicle/...) — checked per selection."),
    FormField("12_distance", "Stay-away distance (yards)",
              source="relief.stay_away_distance_yards",
              note="Defaults to 100 yards on the form if the survivor didn't pick another."),
    FormField("13", "Move-out order", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("13_address", "Move-out home address", source="relief.move_out_address"),
    FormField("16", "Protect animals", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("16_list", "Animals to protect", source="relief.animals[]"),
    FormField("17", "Control of property", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("17_describe", "Property to control", source="relief.property_describe"),
    FormField("17_why", "Why control of property", source="relief.property_why"),
    FormField("18", "No insurance changes", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("19", "Record communications", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("22", "Pay debts owed for property", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("22_items", "Debts to pay (itemized)", source="relief.debts"),
    FormField("23", "Pay expenses caused by abuse", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("23_items", "Expenses to pay (itemized)", source="relief.expenses"),
    FormField("24", "Child support requested", source="selected_reliefs_intents",
              needs_legal_review=True,
              note="Intake gates petitioner.ssn on this selection. Confirm box mapping."),
    FormField("25", "Spousal support requested", source="selected_reliefs_intents",
              needs_legal_review=True,
              note="Married/registered partners only — confirm gate."),
    FormField("26", "Lawyer's fees and costs", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("27", "Batterer intervention program", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("28", "Transfer wireless phone account", source="selected_reliefs_intents",
              needs_legal_review=True),
    FormField("28_numbers", "Phone numbers to transfer",
              source="relief.transfer_phone_numbers"),
    # 29-31 (no firearms / no body armor / cannot look for protected people) are
    # AUTOMATIC if the order is granted — not requested, so no intake question.

    # 20, 21 (property restraint / extend service deadline) are situational and
    # not in the requested-orders set yet — coverage gap G20-21.

    # 33 — Signature
    FormField("33_name", "Petitioner printed name (signature block)",
              source="petitioner.legal_name", required=True),
    # 33 date + wet/e-signature are applied at filing time, not assembled here.
)

# Items 6 and 7 (optional extra incidents) mirror item 5's a-g sub-fields,
# generated from the intake's incident_2.* / incident_3.* answers.
CA_DV100_FIELDS += tuple(
    FormField(f"{item}{letter}", f"Incident {idx} — {label}", source=f"incident_{idx}.{key}")
    for idx, item in ((2, "6"), (3, "7"))
    for letter, key, label in _INCIDENT_SUBFIELDS
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """CA resolver — adds the relief-checkbox rule, else the basic lookup.

    `selected_reliefs_intents` is one intake list that checks many DV-100 boxes,
    one per requested order (item -> relief key in `_ITEM_TO_RELIEF`).
    """
    if f.source == "selected_reliefs_intents" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _ITEM_TO_RELIEF.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto DV-100 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=CA_DV100_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
