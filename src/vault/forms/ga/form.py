"""Georgia Petition for Family Violence Protective Order form mapping.

Maps Vault intake answers onto Georgia form **SC-26, _Petition for Family
Violence Protective Order_** (O.C.G.A. § 19-13-1 et seq.). The petition covers
parties, the § 19-13 relationship basis, a free-text acts-of-violence
statement, firearms, a large relief checklist, a verification, and a sealed
Confidential Information page (respondent fact sheet + protected-parties
identifiers).

The GA intake section (`vault.intake`, the `jurisdiction == "GA"` block) plus
the shared physical/vehicle blocks feed the GA-specific items. GA's relief list
is its own.

Protection: GA's relief list includes "keep my address confidential," and the
respondent/protected-party identifiers go on a **sealed** page. The survivor's
home address is never collected by intake. See coverage.md.

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

FORM_ID = "SC-26"
FORM_REVISION = "current"
JURISDICTION = "GA"


def _substantial_likelihood(_answers: dict[str, Any]) -> str:
    """Item 6 — the petition asserts substantial likelihood of future violence."""
    return "checked"


# Relief checklist — membership over `ga.relief`. (item, relief key.)
_GA_RELIEF = {
    "r_no_abuse": "no_abuse",
    "r_no_contact": "no_contact",
    "r_stay_away_distance": "stay_away_distance",
    "r_vacate": "vacate",
    "r_exclusive_residence": "exclusive_residence",
    "r_pay_rent": "pay_rent",
    "r_alternate_housing": "alternate_housing",
    "r_stay_away_places": "stay_away_places",
    "r_custody": "custody",
    "r_no_visitation": "no_visitation",
    "r_child_support": "child_support",
    "r_financial_support": "financial_support",
    "r_attorney_fees": "attorney_fees",
    "r_address_confidential": "address_confidential",
    "r_property_restraint": "property_restraint",
    "r_utility_insurance_restraint": "utility_insurance_restraint",
    "r_vehicle": "vehicle",
    "r_remove_property": "remove_property",
    "r_drug_evaluation": "drug_evaluation",
    "r_fvip": "fvip",
    "r_return_property": "return_property",
    "r_reimburse": "reimburse",
    "r_additional": "additional",
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ga.relief",
              needs_legal_review=True)
    for item, key in _GA_RELIEF.items()
)

GA_SC26_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("1_county", "Petitioner county of residence", source="ga.county", required=True),
    FormField("2_respondent_address", "Respondent address for service",
              source="respondent.last_known_address"),

    # 3 — Relationship (§ 19-13)
    FormField("3_relationship", "Relationship to respondent", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto § 19-13 relationship checkboxes."),

    # 4 — Acts of family violence (free-text)
    FormField("4_date", "Date of family violence", source="incidents[].date"),
    FormField("4_acts", "Acts of family violence (statement)", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),
    FormField("4_firearm_involved", "Firearm used/threatened",
              source="incidents[].weapon_involved"),

    # 6 — Substantial likelihood of future violence
    FormField("6_substantial_likelihood", "Substantial likelihood of future violence",
              derive=_substantial_likelihood),

    # 7 — Children
    FormField("7_children", "Children under 18", source="protected_persons.children[]",
              note="Names; form wants year-of-birth/sex/age per child — GAG1."),

    # 14, 15 — Criminal record / firearms
    FormField("14_criminal_record", "Respondent criminal record",
              source="respondent.prior_criminal_history"),
    FormField("15_firearms", "Respondent has access to firearms",
              source="firearm.respondent_has_access"),
    FormField("15_firearm_desc", "Firearm description/locations", source="firearm.types[]"),

    # Relief requested + details
    *_RELIEF_FIELDS,
    FormField("r_residence_address", "Residence address", source="ga.residence_address"),
    FormField("r_vehicle_desc", "Vehicle description", source="ga.vehicle"),
    FormField("r_return_property_desc", "Property to return", source="ga.return_property_desc"),
    FormField("r_other_detail", "Additional relief detail", source="ga.other_relief"),

    # Signature
    FormField("signature", "Petitioner signature (printed name)", source="petitioner.legal_name",
              required=True),

    # Sealed Confidential Information page — Respondent's Identifying Fact Sheet
    FormField("conf_resp_dob", "Respondent DOB", source="respondent.dob"),
    FormField("conf_resp_sex", "Respondent sex", source="respondent.gender"),
    FormField("conf_resp_race", "Respondent race", source="respondent.race"),
    FormField("conf_resp_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("conf_resp_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("conf_resp_height", "Respondent height", source="respondent.height"),
    FormField("conf_resp_weight", "Respondent weight", source="respondent.weight"),
    FormField("conf_resp_marks", "Respondent distinguishing marks",
              source="respondent.distinguishing_marks"),
    FormField("conf_resp_vehicle", "Respondent vehicle", source="respondent.vehicle_make_model"),
    FormField("conf_resp_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"),
    FormField("conf_resp_address", "Respondent home address",
              source="respondent.last_known_address"),
    FormField("conf_resp_employer", "Respondent employer", source="respondent.employer_name"),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """GA resolver — adds the relief-checkbox rule, else the basic lookup."""
    if f.source == "ga.relief" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _GA_RELIEF.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto GA SC-26 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=GA_SC26_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
