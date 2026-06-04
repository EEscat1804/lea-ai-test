"""North Dakota Petition for Civil Protection Order form mapping.

Maps Vault intake answers onto the North Dakota District Court **Petition for
Civil Protection Order** (N.D.C.C. Ch. 14-07.7, Rev. Mar 2026). It is a combined
petition for three order types — Domestic Violence Protection Order, Sexual
Assault Restraining Order, and Disorderly Conduct Restraining Order — and the
court issues the single order giving the most protection the petitioner
qualifies for. The petition covers the parties, the order type(s), venue, the
relationship basis, respondent descriptive info, the incident statements, and the
requested temporary relief.

The ND intake section (`vault.intake`, the `_nd_step` method plus the shared
physical-description and vehicle blocks — ND is in those sets) feeds the
ND-specific items. ND's relief list is its own, distinct from the other states'.

Protection: the form lets the petitioner keep their address on a separate
Confidential Information Form; intake only ever holds a safe mailing address, and
the confidential-address request defaults on. See coverage.md.

Same contract as the other form modules (see `_base`): never renders a PDF,
never guesses, flags attorney-review mappings.

Owners: Pranav, Aaron.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vault.forms._base import (
    STATUS_FILLED,
    STATUS_NOT_COLLECTED,
    FormField,
    assemble_form,
    resolve_basic,
)

FORM_ID = "Petition CPO"
FORM_REVISION = "2026-03"  # Rev. Mar 2026
JURISDICTION = "ND"


def _victim_petitioner(_answers: dict[str, Any]) -> str:
    """Para 4 — the petitioner is the victim of the conduct complained of."""
    return "checked"


def _confidential_address(_answers: dict[str, Any]) -> str:
    """Para 6 — request that the address stay confidential (Confidential Info Form)."""
    return "checked"


def _request_hearing(_answers: dict[str, Any]) -> str:
    """Para 15 — request a hearing and a permanent order after it."""
    return "checked"


def _not_minor(answers: dict[str, Any]) -> str | None:
    """Para 5 — "I am not a minor child", checked when the petitioner is an adult."""
    dob_str = answers.get("petitioner.dob")
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    age = today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day))
    return "checked" if age >= 18 else None


def _respondent_age(answers: dict[str, Any]) -> str | None:
    """Para 8 — respondent age, from respondent.dob."""
    dob_str = answers.get("respondent.dob")
    if not isinstance(dob_str, str) or not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return None
    today = datetime.now()
    return str(today.year - dob.year - ((dob.month, dob.day) > (today.month, today.day)))


# Para 2 — order type(s). Membership over `nd.order_types`.
_ND_ORDER_TYPES = {
    "ot_domestic_violence": "domestic_violence",
    "ot_sexual_assault": "sexual_assault",
    "ot_disorderly_conduct": "disorderly_conduct",
}

# Para 3 — venue basis. Membership over `nd.venue`.
_ND_VENUE = {
    "venue_live_here": "live_here",
    "venue_child_lives_here": "child_lives_here",
    "venue_respondent_lives_here": "respondent_lives_here",
    "venue_conduct_here": "conduct_here",
    "venue_other": "other",
}

# Para 14 — requested relief. Membership over `nd.relief`.
_ND_RELIEF = {
    "r_restrain_contact": "restrain_contact",
    "r_exclude_places": "exclude_places",
    "r_prohibit_contact": "prohibit_contact",
    "r_custody": "custody",
    "r_parenting_time": "parenting_time",
    "r_surrender_firearms": "surrender_firearms",
    "r_protect_animals": "protect_animals",
    "r_stop_disorderly": "stop_disorderly",
}

# Para 14 — places to exclude from. Membership over `nd.exclude_places`.
_ND_EXCLUDE = {
    "ex_residence": "residence",
    "ex_employment": "employment",
    "ex_school": "school",
    "ex_daycare": "daycare",
    "ex_other": "other",
}

_MEMBERSHIP = {
    "nd.order_types": _ND_ORDER_TYPES,
    "nd.venue": _ND_VENUE,
    "nd.relief": _ND_RELIEF,
    "nd.exclude_places": _ND_EXCLUDE,
}

_ORDER_TYPE_FIELDS = tuple(
    FormField(
        item,
        f"Order type: {key.replace('_', ' ')}",
        source="nd.order_types",
        needs_legal_review=True,
    )
    for item, key in _ND_ORDER_TYPES.items()
)
_VENUE_FIELDS = tuple(
    FormField(item, f"Venue: {key.replace('_', ' ')}", source="nd.venue")
    for item, key in _ND_VENUE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="nd.relief", needs_legal_review=True)
    for item, key in _ND_RELIEF.items()
)
_EXCLUDE_FIELDS = tuple(
    FormField(item, f"Exclude from: {key.replace('_', ' ')}", source="nd.exclude_places")
    for item, key in _ND_EXCLUDE.items()
)

ND_CPO_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField("county", "County", source="nd.county", required=True),
    FormField("judicial_district", "Judicial district", source="nd.judicial_district"),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    # 2 — Order type(s) requested
    *_ORDER_TYPE_FIELDS,
    # 3 — Venue
    *_VENUE_FIELDS,
    # 4 — Protected individuals / relationship
    FormField("victim_petitioner", "Petitioner is the victim", derive=_victim_petitioner),
    FormField(
        "relationship_basis",
        "Petitioner's relationship to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto ND's para-4 relationship checklist "
        "(spouse / family member / dating / live-together / etc.). Attorney confirms.",
    ),
    FormField(
        "protected_children",
        "Minor child victims (para 4 table)",
        source="protected_persons.children[]",
        note="Names; form wants each child's age / lives-with / relationship — partial, NDG1.",
    ),
    # 5 — Minor petitioner
    FormField(
        "not_minor",
        "Petitioner is not a minor child",
        derive=_not_minor,
        note="Checked when the petitioner is 18+; minor-petitioner path is a legal "
        "determination — NDG2.",
    ),
    # 6 — Petitioner address (confidential)
    FormField(
        "confidential_address",
        "Address kept confidential (Confidential Info Form)",
        derive=_confidential_address,
        note="Defaulted on — the survivor's home address is never collected.",
    ),
    # 7 — Respondent identity
    FormField("respondent_address", "Respondent address", source="respondent.last_known_address"),
    FormField(
        "respondent_ssn",
        "Respondent SSN",
        source=None,
        note="Not collected by intake (sensitive) — NDG3.",
    ),
    FormField("respondent_employer", "Respondent employer", source="respondent.employer_name"),
    # 8 — Respondent age
    FormField("respondent_dob", "Respondent date of birth", source="respondent.dob"),
    FormField("respondent_age", "Respondent age", derive=_respondent_age),
    # 9 — Descriptive info
    FormField(
        "respondent_gender",
        "Respondent gender",
        source="respondent.gender",
        note="Reads respondent.gender — NOT petitioner's.",
    ),
    FormField("respondent_race", "Respondent race", source="respondent.race"),
    FormField("respondent_height", "Respondent height", source="respondent.height"),
    FormField("respondent_weight", "Respondent weight", source="respondent.weight"),
    FormField("respondent_eyes", "Respondent eye color", source="respondent.eye_color"),
    FormField("respondent_hair", "Respondent hair color", source="respondent.hair_color"),
    FormField(
        "respondent_marks",
        "Respondent distinguishing marks",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_vehicle",
        "Respondent vehicle make/model",
        source="respondent.vehicle_make_model",
    ),
    FormField(
        "respondent_vehicle_plate", "Respondent vehicle plate", source="respondent.vehicle_plate"
    ),
    FormField(
        "respondent_dl",
        "Respondent driver's license",
        source=None,
        note="Not collected by intake — NDG3.",
    ),
    # 10, 11 — Other cases
    FormField(
        "custody_cases",
        "Current custody/parenting-time cases",
        source=None,
        note="Not collected by intake — NDG4.",
    ),
    FormField(
        "other_cases",
        "Other civil/criminal cases",
        source="prior_orders.exists",
        note="Protective-order existence only; full case list not collected — NDG4.",
    ),
    # 12, 13 — Incident statements
    FormField("recent_incident_date", "Date of most recent incident", source="incidents[].date"),
    FormField(
        "recent_incidents",
        "Most recent incidents (para 12)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "past_incidents",
        "Past incidents (para 13)",
        source=None,
        note="Not collected separately from the most-recent statement — NDG5.",
    ),
    # 14 — Requested temporary relief + details
    *_RELIEF_FIELDS,
    *_EXCLUDE_FIELDS,
    FormField("stay_away_feet", "Stay-away distance (feet)", source="nd.stay_away_feet"),
    FormField("firearms_detail", "Firearms/weapons to surrender", source="nd.firearms_detail"),
    FormField("animals_detail", "Animals to protect", source="nd.animals_detail"),
    # 15, 16 — Hearing / notification
    FormField("request_hearing", "Request hearing + permanent order", derive=_request_hearing),
    FormField("notification", "Notify petitioner when respondent served", source="nd.notification"),
    # 17 — Verification / signature
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Declared under penalty of perjury (North Dakota) — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """ND resolver — adds the order-type/venue/relief/exclude membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto ND Petition for Civil Protection Order (auditable map)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=ND_CPO_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
