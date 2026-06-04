"""West Virginia DV Petition for Temporary Emergency Protective Order mapping.

Maps Vault intake answers onto West Virginia **MDVTPET, _Domestic Violence
Petition for Temporary Emergency Protective (TEPO) Order_** (W. Va. Code § 48-27,
Rev. 04/24/2017), with its companion Civil Case Information Statement (MDVINFO).
The petition covers the parties (with respondent identifiers for the DV
registry), the relationship basis, children, the item-8 acts checklist, the
abuse narrative, prior orders, firearms, the requested PO duration (with § 505
reasons), and the permissive-relief list.

The WV intake section (`vault.intake`, the `jurisdiction == "WV"` block plus the
shared disability, physical-description, and vehicle blocks — WV is in those
sets) feeds the WV-specific items. WV's relief list is its own, distinct from the
other states'.

Protection: the CCIS lets the petitioner seal their address ("keep my address
confidential"); intake never collects a home address, and the seal box defaults
on. See coverage.md.

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

FORM_ID = "MDVTPET"
FORM_REVISION = "2017-04"  # Rev. 04/24/2017 (TEPO petition)
JURISDICTION = "WV"


def _confidential(_answers: dict[str, Any]) -> str:
    """CCIS — seal the petitioner's address ("keep my address confidential")."""
    return "checked"


def _abused(_answers: dict[str, Any]) -> str:
    """Item 5 — I have been abused or threatened with abuse by the respondent."""
    return "checked"


# Item 8 acts checklist. Membership over `wv.abuse_acts`.
_WV_ABUSE = {
    "ab_physical_harm": "physical_harm",
    "ab_fear_physical_harm": "fear_physical_harm",
    "ab_fear_by_harassment": "fear_by_harassment",
    "ab_sexual_assault": "sexual_assault",
    "ab_held_confined": "held_confined",
}

# Items 9-10 — § 48-27-505 reasons for a 1-year (or longer) order. Membership
# over `wv.duration_reasons`.
_WV_DURATION_REASONS = {
    "dr_violated_prior_po": "violated_prior_po",
    "dr_two_plus_pos": "two_plus_pos",
    "dr_dv_conviction": "dv_conviction",
    "dr_stalking_violation": "stalking_violation",
    "dr_totality": "totality",
    "dr_violated_existing_po": "violated_existing_po",
    "dr_violated_divorce_order": "violated_divorce_order",
}

# Permissive relief (1-5 + law enforcement). Membership over `wv.permissive_relief`.
_WV_PERMISSIVE = {
    "pr_no_abuse": "no_abuse",
    "pr_no_enter_workplace": "no_enter_workplace",
    "pr_no_contact": "no_contact",
    "pr_custody": "custody",
    "pr_visitation_changes": "visitation_changes",
    "pr_le_accompany": "le_accompany_children",
    "pr_le_enter_residence": "le_enter_residence",
}

_MEMBERSHIP = {
    "wv.abuse_acts": _WV_ABUSE,
    "wv.duration_reasons": _WV_DURATION_REASONS,
    "wv.permissive_relief": _WV_PERMISSIVE,
}

_ABUSE_FIELDS = tuple(
    FormField(
        item, f"Abuse: {key.replace('_', ' ')}", source="wv.abuse_acts", needs_legal_review=True
    )
    for item, key in _WV_ABUSE.items()
)
_DURATION_REASON_FIELDS = tuple(
    FormField(
        item,
        f"Duration reason: {key.replace('_', ' ')}",
        source="wv.duration_reasons",
        needs_legal_review=True,
    )
    for item, key in _WV_DURATION_REASONS.items()
)
_PERMISSIVE_FIELDS = tuple(
    FormField(
        item,
        f"Permissive relief: {key.replace('_', ' ')}",
        source="wv.permissive_relief",
        needs_legal_review=True,
    )
    for item, key in _WV_PERMISSIVE.items()
)

WV_MDVTPET_FIELDS: tuple[FormField, ...] = (
    # CCIS caption — the petitioner's home address is never collected and is sealed.
    FormField("county", "County", source="wv.county", required=True),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("petitioner_phone", "Petitioner phone", source="petitioner.safe_phone"),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "petitioner_ssn",
        "Petitioner SSN",
        source=None,
        note="Not collected by intake (sensitive) — WVG1.",
    ),
    FormField(
        "petitioner_address",
        "Petitioner street address",
        source=None,
        note="Never collected by design — sealed via the confidential box.",
    ),
    FormField(
        "confidential",
        "Keep petitioner address confidential (seal page)",
        derive=_confidential,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    FormField(
        "disability_accommodation",
        "Disability accommodations requested",
        source="petitioner.disability_accommodation",
    ),
    # CCIS respondent identifiers (for the DV registry)
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_address", "Respondent street address", source="respondent.last_known_address"
    ),
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
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "respondent_marks",
        "Respondent distinguishing features",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_employer",
        "Respondent employer / work address",
        source="respondent.employer_name",
    ),
    FormField(
        "respondent_ssn",
        "Respondent SSN",
        source=None,
        note="Not collected by intake (sensitive) — WVG2.",
    ),
    FormField(
        "respondent_dl",
        "Respondent driver's license",
        source=None,
        note="Not collected by intake — WVG2.",
    ),
    # TEPO venue / relationship
    FormField("petitioner_county", "Petitioner resident county (item 3)", source="wv.county"),
    FormField(
        "respondent_county",
        "Respondent resident county (item 4)",
        source=None,
        note="Not collected by intake — WVG3.",
    ),
    FormField(
        "relationship_basis",
        "Relationship between respondent and petitioner",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto WV's family/household-member basis "
        "(§ 48-27). Attorney confirms.",
    ),
    # Item 5 abuse assertion + item 6 children
    FormField("abused", "I have been abused or threatened with abuse", derive=_abused),
    FormField(
        "children",
        "Children protected (item 6)",
        source="protected_persons.children[]",
        note="Names; form wants each child's DOB/address/relationship — partial, WVG4.",
    ),
    # Item 7-8 abuse facts
    FormField("abuse_date", "Date(s) of the abuse (item 7)", source="incidents[].date"),
    FormField("abuse_location", "Location of the abuse (item 7)", source="incidents[].location"),
    *_ABUSE_FIELDS,
    FormField(
        "abuse_narrative",
        "Describe the abuse (item 8)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "separate_po",
        "Separate protective order in effect",
        source="prior_orders.exists",
        note="Existence only; county/state not collected — WVG3.",
    ),
    # Firearms
    FormField(
        "firearms_access",
        "Respondent owns/possesses firearms",
        source="firearm.respondent_has_access",
    ),
    FormField("firearms_types", "Firearm type(s)", source="firearm.types[]"),
    FormField("firearms_locations", "Firearm location(s)", source="firearm.locations[]"),
    # Items 9-10 — § 505 duration reasons + requested duration
    *_DURATION_REASON_FIELDS,
    FormField(
        "requested_duration",
        "Requested PO duration (90/180/1yr/longer)",
        source="wv.po_duration",
        needs_legal_review=True,
    ),
    # Permissive relief (1-5 + LE) + visitation detail
    *_PERMISSIVE_FIELDS,
    FormField(
        "custody_children",
        "Children for custody",
        source="protected_persons.children[]",
        note="Maps the protected-children names when custody (item 4) is requested.",
    ),
    FormField("visitation_detail", "Visitation changes (item 5)", source="wv.visitation_detail"),
    # Verification / signature — sworn before a notary/magistrate at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn before a Notary Public / Magistrate / Magistrate Clerk — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """WV resolver — adds the acts/duration-reason/permissive membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto WV MDVTPET fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=WV_MDVTPET_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
