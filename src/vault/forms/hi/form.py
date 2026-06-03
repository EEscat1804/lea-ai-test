"""Hawai'i Petition for an Order for Protection form mapping.

Maps Vault intake answers onto Hawai'i form **1F-P-752A, _Petition for an Order
for Protection_** (HRS ch. 586). The petition covers parties, the ch. 586
relationship basis, an acts-of-abuse checklist plus a harm-type classification,
incident statements, firearms/electric guns, and a section II list of relief
(TRO + protective-order) requested.

The HI intake section (`vault.intake`, the `jurisdiction == "HI"` block) feeds
the HI-specific items. HI's abuse/harm/relief lists are its own.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings. See coverage.md.

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

FORM_ID = "1F-P-752A"
FORM_REVISION = "2023-07"
JURISDICTION = "HI"


def _self_represented(_answers: dict[str, Any]) -> str:
    """Caption — the Vault flow is a self-represented petitioner."""
    return "checked"


def _for_myself(_answers: dict[str, Any]) -> str:
    """Item 4 — the survivor files for themselves."""
    return "myself"


def _jurisdiction_basis(_answers: dict[str, Any]) -> str:
    """Item 3 — petitioner resides in the circuit (default basis)."""
    return "petitioner resides"


def _petitioner_age_band(answers: dict[str, Any]) -> str | None:
    """Item 2 — 16-17 vs adult 18+, from the petitioner's DOB."""
    dob_str = answers.get("petitioner.dob")
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    age = today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))
    return "adult_18_or_older" if age >= 18 else "16_to_17"


# Acts-of-abuse checklist (item 6) — membership over `hi.abuse_acts`.
_HI_ABUSE = {
    "ab_choke": "choke",
    "ab_force_sex": "force_sex",
    "ab_grab": "grab",
    "ab_hit": "hit",
    "ab_kick": "kick",
    "ab_slap": "slap",
    "ab_punch": "punch",
    "ab_push": "push",
    "ab_shove": "shove",
    "ab_other": "other",
}

# Harm-type classification (item 6 "this was") — membership over `hi.harm_types`.
_HI_HARM = {
    "harm_physical": "physical_harm",
    "harm_threat": "threat_imminent",
    "harm_psychological": "psychological",
    "harm_property": "property_damage",
    "harm_coercive": "coercive_control",
}

# Section II relief requested — membership over `hi.relief`.
_HI_RELIEF = {
    "r_no_contact": "no_contact",
    "r_no_residence": "no_residence",
    "r_no_property_damage": "no_property_damage",
    "r_no_psych_abuse": "no_psych_abuse",
    "r_no_contact_work": "no_contact_work",
    "r_no_contact_children_school": "no_contact_children_school",
    "r_protect_animals": "protect_animals",
    "r_vacate": "vacate",
    "r_custody_visitation": "custody_visitation",
    "r_no_visitation": "no_visitation",
    "r_supervised_visitation": "supervised_visitation",
    "r_dv_intervention": "dv_intervention",
}

_MEMBERSHIP = {
    "hi.abuse_acts": _HI_ABUSE,
    "hi.harm_types": _HI_HARM,
    "hi.relief": _HI_RELIEF,
}

_ABUSE_FIELDS = tuple(
    FormField(item, f"Abuse act: {key.replace('_', ' ')}", source="hi.abuse_acts",
              needs_legal_review=True)
    for item, key in _HI_ABUSE.items()
)
_HARM_FIELDS = tuple(
    FormField(item, f"Harm: {key.replace('_', ' ')}", source="hi.harm_types",
              needs_legal_review=True)
    for item, key in _HI_HARM.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="hi.relief",
              needs_legal_review=True)
    for item, key in _HI_RELIEF.items()
)

HI_FOP_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("self_represented", "Self-represented petitioner", derive=_self_represented),

    # 2, 3, 4 — age band / jurisdiction / on behalf of
    FormField("2_age_band", "Petitioner age band", derive=_petitioner_age_band),
    FormField("3_jurisdiction", "Jurisdiction basis", derive=_jurisdiction_basis,
              needs_legal_review=True,
              note="Defaults to petitioner-resides; confirm the circuit/basis."),
    FormField("4_for_myself", "Filing for myself", derive=_for_myself),
    FormField("4_household_members", "Household members protected",
              source="protected_persons.children[]",
              note="Names; form wants gender/year-of-birth/relationship per person — HG1."),

    # 5 — Relationship (ch. 586)
    FormField("5_relationship", "Relationship to respondent", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto ch. 586 relationship checkboxes."),

    # 6 — Incident: date / acts / harm types / narrative
    FormField("6_incident_date", "Incident date", source="incidents[].date"),
    *_ABUSE_FIELDS,
    FormField("ab_other_detail", "Other abuse detail", source="hi.abuse_other"),
    FormField("6_narrative", "Describe this incident", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),
    *_HARM_FIELDS,

    # 7, 8 — Weapons / firearms
    FormField("7e_weapon", "Respondent may have access to a weapon",
              source="firearm.respondent_has_access"),
    FormField("8_firearms", "Respondent owns/possesses/has access to firearms",
              source="firearm.respondent_has_access"),
    FormField("8_firearm_desc", "Firearm/electric gun description", source="firearm.types[]"),
    FormField("8_firearm_location", "Firearm/electric gun location", source="firearm.locations[]"),

    # 9 — Other court cases
    FormField("9_court_cases", "Other court cases", source="prior_orders.exists",
              note="PO existence only — partial, HG2."),

    # Section II — relief requested + duration
    *_RELIEF_FIELDS,
    FormField("ii5_duration", "Requested order duration", source="hi.duration"),

    # Signature
    FormField("signature", "Petitioner signature (printed name)", source="petitioner.legal_name",
              required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """HI resolver — adds the abuse/harm/relief membership rules, else basic lookup."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto HI 1F-P-752A fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=HI_FOP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
