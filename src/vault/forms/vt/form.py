"""Vermont Complaint for Relief from Abuse form mapping.

Maps Vault intake answers onto Vermont form **400-00150C, _Complaint for Relief
from Abuse_** (15 V.S.A. § 1101 et seq.; Superior Court, Family Division). The
complaint covers the parties, the relationship basis, an existing-proceedings
matrix, an acts-of-abuse checklist (item 1), residence/support facts, and TWO
distinct relief lists: a Request for Emergency Relief and a Request for Final
Order. The two lists differ — the Final Order adds temporary living expenses,
temporary child support, and pet possession; the Emergency Relief instead has a
"refrain from cruelly treating pets" box. VT's acts and relief lists are its own.

The narrative facts live on a separate accompanying affidavit (the form says so),
so this map carries the structured incident fields for that affidavit, not a
form box.

The VT intake section (`vault.intake`, the `jurisdiction == "VT"` block) feeds
the VT-specific items.

Protection: intake only ever holds a safe mailing address; the survivor's home
address is never collected. The form's caption asks only for the *defendant's*
physical address (for service), which maps from `respondent.last_known_address`.
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

FORM_ID = "400-00150C"
FORM_REVISION = "2017-08"  # 08/2017
JURISDICTION = "VT"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Plaintiff's address is withheld — intake holds only a safe mailing address."""
    return "checked"


def _danger_further_abuse(_answers: dict[str, Any]) -> str:
    """Item 2 — a danger of further abuse; asserted by the act of filing."""
    return "checked"


def _protect_children(answers: dict[str, Any]) -> str | None:
    """Whether relief/abuse extends to the children (item 1 / relief 'child(ren)' boxes)."""
    if answers.get("vt.includes_children") is True:
        return "checked"
    return None


# Item 1 — acts of abuse. Membership over `vt.abuse_acts`.
_VT_ABUSE = {
    "ab_physical_harm": "physical_harm",
    "ab_fear_serious_harm": "fear_serious_harm",
    "ab_child_abuse": "child_abuse",
    "ab_stalking": "stalking",
    "ab_sexual_assault": "sexual_assault",
}

# Existing court order / proceedings matrix. Membership over `vt.existing_proceedings`.
_VT_PROCEEDINGS = {
    "ep_divorce_separation": "divorce_separation",
    "ep_civil_union_dissolution": "civil_union_dissolution",
    "ep_relief_from_abuse": "relief_from_abuse",
    "ep_criminal": "criminal",
    "ep_parentage": "parentage",
    "ep_guardianship": "guardianship",
    "ep_juvenile_dcf": "juvenile_dcf",
}

# Request for Emergency Relief. Membership over `vt.emergency_relief`.
_VT_EMERGENCY = {
    "em_no_abuse": "no_abuse",
    "em_refrain_stalking_sa": "refrain_stalking_sa",
    "em_leave_residence": "leave_residence",
    "em_parental_rights": "parental_rights",
    "em_no_pet_cruelty": "no_pet_cruelty",
    "em_stay_away": "stay_away",
    "em_no_contact": "no_contact",
    "em_other": "other",
}

# Request for Final Order. Membership over `vt.final_relief`.
_VT_FINAL = {
    "fo_no_abuse": "no_abuse",
    "fo_refrain_stalking_sa": "refrain_stalking_sa",
    "fo_leave_residence": "leave_residence",
    "fo_parental_rights": "parental_rights",
    "fo_pet_possession": "pet_possession",
    "fo_stay_away": "stay_away",
    "fo_no_contact": "no_contact",
    "fo_living_expenses": "living_expenses",
    "fo_child_support": "child_support",
    "fo_other": "other",
}

_MEMBERSHIP = {
    "vt.abuse_acts": _VT_ABUSE,
    "vt.existing_proceedings": _VT_PROCEEDINGS,
    "vt.emergency_relief": _VT_EMERGENCY,
    "vt.final_relief": _VT_FINAL,
}

_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="vt.abuse_acts", needs_legal_review=True
    )
    for item, key in _VT_ABUSE.items()
)
_PROCEEDING_FIELDS = tuple(
    FormField(item, f"Existing case: {key.replace('_', ' ')}", source="vt.existing_proceedings")
    for item, key in _VT_PROCEEDINGS.items()
)
_EMERGENCY_FIELDS = tuple(
    FormField(
        item,
        f"Emergency: {key.replace('_', ' ')}",
        source="vt.emergency_relief",
        needs_legal_review=True,
    )
    for item, key in _VT_EMERGENCY.items()
)
_FINAL_FIELDS = tuple(
    FormField(
        item, f"Final: {key.replace('_', ' ')}", source="vt.final_relief", needs_legal_review=True
    )
    for item, key in _VT_FINAL.items()
)

VT_RFA_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("unit", "Unit (Superior Court, Family Division)", source="vt.unit", required=True),
    FormField("plaintiff", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("plaintiff_dob", "Plaintiff date of birth", source="petitioner.dob"),
    FormField(
        "address_confidential",
        "Plaintiff address withheld (safe mailing address only)",
        derive=_address_confidential,
    ),
    FormField(
        "plaintiff_mailing_address",
        "Plaintiff safe mailing address",
        source="petitioner.safe_mailing_address",
    ),
    FormField("defendant", "Defendant name", source="respondent.legal_name", required=True),
    FormField("defendant_dob", "Defendant date of birth", source="respondent.dob"),
    FormField(
        "defendant_address",
        "Defendant's full physical address",
        source="respondent.last_known_address",
    ),
    # Relationship of the parties
    FormField(
        "relationship_basis",
        "Relationship of the parties",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto VT's relationship categories "
        "(spouses / former spouses / living together / sexual relationship / dating / "
        "family member / other). Attorney confirms the box.",
    ),
    # Existing court order or proceedings
    *_PROCEEDING_FIELDS,
    FormField(
        "existing_proceedings_where",
        "Existing case state(s) / county",
        source="vt.existing_proceedings_where",
    ),
    FormField(
        "attorney_plaintiff",
        "Attorney for Plaintiff",
        source=None,
        note="Not collected by intake — VTG1.",
    ),
    FormField(
        "attorney_defendant",
        "Attorney for Defendant",
        source=None,
        note="Not collected by intake — VTG1.",
    ),
    # Facts (item 1)
    FormField("fact_date", "Date of the abuse (item 1)", source="incidents[].date"),
    FormField(
        "fact_against_children",
        "Item 1 directed at the child(ren)",
        derive=_protect_children,
        needs_legal_review=True,
        note="Checked when the survivor asks to protect the children too.",
    ),
    FormField(
        "fact_children_names",
        "Names of child(ren) (item 1)",
        source="protected_persons.children[]",
        note="Names only; the form wants name + DOB + relationship per child — VTG2.",
    ),
    *_ABUSE_FIELDS,
    FormField(
        "stalking_dates",
        "Stalking date(s) (item 1)",
        source="vt.stalking_dates",
        needs_legal_review=True,
    ),
    # Facts (items 2, 3, 6)
    FormField(
        "fact_danger_further_abuse",
        "Item 2 — danger of further abuse",
        derive=_danger_further_abuse,
        needs_legal_review=True,
    ),
    FormField(
        "fact_defendant_incarcerated",
        "Item 3 — defendant incarcerated/convicted (15 V.S.A. 1103(c)(1)(B))",
        source="vt.defendant_incarcerated",
        needs_legal_review=True,
    ),
    FormField(
        "fact_public_assistance",
        "Item 6 — recipient of public assistance",
        source="vt.public_assistance",
    ),
    # Item 4 / residence facts (also the leave-residence relief)
    FormField("residence_address", "Residence to leave (item 4)", source="vt.residence_address"),
    FormField("residence_tenure", "Residence owned vs rented/leased", source="vt.residence_tenure"),
    FormField("residence_in_name", "Residence in whose name", source="vt.residence_in_name"),
    # Request for Emergency Relief
    *_EMERGENCY_FIELDS,
    FormField(
        "em_stay_away_distance",
        "Emergency stay-away distance (feet)",
        source="vt.stay_away_distance",
        note="One intake answer fills the distance blank in both relief sections.",
    ),
    FormField("em_other_detail", "Emergency other relief detail", source="vt.emergency_other"),
    # Request for Final Order
    *_FINAL_FIELDS,
    FormField(
        "fo_stay_away_distance",
        "Final stay-away distance (feet)",
        source="vt.stay_away_distance",
        note="One intake answer fills the distance blank in both relief sections.",
    ),
    FormField("fo_other_detail", "Final other relief detail", source="vt.final_other"),
    # Affidavit (narrative lives on the accompanying affidavit, not the form face)
    FormField(
        "affidavit_narrative",
        "Abuse narrative (accompanying affidavit)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08). The form face says facts "
        "are on the accompanying affidavit.",
    ),
    # Signature
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """VT resolver — adds the abuse/proceedings/relief membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto VT 400-00150C fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=VT_RFA_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
