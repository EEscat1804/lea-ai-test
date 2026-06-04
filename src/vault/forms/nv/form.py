"""Nevada Application for Protection Order Against Domestic Violence form mapping.

Maps Vault intake answers onto the Nevada Supreme Court **Application for
Protection Order Against Domestic Violence** (© 2022 Nevada Supreme Court, NRS
33). The application covers the court/parties, an interpreter request, who needs
protection, the abuse grounds, the relationship basis, other court cases,
firearms, the most-recent event, the item-10 temporary-protections list, the
page-7 custody/pets requests, and the item-11 order length (45-day vs. extended)
with its extended-relief list. NV's relief list is its own, distinct from the
other states'.

The NV intake section (`vault.intake`, the `_nv_step` method plus the shared
interpreter gate — NV is in it) feeds the NV-specific items.

No printed form number: the document carries only the title and "© 2022 Nevada
Supreme Court", so `FORM_ID` is descriptive and the missing number is flagged as
gap NVG1 (we never fabricate one).

Protection: item 10 warns the adverse party receives a copy and instructs the
applicant not to list confidential addresses ("is your address confidential?
Yes — leave address blank"). Intake only ever holds a safe mailing address, so
the confidential-address request defaults on and the home address is never
written. See coverage.md.

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

# No printed form number — descriptive id; the gap is NVG1.
FORM_ID = "Application for Protection Order - DV"
FORM_REVISION = "2022"  # © 2022 Nevada Supreme Court
JURISDICTION = "NV"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Item 10 — keep the applicant's address confidential (never collected here)."""
    return "checked"


def _temporary_order(_answers: dict[str, Any]) -> str:
    """Item 11 — the application automatically asks for the up-to-45-day temporary order."""
    return "checked"


def _no_personal_info(_answers: dict[str, Any]) -> str:
    """Item 14 — attestation that no NRS 603A.040 personal information is included."""
    return "checked"


# Item 3 — who needs protection. Membership over `nv.who_needs_protection`.
_NV_WHO = {
    "who_me": "me",
    "who_minor_children": "minor_children",
}

# Item 4 — abuse grounds. Membership over `nv.protection_reason`.
_NV_REASON = {
    "reason_dv_me": "dv_against_me",
    "reason_dv_child": "dv_against_child",
}

# Item 10 — temporary protections requested (incl. the page-7 pets requests).
# Membership over `nv.temp_protections`.
_NV_TEMP = {
    "tp_prohibited_activities": "prohibited_activities",
    "tp_no_contact_me": "no_contact_me",
    "tp_contact_me_parenting": "contact_me_parenting",
    "tp_no_contact_children": "no_contact_children",
    "tp_contact_children_parenting": "contact_children_parenting",
    "tp_current_residence": "current_residence",
    "tp_personal_belongings": "personal_belongings",
    "tp_work": "work",
    "tp_school_daycare": "school_daycare",
    "tp_other_places": "other_places",
    "tp_pets_safety": "pets_safety",
    "tp_pets_possession": "pets_possession",
}

# Item 10 — how the adverse party may contact the applicant about parenting.
# Membership over `nv.contact_me_method`.
_NV_CONTACT_METHOD = {
    "cm_text": "text",
    "cm_email": "email",
    "cm_phone": "phone",
    "cm_writing": "writing",
    "cm_other": "other",
}

# Item 11 — extended-order (up to 2 years) additional relief. Membership over
# `nv.extended_relief`.
_NV_EXTENDED = {
    "ext_rent_mortgage": "rent_mortgage",
    "ext_household_support": "household_support",
    "ext_child_support": "child_support",
    "ext_lost_earnings": "lost_earnings",
    "ext_costs_fees": "costs_fees",
    "ext_pets_arrangement": "pets_arrangement",
    "ext_other": "other",
}

_MEMBERSHIP = {
    "nv.who_needs_protection": _NV_WHO,
    "nv.protection_reason": _NV_REASON,
    "nv.temp_protections": _NV_TEMP,
    "nv.contact_me_method": _NV_CONTACT_METHOD,
    "nv.extended_relief": _NV_EXTENDED,
}

_WHO_FIELDS = tuple(
    FormField(item, f"Needs protection: {key.replace('_', ' ')}", source="nv.who_needs_protection")
    for item, key in _NV_WHO.items()
)
_REASON_FIELDS = tuple(
    FormField(
        item,
        f"Grounds: {key.replace('_', ' ')}",
        source="nv.protection_reason",
        needs_legal_review=True,
    )
    for item, key in _NV_REASON.items()
)
_TEMP_FIELDS = tuple(
    FormField(
        item,
        f"Temp protection: {key.replace('_', ' ')}",
        source="nv.temp_protections",
        needs_legal_review=True,
    )
    for item, key in _NV_TEMP.items()
)
_CONTACT_METHOD_FIELDS = tuple(
    FormField(item, f"Parenting contact by: {key.replace('_', ' ')}", source="nv.contact_me_method")
    for item, key in _NV_CONTACT_METHOD.items()
)
_EXTENDED_FIELDS = tuple(
    FormField(
        item,
        f"Extended relief: {key.replace('_', ' ')}",
        source="nv.extended_relief",
        needs_legal_review=True,
    )
    for item, key in _NV_EXTENDED.items()
)

NV_APPLICATION_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court_type", "Court (district / justice)", source="nv.court_type", required=True),
    FormField("court_township", "Justice court township", source="nv.township"),
    FormField("county", "County", source="nv.county", required=True),
    FormField("applicant", "Applicant name", source="petitioner.legal_name", required=True),
    FormField("adverse_party", "Adverse party name", source="respondent.legal_name", required=True),
    FormField(
        "adverse_party_type", "Adverse party is adult / minor", source="nv.adverse_party_type"
    ),
    # 1 — Applicant info
    FormField(
        "interpreter", "Interpreter needed / language", source="petitioner.interpreter_language"
    ),
    # 2 — Adverse party
    FormField(
        "adverse_in_custody",
        "Adverse party currently in jail/prison",
        source="nv.adverse_in_custody",
    ),
    FormField(
        "adverse_custody_where",
        "Where the adverse party is held",
        source=None,
        note="Free-text 'where' not collected — NVG2.",
    ),
    # 3 — Who needs protection
    *_WHO_FIELDS,
    FormField(
        "protected_children",
        "Minor children protected (chart)",
        source="protected_persons.children[]",
        note="Names; the form's chart wants each child's DOB and both parents — partial, NVG3.",
    ),
    # 4 — Abuse grounds
    *_REASON_FIELDS,
    FormField(
        "reason_parent_guardian",
        "Filing as child's parent / legal guardian",
        source=None,
        note="Parent-vs-guardian election not collected — NVG4.",
    ),
    # 5 — Relationship basis
    FormField(
        "relationship_basis",
        "Applicant's relationship to adverse party",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto NV's item-5 categories (married / former "
        "spouse / dating / former dating / child in common / other). NV requires a qualifying "
        "intimate-partner / blood / marriage / parent-of-child relationship — attorney confirms.",
    ),
    # 6 — Other court cases
    FormField(
        "other_cases",
        "Other current/prior court cases",
        source="prior_orders.exists",
        note="Protective-order existence only; the case type/county/state/number detail is "
        "collected as free text — NVG5.",
    ),
    FormField(
        "other_cases_detail", "Other cases (type / county / number)", source="nv.other_cases_detail"
    ),
    # 7 — Firearms
    FormField(
        "firearms_possess",
        "Adverse party owns/possesses a firearm",
        source="firearm.respondent_has_access",
        note="Form offers No / Yes / I don't know; intake is a boolean — NVG6.",
    ),
    # 8 — Most recent event
    FormField("recent_date", "Date of most recent event", source="incidents[].date"),
    FormField("recent_location", "City/state/location of the event", source="incidents[].location"),
    FormField("recent_weapon", "Weapon used or threatened", source="incidents[].weapon_involved"),
    FormField("recent_police", "Did the police come", source="incidents[].police_called"),
    FormField(
        "recent_arrested",
        "Was anyone arrested (who)",
        source=None,
        note="Arrest detail not collected — NVG7.",
    ),
    FormField(
        "recent_narrative",
        "What happened (most recent event)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    # 9 — Past events
    FormField(
        "past_events",
        "Past abuse / threats",
        source=None,
        note="Not collected separately from the most-recent statement — NVG8.",
    ),
    # 10 — Temporary protections + details
    *_TEMP_FIELDS,
    *_CONTACT_METHOD_FIELDS,
    FormField(
        "address_confidential",
        "Applicant's address kept confidential",
        derive=_address_confidential,
        note="Defaulted on — the survivor's home address is never collected; the form warns "
        "the adverse party sees any address written.",
    ),
    FormField(
        "residence_live_together",
        "Applicant and adverse party live together",
        source="relationship.live_together_now",
    ),
    FormField(
        "residence_lease_holder",
        "Whose name is on the lease/title",
        source=None,
        note="Lease/title holder + move-in date not collected — NVG9.",
    ),
    FormField(
        "belongings_address",
        "Address to retrieve belongings (LE escort)",
        source="nv.belongings_address",
    ),
    FormField(
        "work_employer", "Applicant's employer (stay-away)", source="respondent.employer_name"
    ),
    FormField(
        "work_address", "Applicant's work address (stay-away)", source="respondent.employer_address"
    ),
    FormField(
        "other_places_detail", "Other places to stay away from", source="nv.other_places_detail"
    ),
    # 10 (page 7) — Custody / visitation
    FormField(
        "custody_choice",
        "Children/custody request",
        source="nv.custody",
        note="A UCCJEA Declaration is required for temporary custody, not assembled here — NVG10.",
    ),
    FormField("visitation_detail", "Requested visitation schedule", source="nv.visitation_detail"),
    # 11 — Length of order + extended relief
    FormField("temporary_order", "Up-to-45-day temporary order requested", derive=_temporary_order),
    FormField(
        "order_length",
        "Order length (45-day / extended)",
        source="nv.order_length",
        needs_legal_review=True,
    ),
    *_EXTENDED_FIELDS,
    # 14 / verification
    FormField(
        "no_personal_info",
        "No NRS 603A.040 personal information included",
        derive=_no_personal_info,
    ),
    FormField(
        "signature",
        "Applicant signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Verified under penalty of perjury under Nevada law — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NV resolver — adds the who/reason/temp/contact-method/extended membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto the NV Application for Protection Order (auditable map)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NV_APPLICATION_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
