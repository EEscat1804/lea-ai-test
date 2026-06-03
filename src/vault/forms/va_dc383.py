"""Virginia DC-383 form mapping.

Maps Vault intake answers onto Virginia form **DC-383, _Petition for Protective
Order_** (Va. Code §§ 19.2-152.9, 19.2-152.10, Rev. 07/24). DC-383 is a shorter
form than CA's or WA's: one petitioner-fillable page (parties, a respondent
description box, the act-of-violence statement, and a short list of requested
conditions), then court-filled summons/service pages.

The VA intake section (`vault.intake`, the `jurisdiction == "VA"` block) plus
the shared physical-description block feed the VA-specific items.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings. See DC-383_coverage.md.

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

FORM_ID = "DC-383"
FORM_REVISION = "2024-07"
JURISDICTION = "VA"

# DC-383 requested conditions. Intake collects the survivor's choices as the
# `va.conditions` list; each box is checked by membership. (item, condition key.)
_VA_CONDITION_ITEMS = {
    "cond_violence": "no_violence",
    "cond_contact": "no_contact",
    "cond_contact_family": "no_contact_family",
    "cond_animal": "companion_animal",
    "cond_other": "other_conditions",
}

VA_DC383_FIELDS: tuple[FormField, ...] = (
    # Parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address/location",
              source="respondent.last_known_address"),
    FormField("respondent_phone", "Respondent telephone", source=None,
              note="Intake does not collect respondent phone — VG1."),

    # Respondent's description (if known)
    FormField("desc_race", "Respondent race", source="respondent.race"),
    FormField("desc_sex", "Respondent sex", source="respondent.gender"),
    FormField("desc_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("desc_height", "Respondent height", source="respondent.height"),
    FormField("desc_weight", "Respondent weight", source="respondent.weight"),
    FormField("desc_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("desc_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField("desc_ssn", "Respondent SSN", source=None, note="Not collected — VG1."),
    FormField("desc_dl", "Respondent driver's license", source=None, note="Not collected — VG1."),

    # Allegations
    FormField("1", "Warrant/petition for criminal offense issued", source=None,
              note="Criminal-case fact; not collected — VG2 (optional)."),
    FormField("2", "Act of violence, force, or threat (statement)", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),
    FormField("3", "Cohabited as intimate partners >12 months ago", source=None,
              needs_legal_review=True,
              note="Narrow VA eligibility checkbox; not collected — VG3."),
    FormField("4", "Protective order currently in effect", source="prior_orders.exists",
              note="Existence vs 'currently in effect' — confirm."),
    FormField("5", "Respondent owns/possesses firearms", source="firearm.respondent_has_access"),

    # Requested: preliminary order + conditions
    FormField("preliminary_order", "Preliminary protective order requested",
              source="va.preliminary_order", needs_legal_review=True),
    FormField("cond_violence", "Prohibit acts of violence/force/threat", source="va.conditions",
              needs_legal_review=True),
    FormField("cond_contact", "Prohibit other contact with petitioner", source="va.conditions",
              needs_legal_review=True),
    FormField("cond_contact_family", "Prohibit contact with family/household",
              source="va.conditions", needs_legal_review=True),
    FormField("cond_family_names", "Family/household members named",
              source="protected_persons.children[]",
              note="Names; DC-621 addendum wants DOB/gender/race per member — partial."),
    FormField("cond_animal", "Possession of companion animal", source="va.conditions",
              needs_legal_review=True),
    FormField("cond_animal_desc", "Companion animal description", source="va.companion_animal"),
    FormField("cond_other", "Such other conditions", source="va.conditions",
              needs_legal_review=True),
    FormField("cond_other_text", "Other conditions detail", source="va.other_conditions"),

    # Signature
    FormField("sig_petitioner", "Petitioner signature (printed name)",
              source="petitioner.legal_name", required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """VA resolver — adds the conditions-checkbox rule, else the basic lookup."""
    if f.source == "va.conditions" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _VA_CONDITION_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto VA DC-383 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=VA_DC383_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
