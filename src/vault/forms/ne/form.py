"""Nebraska Petition and Affidavit to Obtain a Domestic Abuse Protection Order.

Maps Vault intake answers onto the Nebraska State Court **Petition and Affidavit
to Obtain Domestic Abuse Protection Order** (Form DC 19:8, Rev. 09/2025, Neb.
Rev. Stat. §§ 26-101 et seq.). The petition covers the parties, an interpreter
request, the relationship basis, the respondent identity/description block, prior
cases, the item-7 relief list, the abuse narrative, and the SA/Harassment
fallback request.

The packet is filed with companion forms: the **DC 19:1 Praecipe (Request for
Service)** carries the respondent's vehicle description, employer, and weapon
questions, and **DC 6:5.12** is a *confidential* SSN/gender/DOB sheet kept out of
the public file. This module maps the DC 19:8 petition plus the DC 19:1
respondent-service fields it shares intake with (prefixed `praecipe_`); the
confidential DC 6:5.12 is never assembled here.

The NE intake section (`vault.intake`, the `_ne_step` method plus the shared
interpreter / physical-description / vehicle blocks — NE is in all three) feeds
the NE-specific items. NE's relief list is its own, distinct from the other
states'.

Protection: item 2 offers several confidential-contact mechanisms (Confidential
Address Information form DC 3:03, the Secretary of State's Address Confidentiality
Program, safe-house residence). Intake only ever holds a safe mailing address, so
the confidential-address request defaults on and the home address is never
written. See coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "DC 19:8"
FORM_REVISION = "2025-09"  # Rev. 09/2025
JURISDICTION = "NE"


def _age_from_dob(dob_str: Any) -> int | None:
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    return today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))


def _petitioner_adult(answers: dict[str, Any]) -> str | None:
    """Item 1 — "I am 19 or older" (Nebraska's age of majority), from petitioner.dob."""
    age = _age_from_dob(answers.get("petitioner.dob"))
    if age is None:
        return None
    return "checked" if age >= 19 else None


def _filing_myself(_answers: dict[str, Any]) -> str:
    """Item 1 — petitioner files as a victim on their own behalf (the common case)."""
    return "checked"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Item 2 — keep contact information confidential (DC 3:03 / ACP / safe house)."""
    return "checked"


def _respondent_age(answers: dict[str, Any]) -> str | None:
    """Item 4 — the respondent's age, from respondent.dob."""
    age = _age_from_dob(answers.get("respondent.dob"))
    return None if age is None else str(age)


def _custody_to_petitioner(answers: dict[str, Any]) -> str | None:
    """Item 7 — temporary custody is requested to the petitioner."""
    name = answers.get("petitioner.legal_name")
    return name if isinstance(name, str) and name else None


def _additional_request(_answers: dict[str, Any]) -> str:
    """Item 9 — ask the court to treat this as an SA / Harassment order if it fits better."""
    return "checked"


# Item 7 — relief requested. Membership over `ne.relief`.
_NE_RELIEF = {
    "r_no_restraint": "no_restraint",  # no restraint upon the protected person(s)
    "r_no_abuse": "no_abuse",  # no harass/threaten/assault/disturb the peace
    "r_no_contact": "no_contact",  # no telephoning/contacting/communicating
    "r_exclude_residence": "exclude_residence",  # remove/exclude from a residence
    "r_stay_away": "stay_away",  # stay away from listed location(s)
    "r_no_firearm": "no_firearm",  # no possessing/purchasing a firearm
    "r_custody": "custody",  # temporary custody (up to 90 days)
    "r_pet_possession": "pet_possession",  # sole possession of household pets
    "r_pet_protection": "pet_protection",  # no contact/harm to household pets
    "r_other": "other",  # any other relief for safety/welfare
}

_MEMBERSHIP = {"ne.relief": _NE_RELIEF}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ne.relief", needs_legal_review=True)
    for item, key in _NE_RELIEF.items()
)

NE_DAPO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court_county", "County (District Court of)", source="ne.county", required=True),
    FormField("judge_type", "District or County Court judge requested", source="ne.judge_type"),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "additional_petitioners",
        "Additional petitioners / minor children",
        source="protected_persons.children[]",
        note="Names; the form's item-5 table wants each person's age and relationship to both "
        "parties — partial, NEG1.",
    ),
    # 1 — My request
    FormField("petitioner_adult", "Petitioner is 19 or older", derive=_petitioner_adult),
    FormField(
        "filing_myself",
        "Filing on own behalf as a victim",
        derive=_filing_myself,
        needs_legal_review=True,
        note="Defaults to the common case (self as victim); the file-for-others-only and "
        "mixed variants are not modeled — NEG2.",
    ),
    FormField(
        "petitioner_language",
        "Petitioner's language (does not speak English)",
        source="petitioner.interpreter_language",
    ),
    # 2 — Contact information
    FormField(
        "address_confidential",
        "Contact information kept confidential",
        derive=_address_confidential,
        note="Defaulted on — the survivor's home address is never collected; DC 3:03 / ACP / "
        "safe-house mechanisms apply.",
    ),
    # 3 — Relationship basis
    FormField(
        "relationship_basis",
        "Petitioner's relationship to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto NE's item-3 single-select (spouse / former "
        "spouse / child / parent of my children / living with / lived with / dating / dated / "
        "related). Attorney confirms.",
    ),
    # 4 — The respondent (identity + description, also on the DC 19:1 praecipe)
    FormField("respondent_age", "Respondent age", derive=_respondent_age),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField(
        "respondent_alias",
        "Other name the respondent goes by",
        source=None,
        note="Alias not collected — NEG3.",
    ),
    FormField(
        "respondent_address",
        "Respondent residence/mailing address",
        source="respondent.last_known_address",
    ),
    FormField("respondent_phone", "Respondent phone", source=None, note="Not collected — NEG3."),
    FormField(
        "respondent_sex",
        "Respondent sex",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eye", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField(
        "respondent_skin_tone", "Respondent skin tone", source=None, note="Not collected — NEG3."
    ),
    FormField(
        "respondent_dl", "Respondent driver's license", source=None, note="Not collected — NEG3."
    ),
    FormField(
        "respondent_place_of_birth",
        "Respondent place of birth",
        source=None,
        note="Not collected — NEG3.",
    ),
    FormField(
        "respondent_marks",
        "Respondent scars/marks/tattoos",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_other_features",
        "Respondent other distinguishing features",
        source=None,
        note="Not collected — NEG3.",
    ),
    # DC 19:1 Praecipe — service / vehicle / employer / weapon (companion form)
    FormField(
        "praecipe_employer", "Respondent employer (service)", source="respondent.employer_name"
    ),
    FormField(
        "praecipe_workdays_hours",
        "Respondent workdays/hours",
        source=None,
        note="Not collected (FL-only intake) — NEG4.",
    ),
    FormField(
        "praecipe_vehicle_make_model",
        "Respondent vehicle make/model",
        source="respondent.vehicle_make_model",
    ),
    FormField(
        "praecipe_vehicle_color", "Respondent vehicle color", source="respondent.vehicle_color"
    ),
    FormField(
        "praecipe_vehicle_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"
    ),
    FormField(
        "praecipe_weapon",
        "Respondent carries/keeps a weapon",
        source="firearm.respondent_has_access",
    ),
    # 6 — Prior case information
    FormField(
        "prior_cases",
        "Prior/current cases between the parties",
        source="prior_orders.exists",
        note="Protective-order existence only; the where/date/type/court/number list is collected "
        "as free text — NEG5.",
    ),
    FormField(
        "prior_cases_detail",
        "Prior cases (where / date / type / number)",
        source="ne.prior_cases_detail",
    ),
    # 7 — Relief + details
    *_RELIEF_FIELDS,
    FormField(
        "residence_address",
        "Residence to exclude the respondent from",
        source="ne.residence_address",
    ),
    FormField(
        "stay_away_location", "Location(s) to stay away from", source="ne.stay_away_location"
    ),
    FormField("custody_to", "Temporary custody granted to", derive=_custody_to_petitioner),
    FormField("custody_days", "Custody duration (days, up to 90)", source="ne.custody_days"),
    FormField("pet_possession_to", "Sole pet possession granted to", derive=_custody_to_petitioner),
    FormField("pet_detail", "Pets (name / species / description)", source="ne.pet_detail"),
    FormField("other_relief", "Other relief requested", source="ne.other_relief"),
    # 8 — Describe what happened
    FormField("incident_date", "Date of the incident(s)", source="incidents[].date"),
    FormField(
        "incident_narrative",
        "Description of the most recent / most severe abuse",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "past_incidents",
        "Additional incidents (B / C)",
        source=None,
        note="Not collected separately from the most-recent statement — NEG6.",
    ),
    # 9 — Additional request (SA / Harassment fallback)
    FormField(
        "additional_request",
        "Treat as SA / Harassment order if it fits better",
        derive=_additional_request,
        needs_legal_review=True,
        note="Standard Protection Orders Act fallback election — attorney confirms.",
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn under penalty of perjury; do NOT sign until a clerk or notary witnesses it.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NE resolver — adds the item-7 relief membership rule."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto NE Form DC 19:8 (+ DC 19:1 fields) — auditable map, never a PDF."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NE_DAPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
