"""Minnesota Petition for Order for Protection form mapping.

Maps Vault intake answers onto Minnesota's **Petition for Order for Protection
(OFP)** (OFP102, Minn. Stat. § 518B.01, Rev. 7/25; District Court). The petition
covers the parties, the §1 confidential-address election, the §3/#7 who-needs-
protection and relationship blocks, the §6 respondent information, the #11-#13
narrative and immediate-danger statement, the #15 ex parte relief (items a-j), and
the #16-#22 relief-requiring-a-hearing items (custody/parenting, financial support,
property, restitution, counseling, firearms, extended term). MN's relationship and
relief lists are their own.

The MN intake section (`vault.intake`, the `_mn_step` method) plus the shared
minor-filing gate feeds these items. OFP102 carries only the respondent's
race/gender/DOB (#6), **not** a height/weight/eyes/hair block, so MN is carved out
of `PHYSICAL_DESCRIPTION_STATES`; `_mn_step` asks the respondent dob/gender/race
the form does need. OFP102 has no respondent vehicle block, so MN is not in
`VEHICLE_DESCRIPTION_STATES`. A minor may be a protected person, so MN is in
`MINOR_FILING_STATES`.

Protection: §1 offers a real confidential mechanism — "I am requesting that my
address be kept confidential by submitting the … Confidential Address/Phone
Request form (OFP107-P)". Intake only ever holds a safe mailing address, so
`address_confidential` is derived `"checked"` and the petitioner address maps to
the safe mailing address. The form requests support (#17) but has no petitioner
SSN field, so MN is not in the SSN-for-support gate. See coverage.md.

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

FORM_ID = "OFP102"
FORM_REVISION = "2025-07"  # Rev. 7/25
JURISDICTION = "MN"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """§1 — petitioner requests a confidential address via OFP107-P.

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms OFP107-P is filed.
    """
    return "checked"


# #7 — how the petitioner knows the respondent. Membership over
# `mn.relationship_basis`.
_MN_RELATIONSHIP = {
    "7_married": "married",
    "7_divorced": "divorced",
    "7_currently_live_together": "currently_live_together",
    "7_used_to_live_together": "used_to_live_together",
    "7_child_together": "child_together",
    "7_unborn_child_together": "unborn_child_together",
    "7_parent_child": "parent_child",
    "7_related_by_blood": "related_by_blood",
    "7_romantic_sexual": "romantic_sexual",
}

# #15 — ex parte relief (items a-j). Membership over `mn.relief`.
_MN_RELIEF = {
    "15a_no_harm": "no_harm",
    "15b_no_contact": "no_contact",
    "15c_stay_away_home": "stay_away_home",
    "15d_stay_away_work": "stay_away_work",
    "15e_stay_away_other": "stay_away_other",
    "15f_insurance": "insurance",
    "15g_pet_possession": "pet_possession",
    "15h_no_pet_abuse": "no_pet_abuse",
    "15i_le_assist": "le_assist",
    "15j_other": "other",
}

# #16-#22 — relief requiring a hearing. Membership over `mn.hearing_relief`.
_MN_HEARING_RELIEF = {
    "16_custody_parenting": "custody_parenting",
    "17_financial_support": "financial_support",
    "18_property": "property",
    "19_restitution": "restitution",
    "20_counseling": "counseling",
    "21_firearms": "firearms",
    "22_extended_term": "extended_term",
}

_MEMBERSHIP = {
    "mn.relationship_basis": _MN_RELATIONSHIP,
    "mn.relief": _MN_RELIEF,
    "mn.hearing_relief": _MN_HEARING_RELIEF,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="mn.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _MN_RELATIONSHIP.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="mn.relief", needs_legal_review=True)
    for item, key in _MN_RELIEF.items()
)
_HEARING_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Hearing relief: {key.replace('_', ' ')}",
        source="mn.hearing_relief",
        needs_legal_review=True,
    )
    for item, key in _MN_HEARING_RELIEF.items()
)

MN_OFP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County", source="mn.county", required=True),
    FormField(
        "judicial_district",
        "Judicial district / court file number",
        source=None,
        note="Assigned by the clerk at filing — MNG1.",
    ),
    # #1 — Petitioner
    FormField("petitioner", "Petitioner full name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_gender",
        "Petitioner gender (federal reporting)",
        source="petitioner.gender",
        note="Federal-reporting demographic; not collected by Tier-1 intake — MNG2.",
    ),
    FormField(
        "petitioner_race",
        "Petitioner race (federal reporting)",
        source="petitioner.race",
        note="Federal-reporting demographic; not collected by Tier-1 intake — MNG2.",
    ),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "address_confidential",
        "Confidential address requested (§1, OFP107-P)",
        derive=_address_confidential,
        needs_legal_review=True,
        note="Minnesota's Confidential Address/Phone Request form (OFP107-P); "
        "attorney/advocate confirms it is filed.",
    ),
    FormField(
        "petitioner_address",
        "Petitioner address (§1)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; the residential address is withheld via OFP107-P.",
    ),
    # #3 — Other protected persons
    FormField(
        "protected_others",
        "Other persons who need protection (#3)",
        source="protected_persons.children[]",
        note="Names; the form wants per-person DOB / race / gender / relationship — partial, MNG3.",
    ),
    # #6 — Respondent
    FormField("respondent", "Respondent full name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField("respondent_gender", "Respondent gender", source="respondent.gender"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField(
        "respondent_dob", "Respondent date of birth (or approximate age)", source="respondent.dob"
    ),
    FormField(
        "respondent_employer", "Respondent employer (#17c)", source="respondent.employer_name"
    ),
    FormField(
        "respondent_employer_address",
        "Respondent employer address (#17c)",
        source="respondent.employer_address",
    ),
    # #7 — Relationship
    *_RELATIONSHIP_FIELDS,
    # #11 — Narrative
    FormField(
        "abuse_narrative",
        "What the respondent did to threaten / harm / make you afraid (#11)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the most recent domestic abuse", source="incidents[].date"),
    FormField("abuse_witnesses", "Who was there", source="incidents[].witnesses_present"),
    FormField(
        "abuse_weapon", "Use / threatened use of weapons", source="incidents[].weapon_involved"
    ),
    FormField("abuse_injury", "Injuries", source="incidents[].injury"),
    FormField("abuse_police", "Did the police or sheriff come", source="incidents[].police_called"),
    # #13 — Immediate danger
    FormField(
        "immediate_danger",
        "Belief that the abuse will continue / immediate danger (#13)",
        source="mn.immediate_danger",
        needs_legal_review=True,
    ),
    # #15 — Ex parte relief
    *_RELIEF_FIELDS,
    FormField(
        "15e_other_location",
        "Other location to stay away from (item e)",
        source="mn.other_location",
    ),
    FormField(
        "15g_pet_detail", "Pet / companion-animal possession (item g)", source="mn.pet_detail"
    ),
    FormField(
        "15j_other_detail", "Other ex parte relief (item j)", source="mn.relief_other_detail"
    ),
    # #16-#22 — Relief requiring a hearing
    *_HEARING_RELIEF_FIELDS,
    FormField(
        "17_support_detail",
        "Financial-support detail / incomes (#17)",
        source="mn.support_detail",
        note="#17 income tables; the petitioner SSN is NOT on this form, so MN is not in "
        "the SSN gate — MNG4.",
    ),
    # #10 — Other cases
    FormField(
        "other_cases",
        "Other family / domestic-abuse / harassment cases (#8-#10)",
        source="prior_orders.exists",
        note="Protective-order existence only; the #8-#10 case tables are not collected — MNG5.",
    ),
    FormField("other_cases_detail", "Other cases (free text)", source="mn.other_cases"),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Declared under penalty of perjury (Minn. Stat. § 358.116) at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MN resolver — adds the relationship / #15 / #16-#22 membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MN OFP102 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MN_OFP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
