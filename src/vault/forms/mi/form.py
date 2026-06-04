"""Michigan Petition for Personal Protection Order (Domestic Relationship) mapping.

Maps Vault intake answers onto Michigan's **Petition for Personal Protection Order
(Domestic Relationship)** (SCAO Form CC 375, MCL 600.2950 / 600.2950a, MCR 3.703,
Rev. 3/23; Circuit Court). The petition covers the parties, the §1 domestic
relationship basis, the §2 firearm-in-employment note, the §3 other-actions
disclosure, the §4 narrative, the §5 relief checklist (items a-l, with the §5e
stalking sub-acts and §5j animal sub-acts), and the §6 ex parte election. MI's
relationship and relief lists are their own.

The MI intake section (`vault.intake`, the `_mi_step` method) plus the
unconditional employer gate feeds these items. CC 375 has **no respondent
physical-description block and no vehicle block** (only the parties' names /
addresses / ages), so MI is in neither `PHYSICAL_DESCRIPTION_STATES` nor
`VEHICLE_DESCRIPTION_STATES` and the survivor is never asked for them. MI is also
not in `MINOR_FILING_STATES` — a minor petitions through a "next friend" (§7), a
distinct mechanism, not the shared minor-self-filing path.

Protection: CC 375 prints the petitioner's "address ... where the court can reach
petitioner" and is served on the respondent; the form has no dedicated
confidential-address affidavit, so the petitioner address maps to the safe mailing
address, is flagged `needs_legal_review`, and the confidentiality gap is noted
(Michigan handles address confidentiality through separate MCR procedures). The
form requests no support, so MI is not in the SSN-for-support gate.

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

FORM_ID = "CC 375"
FORM_REVISION = "2023-03"  # SCAO Form CC 375, Rev. 3/23
JURISDICTION = "MI"


# §1(B) — petitioner/respondent domestic relationship. Membership over
# `mi.relationship`.
_MI_RELATIONSHIP = {
    "1_married": "married",
    "1_formerly_married": "formerly_married",
    "1_child_in_common": "child_in_common",
    "1_dating": "dating",
    "1_cohabitants": "cohabitants",
}

# §5 — relief requested (prohibit the respondent from …), items a-l. Membership
# over `mi.relief`.
_MI_RELIEF = {
    "5a_no_enter_my_property": "enter_my_property",
    "5b_no_enter_other_property": "enter_other_property",
    "5c_no_assault": "assault",
    "5d_no_remove_children": "remove_children",
    "5e_no_stalking": "stalking",
    "5f_no_interfere_property_removal": "interfere_property_removal",
    "5g_no_threats": "threats",
    "5h_no_interfere_employment": "interfere_employment",
    "5i_no_access_records": "access_records",
    "5j_no_animal_abuse": "animal_abuse",
    "5k_no_firearm": "firearm",
    "5l_other": "other",
}

# §5(e) — stalking conduct sub-boxes. Membership over `mi.stalking_acts`.
_MI_STALKING_ACTS = {
    "5e_following": "following",
    "5e_appearing_workplace": "appearing_workplace",
    "5e_sending_mail": "sending_mail",
    "5e_contacting_phone": "contacting_phone",
    "5e_approaching": "approaching",
    "5e_entering_property": "entering_property",
    "5e_placing_object": "placing_object",
}

# §5(j) — animal-related sub-boxes. Membership over `mi.animal_acts`.
_MI_ANIMAL_ACTS = {
    "5j_injure_animal": "injure",
    "5j_remove_animal": "remove",
    "5j_retain_animal": "retain",
}

_MEMBERSHIP = {
    "mi.relationship": _MI_RELATIONSHIP,
    "mi.relief": _MI_RELIEF,
    "mi.stalking_acts": _MI_STALKING_ACTS,
    "mi.animal_acts": _MI_ANIMAL_ACTS,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="mi.relationship",
        needs_legal_review=True,
    )
    for item, key in _MI_RELATIONSHIP.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="mi.relief", needs_legal_review=True)
    for item, key in _MI_RELIEF.items()
)
_STALKING_FIELDS = tuple(
    FormField(item, f"Stalking act: {key.replace('_', ' ')}", source="mi.stalking_acts")
    for item, key in _MI_STALKING_ACTS.items()
)
_ANIMAL_FIELDS = tuple(
    FormField(item, f"Animal act: {key.replace('_', ' ')}", source="mi.animal_acts")
    for item, key in _MI_ANIMAL_ACTS.items()
)

MI_PPO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (judicial circuit)", source="mi.county", required=True),
    FormField(
        "case_number",
        "Case number / judge",
        source=None,
        note="Assigned by the clerk at filing — MIG1.",
    ),
    # A — parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_age",
        "Petitioner age",
        source=None,
        note="Computed from petitioner.dob at fill time — MIG2.",
    ),
    FormField(
        "petitioner_address",
        "Address/telephone where the court can reach petitioner",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address; CC 375 has no confidential-address affidavit and is served "
        "on the respondent — confidentiality is a separate MCR process. MIG3.",
    ),
    FormField("petitioner_phone", "Petitioner telephone", source="petitioner.safe_phone"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "respondent_age",
        "Respondent age",
        source=None,
        note="Not collected by intake for MI — MIG2.",
    ),
    # 1 — Domestic relationship basis
    *_RELATIONSHIP_FIELDS,
    # 2 — Respondent firearm-in-employment
    FormField(
        "respondent_firearm_employment",
        "Respondent required to carry a firearm for employment (yes / unknown)",
        source="mi.respondent_carries_firearm",
    ),
    # 3 — Other pending actions / orders
    FormField(
        "other_actions",
        "Other pending actions / orders between the parties (§3)",
        source="prior_orders.exists",
        note="Protective-order existence only; the §3 case-number / court / judge tables are "
        "not collected — MIG4.",
    ),
    FormField("other_actions_detail", "Other actions (free text)", source="mi.other_cases_detail"),
    # 4 — Need for the order (narrative)
    FormField(
        "need_narrative",
        "Why a personal protection order is needed (§4)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("incident_date", "Date of the conduct", source="incidents[].date"),
    FormField("incident_location", "Where it happened", source="incidents[].location"),
    # 5 — Relief requested
    *_RELIEF_FIELDS,
    FormField(
        "5b_other_property_address",
        "Property the respondent must not enter (item b)",
        source="mi.other_property_address",
    ),
    FormField(
        "5c_assault_names",
        "Name(s) the respondent must not assault (item c)",
        source="mi.assault_names",
    ),
    FormField(
        "5g_threat_names",
        "Name(s) the respondent must not threaten (item g)",
        source="mi.threat_names",
    ),
    # 5(e) stalking sub-acts
    *_STALKING_FIELDS,
    # 5(j) animal sub-acts
    *_ANIMAL_FIELDS,
    FormField(
        "5l_other_detail", "Other relief requested (item l)", source="mi.relief_other_detail"
    ),
    # 6 — Ex parte election
    FormField(
        "ex_parte",
        "Ex parte order requested (immediate and irreparable injury)",
        source="mi.ex_parte",
        needs_legal_review=True,
    ),
    # 7 — Next friend (minor petitioner)
    FormField(
        "next_friend",
        "Next friend petitioning for a minor (§7)",
        source=None,
        note="Not collected by intake; a minor MI petitioner files through a next friend — MIG5.",
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner / next-friend signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MI resolver — adds the relationship / relief / stalking / animal membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MI Form CC 375 PPO petition (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MI_PPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
