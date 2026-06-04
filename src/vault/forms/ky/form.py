"""Kentucky Petition/Motion for Order of Protection form mapping.

Maps Vault intake answers onto Kentucky's **Petition/Motion for Order of
Protection** (AOC-275.1, KRS Chapter 403 / 456, FCRPP Part IV, Rev. 6-23; Court of
Justice). The petition covers the caption, the respondent identifier box (a full
physical description), the §2 relationship basis, the §3 children block, the abuse
narrative, the page-1 CAUTION flags, and the Motion-for-Relief checklist (emergency
ex parte / temporary order plus the specific restraints). KY's relationship and
relief lists are their own.

The KY intake section (`vault.intake`, the `_ky_step` method) plus the shared
physical-description gate feeds these items. AOC-275.1 HAS a respondent
physical-description box (Sex / Race / Birthdate / Height / Weight / Eyes / Hair),
so KY is in `PHYSICAL_DESCRIPTION_STATES`. It has **no respondent vehicle block**,
so KY is intentionally carved out of `VEHICLE_DESCRIPTION_STATES` (see the intake
comment), like the OK / TN / NH carve-outs.

Protection: the petition collects the petitioner's residence, but the served copy
is blacked out (page 3 of the form is the redacted respondent copy), so the
petitioner address maps to the safe mailing address, flagged `needs_legal_review`,
and the page-4 stay-away note that "any address information provided … will be
available to Respondent" is surfaced for the attorney. The box has a respondent
**Social Security #** field (the respondent's, not the petitioner's) — not
collected by intake, and KY requests support (temporary child support) but has no
*petitioner* SSN field, so KY is not in the SSN-for-support gate. See coverage.md.

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

FORM_ID = "AOC-275.1"
FORM_REVISION = "2023-06"  # Rev. 6-23
JURISDICTION = "KY"


# §2 — respondent's relationship to petitioner. Membership over
# `ky.relationship_basis`.
_KY_RELATIONSHIP = {
    "2_married": "married",
    "2_formerly_married": "formerly_married",
    "2_unmarried_child_in_common": "unmarried_child_in_common",
    "2_unmarried_living_together": "unmarried_living_together",
    "2_parent": "parent",
    "2_child": "child",
    "2_stepparent": "stepparent",
    "2_grandparent": "grandparent",
    "2_grandchild": "grandchild",
    "2_adult_sibling": "adult_sibling",
    "2_household_member_child_victim": "household_member_child_victim",
    "2_dating_relationship": "dating_relationship",
    "2_none_stalking": "none_stalking",
    "2_none_sexual_assault": "none_sexual_assault",
}

# Page 1 CAUTION flags. Membership over `ky.caution`.
_KY_CAUTION = {
    "caution_weapon_involved": "weapon_involved",
    "caution_armed_dangerous": "armed_dangerous",
}

# Motion for Relief — restraints requested. Membership over `ky.relief`.
_KY_RELIEF = {
    "relief_no_further_acts": "no_further_acts",
    "relief_no_contact": "no_contact",
    "relief_stay_away_distance": "stay_away_distance",
    "relief_no_damage_property": "no_damage_property",
    "relief_vacate_residence": "vacate_residence",
    "relief_temporary_custody": "temporary_custody",
    "relief_child_support": "child_support",
    "relief_possession_pets": "possession_pets",
    "relief_retrieve_belongings": "retrieve_belongings",
    "relief_other": "other",
}

_MEMBERSHIP = {
    "ky.relationship_basis": _KY_RELATIONSHIP,
    "ky.caution": _KY_CAUTION,
    "ky.relief": _KY_RELIEF,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="ky.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _KY_RELATIONSHIP.items()
)
_CAUTION_FIELDS = tuple(
    FormField(item, f"Caution: {key.replace('_', ' ')}", source="ky.caution")
    for item, key in _KY_CAUTION.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ky.relief", needs_legal_review=True)
    for item, key in _KY_RELIEF.items()
)

KY_OP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County", source="ky.county", required=True),
    FormField(
        "case_number",
        "Case number / court / division",
        source=None,
        note="Assigned by the clerk at filing — KYG1.",
    ),
    # Petitioner
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_address",
        "Petitioner residence",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Served copy is blacked out (page 3 redacted respondent copy); page-4 stay-away "
        "addresses are NOT confidential and are available to Respondent.",
    ),
    FormField(
        "petitioner_dob",
        "Petitioner birthdate (page 2)",
        source="petitioner.dob",
    ),
    # Respondent + identifier box
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Respondent current residence", source="respondent.last_known_address"
    ),
    FormField("respondent_sex", "Respondent sex", source="respondent.gender"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_dob", "Respondent birthdate", source="respondent.dob"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "respondent_features",
        "Respondent distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_ssn",
        "Respondent Social Security # / driver's license",
        source=None,
        note="The box wants the respondent's SSN / DL for LINK entry; not collected by "
        "intake — KYG2.",
    ),
    FormField("respondent_employer", "Respondent employer name", source="respondent.employer_name"),
    FormField(
        "respondent_employer_address",
        "Respondent employer address",
        source="respondent.employer_address",
    ),
    # Page-1 CAUTION flags
    *_CAUTION_FIELDS,
    FormField(
        "other_case",
        "Divorce / custody / visitation case between the parties",
        source="prior_orders.exists",
        note="Existence only; the form wants the case court — partial, KYG3.",
    ),
    # §2 — Relationship
    *_RELATIONSHIP_FIELDS,
    # Narrative
    FormField(
        "abuse_narrative",
        "Acts of domestic violence / dating violence / stalking / sexual assault",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the acts", source="incidents[].date"),
    FormField("abuse_county", "County where the acts occurred", source="incidents[].location"),
    # §3 — Children
    FormField(
        "children",
        "Minor children of the parties (§3)",
        source="protected_persons.children[]",
        note="Names; the form wants per-child birthdate / address / parent / seeking-protection "
        "— partial, KYG4.",
    ),
    # Motion for Relief
    FormField(
        "ex_parte",
        "Emergency / temporary protective order (immediate and present danger)",
        source="ky.ex_parte",
        needs_legal_review=True,
    ),
    *_RELIEF_FIELDS,
    FormField(
        "relief_stay_away_location",
        "Residence / school / employment to stay away from",
        source="ky.stay_away_location",
    ),
    FormField(
        "relief_vacate_address",
        "Shared residence the respondent must vacate",
        source="ky.vacate_address",
    ),
    FormField("relief_other_detail", "Other relief requested", source="ky.relief_other_detail"),
    FormField(
        "firearm_access",
        "Respondent has / can access firearms",
        source="firearm.respondent_has_access",
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Subscribed and sworn before the circuit clerk at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """KY resolver — adds the relationship / caution / relief membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto KY AOC-275.1 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=KY_OP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
