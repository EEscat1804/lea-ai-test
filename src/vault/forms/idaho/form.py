"""Idaho Sworn Petition for Protection Order form mapping.

Maps Vault intake answers onto Idaho's **Sworn Petition for Protection Order**
(CAO DV 1-1, I.C. § 39-6304 (domestic violence) / § 18-7907 (stalking & threats),
07/01/2019; District Court, Magistrate Division). The petition covers the parties,
the §1 protected persons, the §2 relationship basis, the §3 residence/living
situation, the §4 children, the §5 other court cases, the §6 petition type
(domestic violence / stalking / telephone threats / protected-class threats), the
narrative, and the §7 relief (personal-conduct / stay-away / move-out / custody /
counseling / other). ID's relationship, petition-type, and relief lists are their
own.

⚠️ Package name: the two-letter code "ID" shadows the Python builtin `id`, so the
package directory is `idaho` (not `id`); the jurisdiction code stays "ID". This
mirrors the `oregon` keyword-collision precedent.

The ID intake section (`vault.intake`, the `_id_step` method) plus the shared
employer gate feeds these items. Form CAO DV 1-1 has **no respondent
physical-description block and no respondent vehicle block**, so ID is carved out
of `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES` (see the intake
comments).

Protection: the form offers a real confidential mechanism — the header checkbox
"No address, email and telephone are given because I do not want my information on
this petition", echoed in the §7b stay-away block. Intake only ever holds a safe
mailing address, so `address_confidential` is derived `"checked"` and the
petitioner address maps to the safe mailing address. See coverage.md.

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

FORM_ID = "CAO DV 1-1"
FORM_REVISION = "2019-07"  # 07/01/2019
JURISDICTION = "ID"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Header / §7b — petitioner withholds their address from the petition.

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms it.
    """
    return "checked"


def _personal_conduct(_answers: dict[str, Any]) -> str:
    """§7a — the personal-conduct (no-contact) order is the form's default ask."""
    return "checked"


# §2 — relationship to the respondent. Membership over `id.relationship_basis`.
_ID_RELATIONSHIP = {
    "2_spouse": "spouse",
    "2_former_spouse": "former_spouse",
    "2_residing_together": "residing_together",
    "2_previously_resided": "previously_resided",
    "2_child_in_common": "child_in_common",
    "2_intimate_partner": "intimate_partner",
    "2_parent": "parent",
    "2_related": "related",
    "2_dating": "dating",
    "2_previously_dated": "previously_dated",
    "2_other": "other",
}

# §6 — what the protection order is for. Membership over `id.petition_type`.
_ID_PETITION_TYPE = {
    "6_domestic_violence": "domestic_violence",
    "6_stalking": "stalking",
    "6_telephone_threats": "telephone_threats",
    "6_protected_class_threats": "protected_class_threats",
}

# §7 — relief requested. Membership over `id.relief`. (§7a personal conduct is the
# default ask, mapped separately.)
_ID_RELIEF = {
    "7b_stay_away": "stay_away",
    "7c_move_out": "move_out",
    "7d_child_custody": "child_custody",
    "7e_treatment_counseling": "treatment_counseling",
    "7f_other": "other",
}

# §7b — places the respondent must stay away from. Membership over
# `id.stay_away_places`.
_ID_STAY_AWAY = {
    "7b_my_residence": "my_residence",
    "7b_minor_residence": "minor_residence",
    "7b_my_workplace_school": "my_workplace_school",
    "7b_minor_workplace_school": "minor_workplace_school",
    "7b_childrens_school_childcare": "childrens_school_childcare",
    "7b_other": "other",
}

_MEMBERSHIP = {
    "id.relationship_basis": _ID_RELATIONSHIP,
    "id.petition_type": _ID_PETITION_TYPE,
    "id.relief": _ID_RELIEF,
    "id.stay_away_places": _ID_STAY_AWAY,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="id.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _ID_RELATIONSHIP.items()
)
_PETITION_TYPE_FIELDS = tuple(
    FormField(
        item,
        f"Petition type: {key.replace('_', ' ')}",
        source="id.petition_type",
        needs_legal_review=True,
    )
    for item, key in _ID_PETITION_TYPE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="id.relief", needs_legal_review=True)
    for item, key in _ID_RELIEF.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="id.stay_away_places")
    for item, key in _ID_STAY_AWAY.items()
)

ID_PO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "county", "County (district court, magistrate division)", source="id.county", required=True
    ),
    FormField(
        "case_number",
        "Case number",
        source=None,
        note="Assigned by the clerk at filing — IDG1.",
    ),
    # Parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "address_confidential",
        "Address withheld (header / §7b 'do not want my information on this petition')",
        derive=_address_confidential,
        needs_legal_review=True,
        note="Header checkbox to keep the petitioner's address/email/phone off the petition.",
    ),
    FormField(
        "petitioner_address",
        "Petitioner mailing address",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; the residential address is withheld.",
    ),
    FormField("petitioner_phone", "Petitioner telephone", source="petitioner.safe_phone"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_residence",
        "Respondent residence (county / state)",
        source="respondent.last_known_address",
    ),
    FormField("respondent_employer", "Respondent employer", source="respondent.employer_name"),
    FormField(
        "respondent_employer_address",
        "Respondent work address",
        source="respondent.employer_address",
    ),
    # §1 — Protected persons
    FormField(
        "protected_children",
        "Protected minor child/ren (§1)",
        source="protected_persons.children[]",
        note="Names; the §4 children table wants per-child DOB / sex / relationship / "
        "residence — partial, IDG2.",
    ),
    # §2 — Relationship
    *_RELATIONSHIP_FIELDS,
    # §6 — Petition type
    *_PETITION_TYPE_FIELDS,
    # narrative (§6 description + §5 incidents)
    FormField(
        "abuse_narrative",
        "Most recent acts / threats by the respondent",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "When the most recent act occurred", source="incidents[].date"),
    FormField(
        "abuse_location", "Where it occurred / where you were", source="incidents[].location"
    ),
    FormField("abuse_witnesses", "Who was present", source="incidents[].witnesses_present"),
    FormField("abuse_weapon", "Was a weapon involved", source="incidents[].weapon_involved"),
    FormField("abuse_injury", "Injuries described", source="incidents[].injury"),
    FormField(
        "past_abuse",
        "Past acts or threats",
        source=None,
        note="Not collected separately from the most-recent statement — IDG3.",
    ),
    # §5 — Other court cases
    FormField(
        "other_cases",
        "Other court cases / prior protection orders (§5)",
        source="prior_orders.exists",
        note="Existence only; the form wants county / date / parties — partial, IDG4.",
    ),
    FormField("other_cases_detail", "Other cases (free text)", source="id.other_cases"),
    # §7 — Relief
    FormField(
        "7a_personal_conduct",
        "Personal Conduct Order (no contact / no abuse)",
        derive=_personal_conduct,
        needs_legal_review=True,
        note="The form's default no-contact / no-abuse order.",
    ),
    *_RELIEF_FIELDS,
    FormField(
        "7b_stay_away_feet",
        "Stay-away distance note (§7b ii, 1,500 ft)",
        source="id.stay_away_feet",
    ),
    *_STAY_AWAY_FIELDS,
    FormField(
        "7c_move_out_address",
        "Residence the respondent must move from (§7c)",
        source="id.move_out_address",
    ),
    FormField(
        "7e_counseling_detail",
        "Treatment / counseling purpose (§7e)",
        source="id.counseling_detail",
    ),
    FormField("7f_other_detail", "Other relief requested (§7f)", source="id.relief_other_detail"),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Certified under penalty of perjury at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """ID resolver — adds the relationship / petition-type / relief / stay-away rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto ID CAO DV 1-1 (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=ID_PO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
