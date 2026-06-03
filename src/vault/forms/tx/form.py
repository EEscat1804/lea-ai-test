"""Texas Application for Protective Order form mapping.

Maps Vault intake answers onto the Texas **Application for Protective Order**
(Tex. Fam. Code / Penal Code Title 5-6). The packet is the Application (parties,
reasons, relationship, children, criminal history, the terms-and-conditions
requested in item 8 a-n, property/support/children orders, ex parte, and
confidentiality) plus a sworn **Affidavit** (or Declaration) statement.

The TX intake section (`vault.intake`, the `jurisdiction == "TX"` block and the
existing TX Tier-2 branches) feeds the TX-specific items. TX's terms list (item
8 a-n) is its own, distinct from CA's and WA's.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings. See coverage.md.

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

FORM_ID = "TX-APO"
FORM_REVISION = "current"
JURISDICTION = "TX"


def _family_violence_reason(_answers: dict[str, Any]) -> str:
    """Item 2 — the Vault files family-violence protective orders."""
    return "checked"


# Item 8 terms requested. Intake collects choices as `tx.terms`; each box is
# checked by membership. (item, term key.)
_TX_TERM_ITEMS = {
    "8a": "no_family_violence",
    "8b": "no_sexual_assault",
    "8c": "no_threat_via_third_party",
    "8d": "no_harassing_communication",
    "8e": "no_communication",
    "8f": "no_go_within_distance",
    "8g": "no_go_near_residence_work_school",
    "8h": "no_go_near_childrens_school",
    "8i": "no_harassing_conduct",
    "8j": "suspend_handgun_license",
    "8k": "prohibit_firearm",
    "8l": "battering_program",
    "8m": "protect_pet",
    "8n": "other",
}

# Item 12 children orders, same membership pattern over `tx.children_orders`.
_TX_CHILDREN_ITEMS = {
    "12_no_removal_possession": "no_removal_possession",
    "12_no_removal_jurisdiction": "no_removal_jurisdiction",
    "12_possession_schedule": "possession_schedule",
    "12_child_support": "child_support",
}

_TERM_FIELDS = tuple(
    FormField(item, f"Term {item[1:]} ({key.replace('_', ' ')})", source="tx.terms",
              needs_legal_review=True)
    for item, key in _TX_TERM_ITEMS.items()
)
_CHILDREN_FIELDS = tuple(
    FormField(item, f"Children order ({key.replace('_', ' ')})", source="tx.children_orders",
              needs_legal_review=True)
    for item, key in _TX_CHILDREN_ITEMS.items()
)

TX_APO_FIELDS: tuple[FormField, ...] = (
    # 1 — Parties
    FormField("1_applicant", "Applicant name", source="petitioner.legal_name", required=True),
    FormField("1_respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("1_respondent_address", "Respondent address for service",
              source="respondent.last_known_address"),
    FormField("1_applicant_county", "Applicant county of residence", source=None,
              note="Not separately collected (only free-text safe address) — TG1."),

    # 2 — Reason for protective order
    FormField("2_family_violence", "Reason: family/dating violence or child abuse",
              derive=_family_violence_reason, needs_legal_review=True,
              note="Vault assumes a family-violence basis. Confirm the matter fits."),

    # 3 — Relationship
    FormField("3_relationship", "Applicant's relationship to respondent",
              source="relationship.type", needs_legal_review=True,
              note="Maps the intake relationship type onto TX's relationship checkboxes."),

    # 4 — Children needing protection
    FormField("4_children", "Children under 18 needing protection",
              source="protected_persons.children[]",
              note="Names; form also asks if respondent is parent/guardian per child — TG2."),

    # 5, 6 — Other adults / other court cases
    FormField("5_other_adults", "Other adults needing protection", source=None,
              note="Not collected — TG3."),
    FormField("6_other_court_cases", "Other court cases", source=None,
              note="Not collected — TG3."),

    # 7 — Criminal history
    FormField("7_criminal_title56", "Respondent convicted under Title 5/6",
              source="respondent.prior_criminal_history"),
    FormField("7_family_violence_finding", "Family-violence finding",
              source="respondent.prior_dv_finding"),
    FormField("7_parental_rights_terminated", "Parental rights terminated",
              source="respondent.parental_rights_terminated"),

    # 8 — Terms and conditions requested (a-n) + details (appended below)
    *_TERM_FIELDS,
    FormField("8f_places", "Stay-away — who", source="tx.stay_away_places"),
    FormField("8f_distance", "Stay-away distance (yards)", source="tx.stay_away_distance_yards"),
    FormField("8m_pet", "Pet to protect", source="tx.pet"),
    FormField("8n_other", "Other term requested", source="tx.other_terms"),

    # 9 — Property / exclusive residence
    FormField("9_exclusive_residence", "Exclusive use of residence / respondent vacate",
              source="tx.exclusive_residence", needs_legal_review=True),

    # 10, 11 — Spousal support / phone transfer
    FormField("10_spousal_support", "Spousal support requested", source="tx.spousal_support"),
    FormField("11_phone_transfer", "Wireless phone transfer requested",
              source="tx.phone_transfer"),

    # 12 — Children orders (membership)
    *_CHILDREN_FIELDS,

    # 13 — Temporary ex parte order
    FormField("13_ex_parte", "Temporary ex parte order requested", source="tx.ex_parte",
              needs_legal_review=True),

    # 14 — Keep information confidential
    FormField("14_confidential", "Keep applicant information confidential",
              source="tx.confidential"),

    # Application signature
    FormField("sig_applicant", "Applicant signature (printed name)",
              source="petitioner.legal_name", required=True),

    # Affidavit / Declaration (sworn statement)
    FormField("aff_relationship", "Affidavit: relationship with respondent",
              source="relationship.type"),
    FormField("aff_incident_narrative", "Affidavit: most recent incident",
              source="incidents[].narrative", required=True,
              note="Survivor's own words — verbatim (guardrail G-08)."),
    FormField("aff_incident_date", "Affidavit: incident date", source="incidents[].date"),
    FormField("aff_weapon", "Affidavit: weapon involved", source="incidents[].weapon_involved"),
    FormField("aff_firearms", "Affidavit: respondent has firearms",
              source="firearm.respondent_has_access"),
    FormField("aff_police", "Affidavit: police called", source="incidents[].police_called"),
    FormField("aff_injured", "Affidavit: injuries", source="incidents[].injury"),
    FormField("aff_prior_fv_conviction", "Affidavit: prior family-violence conviction",
              source="respondent.prior_dv_finding"),
    FormField("aff_exclusive_residence", "Affidavit: requesting exclusive residence",
              source="tx.exclusive_residence"),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """TX resolver — adds the terms/children membership rules, else basic lookup."""
    membership = {"tx.terms": _TX_TERM_ITEMS, "tx.children_orders": _TX_CHILDREN_ITEMS}
    if f.source in membership and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = membership[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto TX Application fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=TX_APO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
