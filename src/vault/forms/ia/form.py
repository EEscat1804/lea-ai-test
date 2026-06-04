"""Iowa Petition for Relief from Domestic Abuse form mapping.

Maps Vault intake answers onto Iowa's **Petition for Relief from Domestic Abuse**
(Iowa Judicial Branch Rule 17.10—Form 11, Iowa Code chapter 236, November 2022;
Iowa District Court). The petition covers the county, the parties, the §7
relationship basis, the §8 abuse types, the §9 recent/past narrative, the §10
firearms block, the §11 children block, the §20 additional-possession requests,
the §22 counseling request, the §23 temporary/final order election and order
checklist (items 1-13), and the §24 confidentiality/sealing requests. IA's
relationship and relief lists are their own.

The IA intake section (`vault.intake`, the `_ia_step` method) plus the shared
minor-filing gate feeds these items. Form 11 has **no respondent
physical-description block and no respondent vehicle block** (the §5 age block and
the §20 "Vehicle" possession item — the petitioner's family car — are not
respondent identifiers), so IA is in neither `PHYSICAL_DESCRIPTION_STATES` nor
`VEHICLE_DESCRIPTION_STATES`. A minor may be a protected person, and IA is in
`MINOR_FILING_STATES`.

Protection: §3 lets the petitioner give a safe mailing address ("If you do not
want Defendant to know where you live, you may use … a shelter, a post office box
…"), and §24 offers explicit seal / remove-address requests, so the petitioner
address maps to the safe mailing address and `ia.confidential_requests` records
the §24 election. Protected information (full names, birthdates, SSNs) goes on a
separate **Protected Information Disclosure** form — Form 11 itself has no SSN
field, so IA is NOT in the SSN-for-support gate even though §19/§23 request
ongoing support. See coverage.md.

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

FORM_ID = "Rule 17.10 Form 11"  # no short form number, IAG1
FORM_REVISION = "2022-11"  # November 2022
JURISDICTION = "IA"


# §7B — relationship at the time of the abuse. Membership over
# `ia.relationship_basis`.
_IA_RELATIONSHIP = {
    "7_family_living_together": "family_living_together",
    "7_separated_divorced": "separated_divorced",
    "7_parents_same_child": "parents_same_child",
    "7_family_not_living_together": "family_not_living_together",
    "7_intimate_relationship": "intimate_relationship",
}

# §8 — how the defendant abused the petitioner. Membership over `ia.abuse_types`.
_IA_ABUSE_TYPES = {
    "8_physical": "physical",
    "8_sexual": "sexual",
    "8_threats": "threats",
}

# §23 A/B — temporary and/or final order. Membership over `ia.order_request`.
_IA_ORDER_REQUEST = {
    "23_temporary": "temporary",
    "23_final": "final",
}

# §23C — order the defendant to … (items 1-13). Membership over `ia.relief`.
_IA_RELIEF = {
    "23c_1_stop_abuse": "stop_abuse",
    "23c_2_stay_away_me": "stay_away_me",
    "23c_3_stay_away_children": "stay_away_children",
    "23c_4_stay_away_home": "stay_away_home",
    "23c_5_stay_away_work_school": "stay_away_work_school",
    "23c_6_no_contact": "no_contact",
    "23c_7_possession_home": "possession_home",
    "23c_8_possession_car": "possession_car",
    "23c_9_custody_visitation": "custody_visitation",
    "23c_10_financial_support": "financial_support",
    "23c_11_no_firearms": "no_firearms",
    "23c_12_possession_other": "possession_other",
    "23c_13_other": "other",
}

# §20 — additional possession requests. Membership over `ia.possession_requests`.
_IA_POSSESSION = {
    "20_residence": "residence",
    "20_vehicle": "vehicle",
    "20_pet": "pet",
    "20_documents": "documents",
    "20_other": "other",
}

# §22 — individual counseling requested for. Membership over `ia.counseling`.
_IA_COUNSELING = {
    "22_no_one": "no_one",
    "22_me": "me",
    "22_defendant": "defendant",
    "22_children": "children",
}

# §24 — confidentiality / sealing requests. Membership over
# `ia.confidential_requests`.
_IA_CONFIDENTIAL = {
    "24_seal_file": "seal_file",
    "24_remove_address": "remove_address",
    "24_seal_children": "seal_children",
    "24_other": "other",
}

_MEMBERSHIP = {
    "ia.relationship_basis": _IA_RELATIONSHIP,
    "ia.abuse_types": _IA_ABUSE_TYPES,
    "ia.order_request": _IA_ORDER_REQUEST,
    "ia.relief": _IA_RELIEF,
    "ia.possession_requests": _IA_POSSESSION,
    "ia.counseling": _IA_COUNSELING,
    "ia.confidential_requests": _IA_CONFIDENTIAL,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="ia.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _IA_RELATIONSHIP.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="ia.abuse_types", needs_legal_review=True
    )
    for item, key in _IA_ABUSE_TYPES.items()
)
_ORDER_REQUEST_FIELDS = tuple(
    FormField(
        item,
        f"Order requested: {key.replace('_', ' ')}",
        source="ia.order_request",
        needs_legal_review=True,
    )
    for item, key in _IA_ORDER_REQUEST.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ia.relief", needs_legal_review=True)
    for item, key in _IA_RELIEF.items()
)
_POSSESSION_FIELDS = tuple(
    FormField(item, f"Possession: {key.replace('_', ' ')}", source="ia.possession_requests")
    for item, key in _IA_POSSESSION.items()
)
_COUNSELING_FIELDS = tuple(
    FormField(item, f"Counseling: {key.replace('_', ' ')}", source="ia.counseling")
    for item, key in _IA_COUNSELING.items()
)
_CONFIDENTIAL_FIELDS = tuple(
    FormField(
        item,
        f"Confidentiality: {key.replace('_', ' ')}",
        source="ia.confidential_requests",
        needs_legal_review=True,
    )
    for item, key in _IA_CONFIDENTIAL.items()
)

IA_RELIEF_FIELDS: tuple[FormField, ...] = (
    # Caption / §2
    FormField("county", "County where the petition is filed", source="ia.county", required=True),
    FormField(
        "civil_number",
        "Civil number",
        source=None,
        note="Filled in by the clerk of court — IAG2.",
    ),
    # §1/§3 — Plaintiff
    FormField("petitioner", "Plaintiff full name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_address",
        "Plaintiff mailing address (§3)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="§3 explicitly allows a safe mailing address (shelter / PO box); the residence is "
        "withheld and goes on the Protected Information Disclosure form.",
    ),
    # §4/§6 — Defendant
    FormField("respondent", "Defendant full name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Defendant home address", source="respondent.last_known_address"
    ),
    FormField(
        "respondent_minor",
        "Defendant is 17 or younger (§5A)",
        source="ia.defendant_minor",
    ),
    FormField(
        "respondent_year_of_birth",
        "Defendant year of birth (§5B, if known)",
        source="respondent.dob",
        note="Intake holds a full date; the form wants the year — partial, IAG3.",
    ),
    FormField("respondent_employer", "Defendant employer (§6)", source="respondent.employer_name"),
    FormField(
        "respondent_employer_address",
        "Defendant work address (§6)",
        source="respondent.employer_address",
    ),
    # §7 — Relationship
    FormField(
        "relationship_describe",
        "Relationship in the petitioner's own words (§7A)",
        source="relationship.type",
        note="Free-text relationship; the §7B checklist is the legal basis.",
    ),
    *_RELATIONSHIP_FIELDS,
    # §8 — Abuse types
    *_ABUSE_FIELDS,
    # §9 — Narrative
    FormField(
        "recent_abuse_narrative",
        "Most recent acts of abuse (§9A)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "When the abuse occurred", source="incidents[].date"),
    FormField("abuse_location", "Where the abuse occurred", source="incidents[].location"),
    FormField(
        "past_abuse",
        "Past abuse (§9B)",
        source=None,
        note="Not collected separately from the most-recent statement — IAG4.",
    ),
    # §10 — Firearms
    FormField(
        "firearms_access",
        "Defendant has access to / owns firearms or weapons (§10)",
        source="firearm.respondent_has_access",
    ),
    FormField(
        "firearms_detail", "Firearm description / location (§10)", source="firearm.locations[]"
    ),
    # §11 — Children
    FormField(
        "children",
        "Children in common, under 18 (§11A) — initials",
        source="protected_persons.children[]",
        note="Names only; the form wants initials / birth year / county-state and uses a "
        "Protected Information Disclosure form for full detail — IAG5.",
    ),
    # §23 A/B — order type
    *_ORDER_REQUEST_FIELDS,
    # §23C — relief
    *_RELIEF_FIELDS,
    FormField(
        "23c_7_home_address",
        "Family-home address / possession reason (item 7)",
        source="ia.home_address",
    ),
    FormField(
        "23c_10_support_detail",
        "Financial support amount / reasons (item 10 / §19)",
        source="ia.support_detail",
        note="§19 income/support detail; the petitioner SSN is NOT on this form (Protected "
        "Information Disclosure form) — IA is not in the SSN gate. IAG6.",
    ),
    FormField(
        "23c_13_other_detail", "Other order requested (item 13)", source="ia.relief_other_detail"
    ),
    # §20 — possession requests
    *_POSSESSION_FIELDS,
    FormField("20_residence_detail", "Residence possession detail", source="ia.residence_detail"),
    FormField("20_vehicle_detail", "Vehicle possession detail", source="ia.vehicle_detail"),
    FormField("20_pet_detail", "Pet / companion-animal detail", source="ia.pet_detail"),
    # §22 — counseling
    *_COUNSELING_FIELDS,
    # §24 — confidentiality
    *_CONFIDENTIAL_FIELDS,
    # §17 — other custody / support order
    FormField(
        "other_court_order",
        "Other court order about custody / support (§17)",
        source="prior_orders.exists",
        note="Existence only; the §15-18 residence-history / custody tables are not "
        "collected — IAG7.",
    ),
    # §27 — Oath and signature
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Certified under penalty of perjury at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """IA resolver — adds the §7/§8/§20/§22/§23/§24 membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto IA Form 11 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=IA_RELIEF_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
