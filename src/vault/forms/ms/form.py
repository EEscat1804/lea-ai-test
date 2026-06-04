"""Mississippi Petition for Domestic Abuse Protection Order form mapping.

Maps Vault intake answers onto Mississippi's **Petition for Domestic Abuse
Protection Order** (M.C.A. § 93-21-1 et seq.). The petition covers the caption,
the emergency-relief election, the §1 protected persons and relationship basis,
the §2 confidential-address election, the §3 venue (abuse / respondent location),
the §4 respondent information (a full physical-description block + caution / medical
flags), the §5 acts of abuse, the §6 narrative, the §7-§8 divorce / children
blocks, the §9 relief checklist (plus Chancery/County-only relief), and the §10
other-cases disclosure. MS's relationship, abuse, caution, and relief lists are
their own.

The MS intake section (`vault.intake`, the `_ms_step` method) plus the shared
physical-description gate feeds these items. The §4 block HAS a respondent
physical description (eye color / hair / height / weight / SSN / DL / features), so
MS is in `PHYSICAL_DESCRIPTION_STATES`; `_ms_step` adds the respondent dob/sex/race
the block also needs. The form has **no respondent vehicle block**, so MS is carved
out of `VEHICLE_DESCRIPTION_STATES` (see the intake comment).

Protection: §2 offers a real confidential mechanism — "Petitioner requests his/her
address remain confidential", with the address on Supplemental Form #2 (SF2,
§ 93-21-9(7)). Intake only ever holds a safe mailing address, so
`address_confidential` is derived `"checked"`. The §4 block has the *respondent's*
SSN (not the petitioner's), and the Chancery/County-only relief includes support,
but there is no *petitioner* SSN field, so MS is not in the SSN-for-support gate.
See coverage.md.

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

FORM_ID = "Petition for Domestic Abuse Protection Order"  # no printed form number, MSG1
FORM_REVISION = "unknown"  # no revision date printed on the form, MSG1
JURISDICTION = "MS"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """§2 — petitioner requests their address remain confidential (SF2, § 93-21-9(7)).

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms SF2 is filed.
    """
    return "checked"


# §1 — protected person's relationship to the respondent. Membership over
# `ms.relationship_basis`.
_MS_RELATIONSHIP = {
    "1_current_former_spouse": "current_former_spouse",
    "1_lived_as_spouse": "lived_as_spouse",
    "1_child_in_common": "child_in_common",
    "1_dating_partner": "dating_partner",
    "1_related_cohabit": "related_cohabit",
}

# §5 — acts of abuse. Membership over `ms.abuse_acts`.
_MS_ABUSE_ACTS = {
    "5_attempted_bodily_injury": "attempted_bodily_injury",
    "5_physical_menace_fear": "physical_menace_fear",
    "5_criminal_sexual_minor": "criminal_sexual_minor",
    "5_stalking_cyberstalking": "stalking_cyberstalking",
    "5_sexual_battery_rape": "sexual_battery_rape",
}

# §4 — caution and medical conditions. Membership over `ms.caution`.
_MS_CAUTION = {
    "4_alcoholic": "alcoholic",
    "4_allergies": "allergies",
    "4_armed_dangerous": "armed_dangerous",
    "4_diabetic": "diabetic",
    "4_epilepsy": "epilepsy",
    "4_escape_risk": "escape_risk",
    "4_explosive": "explosive",
    "4_hemophiliac": "hemophiliac",
    "4_heart_condition": "heart_condition",
    "4_intl_flight_risk": "intl_flight_risk",
    "4_abuse_drugs": "abuse_drugs",
    "4_martial_arts": "martial_arts",
    "4_medication": "medication",
    "4_other": "other",
}

# §9 — relief requested. Membership over `ms.relief`.
_MS_RELIEF = {
    "9_prohibit_abuse": "prohibit_abuse",
    "9_prohibit_contact": "prohibit_contact",
    "9_prohibit_distance": "prohibit_distance",
    "9_prohibit_property_transfer": "prohibit_property_transfer",
    "9_sole_use_residence": "sole_use_residence",
    "9_le_possession_residence": "le_possession_residence",
    "9_le_possession_belongings": "le_possession_belongings",
    "9_court_costs": "court_costs",
    "9_other": "other",
}

# §9 (continued) — Chancery/County-court-only relief. Membership over
# `ms.chancery_relief`.
_MS_CHANCERY_RELIEF = {
    "9c_custody_support": "custody_support",
    "9c_visitation": "visitation",
    "9c_monetary_support": "monetary_support",
    "9c_restitution": "restitution",
}

_MEMBERSHIP = {
    "ms.relationship_basis": _MS_RELATIONSHIP,
    "ms.abuse_acts": _MS_ABUSE_ACTS,
    "ms.caution": _MS_CAUTION,
    "ms.relief": _MS_RELIEF,
    "ms.chancery_relief": _MS_CHANCERY_RELIEF,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="ms.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _MS_RELATIONSHIP.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse act: {key.replace('_', ' ')}", source="ms.abuse_acts", needs_legal_review=True
    )
    for item, key in _MS_ABUSE_ACTS.items()
)
_CAUTION_FIELDS = tuple(
    FormField(item, f"Caution: {key.replace('_', ' ')}", source="ms.caution")
    for item, key in _MS_CAUTION.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ms.relief", needs_legal_review=True)
    for item, key in _MS_RELIEF.items()
)
_CHANCERY_FIELDS = tuple(
    FormField(
        item,
        f"Chancery/County relief: {key.replace('_', ' ')}",
        source="ms.chancery_relief",
        needs_legal_review=True,
    )
    for item, key in _MS_CHANCERY_RELIEF.items()
)

MS_PO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "court_type", "Court (chancery / county / justice / municipal)", source="ms.court_type"
    ),
    FormField("county", "County", source="ms.county", required=True),
    FormField(
        "cause_number",
        "Cause number",
        source=None,
        note="Assigned by the clerk at filing — MSG2.",
    ),
    FormField(
        "emergency_relief",
        "Petitioner requests emergency relief",
        source="ms.emergency_relief",
        needs_legal_review=True,
    ),
    # §1 — Petitioner / protected persons
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "protected_children",
        "Minor child(ren) / incompetent protected (§1a)",
        source="protected_persons.children[]",
        note="Names; the form wants per-person DOB / sex / race / relationship — partial, MSG3.",
    ),
    *_RELATIONSHIP_FIELDS,
    # §2 — Confidential address
    FormField(
        "address_confidential",
        "Address kept confidential (§2, SF2 / § 93-21-9(7))",
        derive=_address_confidential,
        needs_legal_review=True,
        note="Mississippi's confidential-address mechanism (Supplemental Form #2).",
    ),
    FormField(
        "petitioner_address",
        "Petitioner address (§2 No)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; the residential address is withheld via SF2.",
    ),
    # §3 — Venue
    FormField(
        "abuse_location",
        "Where the abuse occurred (§3 city/county/state)",
        source="incidents[].location",
    ),
    FormField(
        "respondent_location",
        "Where the respondent resides (§3)",
        source="respondent.last_known_address",
    ),
    # §4 — Respondent information + physical description
    FormField("respondent", "Respondent name (§4)", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Respondent address (§4)", source="respondent.last_known_address"
    ),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_sex", "Respondent sex", source="respondent.gender"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color/type", source="respondent.hair_color"),
    FormField(
        "respondent_features",
        "Respondent distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_ssn",
        "Respondent Social Security # / driver's license (§4)",
        source=None,
        note="The §4 block wants the respondent's SSN / DL; not collected by intake — MSG4.",
    ),
    FormField(
        "respondent_employer",
        "Respondent place of employment (§4)",
        source="respondent.employer_name",
    ),
    # §4 — Caution / medical conditions
    *_CAUTION_FIELDS,
    # §5 — Acts of abuse
    *_ABUSE_FIELDS,
    # §6 — Narrative
    FormField(
        "abuse_narrative",
        "Facts and circumstances of the alleged abuse (§6)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    # §7 — Divorce
    FormField(
        "divorce_status",
        "Divorce pending / granted (§7)",
        source="prior_orders.exists",
        note="Existence proxy; the §7 divorce detail (where) is not collected — MSG5.",
    ),
    # §8 — Children in common
    FormField(
        "children_in_common",
        "Children in common with respondent (§8)",
        source="relationship.children_in_common",
    ),
    # §9 — Relief
    *_RELIEF_FIELDS,
    FormField(
        "9_residence_address",
        "Residence for sole use / eviction (§9)",
        source="ms.residence_address",
    ),
    FormField(
        "9_belongings_location",
        "Where to recover belongings (§9)",
        source="ms.belongings_location",
    ),
    # §9 (continued) — Chancery/County-only relief
    *_CHANCERY_FIELDS,
    # §10 — Other cases
    FormField(
        "other_cases",
        "Other pending petitions / orders (§10)",
        source="prior_orders.exists",
        note="Existence only; the §10 case detail is not collected — MSG5.",
    ),
    FormField("other_cases_detail", "Other cases (free text)", source="ms.other_cases"),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn and subscribed before a notary / court clerk at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MS resolver — adds the §1/§4/§5/§9 membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MS Petition for Domestic Abuse Protection Order (auditable map)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MS_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
