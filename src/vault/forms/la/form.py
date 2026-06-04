"""Louisiana Petition for Protection from Abuse form mapping.

Maps Vault intake answers onto Louisiana's **Petition for Protection from Abuse**
(Uniform Abuse Prevention Order form LPOR B, La. R.S. 46:2131 et seq. / 46:2151,
v.15.1). The petition covers the caption, the §1 protected persons, the §2
confidential-address election, the §3 interpreter/criminal-history requests, the
§4 defendant address, the §5 venue basis, the §6 relationship basis, the §8 abuse
manner and danger indicators, the §8c narrative, the §9 ex parte TRO relief (items
a-m), and the §10 other (rule-to-show-cause) requests. LA's relationship, venue,
abuse, and relief lists are their own.

The LA intake section (`vault.intake`, the `_la_step` method) plus the shared
interpreter and employer gates feeds these items. LPOR B has **no respondent
physical-description block and no respondent vehicle block**, so LA is carved out
of `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES` (see the intake
comments). LPOR B HAS an interpreter request (§3a), so LA IS in the interpreter
gate.

Protection: LA offers a real confidential-address mechanism — §2a, "Petitioner
requests that his/her address … remain confidential … pursuant to La. R.S.
46:2134(B)" (a separate Confidential Address Form). Intake only ever holds a safe
mailing address, so `address_confidential` is derived `"checked"` and the
petitioner address maps to the safe mailing address. The form requests support
(§10 child / spousal support) but has no petitioner SSN field, so LA is not in the
SSN-for-support gate. See coverage.md.

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

FORM_ID = "LPOR B"
FORM_REVISION = "15.1"  # form version v.15.1; no calendar date printed, LAG1
JURISDICTION = "LA"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """§2a — petitioner files the address confidentially (La. R.S. 46:2134(B)).

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms the Confidential Address Form is filed.
    """
    return "checked"


# §6a — protected person's relationship to the defendant. Membership over
# `la.relationship_basis`.
_LA_RELATIONSHIP = {
    "6_spouse": "spouse",
    "6_dating_partner": "dating_partner",
    "6_intimate_cohabitant": "intimate_cohabitant",
    "6_parent_stepparent_foster": "parent_stepparent_foster",
    "6_child_stepchild_foster": "child_stepchild_foster",
    "6_grandparent_ascendant": "grandparent_ascendant",
    "6_child_of_partner": "child_of_partner",
    "6_grandchild_descendant": "grandchild_descendant",
    "6_child_living_with": "child_living_with",
}

# §5 — venue basis. Membership over `la.venue`.
_LA_VENUE = {
    "5_marital_domicile": "marital_domicile",
    "5_household": "household",
    "5_defendant_resides": "defendant_resides",
    "5_abuse_occurred": "abuse_occurred",
    "5_protected_resides": "protected_resides",
}

# §8a — manner of abuse. Membership over `la.abuse_types`.
_LA_ABUSE_TYPES = {
    "8a_slapped": "slapped",
    "8a_punched": "punched",
    "8a_choked": "choked",
    "8a_shoved": "shoved",
    "8a_kicked": "kicked",
    "8a_stalked": "stalked",
    "8a_abused_pregnant": "abused_pregnant",
    "8a_threatened_bodily_harm": "threatened_bodily_harm",
    "8a_threatened_life": "threatened_life",
    "8a_threatened_weapon": "threatened_weapon",
    "8a_sexually_abused": "sexually_abused",
    "8a_abused_children": "abused_children",
    "8a_abused_pets": "abused_pets",
    "8a_other": "other",
}

# §8b — other danger indicators. Membership over `la.danger_indicators`.
_LA_DANGER = {
    "8b_more_often": "more_often",
    "8b_more_severe": "more_severe",
    "8b_left_past_year": "left_past_year",
    "8b_owns_firearms": "owns_firearms",
    "8b_suicide": "suicide",
}

# §9 — ex parte TRO relief (items a-m). Membership over `la.relief`.
_LA_RELIEF = {
    "9a_no_abuse": "no_abuse",
    "9b_no_contact": "no_contact",
    "9c_stay_away_residence": "stay_away_residence",
    "9d_stay_away_work_school": "stay_away_work_school",
    "9e_no_damage_property": "no_damage_property",
    "9f_use_residence": "use_residence",
    "9g_possession_property": "possession_property",
    "9h_no_transfer_property": "no_transfer_property",
    "9i_retrieve_belongings": "retrieve_belongings",
    "9j_sheriff_accompany": "sheriff_accompany",
    "9k_temporary_custody": "temporary_custody",
    "9l_sheriff_custody": "sheriff_custody",
    "9m_no_interfere_custody": "no_interfere_custody",
}

# §10 — other (rule-to-show-cause) requests. Membership over `la.other_requests`.
_LA_OTHER = {
    "10_child_support": "child_support",
    "10_spousal_support": "spousal_support",
    "10_counseling": "counseling",
    "10_evaluation": "evaluation",
    "10_court_costs": "court_costs",
    "10_attorney_fees": "attorney_fees",
    "10_evaluation_fees": "evaluation_fees",
    "10_expert_fees": "expert_fees",
    "10_medical_care": "medical_care",
    "10_vacate": "vacate",
    "10_other": "other",
}

_MEMBERSHIP = {
    "la.relationship_basis": _LA_RELATIONSHIP,
    "la.venue": _LA_VENUE,
    "la.abuse_types": _LA_ABUSE_TYPES,
    "la.danger_indicators": _LA_DANGER,
    "la.relief": _LA_RELIEF,
    "la.other_requests": _LA_OTHER,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="la.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _LA_RELATIONSHIP.items()
)
_VENUE_FIELDS = tuple(
    FormField(item, f"Venue: {key.replace('_', ' ')}", source="la.venue", needs_legal_review=True)
    for item, key in _LA_VENUE.items()
)
_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="la.abuse_types", needs_legal_review=True
    )
    for item, key in _LA_ABUSE_TYPES.items()
)
_DANGER_FIELDS = tuple(
    FormField(item, f"Danger: {key.replace('_', ' ')}", source="la.danger_indicators")
    for item, key in _LA_DANGER.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="la.relief", needs_legal_review=True)
    for item, key in _LA_RELIEF.items()
)
_OTHER_FIELDS = tuple(
    FormField(
        item,
        f"Other request: {key.replace('_', ' ')}",
        source="la.other_requests",
        needs_legal_review=True,
    )
    for item, key in _LA_OTHER.items()
)

LA_PFA_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("court", "Court", source="la.court"),
    FormField("parish", "Parish / city", source="la.parish", required=True),
    FormField(
        "division_number",
        "Division / number",
        source=None,
        note="Assigned by the clerk at filing — LAG2.",
    ),
    # §1 — Protected persons
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "protected_children",
        "Minor child(ren) protected (§1b)",
        source="protected_persons.children[]",
        note="Names; the form wants name / DOB / relationship per child — partial, LAG3.",
    ),
    # §2 — Address (confidential)
    FormField(
        "address_confidential",
        "Confidential address requested (§2a, La. R.S. 46:2134(B))",
        derive=_address_confidential,
        needs_legal_review=True,
        note="Louisiana's Confidential Address Form; attorney/advocate confirms it is filed.",
    ),
    FormField(
        "petitioner_address",
        "Petitioner current address (§2b)",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; the residential address is withheld via §2a.",
    ),
    # §3 — Special requests
    FormField(
        "interpreter_language",
        "Interpreter requested (§3a) — language",
        source="petitioner.interpreter_language",
    ),
    # §4 — Defendant
    FormField("respondent", "Defendant name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Defendant address (§4)", source="respondent.last_known_address"
    ),
    FormField(
        "respondent_employer", "Defendant employer (service)", source="respondent.employer_name"
    ),
    FormField(
        "respondent_employer_address",
        "Defendant work address (service)",
        source="respondent.employer_address",
    ),
    # §5 — Venue
    *_VENUE_FIELDS,
    # §6 — Relationship
    *_RELATIONSHIP_FIELDS,
    FormField(
        "children_in_common",
        "Protected person(s) and defendant have children in common (§6b)",
        source="relationship.children_in_common",
    ),
    # §8 — Abuse manner + danger indicators
    *_ABUSE_FIELDS,
    *_DANGER_FIELDS,
    # §8c — Narrative
    FormField(
        "abuse_narrative",
        "Facts and circumstances of the abuse (§8c)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the most recent incident", source="incidents[].date"),
    # §9 — Ex parte TRO relief
    *_RELIEF_FIELDS,
    FormField(
        "9c_residence_address",
        "Residence the defendant must stay away from (item c)",
        source="la.residence_address",
    ),
    FormField(
        "9f_use_residence_address",
        "Residence granted to the petitioner (item f)",
        source="la.use_residence_address",
    ),
    FormField(
        "9g_property_detail",
        "Property / pets to grant the petitioner (item g)",
        source="la.property_detail",
    ),
    # §10 — Other requests
    *_OTHER_FIELDS,
    FormField("10_other_detail", "Other relief requested (§10 other)", source="la.other_detail"),
    # §7 — Related legal action
    FormField(
        "related_action",
        "Pending divorce / custody action (§7)",
        source="prior_orders.exists",
        note="Existence only; the Addendum suit-name / number / court detail is not "
        "collected — LAG4.",
    ),
    # Affirmation
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Affirmed before a witness under penalty of perjury (R.S. 14:123) at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """LA resolver — adds the §5/§6/§8/§9/§10 membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto LA LPOR B (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=LA_PFA_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
