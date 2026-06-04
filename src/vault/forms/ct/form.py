"""Connecticut Application for Relief from Abuse form mapping.

Maps Vault intake answers onto Connecticut Judicial Branch form **JD-FM-137,
_Application for Relief from Abuse_** (C.G.S. §§ 46b-15 et al., Rev. 10-21). The
application covers the parties (with a respondent description), the relationship
basis, an attached affidavit of the abuse, CT's coded relief conditions, custody
and visitation, and ex parte relief.

The CT intake section (`vault.intake`, the `jurisdiction == "CT"` block plus the
shared physical-description block — CT is a physical-description state) feeds the
CT-specific items. CT's relief list (the CT## condition codes) is its own,
distinct from the other states'.

Protection: the form warns that any address given is provided to the respondent
and suggests a separate mailing address / Safe at Home. Intake only ever holds a
safe mailing address; the home and work addresses are never collected. See
coverage.md.

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

FORM_ID = "JD-FM-137"
FORM_REVISION = "2021-10"  # Rev. 10-21
JURISDICTION = "CT"


def _with_visitation(answers: dict[str, Any]) -> str | None:
    """CT21 — visitation on the applicant's terms."""
    return "checked" if answers.get("ct.visitation") == "with_visitation" else None


def _without_visitation(answers: dict[str, Any]) -> str | None:
    """CT22 — no visitation rights to the respondent."""
    return "checked" if answers.get("ct.visitation") == "without_visitation" else None


# Relief conditions (item 1) + custody (item 2 / CT20) + further order (item 3) —
# membership over `ct.relief`. The item keys mirror the form's own CT## codes so
# the output is auditable box-by-box.
_CT_RELIEF = {
    "CT01": "no_abuse",
    "CT03": "stay_away_home",
    "CT05": "no_contact",
    "CT14": "respondent_retrieve_belongings",
    "CT15": "applicant_retrieve_belongings",
    "CT16": "stay_100_yards",
    "CT19": "protect_children",
    "CT31": "protect_animals",
    "CT20": "custody",
    "item3_further_order": "further_order",
}

_MEMBERSHIP = {"ct.relief": _CT_RELIEF}

_RELIEF_FIELDS = tuple(
    FormField(
        item, f"Relief {item}: {key.replace('_', ' ')}", source="ct.relief", needs_legal_review=True
    )
    for item, key in _CT_RELIEF.items()
)

CT_JDFM137_FIELDS: tuple[FormField, ...] = (
    # Caption / court
    FormField(
        "judicial_district",
        "Judicial district / court location",
        source="ct.judicial_district",
        required=True,
    ),
    # Applicant. Only the safe mailing address reaches the form; the home and work
    # addresses are never collected (the form warns they are given to the respondent).
    FormField("applicant", "Applicant name", source="petitioner.legal_name", required=True),
    FormField("applicant_dob", "Applicant date of birth", source="petitioner.dob"),
    FormField(
        "applicant_sex", "Applicant sex", source=None, note="Not collected by intake — CTG1."
    ),
    FormField(
        "applicant_race", "Applicant race", source=None, note="Not collected by intake — CTG1."
    ),
    FormField(
        "applicant_mailing",
        "Applicant mailing address (safe address)",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
    FormField(
        "applicant_home_address",
        "Applicant home/residence address",
        source=None,
        note="Never collected by design — the form discloses it to the respondent.",
    ),
    FormField(
        "applicant_work_address",
        "Applicant work address",
        source=None,
        note="Not collected by intake — CTG1.",
    ),
    FormField(
        "applicant_interpreter",
        "Applicant interpreter needed / language",
        source="petitioner.interpreter_language",
    ),
    # Respondent (with description)
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField(
        "respondent_sex",
        "Respondent sex",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "respondent_interpreter",
        "Respondent interpreter needed / language",
        source=None,
        note="Not collected by intake — CTG2.",
    ),
    FormField(
        "respondent_phone",
        "Respondent telephone",
        source=None,
        note="Not collected by intake — CTG2.",
    ),
    FormField(
        "respondent_height", "Respondent height (other identifiers)", source="respondent.height"
    ),
    FormField(
        "respondent_weight", "Respondent weight (other identifiers)", source="respondent.weight"
    ),
    # Relationship basis ("Respondent is — select all that apply")
    FormField(
        "relationship_basis",
        "Relationship of respondent to applicant",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto CT's checkboxes (spouse/civil union, "
        "cohabited intimate partner, parent/child, blood/marriage, resided with, "
        "caretaker of a person 60+, dating relationship). Attorney confirms the box.",
    ),
    # Other orders / cases
    FormField(
        "other_order_exists",
        "Other protective/restraining order exists",
        source="prior_orders.exists",
        note="Existence only; the docket/court fields are not collected — CTG3.",
    ),
    FormField(
        "other_case_exists",
        "Dissolution/custody/visitation case exists",
        source=None,
        note="Not collected by intake — CTG3.",
    ),
    # Firearms (optional, Yes/No/Unknown)
    FormField(
        "firearms_permit",
        "Respondent holds a pistol/revolver permit",
        source=None,
        note="Optional Q1 not collected — CTG4.",
    ),
    FormField(
        "firearms_eligibility_cert",
        "Respondent holds an eligibility/ammunition certificate",
        source=None,
        note="Optional Q2 not collected — CTG4.",
    ),
    FormField(
        "firearms_possess",
        "Respondent possesses one or more firearms",
        source="firearm.respondent_has_access",
    ),
    FormField(
        "firearms_ammunition",
        "Respondent possesses ammunition",
        source=None,
        note="Optional Q4 not collected — CTG4.",
    ),
    # Affidavit of the abuse (the attached affidavit is the survivor's narrative)
    FormField("incident_date", "Date of the abuse", source="incidents[].date"),
    FormField("incident_location", "Where the abuse occurred", source="incidents[].location"),
    FormField(
        "affidavit_narrative",
        "Affidavit — what the respondent did",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    # 1, 2, 3 — Relief conditions / custody / further order
    *_RELIEF_FIELDS,
    FormField(
        "CT19_children",
        "Children to protect (CT19 table)",
        source="protected_persons.children[]",
        note="Names; form wants each child's sex/DOB — partial, CTG5.",
    ),
    FormField(
        "CT20_children",
        "Children for custody (CT20 table)",
        source="protected_persons.children[]",
        note="Names; form wants each child's sex/DOB — partial, CTG5.",
    ),
    FormField("CT21_with_visitation", "With visitation (terms)", derive=_with_visitation),
    FormField("CT21_visitation_terms", "Visitation terms", source="ct.visitation_terms"),
    FormField("CT22_without_visitation", "Without visitation", derive=_without_visitation),
    FormField("item3_detail", "Further order detail", source="ct.further_order_detail"),
    # 4, 5 — Send order to school (applicant / children)
    FormField(
        "applicant_school",
        "Send order to applicant's school",
        source=None,
        note="Item 4 not collected by intake — CTG6.",
    ),
    FormField(
        "children_school",
        "Send order to children's school",
        source=None,
        note="Item 5 not collected by intake — CTG6.",
    ),
    # 6 — Ex parte (immediate) relief
    FormField("ex_parte", "Request ex parte (immediate) relief", source="ct.ex_parte"),
    # Verification / signature — sworn before a clerk/commissioner/notary at filing
    FormField(
        "signature",
        "Applicant signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Subscribed and sworn before an Assistant Clerk / Commissioner / Notary — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """CT resolver — adds the relief membership rule, else the basic lookup."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto CT JD-FM-137 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=CT_JDFM137_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
