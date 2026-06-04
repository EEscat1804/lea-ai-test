"""North Carolina Complaint for DV Protective Order form mapping.

Maps Vault intake answers onto North Carolina form **AOC-CV-303, _Complaint for
Domestic Violence Protective Order_** (G.S. 50B-1 et seq., Rev. 12/25). The
complaint covers parties, the G.S. 50B relationship basis, the abuse statement,
firearms, and a 1-17 list of relief requested.

The NC intake section (`vault.intake`, the `jurisdiction == "NC"` block) feeds
the NC-specific items. NC's relief list (1-17) is its own, distinct from the
other states'.

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

FORM_ID = "AOC-CV-303"
FORM_REVISION = "2025-12"
JURISDICTION = "NC"


def _acts_in_nc(_answers: dict[str, Any]) -> str:
    """Item 2 — relief is sought for acts that occurred in NC."""
    return "checked"


def _immediate_danger(_answers: dict[str, Any]) -> str:
    """Item 7 — the complaint asserts danger of serious and immediate injury."""
    return "checked"


# Relief requested (form items 1-17, incl. 3a/6a). Intake collects choices as
# `nc.relief`; each box is checked by membership. (item, relief key, label.)
_NC_RELIEF = [
    ("r1", "emergency", "emergency relief"),
    ("r2", "ex_parte", "ex parte order"),
    ("r3", "no_abuse", "no assault/threaten/harass"),
    ("r3a", "no_pet_abuse", "no cruelty to pet"),
    ("r4", "residence", "possession of residence (defendant move out)"),
    ("r5", "eviction", "eviction of defendant"),
    ("r6", "personal_property", "possession of personal property"),
    ("r6a", "pet_custody", "custody of pet"),
    ("r7", "stay_away", "stay away from listed places"),
    ("r8", "no_contact", "no contact"),
    ("r9", "vehicle", "possession of vehicle"),
    ("r10", "custody", "temporary child custody"),
    ("r11", "child_support", "child support"),
    ("r12", "prohibit_firearm", "prohibit firearm possession/purchase"),
    ("r13", "surrender_firearms", "surrender firearms/ammunition/permits"),
    ("r14", "abuser_program", "abuser treatment program"),
    ("r15", "alternative_housing", "alternative housing"),
    ("r16", "spousal_support", "spousal support"),
    ("r17", "other", "other relief"),
]
_NC_RELIEF_ITEMS = {item: key for item, key, _ in _NC_RELIEF}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief {item[1:]}: {label}", source="nc.relief", needs_legal_review=True)
    for item, _key, label in _NC_RELIEF
)

NC_AOC303_FIELDS: tuple[FormField, ...] = (
    # Caption / parties
    FormField("county", "County", source="nc.county", required=True),
    FormField("plaintiff", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("defendant", "Defendant name", source="respondent.legal_name", required=True),
    FormField("defendant_address", "Defendant address", source="respondent.last_known_address"),
    FormField("interpreter", "Interpreter / language", source="petitioner.interpreter_language"),

    # 1, 2 — Residence county / acts in NC
    FormField("1_county", "Plaintiff lives in NC county", source="nc.county"),
    FormField("2_acts_in_nc", "Seeking relief for acts in NC", derive=_acts_in_nc),

    # 3 — Relationship (G.S. 50B basis)
    FormField("3_relationship", "Relationship of the parties", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto NC's 50B relationship checkboxes."),

    # 4 — Other court proceeding
    FormField("4_other_proceeding", "Other court proceeding pending", source="prior_orders.exists",
              note="PO existence only — partial, NG1."),

    # 5, 6 — Abuse statements
    FormField("5_abuse_narrative", "Abuse against plaintiff (statement)",
              source="incidents[].narrative", required=True,
              note="Survivor's own words — verbatim (guardrail G-08)."),
    FormField("6_child_abuse", "Abuse against children (statement)", source=None,
              note="Not collected (child-specific) — NG2."),

    # 7, 8 — Danger / children
    FormField("7_immediate_danger", "Danger of serious and immediate injury",
              derive=_immediate_danger),
    FormField("8_children", "Minor children (custody)", source="protected_persons.children[]",
              note="Names; form wants sex/DOB per child (AOC-CV-609 attached) — NG2."),

    # 9-12 — Custody risk / firearms / weapon / suicide
    FormField("9_custody_risk", "Child custody risk statement", source=None,
              note="Not collected — NG2."),
    FormField("10_firearms", "Defendant has firearms/ammunition/permits",
              source="firearm.respondent_has_access"),
    FormField("10_firearm_types", "Firearm description", source="firearm.types[]"),
    FormField("10_firearm_locations", "Firearm location", source="firearm.locations[]"),
    FormField("11_deadly_weapon", "Used/threatened deadly weapon",
              source="incidents[].weapon_involved"),
    FormField("12_suicide_threats", "Defendant threatened suicide", source=None,
              note="Not collected — NG3."),

    # Relief requested (1-17) + details
    *_RELIEF_FIELDS,
    FormField("r4_residence_address", "Residence address", source="nc.residence_address"),
    FormField("r7_places", "Stay-away places", source="nc.stay_away_places"),
    FormField("r9_vehicle", "Vehicle description", source="nc.vehicle"),
    FormField("r17_other", "Other relief detail", source="nc.other_relief"),

    # Signature
    FormField("sig_plaintiff", "Plaintiff signature (printed name)",
              source="petitioner.legal_name", required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """NC resolver — adds the relief-checkbox rule, else the basic lookup."""
    if f.source == "nc.relief" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _NC_RELIEF_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto NC AOC-CV-303 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=NC_AOC303_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
