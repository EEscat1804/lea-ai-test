"""New Hampshire Domestic Violence Petition form mapping.

Maps Vault intake answers onto the New Hampshire Circuit Court **Domestic
Violence Petition** (Form NHJB-2050-DF, Pursuant to RSA 173-B, rev. 03/15/2024).
The petition covers the parties (with a plaintiff demographic block and a
defendant identity block), the relationship basis, other pending court actions,
residence, the statement of facts, the financial-losses block, and the item-1
through item-15 relief list (protective orders 1-7 + additional orders 8-15).

The NH intake section (`vault.intake`, the `_nh_step` method) feeds the
NH-specific items. NH's relief list is its own, distinct from the other states'.
NH's Form NHJB-2050-DF has **no respondent physical-description block and no
respondent-vehicle block**, so NH is carved out of those shared Tier-2 gates (see
`vault.intake`); item 11's vehicle is the *plaintiff's* vehicle, modeled as a
relief detail, not a respondent identifier.

Protection: the petition prints no plaintiff street address at all (only the
defendant's), so intake collects no petitioner address for this form and none is
mapped here. The petition must be signed in person at court — never by fax,
e-mail, or mail. See coverage.md.

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

FORM_ID = "NHJB-2050-DF"
FORM_REVISION = "2024-03"  # rev. 03/15/2024
JURISDICTION = "NH"


def _immediate_danger(_answers: dict[str, Any]) -> str:
    """Opening allegation — "I am in immediate danger of abuse by the defendant"."""
    return "checked"


# Items 1-15 — relief requested (protective orders 1-7 + additional orders 8-15).
# Membership over `nh.relief`.
_NH_RELIEF = {
    "r_1_no_abuse_contact": "no_abuse_contact",  # 1 restrain abuse / all contact
    "r_2_stay_away": "stay_away",  # 2 premises / employment / school
    "r_3_protect_others": "protect_others",  # 3 relatives / household members
    "r_4_no_property_damage": "no_property_damage",  # 4 take / damage property
    "r_5_surrender_firearms": "surrender_firearms",  # 5 relinquish firearms / weapons
    "r_6_custody": "custody",  # 6 temporary custody of children
    "r_7_protect_animals": "protect_animals",  # 7 animal no-contact / cruelty
    "r_8_child_support": "child_support",  # 8 child support payments
    "r_9_visitation": "visitation",  # 9 court-approved visitation plan
    "r_10_exclusive_residence": "exclusive_residence",  # 10 residence + furnishings
    "r_11_exclusive_vehicle": "exclusive_vehicle",  # 11 exclusive use of a vehicle
    "r_12_animal_custody": "animal_custody",  # 12 care / custody of an animal
    "r_13_pay_losses": "pay_losses",  # 13 pay for financial losses
    "r_14_batterer_treatment": "batterer_treatment",  # 14 treatment / counseling
    "r_15_other": "other",  # 15 other relief
}

# "Court actions" block — other cases the parties are involved in. Membership over
# `nh.court_actions`.
_NH_COURT_ACTIONS = {
    "court_divorce": "divorce",
    "court_custody": "custody",
    "court_protective_order": "protective_order",
    "court_none": "none",
    "court_other": "other",
}

# Financial-losses block (page 1) — the losses suffered as a result of the abuse,
# supporting item-13 relief. Membership over `nh.financial_losses`.
_NH_FINANCIAL_LOSSES = {
    "loss_medical": "medical_dental_optical",
    "loss_wages": "lost_wages",
    "loss_property": "lost_property",
    "loss_other": "other",
}

_MEMBERSHIP = {
    "nh.relief": _NH_RELIEF,
    "nh.court_actions": _NH_COURT_ACTIONS,
    "nh.financial_losses": _NH_FINANCIAL_LOSSES,
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="nh.relief", needs_legal_review=True)
    for item, key in _NH_RELIEF.items()
)
_COURT_ACTION_FIELDS = tuple(
    FormField(item, f"Court action: {key.replace('_', ' ')}", source="nh.court_actions")
    for item, key in _NH_COURT_ACTIONS.items()
)
_FINANCIAL_LOSS_FIELDS = tuple(
    FormField(item, f"Financial loss: {key.replace('_', ' ')}", source="nh.financial_losses")
    for item, key in _NH_FINANCIAL_LOSSES.items()
)

NH_DV_PETITION_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court_name", "Court name (NH Circuit Court)", source="nh.court_name", required=True),
    # Plaintiff (petitioner) — name + demographic block
    FormField("petitioner", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Plaintiff date of birth", source="petitioner.dob"),
    FormField("petitioner_sex", "Plaintiff sex", source="petitioner.sex"),
    FormField("petitioner_race", "Plaintiff race", source="petitioner.race"),
    FormField("petitioner_ethnicity", "Plaintiff ethnicity", source="petitioner.ethnicity"),
    # Defendant (respondent) — name + identity block
    FormField("respondent", "Defendant name", source="respondent.legal_name", required=True),
    FormField("respondent_dob", "Defendant date of birth", source="respondent.dob"),
    FormField("respondent_sex", "Defendant sex", source="respondent.sex"),
    FormField(
        "respondent_address",
        "Defendant street address / city / state / zip",
        source="respondent.last_known_address",
    ),
    # Relationship to defendant
    FormField(
        "relationship_basis",
        "Plaintiff's relationship to defendant",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto NH's checklist (married / divorced / "
        "separated / cohabit / child in common / household member / other). Attorney confirms.",
    ),
    # Statement of facts (immediate danger + narrative + dates)
    FormField(
        "immediate_danger",
        "Plaintiff is in immediate danger of abuse (RSA 173-B)",
        derive=_immediate_danger,
        needs_legal_review=True,
        note="Standard opening allegation — the legal abuse finding rests on the narrative; "
        "attorney confirms it is supported.",
    ),
    FormField("abuse_date", "Date(s) the abuse occurred", source="incidents[].date"),
    FormField(
        "statement_of_facts",
        "Statement of facts (the abuse)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "see_attached",
        "See attached additional page(s)",
        source=None,
        note="Overflow-page flag not collected — NHG2.",
    ),
    # Other pending court actions
    *_COURT_ACTION_FIELDS,
    FormField("court_list", "Court(s) handling the case(s)", source="nh.court_list"),
    FormField(
        "represented_by_lawyer",
        "Plaintiff represented by a lawyer in those matters",
        source="nh.represented_by_lawyer",
    ),
    # Residence
    FormField("residence_type", "Residence: own or rent", source="nh.residence_type"),
    FormField("residence_holder", "Residence is in whose name", source="nh.residence_holder"),
    # Children living in household
    FormField(
        "children",
        "Children living in the household",
        source="protected_persons.children[]",
        note="Names; the form wants each child's DOB and who they primarily reside with — "
        "partial, NHG3. Minor children in common also require a UCCJEA Affidavit "
        "(NHJB-2660-FP), not assembled here.",
    ),
    # Financial losses (supports item-13 relief)
    *_FINANCIAL_LOSS_FIELDS,
    FormField(
        "financial_losses_other_detail",
        "Other financial loss (explain)",
        source="nh.financial_losses_other",
    ),
    # Items 1-15 — relief requested + details
    *_RELIEF_FIELDS,
    FormField(
        "firearms_detail",
        "Firearms / other deadly weapons to relinquish (item 5)",
        source="nh.firearms_detail",
    ),
    FormField(
        "exclusive_vehicle_detail",
        "Vehicle for the plaintiff's exclusive use (item 11)",
        source="nh.vehicle_detail",
    ),
    FormField("other_relief_detail", "Other relief (item 15)", source="nh.other_relief"),
    # Signature / verification
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn true under penalty of criminal liability; must be signed in person at "
        "court — never by fax, e-mail, or mail.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NH resolver — adds the relief / court-action / financial-loss membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto NH Form NHJB-2050-DF fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NH_DV_PETITION_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
