"""Indiana Petition for an Order for Protection form mapping.

Maps Vault intake answers onto Indiana's **Petition for an Order for Protection
and Request for a Hearing** (OJA-PO-0100, I.C. 34-26-5; Rev. by Ind. Office Ct.
Serv. 05/25). The petition covers the caption, the §1 victim basis, the §2
relationship basis (family/household or the stalking / sex-offense / harassment
alternatives), the §3 respondent age, the §4 other cases, the §5 venue, the §6
public mailing address, the §7 acts, the §8 incident narratives, and the §9 relief
checklist (protective items + the after-hearing custody/support items) with the §10
ex parte request. IN's lists are their own.

⚠️ Package name: the two-letter code "IN" is a Python keyword, so the package
directory is `indiana` (not `in`); the jurisdiction code stays "IN". This mirrors
the `oregon` keyword-collision precedent.

The IN intake section (`vault.intake`, the `_in_step` method) plus the shared
employer gate feeds these items. OJA-PO-0100 has **no respondent
physical-description block (only §3 age) and no respondent vehicle block**, so IN
is in neither `PHYSICAL_DESCRIPTION_STATES` nor `VEHICLE_DESCRIPTION_STATES`.

Protection: §6 prints a *public* mailing address ("This address will not be kept
secret"), and the confidential address goes on the separate Confidential Form
(PO-0104) / the AG Address Confidentiality Program. Intake only ever holds a safe
mailing address, so the petitioner address maps to the safe mailing address and is
flagged `needs_legal_review`; `in.confidential_address` is derived `"checked"` to
record that the confidential form is used. The §9 relief includes support, but the
petition has no petitioner SSN field, so IN is not in the SSN-for-support gate.
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

FORM_ID = "OJA-PO-0100"
FORM_REVISION = "2025-05"  # Rev. by Ind. Office Ct. Serv. 05/25
JURISDICTION = "IN"


def _confidential_address(_answers: dict[str, Any]) -> str:
    """§6 — the public address is withheld; the confidential form (PO-0104) is used.

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms PO-0104 / the AG ACP is used.
    """
    return "checked"


# §1 — why the petitioner is filing. Membership over `in.victim_basis`.
_IN_VICTIM = {
    "1a_dv": "dv_family_violence",
    "1b_sex_offense": "sex_offense",
    "1c_stalking": "stalking",
    "1d_harassment": "repeated_harassment",
}

# §2 — relationship to the respondent. Membership over `in.relationship_basis`.
_IN_RELATIONSHIP = {
    "2_spouse": "spouse",
    "2_former_spouse": "former_spouse",
    "2_intimate_cohabitant": "intimate_cohabitant",
    "2_child_in_common": "child_in_common",
    "2_dating": "dating",
    "2_sexual_relationship": "sexual_relationship",
    "2_related_blood_adoption": "related_blood_adoption",
    "2_related_marriage": "related_marriage",
    "2_guardian": "guardian",
    "2_ward": "ward",
    "2_custodian": "custodian",
    "2_foster_parent": "foster_parent",
    "2_minor_child_of_relationship": "minor_child_of_relationship",
    "2_nonfamily_stalking": "nonfamily_stalking",
    "2_nonfamily_sex_offense": "nonfamily_sex_offense",
    "2_nonfamily_harassment": "nonfamily_harassment",
}

# §5 — venue. Membership over `in.venue`.
_IN_VENUE = {
    "5a_respondent_lives": "respondent_lives",
    "5b_incident_here": "incident_here",
    "5c_i_live": "i_live",
}

# §7 — acts committed. Membership over `in.abuse_acts`.
_IN_ABUSE = {
    "7_attempted_harm": "attempted_harm",
    "7_threatened_harm": "threatened_harm",
    "7_caused_harm": "caused_harm",
    "7_fear_harm": "fear_harm",
    "7_forced_sexual": "forced_sexual",
    "7_stalking": "stalking",
    "7_sex_offense": "sex_offense",
    "7_animal_cruelty": "animal_cruelty",
    "7_repeated_harassment": "repeated_harassment",
}

# §9 — protective relief (granted without a hearing). Membership over `in.relief`.
_IN_RELIEF = {
    "9_prohibit_dv": "prohibit_dv",
    "9_prohibit_dv_household": "prohibit_dv_household",
    "9_no_tracking": "no_tracking",
    "9_no_contact": "no_contact",
    "9_stay_away": "stay_away",
    "9_stay_away_family_locations": "stay_away_family_locations",
    "9_evict": "evict",
    "9_possession": "possession",
    "9_no_animal_harm": "no_animal_harm",
    "9_exclusive_animal_care": "exclusive_animal_care",
    "9_additional_safety": "additional_safety",
    "9_no_firearm": "no_firearm",
    "9_surrender_firearm": "surrender_firearm",
    "9_wireless_transfer": "wireless_transfer",
}

# §9 — relief granted only after notice and a hearing. Membership over
# `in.hearing_relief`.
_IN_HEARING_RELIEF = {
    "9h_parenting_time": "parenting_time",
    "9h_supervised_parenting": "supervised_parenting",
    "9h_deny_parenting": "deny_parenting",
    "9h_attorney_fees": "attorney_fees",
    "9h_rent": "rent",
    "9h_mortgage": "mortgage",
    "9h_child_support": "child_support",
    "9h_maintenance": "maintenance",
    "9h_reimburse_expenses": "reimburse_expenses",
}

_MEMBERSHIP = {
    "in.victim_basis": _IN_VICTIM,
    "in.relationship_basis": _IN_RELATIONSHIP,
    "in.venue": _IN_VENUE,
    "in.abuse_acts": _IN_ABUSE,
    "in.relief": _IN_RELIEF,
    "in.hearing_relief": _IN_HEARING_RELIEF,
}

_VICTIM_FIELDS = tuple(
    FormField(
        item,
        f"Victim basis: {key.replace('_', ' ')}",
        source="in.victim_basis",
        needs_legal_review=True,
    )
    for item, key in _IN_VICTIM.items()
)
_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="in.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _IN_RELATIONSHIP.items()
)
_VENUE_FIELDS = tuple(
    FormField(item, f"Venue: {key.replace('_', ' ')}", source="in.venue", needs_legal_review=True)
    for item, key in _IN_VENUE.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Act: {key.replace('_', ' ')}", source="in.abuse_acts", needs_legal_review=True
    )
    for item, key in _IN_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="in.relief", needs_legal_review=True)
    for item, key in _IN_RELIEF.items()
)
_HEARING_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Hearing relief: {key.replace('_', ' ')}",
        source="in.hearing_relief",
        needs_legal_review=True,
    )
    for item, key in _IN_HEARING_RELIEF.items()
)

IN_PO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court", "Court (county / division / room)", source="in.court"),
    FormField("county", "County", source="in.county", required=True),
    FormField(
        "case_number",
        "Case number",
        source=None,
        note="Assigned by the clerk at filing — ING1.",
    ),
    # Parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "confidential_address",
        "Confidential address used (§6 public address withheld; PO-0104 / AG ACP)",
        derive=_confidential_address,
        needs_legal_review=True,
        note="§6 prints a public mailing address; the confidential address goes on PO-0104.",
    ),
    FormField(
        "petitioner_address",
        "Petitioner public mailing address (§6)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; §6 warns this address is public, so it must be one "
        "the petitioner is comfortable disclosing.",
    ),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_age", "Respondent age (§3)", source="respondent.age"),
    FormField("respondent_employer", "Respondent employer", source="respondent.employer_name"),
    FormField(
        "respondent_employer_address",
        "Respondent work address",
        source="respondent.employer_address",
    ),
    # §1 — Victim basis
    *_VICTIM_FIELDS,
    # §2 — Relationship
    *_RELATIONSHIP_FIELDS,
    # §4 — Other cases
    FormField(
        "other_cases",
        "Other cases involving the parties (§4)",
        source="prior_orders.exists",
        note="Existence only; the §4 case-name / number / county-state table is not "
        "collected — ING2.",
    ),
    # §5 — Venue
    *_VENUE_FIELDS,
    # §7 — Acts
    *_ABUSE_FIELDS,
    # §8 — Narrative
    FormField(
        "incident_narrative",
        "What happened in each incident (§8)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("incident_date", "Date of the incident", source="incidents[].date"),
    FormField("incident_location", "Place of the incident", source="incidents[].location"),
    FormField("incident_witnesses", "People present", source="incidents[].witnesses_present"),
    # §9 — Protective relief
    *_RELIEF_FIELDS,
    FormField(
        "9_stay_away_location", "Place to stay away from (§9)", source="in.stay_away_location"
    ),
    FormField(
        "9_evict_address", "Residence the respondent must leave (§9)", source="in.evict_address"
    ),
    FormField(
        "9_possession_detail",
        "Residence / vehicle / items for possession (§9)",
        source="in.possession_detail",
    ),
    FormField(
        "9_firearm_detail", "Firearms / weapons to surrender (§9)", source="in.firearm_detail"
    ),
    FormField(
        "9_wireless_detail", "Wireless number(s) to transfer (§9)", source="in.wireless_detail"
    ),
    # §9 — After-hearing relief
    *_HEARING_RELIEF_FIELDS,
    FormField(
        "9h_support_detail",
        "Support / expense detail (§9 hearing relief)",
        source="in.support_detail",
    ),
    # §10 — Ex parte
    FormField(
        "ex_parte",
        "Ex parte order requested (§10 — by filing)",
        derive=_confidential_address,  # always requested by filing the petition
        needs_legal_review=True,
        note="The petition requests an immediate ex parte order by filing; a hearing within "
        "30 days is required for certain relief.",
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Affirmed under the penalties for perjury at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """IN resolver — adds the §1/§2/§5/§7/§9 membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto IN OJA-PO-0100 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=IN_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
