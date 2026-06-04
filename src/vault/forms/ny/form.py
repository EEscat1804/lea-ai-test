"""New York Family Offense Petition form mapping.

Maps Vault intake answers onto New York form **UCS-FC8-2, _Family Offense
Petition_** (FCA 812, 818, 821). The petition covers parties, the FCA 812
relationship basis, the offense details, household members, a safety/firearms
section, and an item-10 list of relief requested.

The NY intake section (`vault.intake`, the `jurisdiction == "NY"` block and the
existing NY Tier-2 branches) feeds the NY-specific items.

Deliberately NOT mapped: item 4's offense checklist (assault / harassment /
stalking / strangulation by penal-law degree) is a legal characterization for
the attorney, flagged `needs_legal_review`. The Vault maps the survivor's
narrative + incident details, not the offense classification.

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

FORM_ID = "UCS-FC8-2"
FORM_REVISION = "2025-05"
JURISDICTION = "NY"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Item 1 — survivors keep their address confidential by default."""
    return "Yes"


def _determine_offense(_answers: dict[str, Any]) -> str:
    """Item 10 — the petition asks the court to determine a family offense."""
    return "checked"


# Item-10 order-of-protection conditions. Intake collects choices as `ny.relief`;
# each box is checked by membership. (item, relief key, label.)
_NY_RELIEF = [
    ("r_stay_away", "stay_away", "stay away from petitioner"),
    ("r_stay_home", "stay_away_home", "stay away from home"),
    ("r_stay_work", "stay_away_work", "stay away from workplace"),
    ("r_no_offense", "no_offense", "no menace/harass/assault"),
    ("r_no_contact", "no_contact", "no communication / social media"),
    ("r_no_third_party", "no_third_party", "no third-party contact"),
    ("r_surrender", "surrender_firearms", "surrender firearms"),
    ("r_aggravated", "aggravated", "finding of aggravated circumstances"),
    ("r_child_support", "child_support", "temporary child support"),
    ("r_spousal_support", "spousal_support", "temporary spousal support"),
]
_NY_RELIEF_ITEMS = {item: key for item, key, _ in _NY_RELIEF}

# The "enter an order of protection" parent box (item 10b) is checked whenever
# any of its conditions is requested.
_OP_CONDITIONS = {
    "stay_away", "stay_away_home", "stay_away_work", "no_offense",
    "no_contact", "no_third_party", "surrender_firearms",
}


def _order_protection(answers: dict[str, Any]) -> str | None:
    relief = answers.get("ny.relief")
    if isinstance(relief, list) and any(c in relief for c in _OP_CONDITIONS):
        return "checked"
    return None


_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {label}", source="ny.relief", needs_legal_review=True)
    for item, _key, label in _NY_RELIEF
)

NY_FOP_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("county", "Family Court county", source="ny.county", required=True),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),

    # 1, 2 — Addresses
    FormField("1_address_confidential", "Keep petitioner address confidential",
              derive=_address_confidential),
    FormField("1_mailing_address", "Petitioner mailing address",
              source="petitioner.safe_mailing_address"),
    FormField("2_respondent_address", "Respondent address", source="respondent.last_known_address"),

    # 3 — Relationship (FCA 812 basis)
    FormField("3_relationship", "Relationship to respondent", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto FCA 812 relationship checkboxes."),

    # 4 — Offense alleged + details
    FormField("4_offenses", "Offense(s) alleged (penal-law checklist)", source=None,
              needs_legal_review=True,
              note="Legal characterization — left to the attorney, not collected — NYG1."),
    FormField("4_date", "Offense date", source="incidents[].date"),
    FormField("4_location", "Offense location", source="incidents[].location"),
    FormField("4_injuries", "Injuries suffered", source="incidents[].injury"),
    FormField("4_weapons", "Weapons used", source="incidents[].weapon_involved"),
    FormField("4_narrative", "What happened (description)", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),

    # 5, 6 — Criminal complaint / household members
    FormField("5_criminal_complaint", "Criminal complaint filed",
              source="incidents[].police_called"),
    FormField("6_children", "Household children", source="protected_persons.children[]",
              note="Names; form wants DOB/relationship per child — NYG2."),

    # 8 — Safety / firearms
    FormField("8_violated_op", "Violated an order of protection", source="prior_orders.exists"),
    FormField("8_owns_firearms", "Respondent owns/has access to firearms",
              source="firearm.respondent_has_access"),
    FormField("8_carries_firearm_job", "Respondent carries a firearm on the job",
              source="respondent.is_law_enforcement"),
    FormField("8_used_firearm_threat", "Used firearm/weapon to threaten",
              source="incidents[].weapon_involved"),

    # 9 — Convictions
    FormField("9_convictions", "Respondent criminal convictions",
              source="respondent.prior_criminal_history"),

    # 10 — Request for relief
    FormField("10a_determine_offense", "Determine respondent committed a family offense",
              derive=_determine_offense, needs_legal_review=True),
    FormField("10b_order_protection", "Enter an order of protection",
              derive=_order_protection),
    *_RELIEF_FIELDS,

    # 11 — Signature
    FormField("11_signature", "Petitioner signature (printed name)",
              source="petitioner.legal_name", required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NY resolver — adds the relief-checkbox rule, else the basic lookup."""
    if f.source == "ny.relief" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _NY_RELIEF_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto NY Family Offense Petition fields."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NY_FOP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
