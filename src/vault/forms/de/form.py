"""Delaware Petition for Order of Protection from Abuse form mapping.

Maps Vault intake answers onto Delaware Family Court **Form 450, _Petition for
Order of Protection from Abuse_** (10 Del. C. § 1041 et seq., Rev. 3/26). The
petition covers the parties, a confidential-address request, the § 1041
relationship basis, an a-k acts-of-abuse checklist, the court's jurisdiction
over a non-resident respondent, firearms, and a PROTECTIVE + ANCILLARY relief
list.

The DE intake section (`vault.intake`, the `jurisdiction == "DE"` block) feeds
the DE-specific items. DE's abuse and relief lists are its own.

Protection: the form says not to list an address if a confidential address is
requested — intake only ever holds a safe mailing address, and the
confidential-address boxes default on. See coverage.md.

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

FORM_ID = "Form 450"
FORM_REVISION = "2026-03"  # Rev 3/26
JURISDICTION = "DE"


def _confidential_residence(_answers: dict[str, Any]) -> str:
    """Item 1 — keep the residence/school/employment address confidential.

    Defaulted on: the survivor's home address is never collected, so the form's
    "DO NOT LIST ADDRESS" instruction is honored and confidentiality requested.
    """
    return "checked"


def _confidential_children(answers: dict[str, Any]) -> str | None:
    """Item 1 — keep the children's address confidential, when there are children."""
    children = answers.get("protected_persons.children[]")
    if isinstance(children, str) and children.strip().lower() not in ("", "none"):
        return "checked"
    return None


# Acts-of-abuse checklist (item 3, a-k) — membership over `de.abuse_acts`.
_DE_ABUSE = {
    "ab_physical_injury": "physical_injury",  # a
    "ab_fear_of_injury": "fear_of_injury",  # b
    "ab_property_damage": "property_damage",  # c
    "ab_alarming_conduct": "alarming_conduct",  # d
    "ab_trespassing": "trespassing",  # e
    "ab_child_abuse": "child_abuse",  # f
    "ab_unlawful_imprisonment": "unlawful_imprisonment",  # g
    "ab_financial_dependency": "financial_dependency",  # h
    "ab_other_threatening": "other_threatening",  # i
    "ab_animal_cruelty": "animal_cruelty",  # j
    "ab_human_trafficking": "human_trafficking",  # k
}

# Relief requested (PROTECTIVE + ANCILLARY) — membership over `de.relief`.
_DE_RELIEF = {
    "r_no_abuse": "no_abuse",
    "r_stay_away": "stay_away",
    "r_no_contact": "no_contact",
    "r_exclusive_residence": "exclusive_residence",
    "r_compensation": "compensation",
    "r_custody": "custody",
    "r_child_support": "child_support",
    "r_spousal_support": "spousal_support",
    "r_reimburse_expenses": "reimburse_expenses",
    "r_personal_property": "personal_property",
    "r_companion_animal": "companion_animal",
    "r_return_documents": "return_documents",
    "r_dv_evaluation": "dv_evaluation",
    "r_other": "other",
}

# Stay-away sub-checkboxes — membership over `de.stay_away_places`.
_DE_STAY_AWAY = {
    "sa_petitioner": "petitioner",
    "sa_home": "home",
    "sa_workplace": "workplace",
    "sa_other": "other",
}

# Aggravating factors (1-6) for relief longer than two years (§ 1045(f)) —
# membership over `de.aggravating_factors`.
_DE_AGGRAVATING = {
    "ag_physical_injury": "physical_injury_caused",  # 1
    "ag_deadly_weapon": "deadly_weapon",  # 2
    "ag_repeated_violations": "repeated_violations",  # 3
    "ag_prior_convictions": "prior_convictions",  # 4
    "ag_family_exposure": "family_exposure",  # 5
    "ag_ongoing_danger": "ongoing_danger",  # 6
}

_MEMBERSHIP = {
    "de.abuse_acts": _DE_ABUSE,
    "de.relief": _DE_RELIEF,
    "de.stay_away_places": _DE_STAY_AWAY,
    "de.aggravating_factors": _DE_AGGRAVATING,
}

_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="de.abuse_acts", needs_legal_review=True
    )
    for item, key in _DE_ABUSE.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="de.stay_away_places")
    for item, key in _DE_STAY_AWAY.items()
)
_AGGRAVATING_FIELDS = tuple(
    FormField(
        item,
        f"Aggravating factor: {key.replace('_', ' ')}",
        source="de.aggravating_factors",
        needs_legal_review=True,
    )
    for item, key in _DE_AGGRAVATING.items()
)

DE_FORM450_FIELDS: tuple[FormField, ...] = (
    # Caption / county (New Castle / Kent / Sussex)
    FormField("county", "County", source="de.county", required=True),
    # Petitioner — the home address is never listed (confidential); only the safe
    # mailing address reaches the form.
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField("petitioner_phone", "Petitioner telephone", source="petitioner.safe_phone"),
    FormField("petitioner_email", "Petitioner email", source="petitioner.safe_email"),
    FormField(
        "petitioner_mailing",
        "Petitioner safe mailing address (PO box / advocate)",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — the survivor's home address is never "
        "collected, so it is never listed (form item 1).",
    ),
    FormField(
        "petitioner_interpreter",
        "Petitioner interpreter / language",
        source="petitioner.interpreter_language",
    ),
    # Respondent
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "respondent_phone",
        "Respondent telephone",
        source=None,
        note="Not collected by intake — DEG1.",
    ),
    FormField(
        "respondent_email", "Respondent email", source=None, note="Not collected by intake — DEG1."
    ),
    # Children table
    FormField(
        "children",
        "Child(ren)",
        source="protected_persons.children[]",
        note="Names; form wants each child's DOB, whether the respondent's child, and "
        "the petitioner's relationship to the child — partial, DEG2.",
    ),
    # 1 — Confidential-address request (protection-minded default)
    FormField(
        "conf_residence",
        "Keep residence/school/employment address confidential",
        derive=_confidential_residence,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "conf_children",
        "Keep children's residence/school/childcare confidential",
        derive=_confidential_children,
        note="Defaulted on when children are present.",
    ),
    # 2 — Relationship basis (choose one)
    FormField(
        "relationship_basis",
        "Relationship of petitioner to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto DE's item-2 categories (spouse / "
        "living together / child in common / custodian / substantive dating "
        "relationship / family member). Attorney confirms the box — especially "
        "'substantive dating relationship' and 'family member'.",
    ),
    # 3 — Acts of abuse (a-k) + the survivor's statement
    *_ABUSE_FIELDS,
    FormField("abuse_date", "Date(s) of abuse", source="incidents[].date", required=True),
    FormField("abuse_location", "Where the abuse occurred", source="incidents[].location"),
    FormField(
        "abuse_narrative",
        "Description of the acts of abuse",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_injury", "Injury", source="incidents[].injury"),
    FormField("abuse_witnesses", "Witnesses present", source="incidents[].witnesses_present"),
    FormField("abuse_weapon", "Weapon used/threatened", source="incidents[].weapon_involved"),
    # 4 — Delaware jurisdiction over the respondent
    FormField(
        "respondent_de_resident",
        "Respondent is a Delaware resident",
        source="de.respondent_is_de_resident",
    ),
    FormField(
        "de_connection",
        "Connection to Delaware (if respondent is a non-resident)",
        source="de.de_connection",
    ),
    # 5 — Firearms
    FormField(
        "firearms_access", "Respondent possesses firearm(s)", source="firearm.respondent_has_access"
    ),
    FormField("firearms_describe", "Describe each firearm", source="firearm.types[]"),
    FormField("firearms_location", "Location of each firearm", source="firearm.locations[]"),
    # PROTECTIVE RELIEF
    FormField(
        "r_no_abuse", "Prohibit any act of abuse", source="de.relief", needs_legal_review=True
    ),
    FormField("r_stay_away", "Stay-away order", source="de.relief", needs_legal_review=True),
    *_STAY_AWAY_FIELDS,
    FormField("sa_other_detail", "Other stay-away place", source="de.stay_away_other"),
    FormField(
        "r_no_contact", "No contact by any means", source="de.relief", needs_legal_review=True
    ),
    FormField(
        "r_extended_duration",
        "Request protective relief longer than two years",
        source="de.extended_duration",
        note="Default DE protective relief is up to two years (10 Del. C. § 1045(f)).",
    ),
    *_AGGRAVATING_FIELDS,
    # ANCILLARY RELIEF (limited to one year)
    FormField(
        "r_exclusive_residence",
        "Exclusive use/possession of the residence",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField("r_exclusive_residence_address", "Residence address", source="de.residence_address"),
    FormField(
        "r_compensation", "Compensation for losses", source="de.relief", needs_legal_review=True
    ),
    FormField("r_compensation_losses", "Losses to compensate", source="de.compensation_losses"),
    FormField(
        "r_custody",
        "Temporary custody/residency of the children",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_custody_children",
        "Children for custody",
        source="protected_persons.children[]",
        note="Form 346 (Custody Separate Statement) is also required when custody is sought.",
    ),
    FormField(
        "r_child_support", "Temporary child support", source="de.relief", needs_legal_review=True
    ),
    FormField(
        "r_child_support_employer",
        "Respondent employer (for support)",
        source="respondent.employer_name",
    ),
    FormField(
        "r_child_support_employer_location",
        "Respondent employer location",
        source="respondent.employer_address",
    ),
    FormField(
        "r_child_support_income",
        "Respondent income",
        source=None,
        note="Not collected by intake — DEG3.",
    ),
    FormField(
        "r_child_support_occupation",
        "Respondent occupation",
        source=None,
        note="Not collected by intake — DEG3.",
    ),
    FormField(
        "r_spousal_support",
        "Support for the petitioner",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_spousal_support_amount",
        "Support amount",
        source=None,
        note="Not collected by intake — DEG3.",
    ),
    FormField(
        "r_reimburse_expenses",
        "Reimburse expenses/fees/costs",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField("r_reimburse_detail", "Expenses to reimburse", source="de.reimburse_expenses"),
    FormField(
        "r_personal_property",
        "Temporary possession of personal property",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField("r_personal_property_detail", "Personal property", source="de.personal_property"),
    FormField(
        "r_companion_animal",
        "Care/custody of a companion animal",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField("r_companion_animal_detail", "Companion animal", source="de.companion_animal"),
    FormField(
        "r_return_documents",
        "Return legal/financial documents",
        source="de.relief",
        needs_legal_review=True,
    ),
    FormField("r_return_documents_detail", "Documents to return", source="de.return_documents"),
    FormField(
        "r_dv_evaluation", "DV treatment evaluation", source="de.relief", needs_legal_review=True
    ),
    FormField("r_other", "Other relief", source="de.relief", needs_legal_review=True),
    FormField("r_other_detail", "Other relief detail", source="de.other_relief"),
    # Verification / signature — sworn before a Clerk of Court / Notary at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Verification sworn before the Clerk of Court / Notary — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """DE resolver — adds the abuse/relief/stay-away/aggravating membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto DE Form 450 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=DE_FORM450_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
