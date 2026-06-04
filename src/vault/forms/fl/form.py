"""Florida Petition for Injunction for Protection Against DV form mapping.

Maps Vault intake answers onto Florida Supreme Court Approved Family Law Form
**12.980(a), _Petition for Injunction for Protection Against Domestic Violence_**
(Fla. Stat. § 741.30). The petition covers the parties, the family/household
relationship basis, a sworn statement of the abuse, a respondent description for
service, firearms, and the relief requested.

FL's intake (`vault.intake`, the FL Tier-2 blocks plus the `jurisdiction == "FL"`
relief block) feeds the FL-specific items. FL's relief list is its own, distinct
from the other states'.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings. See coverage.md.

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

FORM_ID = "12.980(a)"
# Revision of the official Florida Supreme Court Approved Family Law Form. The
# blank fillable PDF dropped in this folder for lea-be-core's renderer must match
# this revision — confirm before rendering (see README / coverage.md).
FORM_REVISION = "2023-09"
JURISDICTION = "FL"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Petitioner's address is withheld by default (FL form 12.980(h)).

    Intake never collects a home address, so there is nothing to leak; this
    asserts the confidential-address request so the box is checked, not blank.
    """
    return "checked"


def _immediate_danger(_answers: dict[str, Any]) -> str:
    """The petition asserts immediate and present danger (Fla. Stat. § 741.30(5)).

    Flagged for legal review — an attorney confirms the factual basis for the
    ex parte temporary injunction.
    """
    return "checked"


# Relief requested. Intake collects choices as `fl.relief`; each box is checked
# by membership. (item, relief key, label.)
_FL_RELIEF = [
    ("r_no_dv", "no_dv", "no acts of domestic violence"),
    ("r_no_contact", "no_contact", "no contact, directly or indirectly"),
    ("r_exclusive_residence", "exclusive_residence", "exclusive use/possession of the dwelling"),
    ("r_parenting_plan", "parenting_plan", "temporary parenting plan / timesharing"),
    ("r_child_support", "child_support", "temporary child support"),
    ("r_spousal_support", "spousal_support", "temporary support for the petitioner"),
    ("r_batterers_program", "batterers_program", "complete a batterers' intervention program"),
    ("r_surrender_firearms", "surrender_firearms", "surrender firearms and ammunition"),
    ("r_other", "other", "other relief"),
]
_FL_RELIEF_ITEMS = {item: key for item, key, _ in _FL_RELIEF}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {label}", source="fl.relief", needs_legal_review=True)
    for item, _key, label in _FL_RELIEF
)

FL_12980A_FIELDS: tuple[FormField, ...] = (
    # Caption / petitioner. The survivor's home address is never collected and
    # never appears here; the confidential-address request is asserted instead.
    FormField("county", "County / circuit", source="fl.county", required=True),
    FormField("petitioner", "Petitioner full name", source="petitioner.legal_name", required=True),
    FormField("petitioner_dob", "Petitioner date of birth", source="petitioner.dob"),
    FormField(
        "address_confidential",
        "Petitioner address kept confidential",
        derive=_address_confidential,
        note="FL form 12.980(h) — withheld by default; intake collects no home address.",
    ),
    FormField("interpreter", "Interpreter / language", source="petitioner.interpreter_language"),
    # Respondent identity
    FormField("respondent", "Respondent full name", source="respondent.legal_name", required=True),
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    # Respondent description (for service by the sheriff)
    FormField("desc_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("desc_race", "Respondent race", source="respondent.race"),
    FormField(
        "desc_sex",
        "Respondent sex/gender",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner.gender. Do not confuse them.",
    ),
    FormField("desc_height", "Respondent height", source="respondent.height"),
    FormField("desc_weight", "Respondent weight", source="respondent.weight"),
    FormField("desc_eye_color", "Respondent eye color", source="respondent.eye_color"),
    FormField("desc_hair_color", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "desc_marks", "Respondent distinguishing marks", source="respondent.distinguishing_marks"
    ),
    FormField("desc_employer", "Respondent employer", source="respondent.employer_name"),
    FormField(
        "desc_employer_address", "Respondent employer address", source="respondent.employer_address"
    ),
    FormField("desc_employer_hours", "Respondent work hours", source="respondent.employer_hours"),
    FormField(
        "desc_vehicle", "Respondent vehicle make/model", source="respondent.vehicle_make_model"
    ),
    FormField("desc_vehicle_color", "Respondent vehicle color", source="respondent.vehicle_color"),
    FormField("desc_vehicle_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"),
    FormField(
        "desc_law_enforcement",
        "Respondent carries a firearm for work (LE/security)",
        source="respondent.is_law_enforcement",
    ),
    FormField(
        "desc_active_military",
        "Respondent on active military duty",
        source="respondent.is_active_military",
    ),
    FormField(
        "desc_prior_criminal",
        "Respondent prior violent arrest/conviction",
        source="respondent.prior_criminal_history",
    ),
    # Relationship basis (family or household member)
    FormField(
        "relationship_basis",
        "Family/household member basis",
        source="relationship.type",
        needs_legal_review=True,
        note="FL DV injunction (12.980(a)) requires the parties to be family or "
        "household members or have a child in common. A dating-only relationship "
        "with no cohabitation or child may require the Dating Violence petition "
        "(12.980(n)) instead — attorney must confirm the correct petition.",
    ),
    FormField(
        "rel_live_together_now",
        "Currently living together as a family",
        source="relationship.live_together_now",
    ),
    FormField(
        "rel_lived_together_past",
        "Formerly lived together as a family",
        source="relationship.lived_together_past",
    ),
    FormField(
        "rel_child_in_common", "Have a child in common", source="relationship.children_in_common"
    ),
    # Immediate danger (basis for the ex parte temporary injunction)
    FormField(
        "immediate_danger",
        "Immediate and present danger of domestic violence",
        derive=_immediate_danger,
        needs_legal_review=True,
        note="Fla. Stat. § 741.30(5) — attorney confirms the factual basis.",
    ),
    # Sworn statement of the abuse (first incident in incidents[])
    FormField(
        "statement_date", "Date of most recent incident", source="incidents[].date", required=True
    ),
    FormField("statement_location", "Location of incident", source="incidents[].location"),
    FormField(
        "statement_narrative",
        "Statement describing the domestic violence",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("statement_injury", "Injury", source="incidents[].injury"),
    FormField("statement_witnesses", "Witnesses present", source="incidents[].witnesses_present"),
    FormField("statement_police_called", "Police were called", source="incidents[].police_called"),
    FormField(
        "statement_police_report", "Police report number", source="incidents[].police_report_number"
    ),
    FormField("statement_weapon", "Weapon used/threatened", source="incidents[].weapon_involved"),
    FormField("statement_frequency", "Frequency / pattern", source="incidents[].pattern_frequency"),
    # Other orders / cases
    FormField(
        "other_orders",
        "Other injunctions/orders exist",
        source="prior_orders.exists",
        note="Existence only; FL also wants case numbers/courts — partial, FG1.",
    ),
    FormField(
        "other_cases",
        "Other pending cases with respondent",
        source=None,
        note="Not collected by intake yet — FG1.",
    ),
    # Children
    FormField(
        "children",
        "Minor children",
        source="protected_persons.children[]",
        note="Names; FL wants each child's name/DOB/residence for the parenting-plan "
        "section — partial, FG2.",
    ),
    FormField(
        "children_why",
        "Why protection extends to the children",
        source="protected_persons.why",
        note="FL intake does not collect this yet (CA-only) — FG2.",
    ),
    # Firearms
    FormField(
        "firearms_access",
        "Respondent has firearms/ammunition",
        source="firearm.respondent_has_access",
    ),
    FormField("firearms_types", "Firearm description", source="firearm.types[]"),
    FormField("firearms_locations", "Firearm location", source="firearm.locations[]"),
    # Relief requested + details
    *_RELIEF_FIELDS,
    FormField(
        "r_exclusive_residence_address", "Shared residence address", source="fl.residence_address"
    ),
    FormField("r_other_detail", "Other relief detail", source="fl.other_relief"),
    # Signature — sworn before a notary/deputy clerk at filing
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="FL petition must be sworn before a notary or deputy clerk — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """FL resolver — adds the relief-checkbox rule, else the basic lookup."""
    if f.source == "fl.relief" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _FL_RELIEF_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto FL form 12.980(a) fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=FL_12980A_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
