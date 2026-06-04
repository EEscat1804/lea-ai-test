"""District of Columbia Civil Protection Order petition form mapping.

Maps Vault intake answers onto the Superior Court of the District of Columbia,
Domestic Violence Division **Petition and Affidavit for Civil Protection Order**
(D.C. Code § 16-1001 et seq.). The petition requests a 12-month CPO and covers
the parties, the § 16-1001 relationship/eligibility basis, the DC nexus, an
affidavit of the acts, and a 1-16 list of relief requested.

The DC intake section (`vault.intake`, the `jurisdiction == "DC"` block) feeds
the DC-specific items. DC's relief list (and its many sub-checkboxes) is its own.

Protection: the form offers a substitute address and a Confidential Address Form
— intake only ever holds a safe mailing address, and the substitute-address box
defaults on. See coverage.md.

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

# The DC CPO petition carries no printed form number or revision date; confirm
# against the blank PDF dropped in this folder for lea-be-core's renderer.
FORM_ID = "DC-CPO-Petition"
FORM_REVISION = "n/a"
JURISDICTION = "DC"


def _substitute_address(_answers: dict[str, Any]) -> str:
    """Caption — request a substitute address (the home address is never listed)."""
    return "checked"


# Relief requested (items 1-16) — membership over `dc.relief`.
_DC_RELIEF = {
    "r_no_abuse": "no_abuse",  # 1
    "r_stay_away": "stay_away",  # 2
    "r_no_contact": "no_contact",  # 3
    "r_custody": "custody",  # 4
    "r_visitation": "visitation",  # 5
    "r_child_support": "child_support",  # 6
    "r_vacate": "vacate",  # 7
    "r_spousal_support": "spousal_support",  # 8
    "r_property": "property_possession",  # 9
    "r_health_insurance": "health_insurance",  # 10
    "r_reimburse": "reimburse",  # 11
    "r_counseling": "counseling",  # 12
    "r_police": "police_assistance",  # 13
    "r_attorney_fees": "attorney_fees",  # 14
    "r_other": "other",  # 15
    "r_emergency_tpo": "emergency_tpo",  # 16
}

# Stay-away sub-checkboxes (item 2) — membership over `dc.stay_away_places`.
_DC_STAY_AWAY = {
    "sa_person": "person",
    "sa_work": "work",
    "sa_home": "home",
    "sa_vehicle": "vehicle",
    "sa_childrens_school": "childrens_school",
    "sa_other_places": "other_places",
    "sa_other_persons": "other_persons",
}

# No-contact sub-checkboxes (item 3) — membership over `dc.contact_methods`.
_DC_CONTACT = {
    "contact_telephone": "telephone",
    "contact_writing": "writing",
    "contact_electronic": "electronic",
    "contact_any": "any_manner",
}

# Counseling sub-checkboxes (item 12) — membership over `dc.counseling_types`.
_DC_COUNSELING = {
    "couns_alcohol": "alcohol",
    "couns_drug": "drug",
    "couns_dv": "domestic_violence",
    "couns_parenting": "parenting",
    "couns_family_violence": "family_violence",
    "couns_other": "other",
}

# Police-assistance sub-checkboxes (item 13) — membership over `dc.police_actions`.
_DC_POLICE = {
    "police_stand_by_vacate": "stand_by_vacate",
    "police_turn_over_keys": "turn_over_keys",
    "police_recover_belongings": "recover_belongings",
    "police_assist_service": "assist_service",
}

_MEMBERSHIP = {
    "dc.relief": _DC_RELIEF,
    "dc.stay_away_places": _DC_STAY_AWAY,
    "dc.contact_methods": _DC_CONTACT,
    "dc.counseling_types": _DC_COUNSELING,
    "dc.police_actions": _DC_POLICE,
}

_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="dc.stay_away_places")
    for item, key in _DC_STAY_AWAY.items()
)
_CONTACT_FIELDS = tuple(
    FormField(item, f"No contact: {key.replace('_', ' ')}", source="dc.contact_methods")
    for item, key in _DC_CONTACT.items()
)
_COUNSELING_FIELDS = tuple(
    FormField(item, f"Counseling: {key.replace('_', ' ')}", source="dc.counseling_types")
    for item, key in _DC_COUNSELING.items()
)
_POLICE_FIELDS = tuple(
    FormField(item, f"Police: {key.replace('_', ' ')}", source="dc.police_actions")
    for item, key in _DC_POLICE.items()
)

DC_CPO_FIELDS: tuple[FormField, ...] = (
    # Caption — the home address is never listed; the substitute-address box is
    # requested and only the safe mailing address reaches the form.
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "substitute_address",
        "Request a substitute address",
        derive=_substitute_address,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "petitioner_substitute_address",
        "Petitioner substitute / safe mailing address",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    # 1 — Relationship / eligibility basis (§ 16-1001)
    FormField(
        "relationship_basis",
        "Respondent's relationship to petitioner",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto DC's item-1 checkboxes (by blood / "
        "legal custody / marriage / child in common / shared residence / "
        "romantic-dating). DC also allows a CPO on a stalking, § 16-1001(6)(B), or "
        "sexual-assault basis with no domestic relationship — those are legal "
        "determinations the attorney makes; not inferred here.",
    ),
    # 2, 3 — DC jurisdiction
    FormField(
        "petitioner_dc_nexus",
        "Petitioner lives/works/attends school in DC",
        source="dc.petitioner_dc_nexus",
    ),
    FormField("incident_in_dc", "An incident occurred in DC", source="dc.incident_in_dc"),
    # 4 — Affidavit of the acts (incident A from intake; B-D are overflow)
    FormField("incident_a_date", "Incident A — date", source="incidents[].date", required=True),
    FormField("incident_a_location", "Incident A — location", source="incidents[].location"),
    FormField(
        "incident_a_narrative",
        "Incident A — what the respondent did",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "incidents_bcd",
        "Incidents B-D",
        source=None,
        note="Additional incident slots not collected by intake (overflow) — DCG1.",
    ),
    # Relief requested (items 1-16)
    # 1
    FormField(
        "r_no_abuse",
        "Not to abuse/threaten/stalk/harass",
        source="dc.relief",
        needs_legal_review=True,
    ),
    # 2 — stay away (+ sub-places + details)
    FormField("r_stay_away", "Stay-away order", source="dc.relief", needs_legal_review=True),
    *_STAY_AWAY_FIELDS,
    FormField(
        "sa_other_places_detail", "Other stay-away places", source="dc.stay_away_other_places"
    ),
    FormField(
        "sa_other_persons_detail",
        "Other persons to stay away from",
        source="dc.stay_away_other_persons",
    ),
    # 3 — no contact (+ methods)
    FormField("r_no_contact", "No-contact order", source="dc.relief", needs_legal_review=True),
    *_CONTACT_FIELDS,
    # 4 — custody
    FormField(
        "r_custody",
        "Temporary custody of the children",
        source="dc.relief",
        needs_legal_review=True,
    ),
    FormField(
        "custody_children",
        "Children for custody",
        source="protected_persons.children[]",
        note="Names; form items 4a-4e (children's addresses, prior cases, other "
        "claimants) and birth certificates are not collected — DCG2.",
    ),
    # 5 — visitation
    FormField(
        "r_visitation",
        "Respondent visitation (if adequately protected)",
        source="dc.relief",
        needs_legal_review=True,
    ),
    # 6 — child support
    FormField(
        "r_child_support",
        "Child support (DC Guideline)",
        source="dc.relief",
        needs_legal_review=True,
    ),
    FormField(
        "child_support_income",
        "Respondent annual gross income",
        source=None,
        note="Items 6/6a-6d (income, prior cases, public assistance, employment, special "
        "costs) not collected by intake — DCG3.",
    ),
    # 7 — vacate
    FormField("r_vacate", "Vacate the home", source="dc.relief", needs_legal_review=True),
    FormField("vacate_home_basis", "Home ownership basis (vacate)", source="dc.vacate_home_basis"),
    # 8 — spousal/financial support
    FormField(
        "r_spousal_support",
        "Financial assistance / spousal support",
        source="dc.relief",
        needs_legal_review=True,
    ),
    # 9 — property possession
    FormField(
        "r_property",
        "Possession of jointly owned property",
        source="dc.relief",
        needs_legal_review=True,
    ),
    FormField("property_description", "Property to possess", source="dc.property_description"),
    # 10 — health insurance
    FormField(
        "r_health_insurance",
        "No removal from health insurance",
        source="dc.relief",
        needs_legal_review=True,
    ),
    # 11 — reimburse
    FormField(
        "r_reimburse",
        "Reimburse costs / property damage",
        source="dc.relief",
        needs_legal_review=True,
    ),
    FormField(
        "reimburse_damaged_property", "Costs / damaged property", source="dc.damaged_property"
    ),
    # 12 — counseling (+ types)
    FormField("r_counseling", "Counseling program", source="dc.relief", needs_legal_review=True),
    *_COUNSELING_FIELDS,
    # 13 — police assistance (+ actions)
    FormField("r_police", "Order police to assist", source="dc.relief", needs_legal_review=True),
    *_POLICE_FIELDS,
    # 14 — attorney's fees
    FormField(
        "r_attorney_fees", "Attorney's fees and costs", source="dc.relief", needs_legal_review=True
    ),
    # 15 — other
    FormField("r_other", "Other relief", source="dc.relief", needs_legal_review=True),
    FormField("other_detail", "Other relief detail", source="dc.other_relief"),
    # 16 — emergency TPO
    FormField(
        "r_emergency_tpo",
        "Emergency Temporary Protection Order today",
        source="dc.relief",
        needs_legal_review=True,
    ),
    # Verification / signature — sworn before a Deputy Clerk / OAG / Notary at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Affidavit sworn before a Deputy Clerk / Office of the Attorney General / "
        "Notary — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """DC resolver — adds the relief and sub-checklist membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto the DC CPO petition fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=DC_CPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
