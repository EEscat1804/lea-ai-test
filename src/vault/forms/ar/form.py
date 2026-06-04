"""Arkansas Petition and Affidavit for an Order of Protection form mapping.

Maps Vault intake answers onto the Arkansas Circuit Court **Petition and
Affidavit for an Order of Protection** (A.C.A. § 9-15-101 et seq., Rev. August
2023). The petition covers the parties (with full identifiers), the relationship
basis, the most-recent-act affidavit, law-enforcement reporting, prior violence,
minor children, and an item-8 list of ex parte order provisions, plus the
law-enforcement NOTICE page.

The AR intake section (`vault.intake`, the `jurisdiction == "AR"` block plus the
shared physical-description block — AR is a physical-description state) feeds the
AR-specific items. AR's relief list (item 8) is its own, distinct from the other
states'.

Protection: the form lets the petitioner omit an address (a mailing address is
provided instead) — intake only ever holds a safe mailing address, and the
omit-address box defaults on. See coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

# The AR petition carries no printed form number; confirm against the blank PDF
# dropped in this folder for lea-be-core's renderer.
FORM_ID = "AR-OP-Petition"
FORM_REVISION = "2023-08"  # Rev. August 2023
JURISDICTION = "AR"


def _age_from(dob_key: str) -> Callable[[dict[str, Any]], str | None]:
    """Build a derive fn that computes age from the DOB at `dob_key`."""

    def _derive(answers: dict[str, Any]) -> str | None:
        dob_str = answers.get(dob_key)
        if not isinstance(dob_str, str) or not dob_str:
            return None
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
        except ValueError:
            return None
        today = datetime.now()
        return str(today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day)))

    return _derive


def _omit_address(_answers: dict[str, Any]) -> str:
    """Page 1 — the petitioner elected to omit an address (mailing address given)."""
    return "checked"


def _filing_self(_answers: dict[str, Any]) -> str:
    """Item 1 — filing on behalf of myself."""
    return "checked"


def _ex_parte_basis(_answers: dict[str, Any]) -> str:
    """Item 3 — afraid of the respondent; immediate and present danger of abuse."""
    return "checked"


# Item 8 — ex parte order provisions (mark all applicable). Membership over
# `ar.relief`.
_AR_RELIEF = {
    "r_exclude_residence": "exclude_residence",
    "r_exclude_workplace": "exclude_workplace",
    "r_no_contact": "no_contact",
    "r_no_phone_disconnect": "no_phone_disconnect",
    "r_custody": "custody",
    "r_child_support": "child_support",
    "r_spousal_support": "spousal_support",
    "r_exclude_address": "exclude_address",
    "r_pay_fees": "pay_fees",
}

_MEMBERSHIP = {"ar.relief": _AR_RELIEF}

AR_OP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County (Circuit Court)", source="ar.county", required=True),
    # Petitioner / Affiant. Only the safe mailing address reaches the form; the
    # home and work addresses are never collected.
    FormField(
        "petitioner", "Petitioner/Affiant name", source="petitioner.legal_name", required=True
    ),
    FormField("petitioner_age", "Petitioner age", derive=_age_from("petitioner.dob")),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "petitioner_race", "Petitioner race", source=None, note="Not collected by intake — ARG1."
    ),
    FormField(
        "petitioner_sex", "Petitioner sex", source=None, note="Not collected by intake — ARG1."
    ),
    FormField(
        "petitioner_interpreter",
        "Petitioner interpreter / language",
        source="petitioner.interpreter_language",
    ),
    FormField("petitioner_phone", "Petitioner telephone", source="petitioner.safe_phone"),
    FormField("petitioner_email", "Petitioner email", source="petitioner.safe_email"),
    FormField(
        "petitioner_mailing",
        "Petitioner mailing address (safe address)",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only — home address is never collected.",
    ),
    FormField(
        "omit_address",
        "Petitioner elected to omit an address",
        derive=_omit_address,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "petitioner_dl",
        "Petitioner driver's license number",
        source=None,
        note="Not collected by intake — ARG1.",
    ),
    FormField(
        "petitioner_work",
        "Petitioner place of work",
        source=None,
        note="Not collected by intake — ARG1.",
    ),
    # Respondent (with full identifiers; NOTICE page reuses these)
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField("respondent_age", "Respondent age", derive=_age_from("respondent.dob")),
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField(
        "respondent_sex",
        "Respondent sex",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField(
        "respondent_address", "Respondent home address", source="respondent.last_known_address"
    ),
    FormField(
        "respondent_work_name", "Respondent place of work (name)", source="respondent.employer_name"
    ),
    FormField(
        "respondent_work_address",
        "Respondent place of work (address)",
        source="respondent.employer_address",
    ),
    FormField(
        "respondent_phone",
        "Respondent telephone",
        source=None,
        note="Not collected by intake — ARG2.",
    ),
    FormField(
        "respondent_email", "Respondent email", source=None, note="Not collected by intake — ARG2."
    ),
    FormField(
        "respondent_dl",
        "Respondent driver's license number",
        source=None,
        note="Not collected by intake — ARG2.",
    ),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "respondent_distinguishing",
        "Respondent distinguishing characteristics",
        source="respondent.distinguishing_marks",
    ),
    # 1 — Filing on behalf of myself
    FormField("filing_self", "Filing on behalf of myself", derive=_filing_self),
    # 2 — Relationship basis (mark all that apply)
    FormField(
        "relationship_basis",
        "Relationship between respondent and petitioner",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto AR's item-2 categories (spouse/"
        "former spouse, blood, reside together now/formerly, child in common, "
        "dating, marriage/in-law). Attorney confirms the box(es).",
    ),
    # 3 — Ex parte basis + most recent act
    FormField(
        "ex_parte_basis",
        "Afraid; immediate and present danger of abuse",
        derive=_ex_parte_basis,
        needs_legal_review=True,
    ),
    FormField(
        "most_recent_act_date", "Date of most recent act", source="incidents[].date", required=True
    ),
    FormField(
        "most_recent_act_location", "Location of most recent act", source="incidents[].location"
    ),
    FormField(
        "abuse_narrative",
        "Most recent act — threats / physical abuse (description)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08). Covers "
        "the page 3 (threats) and page 4 (actual abuse) description.",
    ),
    # 4 — Reported to law enforcement
    FormField(
        "reported_le",
        "Most recent act reported to law enforcement",
        source="incidents[].police_called",
        note="Agency/date/action taken not collected — ARG3.",
    ),
    # 5 — Additional acts of domestic violence
    FormField(
        "additional_acts",
        "Additional acts of domestic violence",
        source=None,
        note="Not collected by intake (overflow) — ARG3.",
    ),
    # 6 — Respondent prior violence
    FormField(
        "respondent_prior_violence",
        "Respondent previously arrested/convicted of violence",
        source="respondent.prior_criminal_history",
        note="When/where/what details not collected — ARG3.",
    ),
    # 7 — Minor children in common
    FormField(
        "children",
        "Minor children in common",
        source="protected_persons.children[]",
        note="Names; form wants each child's age/address — partial, ARG4.",
    ),
    # 8 — Ex parte order provisions (mark all applicable) + details
    FormField(
        "r_exclude_residence",
        "Exclude respondent from the residence",
        source="ar.relief",
        needs_legal_review=True,
    ),
    FormField("residence_address", "Residence address", source="ar.residence_address"),
    FormField("residence_owner", "Residence owner/renter", source="ar.residence_owner"),
    FormField(
        "r_exclude_workplace",
        "Exclude from work/school/other",
        source="ar.relief",
        needs_legal_review=True,
    ),
    FormField("workplace", "Work/school/other location", source="ar.workplace"),
    FormField("r_no_contact", "Prohibit contact", source="ar.relief", needs_legal_review=True),
    FormField("contact_conditions", "Contact conditions (if any)", source="ar.contact_conditions"),
    FormField(
        "r_no_phone_disconnect",
        "Not disconnect phone numbers",
        source="ar.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_custody",
        "Temporary custody of minor children",
        source="ar.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_child_support", "Require child support", source="ar.relief", needs_legal_review=True
    ),
    FormField(
        "child_support_pay",
        "Respondent weekly take-home pay (child support)",
        source=None,
        note="Not collected by intake — ARG5.",
    ),
    FormField(
        "r_spousal_support", "Require spousal support", source="ar.relief", needs_legal_review=True
    ),
    FormField(
        "spousal_support_pay",
        "Respondent weekly take-home pay (spousal support)",
        source=None,
        note="Not collected by intake — ARG5.",
    ),
    FormField(
        "r_exclude_address",
        "Exclude petitioner's address from notice",
        source="ar.relief",
        needs_legal_review=True,
    ),
    FormField(
        "r_pay_fees",
        "Require respondent to pay fees/costs",
        source="ar.relief",
        needs_legal_review=True,
    ),
    # 10, 11 — Existing custody order / prior cases
    FormField(
        "prior_custody_order",
        "Existing custody order",
        source=None,
        note="Not collected by intake — ARG6.",
    ),
    FormField(
        "prior_cases",
        "Prior cases in the circuit court",
        source=None,
        note="Not collected by intake — ARG6.",
    ),
    # NOTICE page — law-enforcement caution
    FormField(
        "caution_firearm",
        "CAUTION: respondent possesses a firearm",
        source="firearm.respondent_has_access",
    ),
    FormField(
        "caution_violence",
        "CAUTION: respondent has history of extreme violence",
        source=None,
        note="Not collected by intake — ARG7.",
    ),
    # Verification / signature — sworn before a notary at filing
    FormField(
        "signature",
        "Petitioner/Affiant signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Subscribed and sworn before a Notary Public — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """AR resolver — adds the item-8 relief membership rule, else basic lookup."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto the AR Order of Protection petition (auditable map)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=AR_OP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
