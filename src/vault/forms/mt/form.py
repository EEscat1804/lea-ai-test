"""Montana Sworn Petition for Temporary Order of Protection form mapping.

Maps Vault intake answers onto the Montana Attorney General's Office **Sworn
Petition for Temporary Order of Protection and Request for Hearing** (AGO Form
OVS 3, Mont. Code Ann. § 40-15-201, Revised 02/11). The petition covers the
parties, the protected persons (self / minor children / others), residence and
living situation, the relationship basis, the recent- and past-abuse narrative,
firearms, other court cases, and the item-1 through item-12 relief list. MT's
relief list is its own, distinct from the other states'.

The MT intake section (`vault.intake`, the `_mt_step` method) feeds the
MT-specific items. The form has **no respondent DOB, no physical-description
block, and no respondent-vehicle block** (the "My vehicle" relief is the
petitioner's vehicle as a stay-away place), so MT is in none of those shared
Tier-2 gates and the survivor is never asked for them.

Protection: the petition's caption holds the petitioner's contact address;
intake only ever holds a safe mailing address, and item 4 lets the petitioner
keep their home location off the form ("if you want the location of your home to
be secret, do not list"). See coverage.md.

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

FORM_ID = "OVS 3"
FORM_REVISION = "2011-02"  # AGO Form OVS 3, Revised 02/11
JURISDICTION = "MT"


def _immediate_danger(_answers: dict[str, Any]) -> str:
    """Para 1 — "I believe I am in danger of harm" if no TOP issues immediately."""
    return "checked"


def _protected_myself(_answers: dict[str, Any]) -> str:
    """Para 2 — the petitioner is always among the protected persons (self)."""
    return "checked"


# "I ask the Court to Order the Following" — items 1-12 relief. Item 11 (parenting)
# is a choose-one, mapped separately. Membership over `mt.relief`.
_MT_RELIEF = {
    "r_1_no_violence": "no_violence",  # 1 no acts/threats of violence
    "r_2_no_contact": "no_contact",  # 2 no harass / contact / communicate
    "r_3_no_remove_children": "no_remove_children",  # 3 not take children from county/state
    "r_4_stay_away": "stay_away",  # 4 stay-away distance + places
    "r_5_firearms": "firearms",  # 5 not possess firearms used/threatened
    "r_6_no_property_damage": "no_property_damage",  # 6 not take/hide/damage property
    "r_7_possession": "possession",  # 7 give petitioner possession/use of items
    "r_8_peace_officer": "peace_officer",  # 8 peace-officer help with possession
    "r_9_counseling": "counseling",  # 9 violence / chemical-dependency counseling
    "r_10_other_safety": "other_safety",  # 10 other orders for safety / welfare
    "r_12_other_relief": "other_relief",  # 12 other relief as just and proper
}

# Item 4 — places the respondent must stay away from. Membership over
# `mt.stay_away_places`.
_MT_STAY_AWAY_PLACES = {
    "sa_me": "me",
    "sa_minor_children": "minor_children",
    "sa_other_people": "other_people",
    "sa_home": "home",
    "sa_job": "job",
    "sa_vehicle": "vehicle",
    "sa_school": "school",
    "sa_other": "other",
}

# Para 3 — living situation. Membership over `mt.living_situation`.
_MT_LIVING_SITUATION = {
    "live_respondent_not_with_me": "respondent_not_with_me",
    "live_with_respondent": "live_with_respondent",
    "live_left_residence": "left_residence",
}

# Para 3 — reason for wanting to return to a left residence. Membership over
# `mt.return_reason`.
_MT_RETURN_REASON = {
    "return_live": "live_there",
    "return_belongings": "get_belongings",
    "return_other": "other",
}

_MEMBERSHIP = {
    "mt.relief": _MT_RELIEF,
    "mt.stay_away_places": _MT_STAY_AWAY_PLACES,
    "mt.living_situation": _MT_LIVING_SITUATION,
    "mt.return_reason": _MT_RETURN_REASON,
}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="mt.relief", needs_legal_review=True)
    for item, key in _MT_RELIEF.items()
)
_STAY_AWAY_FIELDS = tuple(
    FormField(item, f"Stay away from: {key.replace('_', ' ')}", source="mt.stay_away_places")
    for item, key in _MT_STAY_AWAY_PLACES.items()
)
_LIVING_FIELDS = tuple(
    FormField(item, f"Living situation: {key.replace('_', ' ')}", source="mt.living_situation")
    for item, key in _MT_LIVING_SITUATION.items()
)
_RETURN_FIELDS = tuple(
    FormField(item, f"Return to residence: {key.replace('_', ' ')}", source="mt.return_reason")
    for item, key in _MT_RETURN_REASON.items()
)

MT_TOP_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "court_type",
        "Court (justice / city / municipal / district / tribal)",
        source="mt.court_type",
    ),
    FormField("county", "County", source="mt.county", required=True),
    FormField("petitioner", "Petitioner name", source="petitioner.legal_name", required=True),
    FormField(
        "petitioner_address",
        "Petitioner contact address",
        source="petitioner.safe_mailing_address",
        note="Safe mailing address only; item 4 lets the home location stay off the form.",
    ),
    FormField("petitioner_phone", "Petitioner telephone", source="petitioner.safe_phone"),
    FormField("respondent", "Respondent name", source="respondent.legal_name", required=True),
    FormField(
        "respondent_residence",
        "Respondent residence (city / county / state)",
        source="respondent.last_known_address",
        note="Form wants city/county/state separately — partial, MTG1.",
    ),
    # 1 — Request for TOP (immediate danger)
    FormField(
        "immediate_danger",
        "Petitioner is in danger of harm absent a TOP (§ 40-15-201)",
        derive=_immediate_danger,
        needs_legal_review=True,
        note="Standard sworn allegation — the harm finding rests on the narrative; attorney "
        "confirms it is supported.",
    ),
    # 2 — Protected persons
    FormField("protected_myself", "Protect: myself", derive=_protected_myself),
    FormField(
        "protected_children",
        "Protect: minor child/ren",
        source="protected_persons.children[]",
        note="Names; the form wants each child's age / relationship / lives-with — partial, MTG2.",
    ),
    FormField("protected_other", "Protect: other people", source="mt.other_protected"),
    # 3 — Residence / living situation
    FormField(
        "abuse_location",
        "City/county/state where the abuse happened",
        source="incidents[].location",
        note="Form wants city/county/state separately — partial, MTG1.",
    ),
    *_LIVING_FIELDS,
    *_RETURN_FIELDS,
    # 4 — Relationship basis
    FormField(
        "relationship_basis",
        "Petitioner's relationship to respondent",
        source="relationship.type",
        needs_legal_review=True,
        note="Maps the intake relationship type onto MT's para-4 checklist (married / "
        "separated / divorced / dating / live-together / child in common / family member / "
        "former dating). Sexual-assault/stalking and child-contact bases are alternatives "
        "an attorney confirms — MTG3.",
    ),
    # 5A — Recent abuse
    FormField("recent_abuse_date", "Date of most recent abuse", source="incidents[].date"),
    FormField("recent_abuse_who", "Who was there", source="incidents[].witnesses_present"),
    FormField("recent_abuse_where", "Where it took place", source="incidents[].location"),
    FormField(
        "recent_abuse_narrative",
        "What the respondent did or said (recent)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField(
        "recent_abuse_weapon", "Gun/weapon used or threatened", source="incidents[].weapon_involved"
    ),
    FormField("recent_abuse_injury", "Injuries described", source="incidents[].injury"),
    FormField("recent_abuse_police", "Did the police come", source="incidents[].police_called"),
    # 5B — Past abuse
    FormField(
        "past_abuse",
        "Past abuse narrative",
        source=None,
        note="Not collected separately from the most-recent statement — MTG4.",
    ),
    # 6 — Firearms
    FormField(
        "firearms_possess",
        "Respondent currently possesses firearms",
        source="firearm.respondent_has_access",
    ),
    FormField("firearms_location", "Where the firearms are located", source="firearm.locations[]"),
    # 7 — Other court cases
    FormField(
        "other_cases",
        "Other court cases (divorce / criminal / etc.)",
        source="prior_orders.exists",
        note="Protective-order existence only; the family-law/criminal case detail tables are "
        "not collected — MTG5.",
    ),
    FormField("other_cases_detail", "Other cases (free text)", source="mt.other_cases"),
    # 1-12 — Relief + details
    *_RELIEF_FIELDS,
    FormField(
        "stay_away_feet", "Stay-away distance (feet, up to 1500)", source="mt.stay_away_feet"
    ),
    *_STAY_AWAY_FIELDS,
    FormField(
        "firearms_relief_detail",
        "Firearms the respondent must not possess (item 5)",
        source="mt.firearms_relief_detail",
    ),
    FormField(
        "possession_detail",
        "Items / residence / vehicle to give the petitioner (item 7)",
        source="mt.possession_detail",
    ),
    FormField(
        "other_safety_detail",
        "Other safety/welfare orders (item 10)",
        source="mt.other_safety_detail",
    ),
    # 11 — Parenting (choose one)
    FormField(
        "parenting_choice",
        "Parenting of children (not applicable / protections suffice / Appendix A visitation)",
        source="mt.parenting",
        note="Justice/City/Municipal courts can list children but cannot make parenting plans; "
        "Appendix A is a temporary visitation schedule, not assembled here — MTG6.",
    ),
    # Verification
    FormField(
        "signature",
        "Petitioner signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn under oath / affirmed and notarized (or before a judge/clerk) — at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MT resolver — adds the relief / stay-away / living / return membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MT AGO Form OVS 3 fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MT_TOP_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
