"""Maryland Petition for Protection from Domestic Violence form mapping.

Maps Vault intake answers onto Maryland form **CC-DC-DV-001, _Petition for
Protection from Domestic Violence_** (Md. Family Law § 4-504) plus its
respondent-description addendum (CC-DC-DV-001A). The petition covers parties,
the § 4-504 relationship basis, an acts-of-abuse checklist, firearms, and an
items 11-12 list of relief requested.

The MD intake section (`vault.intake`, the `jurisdiction == "MD"` block) feeds
the MD-specific items. MD's abuse and relief lists are its own.

Protection: the form itself says the petitioner need not give an address if
listing it risks further abuse — intake only ever holds a safe mailing address,
and the confidential-address box is defaulted on. See coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "CC-DC-DV-001"
FORM_REVISION = "2025-10"
JURISDICTION = "MD"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Caption box — petitioner's address is withheld (risk of further abuse)."""
    return "checked"


def _petition_dv(_answers: dict[str, Any]) -> str:
    """Petition type — the Vault files domestic-violence petitions."""
    return "checked"


def _relief_for_myself(_answers: dict[str, Any]) -> str:
    """Item 2 — the survivor seeks relief for themselves."""
    return "myself"


# Acts-of-abuse checklist (item 2) — membership over `md.abuse_acts`.
_MD_ABUSE = {
    "ab_kicking": "kicking",
    "ab_punching": "punching",
    "ab_choking": "choking_strangling",
    "ab_slapping": "slapping",
    "ab_shooting": "shooting",
    "ab_rape": "rape_sexual",
    "ab_hitting_object": "hitting_object",
    "ab_stabbing": "stabbing",
    "ab_shoving": "shoving",
    "ab_threats": "threats",
    "ab_mental_injury": "mental_injury_child",
    "ab_detaining": "detaining",
    "ab_stalking": "stalking",
    "ab_biting": "biting",
    "ab_revenge_porn": "revenge_porn",
    "ab_other": "other",
}

# Relief requested (items 11-12) — membership over `md.relief`.
_MD_RELIEF = {
    "r_no_abuse": "no_abuse",
    "r_no_contact": "no_contact",
    "r_stay_away_residence": "stay_away_residence",
    "r_stay_away_school": "stay_away_school",
    "r_stay_away_childcare": "stay_away_childcare",
    "r_stay_away_workplace": "stay_away_workplace",
    "r_leave_home": "leave_home",
    "r_surrender_firearms": "surrender_firearms",
    "r_counseling": "counseling",
    "r_emergency_maintenance": "emergency_maintenance",
    "r_custody": "custody",
    "r_vehicle": "vehicle",
    "r_pet_possession": "pet_possession",
    "r_other": "other",
}

_MEMBERSHIP = {"md.abuse_acts": _MD_ABUSE, "md.relief": _MD_RELIEF}

_ABUSE_FIELDS = tuple(
    FormField(item, f"Abuse: {key.replace('_', ' ')}", source="md.abuse_acts",
              needs_legal_review=True)
    for item, key in _MD_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="md.relief",
              needs_legal_review=True)
    for item, key in _MD_RELIEF.items()
)

MD_DV001_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("address_confidential", "Petitioner address withheld",
              derive=_address_confidential),
    FormField("petitioner_address", "Petitioner mailing address",
              source="petitioner.safe_mailing_address"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField("petition_dv", "Petition type: domestic violence", derive=_petition_dv),

    # 1 — Relationship eligibility (§ 4-504)
    FormField("1_relationship", "Relationship to respondent", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto § 4-504 eligibility checkboxes."),

    # 2 — Relief for / abuser / acts of abuse
    FormField("2_relief_for", "Relief for", derive=_relief_for_myself),
    FormField("2_abuser_name", "Name of alleged abuser", source="respondent.legal_name"),
    FormField("2_whereabouts", "Respondent's present whereabouts",
              source="respondent.last_known_address"),
    FormField("2_date", "Date(s) of abuse", source="incidents[].date"),
    *_ABUSE_FIELDS,
    FormField("ab_other_detail", "Other abuse detail", source="md.abuse_other"),
    FormField("2_details", "Details of what happened", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),

    # 4, 7, 8, 9, 10 — protected persons / cases / injuries / firearms
    FormField("4_persons_protected", "Persons to protect",
              source="protected_persons.children[]",
              note="Names; form wants name + birthdate + relationship per person — MDG1."),
    FormField("7_court_cases", "Other court cases", source="prior_orders.exists",
              note="PO existence only — partial, MDG2."),
    FormField("8_prior_final_order", "Prior final protective order", source="prior_orders.exists",
              note="Existence only — partial, MDG2."),
    FormField("9_past_injuries", "Past injuries", source="incidents[].injury"),
    FormField("10_firearms", "Respondent owns/has access to firearms",
              source="firearm.respondent_has_access"),
    FormField("10_firearm_types", "Firearm description", source="firearm.types[]"),

    # 11, 12 — Relief requested + details
    *_RELIEF_FIELDS,
    FormField("11_home_address", "Home to leave", source="md.home_address"),
    FormField("11_counseling_type", "Counseling type", source="md.counseling_type"),
    FormField("12_vehicle", "Vehicle", source="md.vehicle"),
    FormField("12_pets", "Pet(s)", source="md.pets"),
    FormField("12_other_relief", "Other relief detail", source="md.other_relief"),

    # Signature
    FormField("signature", "Petitioner signature (printed name)", source="petitioner.legal_name",
              required=True),

    # Addendum CC-DC-DV-001A — Description of Respondent
    FormField("add_dob", "Respondent DOB", source="respondent.dob"),
    FormField("add_sex", "Respondent sex", source="respondent.gender"),
    FormField("add_race", "Respondent race", source="respondent.race"),
    FormField("add_employer", "Respondent employer", source="respondent.employer_name"),
    FormField("add_physical", "Respondent physical description", source=None,
              note="Height/weight/eyes/hair not collected for MD (no physical block) — MDG3."),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MD resolver — adds the abuse/relief membership rules, else basic lookup."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MD CC-DC-DV-001 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MD_DV001_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
