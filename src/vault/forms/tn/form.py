"""Tennessee Petition for Order of Protection form mapping.

Maps Vault intake answers onto Tennessee **Form #OP2018-1, _Petition for Order of
Protection and Order for Hearing_** (TCA § 36-3-601 et seq.; rev. 04/30/2018).
The petition covers the parties, a "Describe Respondent" block, the §1
relationship/eligibility basis, the children list, the abuse narrative, and the
items 7-19 relief checklist (no contact through general relief) plus the ex parte
(Temporary Order of Protection) request. TN's relief list is its own.

The TN intake section (`vault.intake`, the `_tn_step` method) plus the shared
physical-description and minor-filing gates feeds these items. TN is intentionally
NOT in `VEHICLE_DESCRIPTION_STATES` — OP2018-1 has no vehicle field.

Protection: the form lets the petitioner leave the children's addresses blank if
listing them would create danger, and never asks for the petitioner's own
address; intake holds only a safe mailing address, and the confidential-address
note is asserted. The respondent's SSN is explicitly "do not list here" on the
form — sensitive, not collected. See coverage.md.

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

FORM_ID = "OP2018-1"
FORM_REVISION = "2018-04-30"  # rev. 04/30/2018
JURISDICTION = "TN"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Petitioner's address is withheld — intake holds only a safe mailing address."""
    return "checked"


def _children_address_confidential(answers: dict[str, Any]) -> str | None:
    """Item 2 — leave children's addresses blank (danger), when there are children."""
    children = answers.get("protected_persons.children[]")
    if isinstance(children, str) and children.strip().lower() not in ("", "none"):
        return "checked"
    return None


# Items 7-19 — relief checklist. Membership over `tn.relief`.
_TN_RELIEF = {
    "7_no_contact": "no_contact",
    "8_stay_away": "stay_away",
    "9_personal_conduct": "personal_conduct",
    "10_temporary_custody": "temporary_custody",
    "11_child_support": "child_support",
    "12_spousal_support": "spousal_support",
    "13_move_out": "move_out",
    "14_counseling": "counseling",
    "15_no_firearms": "no_firearms",
    "16_animals": "animals",
    "17_costs_fees": "costs_fees",
    "18_transfer_wireless": "transfer_wireless",
    "19_other": "other",
}

# Item 7 no-contact sub-targets. Membership over `tn.no_contact_who`.
_TN_NO_CONTACT = {
    "7_contact_me": "me",
    "7_contact_children": "children",
}

# Item 8 stay-away sub-places. Membership over `tn.stay_away_places`.
_TN_STAY_AWAY = {
    "8_sa_home": "home",
    "8_sa_workplace": "workplace",
    "8_sa_anywhere": "anywhere",
}

# Item 9 personal-conduct sub-types. Membership over `tn.personal_conduct_types`.
_TN_PERSONAL_CONDUCT = {
    "9_pc_property_utilities": "property_utilities",
    "9_pc_animals": "animals",
}

_MEMBERSHIP = {
    "tn.relief": _TN_RELIEF,
    "tn.no_contact_who": _TN_NO_CONTACT,
    "tn.stay_away_places": _TN_STAY_AWAY,
    "tn.personal_conduct_types": _TN_PERSONAL_CONDUCT,
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="tn.relief", needs_legal_review=True)
    for item, key in _TN_RELIEF.items()
)
_NO_CONTACT_FIELDS = tuple(
    FormField(
        item,
        f"No contact: {key.replace('_', ' ')}",
        source="tn.no_contact_who",
        needs_legal_review=True,
    )
    for item, key in _TN_NO_CONTACT.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(
        item,
        f"Stay away: {key.replace('_', ' ')}",
        source="tn.stay_away_places",
        needs_legal_review=True,
    )
    for item, key in _TN_STAY_AWAY.items()
)
_PERSONAL_CONDUCT_FIELDS = tuple(
    FormField(
        item,
        f"Personal conduct: {key.replace('_', ' ')}",
        source="tn.personal_conduct_types",
        needs_legal_review=True,
    )
    for item, key in _TN_PERSONAL_CONDUCT.items()
)

TN_OP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Court of … County, TN)", source="tn.county", required=True),
    FormField(
        "court",
        "Court name",
        source=None,
        note="The court designation (Circuit/Chancery/General Sessions) is set locally — TNG1.",
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
        "Petitioner under 18 / filed on behalf of a minor (TCA §36-3-602)",
        source="petitioner.minor_filing_path",
        needs_legal_review=True,
        note="Whether an adult files for an under-18 petitioner — attorney/clerk confirms.",
    ),
    FormField(
        "petitioner_children_protected",
        "Petitioner's children under 18 needing protection",
        source="protected_persons.children[]",
        note="Names only; form wants name + age + relationship-to-respondent per child — TNG2.",
    ),
    # Respondent + Describe Respondent
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField("respondent_employer", "Respondent employer name", source="respondent.employer_name"),
    FormField(
        "respondent_employer_phone",
        "Respondent employer phone",
        source=None,
        note="Not collected by intake (employer address held, not phone) — TNG3.",
    ),
    FormField("respondent_sex", "Respondent sex", source="respondent.gender"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField(
        "respondent_ssn",
        "Respondent Social Security number",
        source=None,
        note="Form says 'Do not list it here' — sensitive, not collected (TNG4).",
    ),
    FormField(
        "respondent_features",
        "Respondent scars / special features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_phone",
        "Respondent phone number",
        source=None,
        note="Not collected by intake — TNG3.",
    ),
    # Warning! — weapon involved / owns a weapon
    FormField("warn_weapon_involved", "Weapon involved", source="incidents[].weapon_involved"),
    FormField(
        "warn_owns_weapon", "Respondent has/owns a weapon", source="firearm.respondent_has_access"
    ),
    # §1 — relationship / eligibility basis
    FormField(
        "relationship_basis",
        "Relationship / eligibility to respondent (§1 a-i)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto TN's §1 check-all categories. The "
        "stalking (g) and sexual-assault (h) grounds are attorney-confirmed from the "
        "narrative — they don't require a domestic relationship.",
    ),
    # §2 — children list confidentiality
    FormField(
        "children_address_confidential",
        "Leave children's addresses blank (danger)",
        derive=_children_address_confidential,
        note="Defaulted on when children are present (protection-minded).",
    ),
    # §4 — other court cases (partial from prior_orders)
    FormField(
        "other_court_cases",
        "Other court cases (§4)",
        source="prior_orders.exists",
        note="Existence only; form wants county/case#/kind — TNG5.",
    ),
    # §6 — abuse narrative
    FormField(
        "abuse_narrative",
        "Describe abuse, stalking or assault (§6)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "When it happened (§6)", source="incidents[].date"),
    FormField("abuse_location", "Where it happened (§6)", source="incidents[].location"),
    FormField("abuse_weapons", "Weapons used (§6)", source="incidents[].weapon_involved"),
    # §15 — firearms list (when respondent has access)
    FormField("15_firearm_types", "Firearm types", source="firearm.types[]"),
    FormField("15_firearm_locations", "Firearm locations", source="firearm.locations[]"),
    # Items 7-19 — relief checklist + sub-detail
    *_RELIEF_FIELDS,
    *_NO_CONTACT_FIELDS,
    *_STAY_AWAY_FIELDS,
    *_PERSONAL_CONDUCT_FIELDS,
    FormField("13_move_out_choice", "Move-out vs provide housing", source="tn.move_out_choice"),
    FormField(
        "18_wireless_numbers", "Wireless number(s) to transfer", source="tn.wireless_numbers"
    ),
    FormField("19_other_detail", "Other orders (general relief)", source="tn.other_relief"),
    # Ex parte (Temporary Order of Protection) request
    FormField(
        "ex_parte_tpo",
        "Request immediate Temporary Order of Protection (ex parte)",
        source="tn.ex_parte",
        needs_legal_review=True,
    ),
    # Verification (sworn before a notary)
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """TN resolver — adds the relief/sub-checklist membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto TN OP2018-1 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=TN_OP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
