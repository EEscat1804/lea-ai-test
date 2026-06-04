"""Colorado Complaint/Motion for Civil Protection Order form mapping.

Maps Vault intake answers onto Colorado Judicial Branch form **JDF 402,
_Complaint/Motion for Civil Protection Order_** (C.R.S. § 13-14-101 et seq., Rev.
December 19, 2022). The motion covers the parties, the statutory basis (item 1),
residence/relationship (item 2), other protected persons, the incidents, imminent
danger, an address-confidentiality request (item 6), and an item-7 relief list.

The CO intake section (`vault.intake`, the `jurisdiction == "CO"` block plus the
shared physical-description block — CO is a physical-description state) feeds the
CO-specific items. CO's basis and relief lists are its own, distinct from the
other states'.

Protection: section 6 lets the petitioner omit their address and phone — intake
only ever holds a safe mailing address, and the omit-address box defaults on. See
coverage.md.

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

FORM_ID = "JDF 402"
FORM_REVISION = "2022-12"  # R: December 19, 2022
JURISDICTION = "CO"


def _confidential_address(_answers: dict[str, Any]) -> str:
    """Section 6 — omit the petitioner's address and phone (defaulted on)."""
    return "checked"


def _filing_type(_answers: dict[str, Any]) -> str:
    """Caption — the Vault files this as a Motion for Civil Protection Order."""
    return "Motion for Civil Protection Order"


# Item 1 — statutory basis. Membership over `co.basis`.
_CO_BASIS = {
    "basis_domestic_abuse": "domestic_abuse",
    "basis_stalking": "stalking",
    "basis_sexual_assault": "sexual_assault",
    "basis_unlawful_sexual_contact": "unlawful_sexual_contact",
    "basis_elder_at_risk": "elder_at_risk",
    "basis_physical_assault": "physical_assault",
}

# Item 5 — imminent danger. Membership over `co.imminent_danger`.
_CO_IMMINENT = {
    "danger_life_health": "harm_life_health",
    "danger_exclude_home": "harm_if_not_excluded",
}

# Item 7 — relief requested (a-i). Membership over `co.relief`.
_CO_RELIEF = {
    "r_no_abuse": "no_abuse",  # 7a
    "r_no_contact": "no_contact",  # 7b
    "r_limited_contact": "limited_contact",  # 7b alt
    "r_exclude_home": "exclude_home",  # 7c
    "r_stay_away": "stay_away",  # 7d
    "r_children_no_contact": "custody_no_contact_children",  # 7e
    "r_children_parenting_time": "custody_parenting_time",  # 7e alt
    "r_protect_animals": "protect_animals",  # 7f
    "r_firearm_relinquish": "firearm_relinquish",  # 7g
    "r_no_interference": "no_interference",  # 7h
    "r_other": "other",  # 7i
}

# Item 7d — stay-away places. Membership over `co.stay_away_places`.
_CO_STAY_AWAY = {
    "sa_home": "home",
    "sa_work": "work",
    "sa_school": "school",
    "sa_other": "other",
}

_MEMBERSHIP = {
    "co.basis": _CO_BASIS,
    "co.imminent_danger": _CO_IMMINENT,
    "co.relief": _CO_RELIEF,
    "co.stay_away_places": _CO_STAY_AWAY,
}

_BASIS_FIELDS = tuple(
    FormField(item, f"Basis: {key.replace('_', ' ')}", source="co.basis", needs_legal_review=True)
    for item, key in _CO_BASIS.items()
)
_IMMINENT_FIELDS = tuple(
    FormField(item, f"Imminent danger: {key.replace('_', ' ')}", source="co.imminent_danger")
    for item, key in _CO_IMMINENT.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="co.stay_away_places")
    for item, key in _CO_STAY_AWAY.items()
)

CO_JDF402_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "court_type",
        "Court type (Municipal/County/District/Juvenile/Probate)",
        source=None,
        needs_legal_review=True,
        note="A CPO is filed in county/district court; the clerk/attorney selects the "
        "court — not inferred from intake.",
    ),
    FormField("county", "County, Colorado", source="co.county", required=True),
    FormField("filing_type", "Filing type", derive=_filing_type),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField(
        "filer_address",
        "Filer address",
        source=None,
        note="Omitted by design — see section 6; only a safe mailing address is held.",
    ),
    FormField("filer_phone", "Filer phone", source=None, note="Omitted by design — see section 6."),
    # 1 — Basis (mark applicable circumstances)
    *_BASIS_FIELDS,
    # 2 — Residence / employment + relationship
    FormField(
        "item2_petitioner_county", "Petitioner resides/employed in county", source="co.county"
    ),
    FormField(
        "item2_respondent_county",
        "Respondent resides/employed in county",
        source=None,
        note="Respondent's county not collected — COG1.",
    ),
    FormField(
        "relationship_basis",
        "How the petitioner knows the respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto item 2's 'I know [respondent] "
        "because' — attorney confirms.",
    ),
    # 3 — Other protected persons (+ JDF 404 if children)
    FormField(
        "protected_persons",
        "Other protected persons",
        source="protected_persons.children[]",
        note="Names; form wants each person's DOB/sex/race and JDF 404 Affidavit "
        "Regarding Children — partial, COG2.",
    ),
    # 4 — Incidents
    FormField("incident_recent_date", "Most recent incident — date", source="incidents[].date"),
    FormField(
        "incident_recent_location",
        "Most recent incident — county/location",
        source="incidents[].location",
    ),
    FormField(
        "incident_recent_narrative",
        "Most recent incident — what happened",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "incident_serious",
        "Most serious incident (4b)",
        source=None,
        note="Not collected by intake (overflow) — COG3.",
    ),
    FormField(
        "incident_other",
        "Other past incidents (4c)",
        source=None,
        note="Not collected by intake (overflow) — COG3.",
    ),
    FormField(
        "other_orders",
        "Other protection orders in effect (4d)",
        source="prior_orders.exists",
        note="Existence only; issuing court/state/date not collected — COG3.",
    ),
    # 5 — Imminent danger
    *_IMMINENT_FIELDS,
    # 6 — Address confidentiality (protection-minded default)
    FormField(
        "confidential_address",
        "Omit petitioner address and phone",
        derive=_confidential_address,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    # 7 — Relief requested (a-i) + details
    FormField(
        "r_no_abuse",
        "7a — refrain from contact/harass/injure/stalk/...",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_no_contact", "7b — no contact at all", source="co.relief", needs_legal_review=True
    ),
    FormField(
        "r_limited_contact",
        "7b — limited contact only",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField("limited_contact_terms", "Limited-contact terms", source="co.limited_contact_terms"),
    FormField(
        "r_exclude_home", "7c — excluded from my home", source="co.relief", needs_legal_review=True
    ),
    FormField("exclude_home_address", "Home address to exclude from", source="co.home_address"),
    FormField(
        "r_stay_away", "7d — stay away from places", source="co.relief", needs_legal_review=True
    ),
    FormField(
        "stay_away_distance", "Stay-away distance (yards)", source="co.stay_away_distance_yards"
    ),
    *_STAY_AWAY_FIELDS,
    FormField(
        "r_children_no_contact",
        "7e — no contact with children + care/control",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_children_parenting_time",
        "7e — care/control + parenting time",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField(
        "parenting_time_terms",
        "Parenting-time / decision-making terms",
        source="co.parenting_time_terms",
    ),
    FormField(
        "r_protect_animals", "7f — protect animals", source="co.relief", needs_legal_review=True
    ),
    FormField(
        "animal_arrangements",
        "Animal possession/care arrangements",
        source="co.animal_arrangements",
    ),
    FormField(
        "r_firearm_relinquish",
        "7g — no firearm + relinquish (DV order)",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_no_interference",
        "7h — no interference at work/school",
        source="co.relief",
        needs_legal_review=True,
    ),
    FormField("r_other", "7i — other relief", source="co.relief", needs_legal_review=True),
    FormField("other_detail", "Other relief detail", source="co.other_relief"),
    # Verification / signature — declared under penalty of perjury at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Declared under penalty of perjury (Colorado) — executed at filing.",
    ),
    FormField(
        "mailing_address",
        "Mailing address (safe address)",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """CO resolver — adds the basis/imminent/relief/stay-away membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto CO JDF 402 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=CO_JDF402_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
