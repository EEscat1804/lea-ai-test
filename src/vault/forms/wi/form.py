"""Wisconsin Petition for TRO / Injunction (Domestic Abuse) form mapping.

Maps Vault intake answers onto Wisconsin Circuit Court **Form CV-402, _Petition
for Temporary Restraining Order and/or Petition and Motion for Injunction Hearing
(Domestic Abuse)_** (§ 813.12 Wis. Stats., Rev. 09/24). The petition covers the
parties (with respondent identifiers), the relationship basis, the weapons
caution, imminent danger, the abuse statement, other court cases, and the relief
requested — the TRO list (items 1a-f) mirrored as the injunction list (items
2a-f), plus injunction duration and items 4-7.

The WI intake section (`vault.intake`, the `jurisdiction == "WI"` block plus the
shared interpreter and physical-description blocks — WI is in those sets) feeds
the WI-specific items. WI's relief list is its own, distinct from the other
states'. The single intake relief selection populates both the TRO and the
injunction sub-lists, since the form's options are identical.

Protection: CV-402 has no petitioner-address field at all, so the survivor's
address cannot reach it. See coverage.md.

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

FORM_ID = "CV-402"
FORM_REVISION = "2024-09"  # Rev. 09/24
JURISDICTION = "WI"


def _schedule_injunction(_answers: dict[str, Any]) -> str:
    """Request 3 — if the TRO is denied, still schedule an injunction hearing."""
    return "checked"


def _petitioner_adult(_answers: dict[str, Any]) -> str:
    """Signature block — the adult petitioner is filing."""
    return "checked"


# TRO relief (request item 1, a-f) — membership over `wi.relief`.
_WI_TRO = {
    "tro_no_abuse": "no_abuse",
    "tro_avoid_residence": "avoid_residence",
    "tro_no_contact": "no_contact",
    "tro_no_pet_harm": "no_pet_harm",
    "tro_allow_pet_retrieval": "allow_pet_retrieval",
    "tro_other": "other",
}

# Injunction relief (request item 2, a-f) — also membership over `wi.relief`
# (the form's TRO and injunction options are identical).
_WI_INJ = {
    "inj_no_abuse": "no_abuse",
    "inj_avoid_residence": "avoid_residence",
    "inj_no_contact": "no_contact",
    "inj_no_pet_harm": "no_pet_harm",
    "inj_allow_pet_retrieval": "allow_pet_retrieval",
    "inj_other": "other",
}

# Items 4-7 add-on requests — membership over `wi.additional_requests`.
_WI_ADDITIONAL = {
    "add_wireless": "wireless_transfer",
    "add_10yr": "extended_10yr",
    "add_permanent": "permanent",
    "add_sheriff": "sheriff_assist",
}

_MEMBERSHIP = {
    "wi.relief": {**_WI_TRO, **_WI_INJ},
    "wi.additional_requests": _WI_ADDITIONAL,
}

_TRO_FIELDS = tuple(
    FormField(item, f"TRO: {key.replace('_', ' ')}", source="wi.relief", needs_legal_review=True)
    for item, key in _WI_TRO.items()
)
_INJ_FIELDS = tuple(
    FormField(
        item, f"Injunction: {key.replace('_', ' ')}", source="wi.relief", needs_legal_review=True
    )
    for item, key in _WI_INJ.items()
)
_ADDITIONAL_FIELDS = tuple(
    FormField(
        item,
        f"Request: {key.replace('_', ' ')}",
        source="wi.additional_requests",
        needs_legal_review=True,
    )
    for item, key in _WI_ADDITIONAL.items()
)

WI_CV402_FIELDS: tuple[FormField, ...] = (
    # Caption (no petitioner-address field on this form)
    FormField("county", "County", source="wi.county", required=True),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "interpreter", "Interpreter party / language", source="petitioner.interpreter_language"
    ),
    # Respondent description
    FormField(
        "respondent_sex",
        "Respondent sex",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField(
        "respondent_marks",
        "Respondent distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    # Relationship (top checklist + petition item 1, a-f)
    FormField(
        "relationship_basis",
        "Petitioner's relationship to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto WI's relationship checkboxes and "
        "the § 813.12 item-1 categories. Attorney confirms the box(es).",
    ),
    # CAUTION — weapons
    FormField(
        "weapon_access",
        "Respondent has access to weapon(s)",
        source="firearm.respondent_has_access",
    ),
    FormField("weapon_types", "Type of weapon(s)", source="firearm.types[]"),
    FormField("weapon_locations", "Location of weapon(s)", source="firearm.locations[]"),
    FormField(
        "weapon_involved", "Weapon involved in an incident", source="incidents[].weapon_involved"
    ),
    # Petition basis (items 2-3)
    FormField(
        "petition_not_married",
        "Petitioner not married to respondent (item 2a)",
        source=None,
        note="Legal determination — not inferred; WIG1.",
    ),
    FormField(
        "imminent_danger",
        "Petitioner is in imminent danger of physical harm (item 3)",
        source="wi.imminent_danger",
    ),
    # Statement of facts (item 4 / page 2)
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    FormField("abuse_location", "Location of the abuse", source="incidents[].location"),
    FormField(
        "abuse_narrative",
        "Statement of facts (domestic abuse)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    # Other court cases (item 5)
    FormField(
        "other_cases",
        "Other court cases addressing contact",
        source="prior_orders.exists",
        note="Protective-order existence only; case detail not collected — WIG2.",
    ),
    # Request item 1 — TRO relief (a-f)
    *_TRO_FIELDS,
    # Request item 2 — Injunction relief (a-f)
    *_INJ_FIELDS,
    FormField("relief_other_detail", "Other relief detail", source="wi.relief_other"),
    # Request item 3 — schedule injunction hearing if TRO denied
    FormField(
        "schedule_injunction_if_denied",
        "Schedule injunction hearing if TRO denied",
        derive=_schedule_injunction,
    ),
    # Request item 4 — injunction duration + items 4-7 add-ons
    FormField(
        "injunction_duration",
        "Injunction duration (default four years)",
        source="wi.injunction_duration",
    ),
    *_ADDITIONAL_FIELDS,
    # Signature
    FormField("petitioner_is_adult", "Filing as the adult petitioner", derive=_petitioner_adult),
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Declared under penalty of false swearing — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """WI resolver — adds the relief and additional-request membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto WI CV-402 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=WI_CV402_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
