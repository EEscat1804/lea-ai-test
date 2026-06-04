"""Pennsylvania Petition for Protection from Abuse (PFA) form mapping.

Maps Vault intake answers onto the Pennsylvania **Petition for Protection from
Abuse** (23 Pa.C.S. ch. 61). The PFA is a large form: plaintiff/defendant
parties + a defendant-identifiers box, relationship, court/criminal history,
children, the most-recent-incident statement, firearms (item 13 + Attachment
A), and an A-P list of relief requested.

The PA intake section (`vault.intake`, the `jurisdiction == "PA"` block) plus
the shared physical-description block feed the PA-specific items. PA's relief
list (A-P) is its own, distinct from the other states'.

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

FORM_ID = "PA-PFA"
FORM_REVISION = "current"
JURISDICTION = "PA"


def _on_behalf_myself(_answers: dict[str, Any]) -> str:
    """Item 3 — the survivor files for themselves in the Vault flow."""
    return "myself"


def _immediate_danger(_answers: dict[str, Any]) -> str:
    """Item 15 — the petition asserts immediate and present danger."""
    return "checked"


# Item A-P relief requested. Intake collects choices as `pa.relief`; each box is
# checked by membership. (item, relief key, label.)
_PA_RELIEF = [
    ("relief_a", "restrain_abuse", "restrain from abuse"),
    ("relief_b", "evict", "evict/exclude from residence"),
    ("relief_c", "other_housing", "other suitable housing"),
    ("relief_d", "custody", "temporary custody of children"),
    ("relief_e", "no_contact", "no contact with plaintiff/children"),
    ("relief_f", "no_contact_family", "no contact with relatives"),
    ("relief_g", "relinquish_firearms", "relinquish firearms"),
    ("relief_h", "prohibit_firearms", "prohibit acquiring firearms"),
    ("relief_i", "support", "temporary support"),
    ("relief_j", "financial_losses", "pay financial losses"),
    ("relief_k", "pay_costs", "pay costs of action"),
    ("relief_l", "attorney_fees", "attorney's fees"),
    ("relief_m", "other", "additional relief"),
    ("relief_n", "court_discretion", "relief the court deems appropriate"),
    ("relief_o", "police_serve", "order police to serve defendant"),
    ("relief_p", "police_escort", "police accompany plaintiff"),
]
_PA_RELIEF_ITEMS = {item: key for item, key, _ in _PA_RELIEF}

_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief {item[-1].upper()}: {label}", source="pa.relief",
              needs_legal_review=True)
    for item, _key, label in _PA_RELIEF
)

PA_PFA_FIELDS: tuple[FormField, ...] = (
    # 1 — Plaintiff
    FormField("1_plaintiff", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("1_plaintiff_dob", "Plaintiff DOB", source="petitioner.dob"),
    FormField("1_plaintiff_address", "Plaintiff address", source="petitioner.safe_mailing_address"),

    # 2 — Defendant + identifiers box
    FormField("2_defendant", "Defendant name", source="respondent.legal_name", required=True),
    FormField("2_defendant_address", "Defendant address", source="respondent.last_known_address"),
    FormField("def_dob", "Defendant DOB", source="respondent.dob"),
    FormField("def_sex", "Defendant sex", source="respondent.gender"),
    FormField("def_race", "Defendant race", source="respondent.race"),
    FormField("def_height", "Defendant height", source="respondent.height"),
    FormField("def_weight", "Defendant weight", source="respondent.weight"),
    FormField("def_eyes", "Defendant eyes", source="respondent.eye_color"),
    FormField("def_hair", "Defendant hair", source="respondent.hair_color"),
    FormField("def_ssn", "Defendant SSN", source=None, note="Not collected — PG1."),
    FormField("def_dl", "Defendant driver's license", source=None, note="Not collected — PG1."),
    FormField("def_employer", "Defendant place of employment", source="respondent.employer_name"),
    FormField("caution_weapon", "Caution: weapon involved", source="incidents[].weapon_involved"),

    # 3, 4 — Filing on behalf / persons protected
    FormField("3_on_behalf", "Filing on behalf of", derive=_on_behalf_myself),
    FormField("4_persons_protected", "Persons seeking protection",
              source="protected_persons.children[]",
              note="Children names; plaintiff is also a protected person — PG2."),

    # 5 — Relationship
    FormField("5_relationship", "Relationship between plaintiff and defendant",
              source="relationship.type", needs_legal_review=True,
              note="Maps the intake relationship type onto PA's relationship checkboxes."),

    # 6, 7 — Court actions / criminal history
    FormField("6_court_actions", "Prior court actions (divorce/custody/support/PFA)",
              source="prior_orders.exists", note="PO existence only — partial, PG3."),
    FormField("7_criminal", "Defendant criminal court action",
              source="respondent.prior_criminal_history"),

    # 8 — Minor children in common
    FormField("8_children", "Minor children of plaintiff and defendant",
              source="protected_persons.children[]", note="Names; ages/addresses — PG2."),

    # 11 — Most recent incident
    FormField("11_incident_date", "Most recent incident date", source="incidents[].date"),
    FormField("11_incident_place", "Most recent incident place", source="incidents[].location"),
    FormField("11_incident_narrative", "Most recent incident description",
              source="incidents[].narrative", required=True,
              note="Survivor's own words — verbatim (guardrail G-08)."),

    # 12, 13 — Prior abuse / firearms
    FormField("12_prior_abuse", "Prior acts of abuse", source=None,
              note="Not collected (pattern only) — PG4."),
    FormField("13a_weapon_used", "Defendant used/threatened weapon",
              source="incidents[].weapon_involved"),
    FormField("13b_owns_firearms", "Defendant owns/possesses firearms",
              source="firearm.respondent_has_access"),

    # 14 — Law-enforcement agency to receive the order
    FormField("14_le_agency", "Law-enforcement agency to serve the order", source=None,
              note="Not collected — PG5."),
    # 15 — Immediate and present danger
    FormField("15_immediate_danger", "Immediate and present danger asserted",
              derive=_immediate_danger),

    # Relief requested (A-P) + details
    *_RELIEF_FIELDS,
    FormField("relief_b_residence", "Residence to evict from", source="pa.evict_residence"),
    FormField("relief_d_restrictions", "Custody contact restrictions",
              source="pa.custody_restrictions"),
    FormField("relief_j_losses", "Out-of-pocket financial losses", source="pa.financial_losses"),
    FormField("relief_m_other", "Additional relief detail", source="pa.other_relief"),

    # Verification signature
    FormField("sig_plaintiff", "Plaintiff signature (printed name)",
              source="petitioner.legal_name", required=True),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """PA resolver — adds the relief-checkbox rule, else the basic lookup."""
    if f.source == "pa.relief" and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _PA_RELIEF_ITEMS.get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto PA PFA fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=PA_PFA_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
