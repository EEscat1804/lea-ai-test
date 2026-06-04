"""Alabama Petition for Protection from Abuse form mapping.

Maps Vault intake answers onto Alabama Unified Judicial System **Form C-2,
_Petition for Protection from Abuse_** (Ala. Code § 30-5-1 et seq., Rev.
10/2023). The petition covers eligibility (§I), the relationship basis, the
acts-of-abuse checklist (§II), the abuse narrative (§III), prior orders (§IV),
children (§V), residence ownership (§VI), the ex parte relief list (§VII, items
1-10), and the final-hearing relief list (§VIII, items 11-19).

The AL intake section (`vault.intake`, the `jurisdiction == "AL"` block) feeds
the AL-specific items. AL's acts and relief lists are its own, distinct from the
other states'.

Protection: Ala. Code § 30-5-5(f)(1) keeps the plaintiff's home/business address
and phone off public court documents — intake only ever holds a safe mailing
address, and the address-confidential note is asserted. See coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "C-2"
FORM_REVISION = "2023-10"  # Rev. 10/2023
JURISDICTION = "AL"


def _age_from(dob_key: str) -> Callable[[dict[str, Any]], str | None]:
    """Build a derive fn that computes age from the DOB at `dob_key`."""

    def _derive(answers: dict[str, Any]) -> str | None:
        dob_str = answers.get(dob_key)
        if not isinstance(dob_str, str) or not dob_str:
            return None
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
        except ValueError:
            return None
        today = datetime.now()
        return str(today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day)))

    return _derive


def _eligible_adult(answers: dict[str, Any]) -> str | None:
    """§I — the 18-or-older victim box, checked when the petitioner is an adult."""
    age = _age_from("petitioner.dob")(answers)
    if age is not None and age.isdigit() and int(age) >= 18:
        return "checked"
    return None


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Plaintiff address withheld from public documents (§ 30-5-5(f)(1))."""
    return "checked"


# §VII page-2 request type. Membership over `al.request_type`.
_AL_REQUEST = {
    "req_protection_order": "protection_order",
    "req_emergency": "emergency_order",
    "req_change_current": "change_current_order",
    "req_change_emergency": "change_emergency_order",
}

# §II acts of abuse. Membership over `al.abuse_acts`.
_AL_ABUSE = {
    "ab_threatened_confine": "threatened_confine",
    "ab_fear_serious_injury": "fear_serious_injury",
    "ab_sex_by_force": "sex_by_force",
    "ab_kidnapped": "kidnapped",
    "ab_trespassed": "trespassed",
    "ab_tortured_child": "tortured_child",
    "ab_stole": "stole",
    "ab_reckless_conduct": "reckless_conduct",
    "ab_tortured_child_multiple": "tortured_child_multiple",
    "ab_exposed_child_drugs": "exposed_child_drugs",
    "ab_injured": "injured",
    "ab_tried_acts": "tried_acts",
    "ab_threatened_injure": "threatened_injure",
    "ab_stalked": "stalked",
    "ab_set_fire": "set_fire",
    "ab_restrained": "restrained",
    "ab_other": "other",
}

# §VII ex parte relief (items 1-10). Membership over `al.ex_parte_relief`.
_AL_EX_PARTE = {
    "ep1_enjoin_abuse": "enjoin_abuse",
    "ep2_restrain_harass": "restrain_harass",
    "ep3_no_contact_300ft": "no_contact_300ft",
    "ep4_custody": "custody",
    "ep5_no_interfere_removal": "no_interfere_removal",
    "ep6_no_remove_children": "no_remove_children",
    "ep7_exclude_residence": "exclude_residence",
    "ep8_possession_auto": "possession_auto_effects",
    "ep9_prohibit_property": "prohibit_property_disposal",
    "ep10_other": "other_safety",
}

# §VIII final-hearing relief (items 11-19). Membership over `al.final_relief`.
_AL_FINAL = {
    "f11_visitation": "visitation",
    "f12_attorney_fees": "attorney_fees",
    "f13_possession_residence": "possession_residence_evict",
    "f14_child_support": "child_support",
    "f15_vehicle": "vehicle_possession",
    "f16_incorporate": "incorporate_order",
    "f17_surrender_firearms": "surrender_firearms",
    "f18_le_accompany": "le_accompany",
    "f19_other": "other_final",
}

_MEMBERSHIP = {
    "al.request_type": _AL_REQUEST,
    "al.abuse_acts": _AL_ABUSE,
    "al.ex_parte_relief": _AL_EX_PARTE,
    "al.final_relief": _AL_FINAL,
}

_REQUEST_FIELDS = tuple(
    FormField(item, f"Requesting: {key.replace('_', ' ')}", source="al.request_type")
    for item, key in _AL_REQUEST.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="al.abuse_acts", needs_legal_review=True
    )
    for item, key in _AL_ABUSE.items()
)
_EX_PARTE_FIELDS = tuple(
    FormField(
        item,
        f"Ex parte: {key.replace('_', ' ')}",
        source="al.ex_parte_relief",
        needs_legal_review=True,
    )
    for item, key in _AL_EX_PARTE.items()
)
_FINAL_FIELDS = tuple(
    FormField(
        item, f"Final: {key.replace('_', ' ')}", source="al.final_relief", needs_legal_review=True
    )
    for item, key in _AL_FINAL.items()
)

AL_C2_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Circuit Court)", source="al.county", required=True),
    FormField("plaintiff", "Plaintiff (victim)", source="petitioner.legal_name", required=True),
    FormField(
        "defendant",
        "Defendant (person to be restrained)",
        source="respondent.legal_name",
        required=True,
    ),
    FormField("defendant_address", "Defendant address", source="respondent.last_known_address"),
    FormField("defendant_dob", "Defendant date of birth", source="respondent.dob"),
    FormField("defendant_age", "Defendant age", derive=_age_from("respondent.dob")),
    FormField(
        "defendant_ssn4",
        "Defendant SSN (last 4)",
        source=None,
        note="Not collected by intake (sensitive) — ALG1.",
    ),
    FormField(
        "address_confidential",
        "Plaintiff address withheld (§ 30-5-5(f)(1))",
        derive=_address_confidential,
    ),
    # §I — Eligibility + relationship
    FormField(
        "eligible_adult",
        "Plaintiff is an adult victim (18+)",
        derive=_eligible_adult,
        needs_legal_review=True,
        note="Checked when the petitioner is 18+. Minor/guardian eligibility boxes are "
        "a legal determination — ALG2.",
    ),
    FormField(
        "relationship_basis",
        "Relationship of victim to defendant (§I.1-6)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto AL's §I relationship categories. "
        "Attorney confirms the box (only ONE may be checked).",
    ),
    # Plaintiff residence / age + prior cases
    FormField("plaintiff_county", "Plaintiff resident county", source="al.county"),
    FormField("plaintiff_age", "Plaintiff age", derive=_age_from("petitioner.dob")),
    FormField(
        "other_civil_case",
        "Other civil/DR/custody case with defendant",
        source=None,
        note="Not collected by intake — ALG3.",
    ),
    FormField(
        "criminal_charges",
        "Criminal charges against defendant",
        source=None,
        note="Not collected by intake — ALG3.",
    ),
    # Page 2 — venue + request type
    FormField(
        "abuse_county",
        "County where the abuse occurred",
        source="incidents[].location",
        note="Mapped from the incident location — confirm county.",
    ),
    *_REQUEST_FIELDS,
    # §II — Acts of abuse
    *_ABUSE_FIELDS,
    # §III — Abuse narrative
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    FormField(
        "abuse_description",
        "Describe how the defendant hurt or threatened the plaintiff",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "fear_further",
        "Why the plaintiff fears further abuse",
        source=None,
        note="Not collected as a separate prompt — ALG4.",
    ),
    # §IV — Legal info (prior orders)
    FormField(
        "existing_po_against_defendant",
        "Existing protection order against defendant",
        source="prior_orders.exists",
        note="Existence only; county/state not collected — ALG3.",
    ),
    FormField(
        "existing_po_against_plaintiff",
        "Existing protection order against plaintiff",
        source=None,
        note="Not collected by intake — ALG3.",
    ),
    # §V — Children
    FormField(
        "children",
        "Children of defendant and plaintiff (under 19)",
        source="protected_persons.children[]",
        note="Names; form wants each child's DOB and the custody/residence history — "
        "partial, ALG5.",
    ),
    FormField(
        "custody_order_exists",
        "Existing custody order about the children",
        source=None,
        note="Not collected by intake — ALG5.",
    ),
    # §VI — Residence ownership
    FormField("residence_basis", "Residence ownership/rental basis", source="al.residence_basis"),
    # §VII — Ex parte relief (1-10) + details
    *_EX_PARTE_FIELDS,
    FormField(
        "ep9_property_description",
        "Property to protect from disposal",
        source="al.property_description",
    ),
    FormField("ep10_other_detail", "Other ex parte safety relief", source="al.other_ex_parte"),
    # §VIII — Final-hearing relief (11-19) + details
    *_FINAL_FIELDS,
    FormField("f11_visitation_type", "Visitation type", source="al.visitation_type"),
    FormField("f11_visitation_terms", "Visitation arrangement", source="al.visitation_terms"),
    FormField("f15_vehicle_description", "Vehicle to possess", source="al.vehicle_description"),
    FormField("f19_other_detail", "Other final relief", source="al.other_final"),
    # Verification / signature — sworn before a notary at filing
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn before an officer authorized to administer oaths / notary — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """AL resolver — adds the request/abuse/ex-parte/final membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto AL Form C-2 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=AL_C2_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
