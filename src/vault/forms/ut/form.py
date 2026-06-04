"""Utah Request for Protective Order form mapping.

Maps Vault intake answers onto Utah's **Request for Protective Order** (Utah Code
78B-7-601 et seq.; District Court). The form carries no printed form number — it
is identified by its title and revision (Approved Board of District Court Judges
May 21, 2008; Revised by Forms Committee April 11, 2022). FORM_ID is therefore
descriptive; see coverage.md.

The request covers the parties, a "Describe Respondent" block (sex/race/DOB plus
the shared physical description and vehicle), the relationship basis, the most
recent and past abuse (from the Tier-1 incident), an imminent-fear declaration,
and a large items 8-25 relief checklist — personal conduct, no contact, stay
away, no weapons, property control, pets, wireless transfer, custody &
parent-time, support & expenses, orders to agencies, and a guardian ad litem.
UT's relief list is its own.

The UT intake section (`vault.intake`, the `jurisdiction == "UT"` block), plus
the shared physical-description and vehicle gates, feeds these items.

Protection: the form says the petitioner may leave their address/phone blank to
keep it private; intake only ever holds a safe mailing address, and the
address-confidential note is asserted. The respondent's Social Security number
and driver's license are sensitive and not collected. See coverage.md.

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

FORM_ID = "Request for Protective Order"  # no printed form number — UTG1
FORM_REVISION = "2022-04-11"  # Revised by Forms Committee April 11, 2022
JURISDICTION = "UT"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Petitioner may keep address/phone private — intake holds only safe mailing."""
    return "checked"


# Items 8-25 — relief checklist. Membership over `ut.relief`.
_UT_RELIEF = {
    "8_personal_conduct": "personal_conduct",
    "9_no_contact": "no_contact",
    "10_contact_mediation": "contact_mediation",
    "11_stay_away": "stay_away",
    "12_no_weapons": "no_weapons",
    "13_property_control": "property_control_petitioner",
    "14_property_services": "property_control_services",
    "15_no_harming_pets": "no_harming_pets",
    "16_transfer_wireless": "transfer_wireless",
    "17_custody": "custody",
    "18_no_alcohol_drugs": "no_alcohol_drugs",
    "19_supervised_visitation": "supervised_visitation",
    "20_travel_restrictions": "travel_restrictions",
    "21_support_expenses": "support_expenses",
    "22_other_assistance": "other_assistance",
    "23_law_enforcement": "law_enforcement_assist",
    "24_investigate_child_abuse": "investigate_child_abuse",
    "25_guardian_children": "guardian_children",
}

# Item 11 stay-away sub-locations. Membership over `ut.stay_away_locations`.
_UT_STAY_AWAY = {
    "11_sa_home": "home",
    "11_sa_work": "work",
    "11_sa_school": "school",
    "11_sa_worship": "worship",
    "11_sa_other": "other",
}

# Item 21 support sub-checklist. Membership over `ut.support_types`.
_UT_SUPPORT = {
    "21a_child_support": "child_support",
    "21b_spousal_support": "spousal_support",
    "21c_income_withholding": "income_withholding",
    "21d_childcare_half": "childcare_half",
    "21e_medical_half": "medical_half",
    "21f_abuse_medical": "abuse_medical",
}

# Item 23 law-enforcement sub-tasks. Membership over `ut.law_enforcement_tasks`.
_UT_LAW_ENFORCEMENT = {
    "23a_control_property": "control_property",
    "23b_obtain_custody": "obtain_custody",
    "23c_remove_belongings": "remove_belongings",
}

_MEMBERSHIP = {
    "ut.relief": _UT_RELIEF,
    "ut.stay_away_locations": _UT_STAY_AWAY,
    "ut.support_types": _UT_SUPPORT,
    "ut.law_enforcement_tasks": _UT_LAW_ENFORCEMENT,
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ut.relief", needs_legal_review=True)
    for item, key in _UT_RELIEF.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(
        item,
        f"Stay away: {key.replace('_', ' ')}",
        source="ut.stay_away_locations",
        needs_legal_review=True,
    )
    for item, key in _UT_STAY_AWAY.items()
)
_SUPPORT_FIELDS = tuple(
    FormField(
        item,
        f"Support: {key.replace('_', ' ')}",
        source="ut.support_types",
        needs_legal_review=True,
    )
    for item, key in _UT_SUPPORT.items()
)
_LAW_ENFORCEMENT_FIELDS = tuple(
    FormField(
        item,
        f"Law enforcement: {key.replace('_', ' ')}",
        source="ut.law_enforcement_tasks",
        needs_legal_review=True,
    )
    for item, key in _UT_LAW_ENFORCEMENT.items()
)

UT_RPO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (District Court)", source="ut.county", required=True),
    FormField(
        "district",
        "Judicial district number",
        source=None,
        note="Determined by county at filing; intake collects county only — UTG2.",
    ),
    # 1 — Petitioner
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "address_confidential",
        "Petitioner address kept private (left blank)",
        derive=_address_confidential,
    ),
    FormField(
        "petitioner_mailing_address",
        "Petitioner safe mailing address",
        source="petitioner.safe_mailing_address",
    ),
    FormField(
        "petitioner_attorney",
        "Petitioner's attorney name/phone",
        source=None,
        note="Not collected by intake — UTG3.",
    ),
    FormField(
        "other_protected",
        "Other people protected (relatives / household)",
        source="protected_persons.children[]",
        note="Names only; form wants name + age + relationship per person — UTG4.",
    ),
    # 2 — Respondent + Describe Respondent
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_relationship",
        "Respondent relationship to petitioner",
        source="relationship.type",
        needs_legal_review=True,
        note="Mirrors the §3 relationship basis.",
    ),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "respondent_other_names",
        "Other names used by respondent",
        source=None,
        note="Not collected by intake — UTG5.",
    ),
    FormField("respondent_sex", "Respondent sex", source="respondent.gender"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "respondent_features",
        "Respondent distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_ssn",
        "Respondent Social Security number",
        source=None,
        note="Sensitive — not collected by intake (UTG6).",
    ),
    FormField(
        "respondent_dl",
        "Respondent driver's license (state / expiry)",
        source=None,
        note="Not collected by intake — UTG5.",
    ),
    FormField(
        "respondent_employer",
        "Respondent employer (name/address)",
        source="respondent.employer_name",
    ),
    FormField(
        "respondent_employer_address",
        "Respondent employer address",
        source="respondent.employer_address",
    ),
    FormField(
        "respondent_vehicle",
        "Respondent vehicle make/model",
        source="respondent.vehicle_make_model",
    ),
    FormField(
        "respondent_vehicle_color", "Respondent vehicle color", source="respondent.vehicle_color"
    ),
    FormField(
        "respondent_vehicle_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"
    ),
    FormField(
        "respondent_violent_past",
        "Respondent used weapons / violent in past",
        source="ut.respondent_violent_past",
        needs_legal_review=True,
    ),
    FormField(
        "respondent_violent_detail",
        "Respondent violent-past detail",
        source="ut.respondent_violent_detail",
    ),
    FormField(
        "respondent_probation", "Respondent on probation/parole", source="ut.respondent_probation"
    ),
    FormField(
        "respondent_probation_detail",
        "Probation/parole agency/officer/phone",
        source="ut.respondent_probation_detail",
    ),
    # 3 — Relationship basis
    FormField(
        "relationship_basis",
        "Relationship of petitioner to respondent (§3 a-i)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto UT's §3 categories (check all that "
        "apply). Attorney confirms the boxes.",
    ),
    # 4 — Most recent abuse (from the Tier-1 incident)
    FormField("abuse_date", "Date of most recent abuse (4a)", source="incidents[].date"),
    FormField("abuse_location", "Where it happened (4b)", source="incidents[].location"),
    FormField("abuse_police_came", "Did police come (4c)", source="incidents[].police_called"),
    FormField(
        "abuse_narrative",
        "Describe the abuse (4e)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    FormField("abuse_weapon", "Weapon used/threatened (4g)", source="incidents[].weapon_involved"),
    FormField("abuse_witnesses", "Who else was there (4i)", source="incidents[].witnesses_present"),
    FormField("abuse_injury", "Was anyone hurt (4j)", source="incidents[].injury"),
    # 6 — Fear of imminent physical harm
    FormField(
        "fear_imminent",
        "Imminent physical-harm declaration (§6)",
        source="ut.fear_imminent",
        needs_legal_review=True,
    ),
    FormField(
        "fear_imminent_detail",
        "Why harm is feared imminently (§6)",
        source="ut.fear_imminent_detail",
    ),
    # 7 — Other court cases (partial from prior_orders)
    FormField(
        "other_court_cases",
        "Other court cases (§7)",
        source="prior_orders.exists",
        note="Existence only; form wants the full case list — UTG7.",
    ),
    # 8-25 — Relief checklist
    *_RELIEF_FIELDS,
    # 11 — Stay-away sub-detail
    FormField("11_distance", "Stay-away distance", source="ut.stay_away_distance"),
    *_STAY_AWAY_FIELDS,
    FormField("11_sa_other_detail", "Stay-away other place", source="ut.stay_away_other"),
    # 12 — Weapons detail
    FormField("12_weapons_detail", "Weapons to name", source="ut.weapons_detail"),
    # 13 — Property control detail
    FormField("13a_home_address", "Home to control (13a)", source="ut.property_home_address"),
    FormField("13b_belongings", "Car/belongings to control (13b)", source="ut.property_belongings"),
    # 17 — Custody detail
    FormField("17_custody_to", "Custody to", source="ut.custody_to", needs_legal_review=True),
    FormField("17_custody_other_name", "Custody to (other person)", source="ut.custody_other_name"),
    FormField("17_parent_time", "Respondent parent-time", source="ut.parent_time"),
    # 19 — Supervised visitation detail
    FormField(
        "19_supervisor",
        "Supervised-visitation supervisor",
        source="ut.supervised_visitation_detail",
    ),
    # 21 — Support sub-checklist + amounts
    *_SUPPORT_FIELDS,
    FormField("21a_amount", "Child support monthly amount", source="ut.child_support_amount"),
    FormField("21b_amount", "Spousal support monthly amount", source="ut.spousal_support_amount"),
    # 16 — Wireless transfer detail
    FormField(
        "16_wireless_numbers", "Wireless number(s) to transfer", source="ut.wireless_numbers"
    ),
    # 22 — Other assistance detail
    FormField("22_other_detail", "Other assistance needed", source="ut.other_assistance_detail"),
    # 23 — Law-enforcement sub-tasks
    *_LAW_ENFORCEMENT_FIELDS,
    # Signature / verification (sworn under criminal penalty)
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """UT resolver — adds the relief/sub-checklist membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto UT Request for Protective Order (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=UT_RPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
