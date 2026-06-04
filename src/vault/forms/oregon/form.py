"""Oregon FAPA Restraining Order Petition form mapping.

Maps Vault intake answers onto Oregon's **Petition for Restraining Order to
Prevent Abuse** (Family Abuse Prevention Act, ORS 107.700; Circuit Court; OJD
Official, rev. Jan 2026). The petition covers the county, the parties and their
ages, the §3 relationship basis, the §4 abuse grounds (within the past 180 days),
the §5 incident narrative, an imminent-danger declaration (§6), firearms (§7),
existing orders (§8), and the discretionary relief — move-out (§10), emergency
money (§11), companion animals (§12), and custody assistance (§19). OR's abuse
and relief lists are their own.

The module is named `oregon` (not `or`) because `or` is a Python keyword and
cannot be an importable module name — see README. The jurisdiction code is "OR".

The OR intake section (`vault.intake`, the `_or_step` method) plus the shared
interpreter and employer gates feeds these items. OR is intentionally NOT in
`PHYSICAL_DESCRIPTION_STATES` or `VEHICLE_DESCRIPTION_STATES` — the FAPA petition
has no respondent description or vehicle block.

Protection: the form's contact address/phone are the safe values intake holds, the
form's own notice tells the petitioner to use a SAFE contact address, and the §21
Confidential Information Form is asserted on the petitioner's behalf. The large
UCCJEA / joint-children section (§§13-20) is mostly beyond what intake collects
and is flagged. See coverage.md.

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

FORM_ID = "Petition for Restraining Order to Prevent Abuse"  # OJD FAPA — no printed number, ORG1
FORM_REVISION = "2026-01"  # OJD Official, Jan 2026
JURISDICTION = "OR"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Form directs the petitioner to use a SAFE contact address — assert it."""
    return "checked"


def _cif_petitioner(_answers: dict[str, Any]) -> str:
    """§21 — a Confidential Information Form is filed for the petitioner."""
    return "checked"


def _injured(answers: dict[str, Any]) -> str | None:
    """§5 — check 'I was injured' when the Tier-1 incident records an injury."""
    injury = answers.get("incidents[].injury")
    if isinstance(injury, str) and injury.strip().lower() not in ("", "none", "n/a"):
        return "checked"
    return None


# §4 — abuse within the past 180 days. Membership over `or.abuse_types`.
_OR_ABUSE = {
    "4_physical_injury": "physical_injury",
    "4_attempted_injury": "attempted_injury",
    "4_fear_imminent": "fear_imminent",
    "4_sexual_force": "sexual_force",
}

# Discretionary relief (§§7, 10, 11, 12, 19). Membership over `or.relief`.
_OR_RELIEF = {
    "7_firearms_prohibit": "firearms_prohibit",
    "10_move_out": "move_out",
    "11_emergency_money": "emergency_money",
    "12_animals": "animals",
    "19_custody_assistance": "custody_assistance",
}

# §10 — move-out basis. Membership over `or.move_out_basis`.
_OR_MOVE_OUT = {
    "10_sole_name": "sole_name",
    "10_joint_own": "joint_own",
    "10_joint_lease": "joint_lease",
    "10_spouse_rdp": "spouse_rdp",
}

_MEMBERSHIP = {
    "or.abuse_types": _OR_ABUSE,
    "or.relief": _OR_RELIEF,
    "or.move_out_basis": _OR_MOVE_OUT,
}

_ABUSE_FIELDS = tuple(
    FormField(
        item,
        f"Abuse (180 days): {key.replace('_', ' ')}",
        source="or.abuse_types",
        needs_legal_review=True,
    )
    for item, key in _OR_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(
        item,
        f"Relief: {key.replace('_', ' ')}",
        source="or.relief",
        needs_legal_review=True,
    )
    for item, key in _OR_RELIEF.items()
)
_MOVE_OUT_FIELDS = tuple(
    FormField(
        item,
        f"Move-out basis: {key.replace('_', ' ')}",
        source="or.move_out_basis",
        needs_legal_review=True,
    )
    for item, key in _OR_MOVE_OUT.items()
)

OR_FAPA_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "county",
        "County (Circuit Court of Oregon for the County of)",
        source="or.county",
        required=True,
    ),
    FormField(
        "case_number",
        "Case number",
        source=None,
        note="Assigned by the clerk at filing — ORG2.",
    ),
    FormField(
        "interpreter",
        "Interpreter needed (Spanish / ASL / other)",
        source="petitioner.interpreter_language",
    ),
    # Parties
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_age",
        "Petitioner age (§2)",
        source="petitioner.dob",
        note="Age computed from date of birth at fill time.",
    ),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_age",
        "Respondent age — must be 18+ (§2)",
        source="respondent.dob",
        note="Age computed from date of birth at fill time.",
    ),
    # 1 — Residency
    FormField(
        "petitioner_residence_county",
        "Petitioner's county of residence (§1)",
        source="or.county",
        note="Assumes the filing county is the petitioner's residence county — ORG3.",
    ),
    FormField(
        "petitioner_residence_state",
        "Petitioner's state of residence (§1)",
        source=None,
        note="Not separately collected — ORG3.",
    ),
    FormField(
        "respondent_residence",
        "Respondent's county / state of residence (§1)",
        source="respondent.last_known_address",
        note="Free-text last-known address; county/state not separately parsed — ORG3.",
    ),
    # 3 — Relationship
    FormField(
        "relationship_basis",
        "Relationship of respondent to petitioner (§3 check-all)",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto OR's §3 categories (spouse/RDP, "
        "blood/marriage/adoption, cohabiting intimate, intimate within 2 years, parent of "
        "my child). Attorney confirms the boxes.",
    ),
    FormField(
        "relationship_explain",
        "Relationship explain / dates (§3)",
        source=None,
        note="The blood-relative 'explain' and the intimate-relationship dates are not "
        "separately collected — ORG4.",
    ),
    # 4 — Abuse within the past 180 days
    *_ABUSE_FIELDS,
    FormField(
        "4_tolling_jail",
        "Respondent in jail/prison (tolls the 180 days)",
        source=None,
        note="Tolling dates not collected — ORG5.",
    ),
    FormField(
        "4_tolling_distance",
        "Respondent lived 100+ miles away (tolls the 180 days)",
        source=None,
        note="Tolling dates not collected — ORG5.",
    ),
    # 5 — Incidents of abuse (most-recent, from the Tier-1 incident)
    FormField("incident_date", "Incident date (§5A)", source="incidents[].date"),
    FormField("incident_location", "Incident county / state (§5A)", source="incidents[].location"),
    FormField(
        "incident_details",
        "Describe the incident (§5A)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — verbatim (guardrail G-08).",
    ),
    FormField("incident_injured", "I was injured (§5A)", derive=_injured),
    FormField(
        "incident_medical",
        "I sought medical care (§5A)",
        source=None,
        note="Not collected by intake — ORG6.",
    ),
    FormField(
        "incident_weapon", "Respondent had a weapon (§5A)", source="incidents[].weapon_involved"
    ),
    FormField(
        "incident_drugs_alcohol",
        "Respondent was using drugs / alcohol (§5A)",
        source=None,
        note="Not collected by intake — ORG6.",
    ),
    FormField(
        "incident_police", "The police were called (§5A)", source="incidents[].police_called"
    ),
    FormField(
        "incident_arrested",
        "Respondent was arrested (§5A)",
        source=None,
        note="Not collected by intake — ORG6.",
    ),
    FormField(
        "prior_incidents",
        "Other incidents more than 180 days ago (§5B)",
        source=None,
        note="Intake holds the most-recent incident only — ORG7.",
    ),
    # 6 — Imminent danger of future abuse
    FormField(
        "imminent_danger",
        "I am in imminent danger of future abuse (§6)",
        source="or.imminent_danger",
        needs_legal_review=True,
    ),
    FormField(
        "imminent_danger_explain",
        "Why respondent is a threat in the near future (§6)",
        source="or.imminent_danger_explain",
    ),
    # Discretionary relief checklist (§§7, 10, 11, 12, 19)
    *_RELIEF_FIELDS,
    # 7 — Firearms (additional facts)
    FormField(
        "respondent_has_firearms",
        "Respondent has / can access firearms (§7)",
        source="firearm.respondent_has_access",
    ),
    FormField(
        "firearms_already_prohibited",
        "Respondent already prohibited from firearms (§7)",
        source=None,
        note="Not collected by intake — ORG8.",
    ),
    FormField("firearm_types", "Firearm types (§7)", source="firearm.types[]"),
    FormField("firearm_locations", "Firearm locations (§7)", source="firearm.locations[]"),
    # 8 / 9 — Existing orders and other family cases
    FormField(
        "existing_orders",
        "Existing restraining / stalking order (§8)",
        source="prior_orders.exists",
        note="Existence only; form wants county/state/case# — ORG9.",
    ),
    FormField(
        "other_family_cases",
        "Other family-law cases between the parties (§9)",
        source=None,
        note="Not collected by intake — ORG9.",
    ),
    # 10 — Move-out
    *_MOVE_OUT_FIELDS,
    # 11 — Emergency money
    FormField(
        "emergency_amount", "Emergency money — one-time amount (§11)", source="or.emergency_amount"
    ),
    FormField("emergency_reason", "Emergency money — reason (§11)", source="or.emergency_reason"),
    # 12 — Animals
    FormField(
        "animals_detail", "Companion / service animals to award (§12)", source="or.animals_detail"
    ),
    # 13-20 — Joint children (UCCJEA)
    FormField(
        "children_names",
        "Minor children — names and ages (§13)",
        source="protected_persons.children[]",
        note="Names only; form wants name + age per child — ORG10.",
    ),
    FormField(
        "children_uccjea",
        "Children's residence / 5-year history / parentage / prior cases (§§14-18)",
        source=None,
        note="The UCCJEA custody section is beyond what intake collects — ORG11.",
    ),
    FormField(
        "dhs_involvement",
        "DHS Child Welfare involvement (§20)",
        source=None,
        note="Not collected by intake — ORG12.",
    ),
    # 21 — Confidential Information Form + safe contact
    FormField(
        "cif_petitioner",
        "Confidential Information Form filed for petitioner (§21)",
        derive=_cif_petitioner,
    ),
    FormField(
        "address_confidential",
        "Petitioner using a safe contact address (per the form's notice)",
        derive=_address_confidential,
    ),
    # Verification / signature
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
    ),
    FormField(
        "contact_address", "Contact address (SAFE)", source="petitioner.safe_mailing_address"
    ),
    FormField("contact_phone", "Contact phone (SAFE)", source="petitioner.safe_phone"),
    FormField("contact_email", "Contact email", source="petitioner.safe_email"),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """OR resolver — adds the abuse/relief/move-out membership rules, else basic."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto OR FAPA petition fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=OR_FAPA_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
