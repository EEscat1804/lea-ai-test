"""New Mexico Petition for Order of Protection from Domestic Abuse form mapping.

Maps Vault intake answers onto New Mexico **Form 4-961, _Petition for Order of
Protection from Domestic Abuse_** (Family Violence Protection Act, §§ 40-13-1 to
40-13-8 NMSA 1978). The petition covers the court-assistance request, the
relationship basis, the respondent's firearms, children (UCCJEA), other cases,
the domestic-abuse statement, the item-6 (A-J) requests to the court, and the
respondent's location.

The NM intake section (`vault.intake`, the `_nm_step` method plus the shared
interpreter block — NM is in the interpreter gate) feeds the NM-specific items.
NM's relief list is its own, distinct from the other states'. (NM is in none of
the physical-description / vehicle / minor-filing sets, so the petition takes a
clean intake path.)

Protection: Form 4-961 lets the petitioner seal their address via Forms 4-961A/
4-961B; intake only ever holds a safe mailing address, and the
confidential-address request defaults on. See coverage.md.

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

FORM_ID = "4-961"
FORM_REVISION = "2019-07"  # effective for petitions filed on or after July 1, 2019
JURISDICTION = "NM"


def _confidential_address(_answers: dict[str, Any]) -> str:
    """Item 7A — seal the petitioner's address (Forms 4-961A/4-961B)."""
    return "checked"


# Item 6 — requests to the court (A-J). Membership over `nm.relief`.
_NM_RELIEF = {
    "r_no_contact_stay_away": "no_contact_stay_away",  # A
    "r_leave_residence": "leave_residence",  # B(1)
    "r_alternative_housing": "alternative_housing",  # B(2)
    "r_no_property_disposal": "no_property_disposal",  # C
    "r_le_retrieve": "le_retrieve_belongings",  # D
    "r_custody": "custody",  # E
    "r_children_contact": "children_contact",  # F
    "r_support": "support",  # G
    "r_pay_damages": "pay_damages",  # H
    "r_other": "other",  # I
    "r_surrender_firearms": "surrender_firearms",  # J
}

# Item 6G — support for whom. Membership over `nm.support_types`.
_NM_SUPPORT = {
    "support_children": "children",
    "support_petitioner": "petitioner",
}

_MEMBERSHIP = {
    "nm.relief": _NM_RELIEF,
    "nm.support_types": _NM_SUPPORT,
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="nm.relief", needs_legal_review=True)
    for item, key in _NM_RELIEF.items()
)
_SUPPORT_FIELDS = tuple(
    FormField(item, f"Support for: {key.replace('_', ' ')}", source="nm.support_types")
    for item, key in _NM_SUPPORT.items()
)

NM_OP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County", source="nm.county", required=True),
    FormField("judicial_district", "Judicial district", source="nm.judicial_district"),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    # 1 — Court assistance request (interpreter)
    FormField(
        "interpreter", "Interpreter needed / language", source="petitioner.interpreter_language"
    ),
    # 2 — Respondent: relationship + firearms
    FormField(
        "relationship_basis",
        "Respondent's relationship to petitioner",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto NM's item-2A categories (spouse / "
        "ex / parent of my children / family member / continuing personal "
        "relationship / sexual assault / stalking). Attorney confirms.",
    ),
    FormField(
        "respondent_firearms",
        "Respondent's firearms (make/model)",
        source="firearm.types[]",
        note="Firearm descriptions from intake; presence from firearm.respondent_has_access.",
    ),
    # 3 — Children (UCCJEA)
    FormField(
        "children",
        "Minor children of either party",
        source="protected_persons.children[]",
        note="Names; form wants DOB / relationship / residence history per child — partial, NMG1.",
    ),
    # 4 — Other cases
    FormField(
        "other_cases",
        "Other divorce/OP/support/abuse cases",
        source="prior_orders.exists",
        note="Protective-order existence only; full case list not collected — NMG2.",
    ),
    # 5 — Domestic abuse
    FormField(
        "abuse_description",
        "Acts of domestic abuse (physical / threats / other)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08). Covers "
        "the physical/threats/other-abuse description.",
    ),
    FormField("abuse_date", "Date of abuse", source="incidents[].date"),
    FormField("abuse_place", "Place of abuse", source="incidents[].location"),
    FormField(
        "abuse_witnesses", "Others present during the abuse", source="incidents[].witnesses_present"
    ),
    FormField("drugs_alcohol", "Drugs/alcohol played a role", source="nm.drugs_alcohol"),
    FormField(
        "weapons_used", "Weapons used during the abuse", source="incidents[].weapon_involved"
    ),
    FormField("prior_abuse", "Prior domestic abuse", source="nm.prior_abuse"),
    # 6 — Requests to the court (A-J) + details
    *_RELIEF_FIELDS,
    FormField("residence_address", "Residence to leave (B1)", source="nm.residence_address"),
    FormField(
        "retrieve_address", "Address to retrieve belongings (D)", source="nm.retrieve_address"
    ),
    *_SUPPORT_FIELDS,
    FormField(
        "children_contact", "Children contact until hearing (F)", source="nm.children_contact"
    ),
    FormField("other_relief", "Other relief (I)", source="nm.other_relief"),
    # 7 — Petitioner info (confidential)
    FormField(
        "confidential_address",
        "Address kept under seal (Forms 4-961A/B)",
        derive=_confidential_address,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "petitioner_mailing",
        "Petitioner safe mailing address",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
    # 9 — Location of respondent
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_work", "Respondent work address", source="respondent.employer_address"),
    FormField("respondent_in_jail", "Respondent is in jail", source="nm.respondent_in_jail"),
    # Verification / signature
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Affirmed under penalty of perjury (New Mexico) — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NM resolver — adds the relief and support membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto NM Form 4-961 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NM_OP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
