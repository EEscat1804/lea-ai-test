"""Oklahoma Petition for Protective Order form mapping.

Maps Vault intake answers onto Oklahoma's **AOC Petition for Protective Order**
(Protection from Domestic Abuse Act, 22 O.S. § 60.1; District Court; AOC form
effective Nov 1, 2023). The petition covers the county, the parties, a "Defendant
Identifiers" description block, the §1 relationship basis, the §2 jurisdiction
statement, the §3 actions of the defendant, the §4 incident narrative, and the §6
relief checklist (items 1-15) with the emergency ex parte election. OK's actions
and relief lists are their own.

The OK intake section (`vault.intake`, the `_ok_step` method) plus the shared
physical-description and minor-filing gates feeds these items. OK is intentionally
NOT in `VEHICLE_DESCRIPTION_STATES` — the AOC petition has no vehicle field, even
though the source doc lists OK among the vehicle states (see the intake comment).

Protection: the petition does not print the petitioner's residential address (only
the defendant's), so there is no petitioner-address field to withhold. The
respondent's Social Security number is not asked by the form and not collected.
The police-report requirement for non-family / non-dating petitioners (Appendix 1)
is left to the attorney/advocate — see coverage.md.

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

FORM_ID = "Petition for Protective Order"  # AOC form, 22 O.S. 60.1 — no printed number, OKG1
FORM_REVISION = "2023-11"  # effective November 1, 2023
JURISDICTION = "OK"


# §2 — statement of jurisdiction. Membership over `ok.jurisdiction_basis`.
_OK_JURISDICTION = {
    "2_petitioner_resident": "petitioner_resident",
    "2_defendant_resident": "defendant_resident",
    "2_abuse_in_county": "abuse_in_county",
}

# §3 — actions of the defendant. Membership over `ok.actions`.
_OK_ACTIONS = {
    "3_physical_harm": "physical_harm",
    "3_threatened_harm": "threatened_harm",
    "3_harassed": "harassed",
    "3_stalked": "stalked",
    "3_crime": "crime",
    "3_adult_crime": "adult_crime",
}

# §6 — relief requested (items 1-15). Membership over `ok.relief`.
_OK_RELIEF = {
    "6_1_no_contact": "no_contact",
    "6_2_no_abuse": "no_abuse",
    "6_3_no_fear_conduct": "no_fear_conduct",
    "6_4_move_out": "move_out",
    "6_5_le_remove_defendant": "le_remove_defendant",
    "6_6_civil_standby": "civil_standby",
    "6_7_minor_defendant_leave": "minor_defendant_leave",
    "6_8_suspend_visitation": "suspend_visitation",
    "6_9_counseling": "counseling",
    "6_10_protect_animals": "protect_animals",
    "6_11_gps_monitoring": "gps_monitoring",
    "6_12_transfer_utilities": "transfer_utilities",
    "6_13_surrender_firearms": "surrender_firearms",
    "6_14_pay_court_costs": "pay_court_costs",
    "6_15_attorney_fees": "attorney_fees",
}

_MEMBERSHIP = {
    "ok.jurisdiction_basis": _OK_JURISDICTION,
    "ok.actions": _OK_ACTIONS,
    "ok.relief": _OK_RELIEF,
}

_JURISDICTION_FIELDS = tuple(
    FormField(
        item,
        f"Jurisdiction: {key.replace('_', ' ')}",
        source="ok.jurisdiction_basis",
        needs_legal_review=True,
    )
    for item, key in _OK_JURISDICTION.items()
)
_ACTIONS_FIELDS = tuple(
    FormField(
        item,
        f"Action: {key.replace('_', ' ')}",
        source="ok.actions",
        needs_legal_review=True,
    )
    for item, key in _OK_ACTIONS.items()
)
_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Relief: {key.replace('_', ' ')}",
        source="ok.relief",
        needs_legal_review=True,
    )
    for item, key in _OK_RELIEF.items()
)

OK_PO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (District Court of … County)", source="ok.county", required=True),
    FormField(
        "case_number",
        "Case number (PO-20__) / court phone",
        source=None,
        note="Assigned / filled by the clerk at filing — OKG2.",
    ),
    # Petitioner
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "minor_family_members",
        "Minor family member(s) — names and ages",
        source="protected_persons.children[]",
        note="Names only; form wants name + age per minor — OKG3.",
    ),
    # Defendant + identifiers
    FormField("respondent", "Defendant name", source="respondent.legal_name", required=True),
    FormField(
        "relationship_to_petitioner",
        "Relationship to petitioner (caption)",
        source="relationship.type",
        needs_legal_review=True,
    ),
    FormField("respondent_address", "Defendant address", source="respondent.last_known_address"),
    FormField("respondent_sex", "Defendant sex", source="respondent.gender"),
    FormField("respondent_race", "Defendant race", source="respondent.race"),
    FormField("respondent_dob", "Defendant date of birth", source="respondent.dob"),
    FormField("respondent_height", "Defendant height", source="respondent.height"),
    FormField("respondent_weight", "Defendant weight", source="respondent.weight"),
    FormField("respondent_eyes", "Defendant eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Defendant hair color", source="respondent.hair_color"),
    FormField(
        "respondent_features",
        "Defendant distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_dl",
        "Defendant driver's license (#, state, expires)",
        source=None,
        note="Not collected by intake — OKG4.",
    ),
    # 1 — Relationship / victim characterization
    FormField(
        "relationship_basis",
        "Defendant's relationship to petitioner (§1A intimate partner / family-household)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto OK's §1A categories. The §1B/§1C/§1D "
        "victim-and-crime characterization is attorney-confirmed — OKG5.",
    ),
    FormField(
        "victim_characterization",
        "Petitioner victim type / acts committed (§1B / §1C / §1D)",
        source=None,
        note="Section B/C/D selection (victim of DV / stalking / crime, or first-degree "
        "murder) is attorney-confirmed from the actions and relationship — OKG5.",
    ),
    # 2 — Statement of jurisdiction
    *_JURISDICTION_FIELDS,
    # 3 — Actions of the defendant
    *_ACTIONS_FIELDS,
    FormField(
        "actions_names",
        "Name(s) per action (§3 blanks)",
        source=None,
        note="The per-action name blanks are not separately captured; the protected parties "
        "are the petitioner and any listed minors — OKG6.",
    ),
    # 4 — Description of incident(s)
    FormField("incident_date", "Incident date(s) (§4)", source="incidents[].date"),
    FormField(
        "incident_description",
        "Describe what happened (§4)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    FormField("incident_location", "Where it happened (§4)", source="incidents[].location"),
    # 5 — Other cases
    FormField(
        "other_cases",
        "Other cases involving the parties (§5)",
        source="prior_orders.exists",
        note="Existence only; form wants case name / number / county-state — OKG7.",
    ),
    # 6 — Type of order + relief
    FormField(
        "ex_parte",
        "Emergency ex parte order requested (§6 — B vs A)",
        source="ok.ex_parte",
        needs_legal_review=True,
    ),
    *_RELIEF_FIELDS,
    FormField(
        "6_4_move_out_address",
        "Residence the defendant must leave (item 4)",
        source="ok.move_out_address",
    ),
    FormField(
        "6_6_civil_standby_address",
        "Civil-standby residence address (item 6)",
        source="ok.civil_standby_address",
    ),
    FormField(
        "6_12_transfer_detail",
        "Utilities / wireless numbers to transfer (item 12)",
        source="ok.transfer_detail",
    ),
    FormField(
        "6_15_attorney_fees_amount",
        "Attorney's fees amount (item 15)",
        source="ok.attorney_fees_amount",
    ),
    FormField("6_additional_relief", "Additional relief requested", source="ok.additional_relief"),
    # Firearms context (item 13)
    FormField(
        "respondent_has_firearms",
        "Defendant has / can access firearms",
        source="firearm.respondent_has_access",
    ),
    FormField("firearm_types", "Firearm types", source="firearm.types[]"),
    FormField("firearm_locations", "Firearm locations", source="firearm.locations[]"),
    # 8 — Sworn statement
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
    FormField(
        "notary",
        "Subscribed and sworn before clerk / judge / notary",
        source=None,
        note="Completed before the clerk/notary at filing — OKG8.",
    ),
    FormField(
        "le_agencies",
        "Law enforcement agencies to receive a copy",
        source=None,
        note="Not collected by intake — OKG8.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """OK resolver — adds the jurisdiction/actions/relief membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto OK Petition for Protective Order (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=OK_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
