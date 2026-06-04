"""South Dakota Petition and Affidavit for a Protection Order form mapping.

Maps Vault intake answers onto South Dakota **Form UJS-091A (adult) / UJS-091AJ
(juvenile), _Petition and Affidavit for a Protection Order (Domestic Abuse)_**
(SDCL ch. 25-10; Rev. 07/21). The petition covers the parties and South Dakota
residency basis, the relationship categories, an acts-of-domestic-abuse
checklist, prior-PO and weapon history (yes/no/don't-know), the abuse narrative,
and the items 1-11 relief list plus the ex parte (immediate Temporary Protection
Order) request. SD's relief and abuse lists are its own.

The SD intake section (`vault.intake`, the `_sd_step` method) plus the shared
minor-filing gate feeds these items. SD is intentionally NOT in the
physical-description or vehicle sets — the form describes neither.

Protection: the petitioner's home address is never collected; intake holds only a
safe mailing address, and the confidential-address note is asserted. The form
takes proof of income at the hearing (not on the petition) and asks for no SSN.
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

FORM_ID = "UJS-091A"
FORM_REVISION = "2021-07"  # Rev. 07/21
JURISDICTION = "SD"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Petitioner's address is withheld — intake holds only a safe mailing address."""
    return "checked"


# Acts of domestic abuse checklist. Membership over `sd.abuse_acts`.
_SD_ABUSE = {
    "ab_caused_harm": "caused_harm",
    "ab_attempted_harm": "attempted_harm",
    "ab_inflicted_fear": "inflicted_fear",
    "ab_violated_po": "violated_po",
    "ab_followed": "followed",
    "ab_harassing_conduct": "harassing_conduct",
    "ab_credible_threat": "credible_threat",
    "ab_harassing_communication": "harassing_communication",
    "ab_crime_of_violence": "crime_of_violence",
}

# Items 1-11 relief list. Membership over `sd.relief`.
_SD_RELIEF = {
    "1_restrain_abuse": "restrain_abuse",
    "2_set_duration": "set_duration",
    "3_exclude_residence": "exclude_residence",
    "4_stay_away": "stay_away",
    "5_custody": "custody",
    "6_visitation": "visitation",
    "7_support": "support",
    "8_parenting_classes": "parenting_classes",
    "9_counseling": "counseling",
    "10_no_contact": "no_contact",
    "11_other": "other",
}

# Item 4 stay-away targets. Membership over `sd.stay_away_targets`.
_SD_STAY_AWAY = {
    "4a_petitioner": "petitioner",
    "4b_children": "children",
    "4c_residence": "residence",
    "4d_employment": "employment",
    "4e_other": "other",
}

# Item 7 support sub-checklist. Membership over `sd.support_types`.
_SD_SUPPORT = {
    "7_child_support": "child_support",
    "7_spousal_support": "spousal_support",
}

_MEMBERSHIP = {
    "sd.abuse_acts": _SD_ABUSE,
    "sd.relief": _SD_RELIEF,
    "sd.stay_away_targets": _SD_STAY_AWAY,
    "sd.support_types": _SD_SUPPORT,
}

_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="sd.abuse_acts", needs_legal_review=True
    )
    for item, key in _SD_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="sd.relief", needs_legal_review=True)
    for item, key in _SD_RELIEF.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(
        item,
        f"Stay away: {key.replace('_', ' ')}",
        source="sd.stay_away_targets",
        needs_legal_review=True,
    )
    for item, key in _SD_STAY_AWAY.items()
)
_SUPPORT_FIELDS = tuple(
    FormField(
        item,
        f"Support: {key.replace('_', ' ')}",
        source="sd.support_types",
        needs_legal_review=True,
    )
    for item, key in _SD_SUPPORT.items()
)

SD_UJS091A_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Circuit Court)", source="sd.county", required=True),
    FormField(
        "judicial_circuit",
        "Judicial circuit",
        source=None,
        note="Determined by county at filing; intake collects county only — SDG1.",
    ),
    # Petitioner
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "address_confidential",
        "Petitioner address withheld (safe mailing only)",
        derive=_address_confidential,
    ),
    FormField(
        "petitioner_mailing_address",
        "Petitioner safe mailing address",
        source="petitioner.safe_mailing_address",
    ),
    FormField(
        "minor_filing",
        "Petitioner under 18 / filed by parent-guardian (the Filer)",
        source="petitioner.minor_filing_path",
        needs_legal_review=True,
        note="Whether an adult Filer files for an under-18 petitioner (UJS-091AJ) — confirm.",
    ),
    # Residency basis (at least one party is an SD resident)
    FormField(
        "petitioner_county",
        "Petitioner county of residence",
        source="sd.county",
        note="Mapped from the filing county; confirm petitioner residence county.",
    ),
    FormField(
        "respondent_residence",
        "Respondent county/state of residence",
        source="respondent.last_known_address",
        note="From the respondent's last-known address; form wants county + state — SDG2.",
    ),
    FormField(
        "protected_parties_residence",
        "Protected parties' county/state of residence",
        source=None,
        note="Not collected by intake — SDG2.",
    ),
    # Respondent
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    # Existing custody order
    FormField(
        "existing_custody_order",
        "Existing custody order (SD or other state)",
        source="sd.existing_custody_order",
    ),
    FormField(
        "custody_order_details",
        "Existing custody order county/case #",
        source="sd.custody_order_details",
    ),
    # Relationship categories
    FormField(
        "relationship_basis",
        "Relationship of respondent to petitioner (check all that apply)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto SD's categories (spouse/former spouse, "
        "significant romantic relationship, child in common, parent/child, sibling). "
        "Attorney confirms the boxes.",
    ),
    # Facts — date + acts of domestic abuse
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    FormField(
        "abuse_time",
        "Approximate time of the abuse",
        source=None,
        note="Intake collects the date, not the clock time — SDG3.",
    ),
    *_ABUSE_FIELDS,
    FormField(
        "abuse_narrative",
        "Detailed description of what happened",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    # Yes/No/Don't-Know history
    FormField("q_le_called", "Was law enforcement called?", source="incidents[].police_called"),
    FormField("q_arrested", "Was respondent arrested?", source="sd.respondent_arrested"),
    FormField("q_in_jail", "Is respondent in jail?", source="sd.respondent_in_jail"),
    FormField(
        "q_violated_po",
        "Has respondent violated previous protection orders?",
        source="sd.respondent_violated_po",
        needs_legal_review=True,
    ),
    FormField("q_violated_po_whom", "Violated PO — against whom", source="sd.violated_po_whom"),
    FormField(
        "q_convicted_po",
        "Has respondent been found guilty of violating PO?",
        source="sd.respondent_convicted_po",
        needs_legal_review=True,
    ),
    FormField(
        "q_convicted_po_details",
        "PO conviction — whom / date / county-state",
        source="sd.convicted_po_details",
    ),
    FormField(
        "q_possesses_weapons",
        "Does respondent possess guns or weapons?",
        source="firearm.respondent_has_access",
    ),
    FormField(
        "q_weapon_used", "Was a weapon used in this incident?", source="incidents[].weapon_involved"
    ),
    FormField(
        "q_threatened_weapon",
        "Has respondent threatened anyone with a weapon?",
        source="sd.respondent_threatened_weapon",
        needs_legal_review=True,
    ),
    FormField(
        "other_incidents",
        "Other similar incidents / why it will continue",
        source="incidents[].pattern_frequency",
        note="Mapped from the incident pattern/frequency — partial (SDG3).",
    ),
    # Items 1-11 relief + sub-detail
    *_RELIEF_FIELDS,
    FormField("2_duration", "Order duration (up to 5 years)", source="sd.duration"),
    FormField(
        "3_4c_residence_address",
        "Residence to exclude respondent from",
        source="sd.residence_address",
    ),
    FormField("4_stay_away_distance", "Stay-away distance", source="sd.stay_away_distance"),
    *_STAY_AWAY_FIELDS,
    FormField("4e_stay_away_other", "Stay-away other place", source="sd.stay_away_other"),
    FormField(
        "5_custody_children",
        "Children for temporary custody",
        source="protected_persons.children[]",
        note="Names only; form wants name + DOB + relationship per child — SDG4.",
    ),
    FormField("6_visitation_detail", "Temporary visitation detail", source="sd.visitation_detail"),
    *_SUPPORT_FIELDS,
    FormField(
        "7_child_support_amount", "Child support monthly amount", source="sd.child_support_amount"
    ),
    FormField(
        "7_spousal_support_amount",
        "Spousal support monthly amount",
        source="sd.spousal_support_amount",
    ),
    FormField("9_counseling_detail", "Counseling detail", source="sd.counseling_detail"),
    FormField("11_other_detail", "Other relief detail", source="sd.other_relief"),
    # Ex parte (immediate TPO) request
    FormField(
        "ex_parte_tpo",
        "Request immediate Temporary Protection Order (without notice)",
        source="sd.ex_parte",
        needs_legal_review=True,
    ),
    FormField(
        "ex_parte_reasons",
        "Reasons immediate protection is needed (irreparable injury)",
        source="sd.ex_parte_reasons",
    ),
    # Verification (sworn before a notary / deputy clerk)
    FormField(
        "signature",
        "Filer/Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """SD resolver — adds the abuse/relief/sub-checklist membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto SD UJS-091A fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=SD_UJS091A_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
