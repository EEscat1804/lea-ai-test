"""Ohio Petition for Domestic Violence Civil Protection Order form mapping.

Maps Vault intake answers onto Ohio **Form 10.01-D, _Petition for Domestic
Violence Civil Protection Order_** (R.C. 3113.31, Amended April 15, 2021). The
petition covers the parties, an interpreter request, the ex parte request, who
needs protection, the relationship basis, other protected household members, the
abuse narrative, optional aggravating factors (item 7), and the item-9 (a-n)
relief list.

The OH intake section (`vault.intake`, the `jurisdiction == "OH"` block plus the
shared interpreter / physical-description / vehicle blocks — OH is in those sets)
feeds the OH-specific items. OH's relief list is its own, distinct from the other
states'. (OH has no respondent physical/vehicle section on this form, so those
shared answers are collected but not mapped here.)

Protection: the form is a public record and instructs the petitioner to use a
safe mailing address; intake only ever holds a safe mailing address. See
coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "10.01-D"
FORM_REVISION = "2021-04"  # Amended April 15, 2021
JURISDICTION = "OH"


def _respondent_adult(answers: dict[str, Any]) -> str | None:
    """Caption — "Respondent is 18 years old or older", from respondent.dob."""
    dob_str = answers.get("respondent.dob")
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    age = today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))
    return "checked" if age >= 18 else None


def _full_hearing(_answers: dict[str, Any]) -> str:
    """Item 2 — a full hearing is always requested, even if ex parte is granted/denied."""
    return "checked"


def _in_fear(_answers: dict[str, Any]) -> str:
    """Item 8 — petitioner is in fear and in continuing danger."""
    return "checked"


# Item 3 — who needs protection. Membership over `oh.who_needs_protection`.
_OH_WHO = {
    "who_me": "me",
    "who_minor_children": "minor_children",
    "who_household_member": "household_member",
    "who_other": "other",
}

# Item 7 — optional aggravating factors. Membership over `oh.aggravating_factors`.
_OH_AGGRAVATING = {
    "ag_history_dv": "history_dv",
    "ag_violating_orders": "violating_orders",
    "ag_mental_health": "mental_health",
    "ag_threats_others": "threats_others",
    "ag_weapons_access": "weapons_access",
    "ag_substance_abuse": "substance_abuse",
    "ag_serious_injury": "serious_injury",
    "ag_recent_separation": "recent_separation",
    "ag_controlling_stalking": "controlling_stalking",
    "ag_threats_kill": "threats_kill",
}

# Item 9 — relief requested (a-n). Membership over `oh.relief`.
_OH_RELIEF = {
    "r_no_abuse": "no_abuse",
    "r_no_enter_locations": "no_enter_locations",
    "r_no_contact": "no_contact",
    "r_exclusive_residence": "exclusive_residence",
    "r_custody": "custody",
    "r_parenting_time": "parenting_time",
    "r_financial_support": "financial_support",
    "r_no_property_disposal": "no_property_disposal",
    "r_take_pets": "take_pets",
    "r_divide_property": "divide_property",
    "r_vehicle": "vehicle",
    "r_counseling": "counseling",
    "r_wireless_transfer": "wireless_transfer",
    "r_additional": "additional",
}

_MEMBERSHIP = {
    "oh.who_needs_protection": _OH_WHO,
    "oh.aggravating_factors": _OH_AGGRAVATING,
    "oh.relief": _OH_RELIEF,
}

_WHO_FIELDS = tuple(
    FormField(item, f"Needs protection: {key.replace('_', ' ')}", source="oh.who_needs_protection")
    for item, key in _OH_WHO.items()
)
_AGGRAVATING_FIELDS = tuple(
    FormField(item, f"Factor: {key.replace('_', ' ')}", source="oh.aggravating_factors")
    for item, key in _OH_AGGRAVATING.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="oh.relief", needs_legal_review=True)
    for item, key in _OH_RELIEF.items()
)

OH_DVCPO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Court of Common Pleas)", source="oh.county", required=True),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_address",
        "Petitioner safe mailing address",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — the form is a public record; home address "
        "is never collected.",
    ),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address",
        "Respondent address (or work address)",
        source="respondent.last_known_address",
    ),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_adult", "Respondent is 18 or older", derive=_respondent_adult),
    # 1 — Interpreter
    FormField(
        "interpreter", "Interpreter needed / language", source="petitioner.interpreter_language"
    ),
    # 2 — Ex parte + full hearing
    FormField("ex_parte", "Ex parte (emergency) order requested", source="oh.ex_parte"),
    FormField("full_hearing", "Full hearing requested", derive=_full_hearing),
    # 3 — Who needs protection
    *_WHO_FIELDS,
    FormField(
        "who_other_detail",
        "Other person needing protection",
        source=None,
        note="Free-text 'other' detail not collected — OHG1.",
    ),
    # 4 — Relationship basis
    FormField(
        "relationship_basis",
        "Victim's relationship to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto OH's item-4 categories (spouse / "
        "former spouse / parent of respondent's child / living as a spouse / "
        "relative / etc.). Attorney confirms.",
    ),
    # 5 — Other protected household members
    FormField(
        "protected_members",
        "Other family/household members to protect",
        source="protected_persons.children[]",
        note="Names; form wants DOB / relationship / lives-with per person — partial, OHG2.",
    ),
    # 6 — Abuse narrative
    FormField("abuse_date", "Date(s) of the abuse", source="incidents[].date"),
    FormField(
        "abuse_narrative",
        "Describe the respondent's threats or actions",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    # 7 — Optional aggravating factors (+ firearms context)
    *_AGGRAVATING_FIELDS,
    FormField(
        "firearms_access",
        "Respondent access to deadly weapons/firearms",
        source="firearm.respondent_has_access",
    ),
    # 8 — Fear / continuing danger
    FormField("in_fear", "Petitioner is in fear and continuing danger", derive=_in_fear),
    # 9 — Relief (a-n) + details
    *_RELIEF_FIELDS,
    FormField(
        "exclusive_residence_address",
        "Residence for exclusive possession",
        source="oh.residence_address",
    ),
    FormField("take_pets_detail", "Companion animals/pets to take", source="oh.pets_detail"),
    FormField("divide_property_detail", "How to divide property", source="oh.property_detail"),
    FormField("vehicle_detail", "Motor vehicle for exclusive use", source="oh.vehicle_detail"),
    FormField("wireless_detail", "Wireless numbers to transfer", source="oh.wireless_detail"),
    FormField("additional_provisions", "Additional provisions", source="oh.additional_provisions"),
    # 13 — Other court cases
    FormField(
        "other_cases",
        "Other court cases regarding respondent",
        source="prior_orders.exists",
        note="Protective-order existence only; full case table not collected — OHG3.",
    ),
    # Signature
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Attests the information is true under penalty (R.C. 2921.13) — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """OH resolver — adds the who/aggravating/relief membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto OH Form 10.01-D fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=OH_DVCPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
