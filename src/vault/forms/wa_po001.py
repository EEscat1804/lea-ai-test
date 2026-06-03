"""Washington PO 001 form mapping.

Maps Vault intake answers onto Washington form **PO 001, _Petition for
Protection Order_** (RCW 7.105.100, Rev. 01/2026). WA's PO 001 is a *unified*
petition covering five order types (domestic violence, sexual assault,
stalking, vulnerable adult, anti-harassment). The Vault serves DV survivors,
so this module maps the **Domestic Violence** path (PTORPRT).

The WA intake section (`vault.intake`, the `jurisdiction == "WA"` block) feeds
the WA-specific items — the A-Z restraints (item 14), the temporary-order
request, length, jurisdiction basis, and so on. WA's restraint list is its
own, distinct from CA's relief set.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings. See PO-001_coverage.md.

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

FORM_ID = "PO 001"
FORM_REVISION = "2026-01"
JURISDICTION = "WA"


def _dv_order_type(_answers: dict[str, Any]) -> str:
    """The Vault files DV protection orders; item 1 is fixed to that path."""
    return "Domestic Violence (PTORPRT)"


# PO 001 item 14 restraints (DV-relevant A-Z). Intake collects the survivor's
# chosen restraints as the `wa.restraints` list; each box is checked by
# membership. (item, restraint key, human label.)
_WA_RESTRAINTS = [
    ("14A", "no_harm", "no harm"),
    ("14B", "no_contact", "no contact"),
    ("14C", "stalking", "no stalking/surveillance"),
    ("14D", "stay_away", "exclude and stay away"),
    ("14E", "vacate", "vacate shared residence"),
    ("14F", "intimate_images", "intimate images"),
    ("14G", "electronic_monitoring", "electronic monitoring"),
    ("14H", "evaluation", "evaluation"),
    ("14I", "treatment", "treatment"),
    ("14J", "personal_belongings", "personal belongings"),
    ("14K", "no_transfer_assets", "no transfer of assets"),
    ("14K_fin", "financial_relief", "financial relief"),
    ("14L", "vehicle_use", "use of vehicle"),
    ("14M", "restrict_abusive_litigation", "restrict abusive litigation"),
    ("14N", "pay_fees", "pay fees and costs"),
    ("14O", "surrender_weapons", "surrender weapons"),
    ("14P", "custody", "custody"),
    ("14Q", "no_interference_custody", "no interference with custody"),
    ("14R", "no_removal_from_state", "no removal from state"),
    ("14S", "school_enrollment", "school enrollment"),
    ("14T", "pets_custody", "pet custody"),
    ("14U", "pets_no_interference", "no interference with pets"),
    ("14V", "pets_stay_away", "stay away from pets"),
    ("14Z", "other", "other"),
]
_WA_RESTRAINT_ITEMS = {item: key for item, key, _ in _WA_RESTRAINTS}

_RESTRAINT_FIELDS = tuple(
    FormField(item, f"Restraint: {label}", source="wa.restraints", needs_legal_review=True)
    for item, _key, label in _WA_RESTRAINTS
)

# Restraints needing a parameter to be fillable.
_RESTRAINT_DETAIL_FIELDS = (
    FormField("14D_places", "Stay-away places", source="wa.stay_away_places"),
    FormField("14D_distance", "Stay-away distance (feet)", source="wa.stay_away_distance_feet",
              note="Defaults to 1,000 feet on the form if the survivor didn't pick another."),
    FormField("14J_items", "Personal belongings to recover", source="wa.belongings"),
    FormField("14L_vehicle", "Vehicle for petitioner's use", source="wa.vehicle_use"),
    FormField("14T_pets", "Pets to protect", source="wa.pets"),
)

WA_PO001_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("caption_petitioner", "Petitioner name", source="petitioner.legal_name",
              required=True),
    FormField("caption_petitioner_dob", "Petitioner DOB", source="petitioner.dob"),
    FormField("caption_respondent", "Respondent name", source="respondent.legal_name",
              required=True),
    FormField("caption_respondent_dob", "Respondent DOB", source="respondent.dob"),

    # 1 — Protection order type (single-select). DV path for the Vault.
    FormField("1", "Protection order type", derive=_dv_order_type, needs_legal_review=True,
              note="Vault assumes a Domestic Violence order (PTORPRT). Confirm the matter "
                   "isn't better suited to a sexual-assault / stalking / anti-harassment order."),

    # 3 — Restrained person
    FormField("3_name", "Restrained person name", source="respondent.legal_name", required=True),
    FormField("3_age", "Restrained person age band", source="respondent.age_band"),

    # 4 — Protected persons
    FormField("4_me", "Protected person (petitioner) name", source="petitioner.legal_name",
              required=True),
    FormField("4_children", "Protected minor children", source="protected_persons.children[]",
              note="Names only; WA wants age/gender/race/lives-with/relationship per child — WG2."),

    # 5 — Service address
    FormField("5_mail", "Service mailing address", source="petitioner.safe_mailing_address",
              required=True),
    FormField("5_email", "Service email", source="petitioner.safe_email"),

    # 6, 7 — Interpreter / accommodations
    FormField("6", "Interpreter needed / language", source="petitioner.interpreter_language"),
    FormField("7", "Disability accommodations", source="petitioner.disability_accommodation"),

    # 8 — Relationship of the parties
    FormField("8", "Relationship of parties", source="relationship.type", needs_legal_review=True,
              note="Maps the intake relationship type onto WA's intimate-partner / "
                   "family-household checkboxes — confirm the box."),

    # 9 — Connection to Washington (jurisdiction)
    FormField("9", "Connection to Washington (jurisdiction basis)", source="wa.jurisdiction_basis"),

    # 10, 11 — Restrained person residence / other court cases
    FormField("10", "Restrained person residence", source="respondent.last_known_address",
              note="Free-text; WA wants in-WA city/county vs outside vs unknown — confirm."),
    FormField("11", "Other court cases exist", source="prior_orders.exists",
              note="Existence only; WA wants a per-case table — partial."),

    # 12, 13 — Immediate (temporary) order + weapons surrender
    FormField("12", "Temporary (immediate) protection order requested",
              source="wa.temporary_order", needs_legal_review=True),
    FormField("13", "Immediate weapons surrender requested", source="wa.weapons_surrender",
              needs_legal_review=True),

    # 14 — Protections requested (restraints A-Z) + details (appended below).
    *_RESTRAINT_FIELDS,
    *_RESTRAINT_DETAIL_FIELDS,

    # 15, 16, 17
    FormField("15", "Law-enforcement help requested", source=None, note="Not collected — WG6."),
    FormField("16", "Length of order requested", source="wa.order_length", needs_legal_review=True),
    FormField("17", "Firearms restoration notice preference",
              source="wa.firearms_restoration_notice"),

    # 18, 19 — Incident statements
    FormField("18_date", "Most recent incident date", source="incidents[].date", required=True),
    FormField("18_narrative", "Most recent incident statement", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),
    FormField("19", "Past incidents statement", source="wa.past_incidents"),

    # 20, 21, 22 — Background (optional free-text on the form; not collected — WG9)
    FormField("20", "Petitioner medical treatment", source=None,
              note="Optional; not collected — WG9."),
    FormField("21", "Restrained person suicidal behavior", source=None,
              note="Optional; not collected — WG9."),
    FormField("22", "Restrained person substance abuse", source=None,
              note="Optional; not collected — WG9."),

    # 23 — Minors needing protection
    FormField("23", "Minors needing protection (detail)", source="protected_persons.children[]",
              note="Presence only — WG2."),

    # 24 — Supporting evidence
    FormField("24", "Supporting evidence types", source="wa.evidence_types"),

    # Firearms (item 14-O question + Attachment E)
    FormField("fw_access", "Restrained person has firearms",
              source="firearm.respondent_has_access"),
    FormField("fw_types", "Firearm description (Attachment E)", source="firearm.types[]"),
    FormField("fw_locations", "Firearm location (Attachment E)", source="firearm.locations[]"),

    # Signature
    FormField("sig_name", "Petitioner printed name (signature)", source="petitioner.legal_name",
              required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """WA resolver — adds the restraint-checkbox rule, else the basic lookup.

    `wa.restraints` is one intake list that checks many item-14 boxes, one per
    requested restraint (item -> restraint key in `_WA_RESTRAINT_ITEMS`).
    """
    if f.source == "wa.restraints" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _WA_RESTRAINT_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto WA PO 001 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=WA_PO001_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
