"""South Carolina Petition for Family Court Order of Protection form mapping.

Maps Vault intake answers onto South Carolina's **Petition for Family Court Order
of Protection** (SCCA 425, Protection from Domestic Abuse Act, Revised 11/2025;
Family Court). The petition covers the caption, the §1 venue, the §2-§5 respondent
information, the §6 protected persons, the §7 relationship basis, the §8 incident
narrative, and the §9 relief checklist (items a-q). SC's relationship and relief
lists are their own.

The SC intake section (`vault.intake`, the `_sc_step` method) plus the shared
minor-filing gate feeds these items. SCCA 425 §4 carries only the respondent's
DOB / race / sex — **not** a height/weight/eyes/hair block — so SC is carved out of
`PHYSICAL_DESCRIPTION_STATES` (see the intake comment); `_sc_step` asks the
respondent dob/race/sex the form does need. The form has no respondent vehicle
block, so SC is carved out of `VEHICLE_DESCRIPTION_STATES`. A child under 18 may be
a protected person (§6b), so SC stays in `MINOR_FILING_STATES`.

Protection: the petition prints the respondent's address, not the petitioner's
residence; South Carolina's address protection runs through the Family Court /
Address Confidentiality Program. The §3 Social Security Number is the
*respondent's*, not the petitioner's. The §9 relief includes child / financial
support (which require a separate Financial Declaration, SCCA 430), but the
petition has no petitioner SSN field, so SC is not in the SSN-for-support gate.
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

FORM_ID = "SCCA 425"
FORM_REVISION = "2025-11"  # Revised 11/2025
JURISDICTION = "SC"


# §1 — where the case is filed. Membership over `sc.venue`.
_SC_VENUE = {
    "1a_abuse_occurred": "abuse_occurred",
    "1b_respondent_lives": "respondent_lives",
    "1c_last_lived_here": "last_lived_here",
    "1d_transfer_request": "transfer_request",
}

# §7 — relationship to the person who caused the abuse. Membership over
# `sc.relationship_basis`.
_SC_RELATIONSHIP = {
    "7a_married": "married",
    "7b_previously_married": "previously_married",
    "7c_child_in_common": "child_in_common",
    "7d_live_together_romantic": "live_together_romantic",
    "7e_formerly_lived_romantic": "formerly_lived_romantic",
    "7f_family_sexual_abuse": "family_sexual_abuse",
}

# §9 — relief requested (items a-q). Membership over `sc.relief`.
_SC_RELIEF = {
    "9a_no_abuse": "no_abuse",
    "9b_stop_offensive": "stop_offensive",
    "9c_no_communicate": "no_communicate",
    "9d_stay_away": "stay_away",
    "9e_custody": "custody",
    "9f_child_support": "child_support",
    "9g_financial_support": "financial_support",
    "9h_exclusive_home": "exclusive_home",
    "9i_insurance": "insurance",
    "9j_no_property_disposal": "no_property_disposal",
    "9k_no_pet_harm": "no_pet_harm",
    "9l_possession_property": "possession_property",
    "9m_le_assist": "le_assist",
    "9n_reimburse_fees": "reimburse_fees",
    "9o_hearing_15_days": "hearing_15_days",
    "9p_emergency_hearing_24h": "emergency_hearing_24h",
    "9q_other": "other",
}

_MEMBERSHIP = {
    "sc.venue": _SC_VENUE,
    "sc.relationship_basis": _SC_RELATIONSHIP,
    "sc.relief": _SC_RELIEF,
}

_VENUE_FIELDS = tuple(
    FormField(item, f"Venue: {key.replace('_', ' ')}", source="sc.venue", needs_legal_review=True)
    for item, key in _SC_VENUE.items()
)
_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="sc.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _SC_RELATIONSHIP.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="sc.relief", needs_legal_review=True)
    for item, key in _SC_RELIEF.items()
)

SC_PO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "county", "County (family court, judicial circuit)", source="sc.county", required=True
    ),
    FormField(
        "docket_number",
        "Docket number",
        source=None,
        note="Assigned by the clerk at filing — SCG1.",
    ),
    # §1 — Venue
    *_VENUE_FIELDS,
    # §2-§5 — Respondent
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Respondent address (§2)", source="respondent.last_known_address"
    ),
    FormField(
        "respondent_ssn",
        "Respondent Social Security Number (§3)",
        source=None,
        note="The §3 SSN is the respondent's; not collected by intake — SCG2.",
    ),
    FormField("respondent_dob", "Respondent date of birth (§4)", source="respondent.dob"),
    FormField("respondent_race", "Respondent race (§4)", source="respondent.race"),
    FormField("respondent_sex", "Respondent sex (§4)", source="respondent.gender"),
    FormField(
        "respondent_prior_dv",
        "Prior DV convictions / orders against respondent (§5)",
        source="prior_orders.exists",
        note="Existence proxy; the form wants the date(s) — partial, SCG3.",
    ),
    FormField(
        "respondent_employer", "Respondent employer (service)", source="respondent.employer_name"
    ),
    FormField(
        "respondent_employer_address",
        "Respondent work address (service)",
        source="respondent.employer_address",
    ),
    # §6 — Protected persons
    FormField(
        "petitioner",
        "Petitioner (abused person) name (§6a)",
        source="petitioner.legal_name",
        required=True,
    ),
    FormField(
        "protected_child",
        "Child under 18 who lives with petitioner (§6b)",
        source="protected_persons.children[]",
        note="Names; the form lists protected children — partial, SCG4.",
    ),
    # §7 — Relationship
    *_RELATIONSHIP_FIELDS,
    # §8 — Narrative
    FormField(
        "abuse_narrative",
        "What happened (§8)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the abuse (§8)", source="incidents[].date"),
    FormField("abuse_location", "Where the abuse happened (§8)", source="incidents[].location"),
    # §9 — Relief
    *_RELIEF_FIELDS,
    FormField(
        "9d_stay_away_location", "Place to stay away from (item d)", source="sc.stay_away_location"
    ),
    FormField(
        "9e_custody_detail", "Custody / visitation detail (item e)", source="sc.custody_detail"
    ),
    FormField("9h_home_address", "Home for exclusive use (item h)", source="sc.home_address"),
    FormField(
        "9l_property_detail",
        "Personal property / pets / law-enforcement-assist detail",
        source="sc.property_detail",
    ),
    FormField(
        "9q_other_detail", "Other relief requested (item q)", source="sc.relief_other_detail"
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn and subscribed before a notary at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """SC resolver — adds the §1 venue / §7 relationship / §9 relief membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto SC SCCA 425 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=SC_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
