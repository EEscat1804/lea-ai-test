"""Wyoming Petition for Domestic Violence Order of Protection form mapping.

Maps Vault intake answers onto Wyoming Circuit Court **PO DV Form 03, _Petition
for Domestic Violence Order of Protection_** (W.S. § 35-21-101 to 112, Last Form
Revision October 2025). The petition covers the parties (with full respondent
identifiers), other court cases, the household-member relationship basis (¶6),
children (¶7), the abuse description (¶8), weapons/firearms (¶9-10), and the
paragraph-11 relief list (A-T), plus the hearing-appearance choice (¶12).

The WY intake section (`vault.intake`, the `jurisdiction == "WY"` block plus the
shared physical-description and vehicle blocks — WY is in both sets) feeds the
WY-specific items. WY's relief list (A-T) is its own, distinct from the other
states'.

Protection: the form lets the petitioner keep their (and the children's) address
and phone confidential — intake only ever holds a safe mailing address, and the
confidential box defaults on. See coverage.md.

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

FORM_ID = "PO DV Form 03"
FORM_REVISION = "2025-10"  # Last Form Revision: October 2025
JURISDICTION = "WY"


def _confidential(_answers: dict[str, Any]) -> str:
    """¶1 — keep the petitioner's (and children's) address/phone confidential."""
    return "checked"


# ¶11 relief (A-T). Membership over `wy.relief`.
_WY_RELIEF = {
    "rA_personal_conduct": "personal_conduct",
    "rB_no_contact": "no_contact",
    "rC_medical_expenses": "medical_expenses",
    "rD_stay_away": "stay_away",
    "rE_no_guns": "no_guns",
    "rF_property_no_disposal": "property_no_disposal",
    "rG_property_possession": "property_possession",
    "rH_property_services": "property_services",
    "rI_alternative_housing": "alternative_housing",
    "rJ_pets": "pets",
    "rK_transfer_wireless": "transfer_wireless",
    "rL_custody_visitation": "custody_visitation",
    "rM_no_abduct": "no_abduct",
    "rN_no_alcohol_drugs": "no_alcohol_drugs",
    "rO_supervised_visitation": "supervised_visitation",
    "rP_travel_restrictions": "travel_restrictions",
    "rQ_support": "support",
    "rR_attorney_fees": "attorney_fees",
    "rS_appoint_attorney": "appoint_attorney",
    "rT_other_assistance": "other_assistance",
}

# ¶11(D) stay-away places. Membership over `wy.stay_away_places`.
_WY_STAY_AWAY = {
    "sa_my_home": "my_home",
    "sa_my_work": "my_work",
    "sa_my_school": "my_school",
    "sa_my_worship": "my_worship",
    "sa_children_home": "children_home",
    "sa_children_work": "children_work",
    "sa_children_school": "children_school",
    "sa_children_worship": "children_worship",
    "sa_other": "other",
}

_MEMBERSHIP = {
    "wy.relief": _WY_RELIEF,
    "wy.stay_away_places": _WY_STAY_AWAY,
}

_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Relief {item[1:2]}: {key.replace('_', ' ')}",
        source="wy.relief",
        needs_legal_review=True,
    )
    for item, key in _WY_RELIEF.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="wy.stay_away_places")
    for item, key in _WY_STAY_AWAY.items()
)

WY_PODV03_FIELDS: tuple[FormField, ...] = (
    # Caption (¶1 petitioner / ¶5 venue)
    FormField("county", "County", source="wy.county", required=True),
    FormField("judicial_district", "Judicial district", source="wy.judicial_district"),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "petitioner_description",
        "Petitioner race/gender/height/weight/eyes/hair",
        source=None,
        note="Petitioner physical description not collected — WYG1.",
    ),
    FormField(
        "confidential",
        "Keep petitioner/children address and phone confidential",
        derive=_confidential,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    # ¶2 Respondent (full identifiers)
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField(
        "respondent_gender",
        "Respondent gender",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("respondent_employer", "Respondent employer", source="respondent.employer_name"),
    FormField(
        "respondent_vehicle_plate",
        "Respondent vehicle license plate",
        source="respondent.vehicle_plate",
    ),
    FormField(
        "respondent_vehicle_desc", "Respondent vehicle", source="respondent.vehicle_make_model"
    ),
    FormField(
        "respondent_marks",
        "Respondent distinguishing marks",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_dl",
        "Respondent driver's license",
        source=None,
        note="Not collected by intake — WYG2.",
    ),
    FormField(
        "respondent_birth_place",
        "Respondent state/country of birth",
        source=None,
        note="Not collected by intake — WYG2.",
    ),
    # ¶3 Other court cases
    FormField(
        "respondent_probation",
        "Respondent on probation for domestic violence",
        source="wy.respondent_probation",
    ),
    FormField(
        "other_cases",
        "Other court cases",
        source="prior_orders.exists",
        note="Protective-order existence only; full case list not collected — WYG3.",
    ),
    # ¶5 Venue / ¶6 Relationship
    FormField("petitioner_county", "Petitioner resident county", source="wy.county"),
    FormField("abuse_location", "Location of the abuse", source="incidents[].location"),
    FormField(
        "relationship_basis",
        "Household-member relationship (¶6)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto WY's ¶6 household-member categories. "
        "WY requires the parties be household members — attorney confirms the box(es).",
    ),
    # ¶7 Children
    FormField(
        "children",
        "Minor children",
        source="protected_persons.children[]",
        note="Names; form wants each child's DOB/race/gender/residence — partial, WYG4.",
    ),
    # ¶8 Abuse description
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    FormField(
        "abuse_narrative",
        "Describe the domestic abuse",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    # ¶9-10 Weapons / firearms
    FormField(
        "weapons_used", "Weapons used during the incidents", source="incidents[].weapon_involved"
    ),
    FormField(
        "firearms_access",
        "Respondent possesses firearms/ammunition",
        source="firearm.respondent_has_access",
    ),
    FormField("firearms_types", "Firearms description", source="firearm.types[]"),
    FormField("firearms_locations", "Firearms location", source="firearm.locations[]"),
    # ¶11 Relief (A-T) + details
    *_RELIEF_FIELDS,
    FormField("rD_stay_away_distance", "Stay-away distance", source="wy.stay_away_distance"),
    *_STAY_AWAY_FIELDS,
    FormField(
        "rG_property_possession_detail",
        "Property to possess",
        source="wy.property_possession_detail",
    ),
    FormField("rJ_pets_detail", "Pets to protect", source="wy.pets_detail"),
    FormField("rK_wireless_numbers", "Wireless numbers to transfer", source="wy.wireless_numbers"),
    FormField("rL_custody_to", "Custody to", source="wy.custody_to"),
    FormField("rL_visitation_terms", "Visitation terms", source="wy.visitation_terms"),
    FormField(
        "rO_supervised_detail", "Supervised-visitation supervisor", source="wy.supervised_detail"
    ),
    FormField("rQ_support_detail", "Support requested", source="wy.support_detail"),
    FormField("rT_other_detail", "Other assistance", source="wy.other_assistance"),
    # ¶12 Hearing appearance
    FormField("appearance", "Hearing appearance (in person / virtual)", source="wy.appearance"),
    # Verification / signature — sworn before a clerk/notary at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn before the Clerk of Court / notarial officer — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """WY resolver — adds the relief and stay-away membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto WY PO DV Form 03 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=WY_PODV03_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
