"""Alaska Petition for Domestic Violence Protective Order form mapping.

Maps Vault intake answers onto Alaska Court System form **DV-100, _Petition for
Domestic Violence Protective Order (One Petitioner)_** (AS 18.66.100-.990, Civil
Rule 65.1, Rev. 1/26). The petition covers the parties, the order type
(20-day ex parte and/or long-term), the relationship, the abuse description,
short-term protections (§5), long-term protections (§6), children/custody, other
cases, and law-enforcement assistance (§9).

The AK intake section (`vault.intake`, the `jurisdiction == "AK"` block) feeds
the AK-specific items. AK's protection lists are its own, distinct from the other
states'. (Alaska's form number "DV-100" coincides with California's — different
form, disambiguated by jurisdiction.)

Protection: the form keeps the petitioner's contact info confidential via the
DV-128 sheet and an address-confidentiality option — intake only ever holds a
safe mailing address, and the confidential options default on. See coverage.md.

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

FORM_ID = "DV-100"
FORM_REVISION = "2026-01"  # Rev. 1/26
JURISDICTION = "AK"


def _checked(_answers: dict[str, Any]) -> str:
    """A protection-minded box that is asserted on (confidential contact info)."""
    return "checked"


# 1 — order type. Membership over `ak.order_type`.
_AK_ORDER_TYPE = {
    "order_ex_parte": "ex_parte",
    "order_long_term": "long_term",
}

# 5 — short-term protections. Membership over `ak.protections`.
_AK_PROTECTIONS = {
    "p_no_dv": "no_dv",
    "p_no_contact": "no_contact",
    "p_stay_away_residence": "stay_away_residence",
    "p_stay_away_locations": "stay_away_locations",
    "p_no_vehicle_interference": "no_vehicle_interference",
    "p_no_controlled_substances": "no_controlled_substances",
    "p_possession_residence": "possession_residence",
    "p_possession_vehicle": "possession_vehicle",
    "p_possession_personal_items": "possession_personal_items",
    "p_spousal_support": "spousal_support",
    "p_no_property_disposal": "no_property_disposal",
    "p_other_short_term": "other_short_term",
}

# 6 — long-term protections. Membership over `ak.long_term_protections`.
_AK_LONG_TERM = {
    "lt_no_weapon": "no_weapon",
    "lt_surrender_firearm": "surrender_firearm",
    "lt_pay_costs": "pay_costs",
    "lt_pay_expenses": "pay_expenses",
    "lt_batterers_program": "batterers_program",
    "lt_substance_treatment": "substance_treatment",
    "lt_other": "other_long_term",
}

# 9 — law-enforcement assistance. Membership over `ak.le_assistance`.
_AK_LE = {
    "le_possession_residence": "possession_residence",
    "le_possession_vehicle": "possession_vehicle",
    "le_possession_personal_items": "possession_personal_items",
    "le_child_custody": "child_custody_assist",
    "le_recover_items": "recover_items",
}

_MEMBERSHIP = {
    "ak.order_type": _AK_ORDER_TYPE,
    "ak.protections": _AK_PROTECTIONS,
    "ak.long_term_protections": _AK_LONG_TERM,
    "ak.le_assistance": _AK_LE,
}

_ORDER_TYPE_FIELDS = tuple(
    FormField(
        item,
        f"Order type: {key.replace('_', ' ')}",
        source="ak.order_type",
        needs_legal_review=True,
    )
    for item, key in _AK_ORDER_TYPE.items()
)
_PROTECTION_FIELDS = tuple(
    FormField(
        item,
        f"Protection: {key.replace('_', ' ')}",
        source="ak.protections",
        needs_legal_review=True,
    )
    for item, key in _AK_PROTECTIONS.items()
)
_LONG_TERM_FIELDS = tuple(
    FormField(
        item,
        f"Long-term: {key.replace('_', ' ')}",
        source="ak.long_term_protections",
        needs_legal_review=True,
    )
    for item, key in _AK_LONG_TERM.items()
)
_LE_FIELDS = tuple(
    FormField(item, f"Law enforcement: {key.replace('_', ' ')}", source="ak.le_assistance")
    for item, key in _AK_LE.items()
)

AK_DV100_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court_location", "Court location (AT)", source="ak.court_location", required=True),
    FormField(
        "petitioner", "Petitioner (protected person)", source="petitioner.legal_name", required=True
    ),
    FormField("petitioner_dob", "Petitioner birthdate", source="petitioner.dob"),
    FormField(
        "respondent",
        "Respondent (restrained person)",
        source="respondent.legal_name",
        required=True,
    ),
    FormField(
        "respondent_dob", "Respondent birthdate (estimate if unknown)", source="respondent.dob"
    ),
    # 1 — Type of order
    *_ORDER_TYPE_FIELDS,
    FormField(
        "notify_respondent",
        "Notified respondent before filing",
        source=None,
        note="Item 1 notice question not collected — AKG1.",
    ),
    # 2 — Relationship
    FormField(
        "relationship_basis",
        "How petitioner and respondent are related",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto AK's item-2 categories (married, "
        "child together, living together, dating/sexual, by marriage, other family). "
        "Attorney confirms the box(es).",
    ),
    # 3 — Children in household
    FormField(
        "children_in_household",
        "Children in petitioner's household",
        source="ak.children_in_household",
    ),
    # 4 — Describe the domestic violence
    FormField(
        "dv_narrative",
        "Describe the domestic violence",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("dv_weapon", "Weapon involved", source="incidents[].weapon_involved"),
    FormField("dv_injury", "Anyone injured", source="incidents[].injury"),
    FormField(
        "dv_other_instances",
        "Other instances of domestic violence",
        source="incidents[].pattern_frequency",
        note="Mapped from the intake pattern/frequency answer — confirm.",
    ),
    # 5 — Short-term protections + details
    *_PROTECTION_FIELDS,
    FormField("p_contact_exceptions", "No-contact exceptions", source="ak.contact_exceptions"),
    FormField(
        "address_confidential",
        "Petitioner address kept confidential from respondent",
        derive=_checked,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "respondent_lives_with",
        "Respondent lives with petitioner",
        source="relationship.live_together_now",
    ),
    FormField(
        "p_stay_away_locations_detail",
        "Stay-away locations / distances",
        source="ak.stay_away_locations",
    ),
    FormField(
        "p_possession_residence_address", "Residence to possess", source="ak.residence_address"
    ),
    FormField("p_possession_vehicle_desc", "Vehicle to possess", source="ak.vehicle_description"),
    FormField(
        "p_possession_personal_items_detail",
        "Essential personal items",
        source="ak.personal_items",
        note="Form lists specific item checkboxes; intake collects a free-text list — AKG2.",
    ),
    FormField(
        "p_spousal_support_detail", "Spousal support amount / reason", source="ak.spousal_support"
    ),
    FormField(
        "p_other_short_term_detail", "Other short-term protection", source="ak.other_short_term"
    ),
    # 6 — Long-term protections + details
    *_LONG_TERM_FIELDS,
    FormField(
        "lt_pay_costs_amount",
        "Filing costs/fees amount",
        source=None,
        note="Amount not collected — AKG3.",
    ),
    FormField("lt_expenses_detail", "Expenses caused by the DV", source="ak.expenses"),
    FormField("lt_other_detail", "Other long-term protection", source="ak.other_long_term"),
    # 7 — Children: custody, visitation, support
    FormField("custody", "Temporary physical custody requested", source="ak.custody"),
    FormField(
        "custody_children",
        "Children for custody",
        source="protected_persons.children[]",
        note="Names; form wants each child's DOB and relationship — partial, AKG4.",
    ),
    FormField("child_support", "Child support requested", source="ak.child_support"),
    FormField(
        "child_support_employer",
        "Respondent employer (child support)",
        source="respondent.employer_name",
    ),
    FormField(
        "child_support_take_home",
        "Respondent monthly take-home pay",
        source=None,
        note="Not collected by intake (bring DR-305 + proof of income) — AKG3.",
    ),
    # 8 — Other cases
    FormField(
        "other_cases",
        "Other open DV/civil cases",
        source="prior_orders.exists",
        note="Protective-order existence only; full case list not collected — AKG5.",
    ),
    # 9 — Law-enforcement assistance
    *_LE_FIELDS,
    # 10 — Information about respondent
    FormField(
        "respondent_address", "Respondent physical address", source="respondent.last_known_address"
    ),
    FormField(
        "respondent_phone", "Respondent phone", source=None, note="Not collected by intake — AKG6."
    ),
    FormField(
        "respondent_email", "Respondent email", source=None, note="Not collected by intake — AKG6."
    ),
    FormField("respondent_employer", "Respondent employer", source="respondent.employer_name"),
    # 11 — Information about petitioner (safe contact only)
    FormField(
        "dv128_confidential",
        "Providing contact info on DV-128 (confidential)",
        derive=_checked,
        note="Defaulted on — only safe contact info is held; home address never collected.",
    ),
    FormField(
        "petitioner_mailing",
        "Petitioner safe mailing address",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
    FormField("petitioner_phone", "Petitioner safe phone", source="petitioner.safe_phone"),
    FormField("petitioner_email", "Petitioner safe email", source="petitioner.safe_email"),
    # Verification / signature — sworn before a notary or court clerk at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn before a notary public or court clerk — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """AK resolver — adds the order-type/protections/long-term/LE membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto AK DV-100 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=AK_DV100_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
