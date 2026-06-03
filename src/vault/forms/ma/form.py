"""Massachusetts Chapter 209A Complaint for Protection from Abuse form mapping.

Maps Vault intake answers onto the Massachusetts **Chapter 209A Complaint
Packet** (TC0061, G.L. c. 209A): the Complaint for Protection from Abuse, the
Affidavit, the **Plaintiff Confidential Information Form** (sealed), and the
Defendant Information Form (defendant identifiers for police service).

The MA intake section (`vault.intake`, the `jurisdiction == "MA"` block) plus
the shared physical/vehicle blocks feed the MA-specific items.

Protection by design: the plaintiff's home/work/school address is **not
collected** by intake (only a safe mailing address) — so it never lands on the
public complaint — and the relief list includes explicit "keep my address off
the order" requests. See coverage.md.

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

FORM_ID = "TC0061-209A"
FORM_REVISION = "2024-09"
JURISDICTION = "MA"

# Nature-of-abuse boxes (Complaint) — membership over `ma.abuse_types`.
_MA_ABUSE = {
    "ab_physical_harm": "physical_harm",
    "ab_attempted_harm": "attempted_harm",
    "ab_fear_imminent": "fear_imminent",
    "ab_sexual_coercion": "sexual_coercion",
    "ab_cc_child": "coercive_control_child",
    "ab_cc_animal": "coercive_control_animal",
    "ab_cc_images": "coercive_control_images",
    "ab_cc_pattern": "coercive_control_pattern",
}

# Request-for-relief boxes (Complaint) — membership over `ma.relief`.
_MA_RELIEF = {
    "r_stop_abusing": "stop_abusing",
    "r_no_contact": "no_contact",
    "r_no_contact_except": "no_contact_except",
    "r_leave_residence": "leave_residence",
    "r_leave_workplace": "leave_workplace",
    "r_leave_school": "leave_school",
    "r_address_off_home": "address_off_home",
    "r_address_off_work": "address_off_work",
    "r_address_off_school": "address_off_school",
    "r_compensation": "compensation",
    "r_support_alimony": "child_support_alimony",
    "r_custody": "custody",
    "r_no_contact_children": "no_contact_children",
    "r_stay_away_children_school": "stay_away_children_school",
    "r_animal_protection": "animal_protection",
    "r_animal_possession": "animal_possession",
    "r_other": "other",
}

_MEMBERSHIP = {"ma.abuse_types": _MA_ABUSE, "ma.relief": _MA_RELIEF}

_ABUSE_FIELDS = tuple(
    FormField(item, f"Abuse: {key.replace('_', ' ')}", source="ma.abuse_types",
              needs_legal_review=True)
    for item, key in _MA_ABUSE.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="ma.relief",
              needs_legal_review=True)
    for item, key in _MA_RELIEF.items()
)

MA_209A_FIELDS: tuple[FormField, ...] = (
    # --- Complaint ---
    FormField("c_plaintiff", "Plaintiff name", source="petitioner.legal_name", required=True),
    FormField("c_defendant", "Defendant name", source="respondent.legal_name", required=True),
    FormField("c_abuse_date", "Date(s) of abuse", source="incidents[].date"),
    *_ABUSE_FIELDS,
    FormField("c_relationship", "Qualifying relationship", source="relationship.type",
              needs_legal_review=True,
              note="Maps the intake relationship type onto the 209A relationship checkboxes."),
    FormField("c_other_court", "Open/closed court matters", source="prior_orders.exists",
              note="PO existence only — partial, MG1."),
    *_RELIEF_FIELDS,
    FormField("c_compensation_detail", "Compensation losses", source="ma.compensation"),
    FormField("c_contact_methods", "Permitted contact methods", source="ma.contact_methods"),
    FormField("c_animals", "Animal(s)", source="ma.animals"),
    FormField("c_other_relief", "Other relief detail", source="ma.other_relief"),
    FormField("c_children", "Children under 18", source="protected_persons.children[]",
              note="Names; form wants name + age per child (page 2) — MG2."),
    FormField("c_signature", "Plaintiff signature (printed name)", source="petitioner.legal_name",
              required=True),

    # --- Affidavit ---
    FormField("aff_date", "Affidavit: date(s) of abuse", source="incidents[].date"),
    FormField("aff_narrative", "Affidavit: describe the abuse", source="incidents[].narrative",
              required=True, note="Survivor's own words — verbatim (guardrail G-08)."),

    # --- Plaintiff Confidential Information Form (sealed) ---
    FormField("pci_name", "Plaintiff name", source="petitioner.legal_name"),
    FormField("pci_dob", "Plaintiff DOB", source="petitioner.dob"),
    FormField("pci_interpreter", "Interpreter / language",
              source="petitioner.interpreter_language"),
    FormField("pci_email", "Plaintiff email", source="petitioner.safe_email"),
    FormField("pci_phone", "Plaintiff cellphone", source="petitioner.safe_phone"),
    FormField("pci_home_address", "Plaintiff home address", source=None,
              note="NOT collected by intake — only a safe mailing address — so the "
                   "survivor's home address never reaches the form. Protection by design."),

    # --- Defendant Information Form (for police service) ---
    FormField("dif_name", "Defendant name", source="respondent.legal_name"),
    FormField("dif_dob", "Defendant DOB", source="respondent.dob"),
    FormField("dif_sex", "Defendant sex", source="respondent.gender"),
    FormField("dif_race", "Defendant race", source="respondent.race"),
    FormField("dif_eyes", "Defendant eyes", source="respondent.eye_color"),
    FormField("dif_hair", "Defendant hair", source="respondent.hair_color"),
    FormField("dif_height", "Defendant height", source="respondent.height"),
    FormField("dif_weight", "Defendant weight", source="respondent.weight"),
    FormField("dif_marks", "Defendant other physical characteristics",
              source="respondent.distinguishing_marks"),
    FormField("dif_home_address", "Defendant home address", source="respondent.last_known_address"),
    FormField("dif_employer", "Defendant workplace/employer", source="respondent.employer_name"),
    FormField("dif_work_address", "Defendant work address", source="respondent.employer_address"),
    FormField("dif_vehicle_make_model", "Defendant vehicle make/model",
              source="respondent.vehicle_make_model"),
    FormField("dif_vehicle_color", "Defendant vehicle color", source="respondent.vehicle_color"),
    FormField("dif_vehicle_plate", "Defendant vehicle plate", source="respondent.vehicle_plate"),
    FormField("dif_firearms", "Defendant access to firearms",
              source="firearm.respondent_has_access"),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """MA resolver — adds the abuse/relief membership rules, else basic lookup."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto MA 209A packet fields (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=MA_209A_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
