"""Missouri Petition for a Court Order of Protection (Adult) form mapping.

Maps Vault intake answers onto Missouri's **Petition for a Court Order of
Protection - Adult** (SJRC form AA40, RSMo 455.010 et seq., 09-25; Circuit Court).
The petition covers the county/venue, the §A party + respondent identifiers (a
full physical description + a vehicle question), the §B acts and ex-parte basis,
the §B narrative, and the §C relief (the "NOT to" list, the serious-danger
two-to-ten-year finding, custody, support, property, counseling, and other
requests). MO's lists are their own.

The MO intake section (`vault.intake`, the `_mo_step` method) plus the shared
physical-description, vehicle, and minor-filing gates feeds these items. The §A
block HAS a respondent physical description (race / sex / height / weight / hair /
eyes / marks), so MO is in `PHYSICAL_DESCRIPTION_STATES`; and §B asks the
respondent's vehicle (make / model / year / color / plate), so MO is in
`VEHICLE_DESCRIPTION_STATES`. `_mo_step` adds the respondent age / sex / race the §A
block also needs.

Protection: the form states up front "The person you need protection from will get
a copy of this form", and §C(7) offers "Order my residential address on my voter's
registration record to be closed to the public" — Missouri's address protection is
a separate Address Confidentiality Program / redacted-filing-sheet, so the
petitioner address maps to the safe mailing address and is flagged
`needs_legal_review`. The form requests support (§C(4)) but has no petitioner SSN
field, so MO is not in the SSN-for-support gate. See coverage.md.

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

FORM_ID = "AA40"
FORM_REVISION = "2025-09"  # SJRC (09-25)
JURISDICTION = "MO"


# Top — county where filed. Membership over `mo.venue`.
_MO_VENUE = {
    "venue_i_live": "i_live",
    "venue_abuse_happened": "abuse_happened",
    "venue_respondent_served": "respondent_served",
}

# §A — relationship to the respondent. Membership over `mo.relationship_basis`.
_MO_RELATIONSHIP = {
    "a_spouse": "spouse",
    "a_former_spouse": "former_spouse",
    "a_child_in_common": "child_in_common",
    "a_continuing_social_romantic": "continuing_social_romantic",
    "a_resided_with_intimacy": "resided_with_intimacy",
    "a_resided_no_intimacy": "resided_no_intimacy",
    "a_related_blood": "related_blood",
    "a_related_marriage": "related_marriage",
    "a_stalking": "stalking",
    "a_sexual_assault": "sexual_assault",
}

# §B — acts. Membership over `mo.abuse_acts`.
_MO_ABUSE = {
    "b_caused_harm": "caused_harm",
    "b_fear_harm": "fear_harm",
    "b_coerced": "coerced",
    "b_stalked": "stalked",
    "b_harassed": "harassed",
    "b_sexually_assaulted": "sexually_assaulted",
    "b_unlawfully_imprisoned": "unlawfully_imprisoned",
    "b_followed": "followed",
    "b_abused_pet": "abused_pet",
    "b_threatened": "threatened",
}

# §B — ex parte (emergency temporary) basis. Membership over `mo.ex_parte_basis`.
_MO_EX_PARTE = {
    "b_afraid": "afraid",
    "b_immediate_danger": "immediate_danger",
    "b_other_reasons": "other_reasons",
    "b_has_evidence": "has_evidence",
}

# §C(1) — order respondent NOT to. Membership over `mo.relief`.
_MO_RELIEF = {
    "c1_no_dv": "no_dv",
    "c1_no_pet_abuse": "no_pet_abuse",
    "c1_no_enter_home": "no_enter_home",
    "c1_no_enter_school": "no_enter_school",
    "c1_no_enter_work": "no_enter_work",
    "c1_stay_distance": "stay_distance",
    "c1_no_communicate": "no_communicate",
    "c1_other": "other",
}

# §C(3-7) — additional relief. Membership over `mo.additional_relief`.
_MO_ADDITIONAL = {
    "c3_custody": "custody",
    "c4_child_support": "child_support",
    "c4_maintenance": "maintenance",
    "c4_rent_mortgage": "rent_mortgage",
    "c4_shelter_costs": "shelter_costs",
    "c4_medical_costs": "medical_costs",
    "c4_court_costs": "court_costs",
    "c4_attorney_fees": "attorney_fees",
    "c5_possession_property": "possession_property",
    "c5_prohibit_transfer": "prohibit_transfer",
    "c6_counseling": "counseling",
    "c6_substance_abuse": "substance_abuse",
    "c7_auto_renew": "auto_renew",
    "c7_wireless_transfer": "wireless_transfer",
    "c7_pet_possession": "pet_possession",
    "c7_voter_address": "voter_address",
    "c7_other": "other",
}

_MEMBERSHIP = {
    "mo.venue": _MO_VENUE,
    "mo.relationship_basis": _MO_RELATIONSHIP,
    "mo.abuse_acts": _MO_ABUSE,
    "mo.ex_parte_basis": _MO_EX_PARTE,
    "mo.relief": _MO_RELIEF,
    "mo.additional_relief": _MO_ADDITIONAL,
}

_VENUE_FIELDS = tuple(
    FormField(item, f"Venue: {key.replace('_', ' ')}", source="mo.venue", needs_legal_review=True)
    for item, key in _MO_VENUE.items()
)
_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="mo.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _MO_RELATIONSHIP.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Act: {key.replace('_', ' ')}", source="mo.abuse_acts", needs_legal_review=True
    )
    for item, key in _MO_ABUSE.items()
)
_EX_PARTE_FIELDS = tuple(
    FormField(
        item,
        f"Ex parte basis: {key.replace('_', ' ')}",
        source="mo.ex_parte_basis",
        needs_legal_review=True,
    )
    for item, key in _MO_EX_PARTE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="mo.relief", needs_legal_review=True)
    for item, key in _MO_RELIEF.items()
)
_ADDITIONAL_FIELDS = tuple(
    FormField(
        item,
        f"Additional relief: {key.replace('_', ' ')}",
        source="mo.additional_relief",
        needs_legal_review=True,
    )
    for item, key in _MO_ADDITIONAL.items()
)

MO_PO_FIELDS: tuple[FormField, ...] = (
    # Caption / venue
    FormField("county", "County (circuit court)", source="mo.county", required=True),
    FormField(
        "case_number",
        "Case number",
        source=None,
        note="Assigned by the court when filed — MOG1.",
    ),
    *_VENUE_FIELDS,
    # §A — Petitioner + respondent identifiers
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_address",
        "Petitioner address",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="The respondent gets a copy of this form; address protection is the separate ACP "
        "/ redacted-filing-sheet (and §C(7) voter-record closure). Safe mailing address only.",
    ),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Respondent home address", source="respondent.last_known_address"
    ),
    FormField("respondent_age", "Respondent age (§A)", source="respondent.age"),
    FormField("respondent_sex", "Respondent sex", source="respondent.gender"),
    FormField("respondent_race", "Respondent race / ethnicity", source="respondent.race"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField(
        "respondent_marks", "Respondent identifying marks", source="respondent.distinguishing_marks"
    ),
    FormField("respondent_employer", "Respondent work name", source="respondent.employer_name"),
    FormField(
        "respondent_employer_address",
        "Respondent work address",
        source="respondent.employer_address",
    ),
    FormField(
        "respondent_vehicle",
        "Respondent vehicle (make/model/year/color/plate)",
        source="respondent.vehicle_make_model",
    ),
    FormField(
        "respondent_vehicle_color", "Respondent vehicle color", source="respondent.vehicle_color"
    ),
    FormField(
        "respondent_vehicle_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"
    ),
    FormField(
        "respondent_firearm",
        "Respondent carries a weapon / firearm",
        source="firearm.respondent_has_access",
    ),
    # §A — Relationship
    *_RELATIONSHIP_FIELDS,
    # §B — Acts + ex parte basis
    *_ABUSE_FIELDS,
    *_EX_PARTE_FIELDS,
    # §B — Narrative
    FormField(
        "abuse_narrative",
        "This is what happened (§B specific details)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date(s) of the acts", source="incidents[].date"),
    FormField("abuse_location", "Location(s) of the acts", source="incidents[].location"),
    # §C(1) — Relief
    *_RELIEF_FIELDS,
    FormField(
        "c1_school_address", "School address (item: no enter school)", source="mo.school_address"
    ),
    FormField("c1_work_address", "Work address (item: no enter work)", source="mo.work_address"),
    FormField(
        "c1_stay_distance_feet",
        "Stay-away distance in feet (item: come within)",
        source="mo.stay_distance_feet",
    ),
    # §C(2) — Serious danger
    FormField(
        "c2_serious_danger",
        "Serious-danger 2-to-10-year order requested (§C2)",
        source="mo.serious_danger",
        needs_legal_review=True,
    ),
    # §C(3-7) — Additional relief
    *_ADDITIONAL_FIELDS,
    FormField("c3_custody_detail", "Custody / visitation detail (§C3)", source="mo.custody_detail"),
    FormField(
        "c4_support_detail",
        "Support / cost amounts (§C4)",
        source="mo.support_detail",
        note="§C4 amounts; the petitioner SSN is NOT on this form, so MO is not in the SSN "
        "gate — MOG2.",
    ),
    FormField("c5_property_detail", "Personal property items (§C5)", source="mo.property_detail"),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn under penalty of perjury at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MO resolver — adds the venue / §A / §B / §C membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MO AA40 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MO_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
