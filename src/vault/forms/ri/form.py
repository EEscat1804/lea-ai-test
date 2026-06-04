"""Rhode Island Complaint for an Order of Protection form mapping.

Maps Vault intake answers onto Rhode Island **Form FC-79, _Complaint for an Order
of Protection and Motion for Temporary Ex Parte Order of Protection_** (Family
Court; G.L. 1956 ch. 15 of tit. 15 (Domestic Abuse Prevention) / ch. 37.2 of tit.
11 (Sexual Assault Protective Orders); rev. July 2025). The complaint covers the
county and case type, the parties (plaintiff/defendant name + DOB + address), the
§5 relationship basis, the §7 abuse checklist, the requested relief, and the
motion for an immediate ex parte order. RI's abuse and relief lists are their own.

The RI intake section (`vault.intake`, the `_ri_step` method) plus the
unconditional employer gate feeds these items. RI is intentionally NOT in
`PHYSICAL_DESCRIPTION_STATES` or `VEHICLE_DESCRIPTION_STATES` — FC-79 has no
respondent description or vehicle block.

Protection: the petitioner's address is the safe mailing address intake holds, and
FC-79 carries no address-confidentiality checkbox, so the mapping is flagged
(RIG3). The defendant's Social Security number is not asked by the form and not
collected. See coverage.md.

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

FORM_ID = "FC-79"
FORM_REVISION = "2025-07"  # revised July 2025
JURISDICTION = "RI"


# Caption — case type. Membership over `ri.case_type`.
_RI_CASE_TYPE = {
    "case_domestic_abuse": "domestic_abuse",
    "case_sexual_exploitation": "sexual_exploitation",
    "case_sexual_abuse": "sexual_abuse",
    "case_domestic_abuse_juvenile": "domestic_abuse_juvenile",
}

# §7 — what the defendant did. Membership over `ri.abuse_types`.
_RI_ABUSE = {
    "7_weapon": "weapon",
    "7_attempted_harm": "attempted_harm",
    "7_caused_harm": "caused_harm",
    "7_fear_imminent": "fear_imminent",
    "7_sexual_force": "sexual_force",
    "7_attempted_sexual": "attempted_sexual",
    "7_stalking": "stalking",
    "7_sexual_exploitation": "sexual_exploitation",
}

# "I ask that the Family Court" — relief checklist. Membership over `ri.relief`.
_RI_RELIEF = {
    "relief_no_contact": "no_contact",
    "relief_surrender_firearms": "surrender_firearms",
    "relief_vacate": "vacate",
    "relief_no_utility_disruption": "no_utility_disruption",
    "relief_custody": "custody",
    "relief_child_support": "child_support",
    "relief_pets": "pets",
}

_MEMBERSHIP = {
    "ri.case_type": _RI_CASE_TYPE,
    "ri.abuse_types": _RI_ABUSE,
    "ri.relief": _RI_RELIEF,
}

_CASE_TYPE_FIELDS = tuple(
    FormField(
        item,
        f"Case type: {key.replace('_', ' ')}",
        source="ri.case_type",
        needs_legal_review=True,
    )
    for item, key in _RI_CASE_TYPE.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item,
        f"Abuse: {key.replace('_', ' ')}",
        source="ri.abuse_types",
        needs_legal_review=True,
    )
    for item, key in _RI_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Relief: {key.replace('_', ' ')}",
        source="ri.relief",
        needs_legal_review=True,
    )
    for item, key in _RI_RELIEF.items()
)

RI_FC79_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Family Court division)", source="ri.county", required=True),
    FormField(
        "civil_action_file_number",
        "Civil Action File Number",
        source=None,
        note="Assigned by the clerk at filing — RIG1.",
    ),
    *_CASE_TYPE_FIELDS,
    # Plaintiff
    FormField("plaintiff", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("plaintiff_dob", "Plaintiff date of birth", source="petitioner.dob"),
    FormField(
        "plaintiff_capacity",
        "Plaintiff capacity (individually / parent / guardian / POA)",
        source=None,
        note="Form lets the plaintiff file individually and/or for a child; intake assumes "
        "individually and does not collect the capacity checkboxes — RIG2.",
    ),
    # 1 — plaintiff address
    FormField(
        "plaintiff_address",
        "Plaintiff full name, street address, city, state (§1)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Intake holds a safe mailing address; FC-79 has no address-confidentiality "
        "checkbox, so confirm before printing the street address — RIG3.",
    ),
    # 2 — former residence left to avoid abuse
    FormField(
        "former_residence",
        "Former residence left to avoid abuse (§2)",
        source="ri.former_residence",
    ),
    # Plaintiff's protected children (a-e)
    FormField(
        "other_protected",
        "Children protected by this order (a-e)",
        source="protected_persons.children[]",
        note="Names only; form wants name + DOB per child — RIG4.",
    ),
    # Defendant
    FormField("defendant", "Defendant name", source="respondent.legal_name", required=True),
    FormField("defendant_dob", "Defendant date of birth", source="respondent.dob"),
    # 3 — defendant address
    FormField(
        "defendant_address",
        "Defendant full name, street address, city, state (§3)",
        source="respondent.last_known_address",
    ),
    FormField(
        "defendant_capacity",
        "Defendant capacity (individually / parent / guardian / POA)",
        source=None,
        note="Not collected by intake — RIG2.",
    ),
    # 4 — other lawsuits / orders between the parties
    FormField(
        "other_court_cases",
        "Other lawsuits / protection / no-contact orders (§4)",
        source="prior_orders.exists",
        note="Existence only; form wants 'None' or the case numbers — RIG5.",
    ),
    # 5 — relationship basis
    FormField(
        "relationship_basis",
        "Relationship of plaintiff to defendant (§5 check-one)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto RI's §5 categories (married, blood/"
        "marriage relative, shared children, substantive dating within the past year, or "
        "none — sexual-abuse only). Attorney confirms the box.",
    ),
    FormField(
        "relationship_relative_specify",
        "If a relative — 'the defendant is my ___' (§5)",
        source=None,
        note="The blood/marriage-relative free-text is not separately collected — RIG6.",
    ),
    # 6 — servicemember certification (standing statement)
    FormField(
        "military_certification",
        "Defendant not in military service / national guard (§6)",
        source=None,
        note="Standing certification on the form; defendant military status is not collected "
        "by intake for RI — RIG7.",
    ),
    # 7 — abuse
    FormField("abuse_date", "On or about — date of abuse (§7)", source="incidents[].date"),
    *_ABUSE_FIELDS,
    FormField("7_weapon_detail", "Weapon used / threatened (§7)", source="ri.weapon_detail"),
    FormField(
        "abuse_narrative",
        "Facts of abuse (verified complaint / affidavit)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    # Relief — "I ask that the Family Court"
    *_RELIEF_FIELDS,
    FormField("vacate_address", "Household to vacate / stay out of", source="ri.vacate_address"),
    FormField(
        "custody_children", "Minor children for temporary custody", source="ri.custody_children"
    ),
    FormField("pets_detail", "Household animals / pets to protect", source="ri.pets_detail"),
    # Motion for temporary ex parte order
    FormField(
        "ex_parte_request",
        "Request relief without notice (temporary ex parte order)",
        source="ri.ex_parte",
        needs_legal_review=True,
    ),
    # Verification (sworn before a notary)
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
    FormField(
        "notary",
        "Notary acknowledgment",
        source=None,
        note="Completed before a notary at filing — RIG8.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """RI resolver — adds the case-type/abuse/relief membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto RI FC-79 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=RI_FC79_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
