"""Maine Complaint for Protection from Abuse form mapping.

Maps Vault intake answers onto Maine's **Complaint for Protection from Abuse**
(Maine Judicial Branch Form PA-001, 19-A M.R.S. §§ 4101-4116, Rev. 09/25;
District Court). The complaint covers the parties, the plaintiff's relationship
to the defendant (§4), the parents/children blocks (§§5-6), public assistance and
other court cases (§§7-9), the temporary (ex parte) order election (§10), the
defendant's access to and use of weapons (§11), the abuse narrative (§12), and the
relief checklist (orders a-q). ME's relationship and relief lists are their own.

The respondent physical-description and vehicle blocks come from the companion
**Protection Order Service Information** sheet (Form PA-005), which is filed with
every PFA complaint — so ME is in `PHYSICAL_DESCRIPTION_STATES` and
`VEHICLE_DESCRIPTION_STATES` and the shared gates feed those identifiers.

The ME intake section (`vault.intake`, the `_me_step` method) plus the shared
physical-description, vehicle, and minor-filing gates feeds these items.

Protection: Maine offers a real confidential-contact-address mechanism — the
**Affidavit of Confidential Address** (Form PA-015). Intake only ever holds a safe
mailing address, so `address_confidential` is derived `"checked"` and the
petitioner address maps to the safe mailing address (PA-015 is filed alongside).
The complaint requests support via order (m), but the petitioner SSN lives on a
separate confidential disclosure form (CR-CV-FM-PC-200) filed only in family /
support matters — the PA-001 itself has no SSN field, so ME is NOT in the
SSN-for-support gate. See coverage.md.

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

FORM_ID = "PA-001"
FORM_REVISION = "2025-09"  # Form PA-001, Rev. 09/25
JURISDICTION = "ME"


def _address_confidential(_answers: dict[str, Any]) -> str:
    """Petitioner uses Maine's Affidavit of Confidential Address (PA-015).

    Intake only ever holds a safe mailing address (never the residential street
    address), so the confidential-address election is the safe default; an
    attorney/advocate confirms PA-015 is filed.
    """
    return "checked"


# §4 — plaintiff's relationship to the defendant. Membership over
# `me.relationship_basis`.
_ME_RELATIONSHIP = {
    "4_spouse": "married",
    "4_former_spouse": "former_spouse",
    "4_parent_of_child": "parent_of_child",
    "4_minor_child_household": "minor_child_household",
    "4_relative": "relative",
    "4_sexual_partner": "sexual_partner",
    "4_living_together": "living_together",
    "4_dating_partner": "dating_partner",
    "4_dependent_adult": "dependent_adult",
    "4_sex_trafficking": "sex_trafficking",
    "4_condom_tampering": "condom_tampering",
    "4_sexual_assault": "sexual_assault",
    "4_stalking": "stalking",
    "4_image_dissemination": "image_dissemination",
    "4_minor_exploitation": "minor_exploitation",
    "4_minor_harassment": "minor_harassment",
}

# §10 — temporary (ex parte) order election. Membership over `me.temporary_order`.
_ME_TEMPORARY_ORDER = {
    "10_self_danger": "self_danger",
    "10_children_danger": "children_danger",
    "10_not_requesting": "not_requesting",
}

# §11 — defendant's access to / possession of weapons. Membership over
# `me.weapon_access`.
_ME_WEAPON_ACCESS = {
    "11_firearm": "firearm",
    "11_muzzle_loading": "muzzle_loading",
    "11_bow_crossbow": "bow_crossbow",
    "11_other_weapon": "other_dangerous",
}

# "Therefore, I ask the court to enter ... orders" (a-q). Membership over
# `me.relief`.
_ME_RELIEF = {
    "order_a_stop_abuse": "stop_abuse",
    "order_b_no_contact": "no_contact",
    "order_c_no_enter_residence": "no_enter_residence",
    "order_d_no_follow": "no_follow",
    "order_e_stay_distance": "stay_distance",
    "order_f_no_weapons": "no_weapons",
    "order_g_remove_images": "remove_images",
    "order_h_possession_residence": "possession_residence",
    "order_i_possession_property_pets": "possession_property_pets",
    "order_j_parental_rights": "parental_rights",
    "order_k_defendant_contact": "defendant_contact",
    "order_l_counseling": "counseling",
    "order_m_support": "support",
    "order_n_monetary_relief": "monetary_relief",
    "order_o_trafficking_damages": "trafficking_damages",
    "order_p_no_passport_tampering": "no_passport_tampering",
    "order_q_other": "other",
}

_MEMBERSHIP = {
    "me.relationship_basis": _ME_RELATIONSHIP,
    "me.temporary_order": _ME_TEMPORARY_ORDER,
    "me.weapon_access": _ME_WEAPON_ACCESS,
    "me.relief": _ME_RELIEF,
}

_RELATIONSHIP_FIELDS = tuple(
    FormField(
        item,
        f"Relationship: {key.replace('_', ' ')}",
        source="me.relationship_basis",
        needs_legal_review=True,
    )
    for item, key in _ME_RELATIONSHIP.items()
)
_TEMPORARY_ORDER_FIELDS = tuple(
    FormField(
        item,
        f"Temporary order: {key.replace('_', ' ')}",
        source="me.temporary_order",
        needs_legal_review=True,
    )
    for item, key in _ME_TEMPORARY_ORDER.items()
)
_WEAPON_ACCESS_FIELDS = tuple(
    FormField(item, f"Weapon access: {key.replace('_', ' ')}", source="me.weapon_access")
    for item, key in _ME_WEAPON_ACCESS.items()
)
_RELIEF_FIELDS = tuple(
    FormField(item, f"Relief: {key.replace('_', ' ')}", source="me.relief", needs_legal_review=True)
    for item, key in _ME_RELIEF.items()
)

ME_PFA_FIELDS: tuple[FormField, ...] = (
    # Caption
    FormField(
        "court_location",
        "District Court location (town)",
        source="me.court_location",
        required=True,
    ),
    FormField(
        "docket_number",
        "Docket number",
        source=None,
        note="Assigned by the clerk at filing — MEG1.",
    ),
    # 1 — Plaintiff information
    FormField("petitioner", "Plaintiff full name", source="petitioner.legal_name", required=True),
    FormField("petitioner_gender", "Plaintiff gender", source="petitioner.gender"),
    FormField("petitioner_dob", "Plaintiff date of birth", source="petitioner.dob"),
    FormField(
        "petitioner_address",
        "Plaintiff contact address",
        source="petitioner.safe_mailing_address",
        needs_legal_review=True,
        note="Safe mailing address only; the residential address is withheld via PA-015.",
    ),
    FormField("petitioner_phone", "Plaintiff telephone", source="petitioner.safe_phone"),
    FormField(
        "address_confidential",
        "Confidential address requested (PA-015 filed)",
        derive=_address_confidential,
        needs_legal_review=True,
        note="Maine's Affidavit of Confidential Address (PA-015); attorney/advocate confirms it "
        "is filed.",
    ),
    FormField(
        "petitioner_children",
        "Minor child(ren) filed on behalf of — names",
        source="protected_persons.children[]",
        note="Names; the form wants each minor's name / DOB / gender — partial, MEG2.",
    ),
    # 2 — Defendant information
    FormField("respondent", "Defendant full name", source="respondent.legal_name", required=True),
    FormField("respondent_gender", "Defendant gender", source="respondent.gender"),
    FormField(
        "respondent_dob", "Defendant date of birth (or approximate age)", source="respondent.dob"
    ),
    FormField("respondent_race", "Defendant race", source="respondent.race"),
    FormField("respondent_address", "Defendant address", source="respondent.last_known_address"),
    # PA-005 service sheet — physical description + vehicle (shared Tier-2 gates)
    FormField("respondent_height", "Defendant height (PA-005)", source="respondent.height"),
    FormField("respondent_weight", "Defendant weight (PA-005)", source="respondent.weight"),
    FormField("respondent_eyes", "Defendant eye color (PA-005)", source="respondent.eye_color"),
    FormField("respondent_hair", "Defendant hair color (PA-005)", source="respondent.hair_color"),
    FormField(
        "respondent_features",
        "Defendant distinguishing features (PA-005)",
        source="respondent.distinguishing_marks",
    ),
    FormField(
        "respondent_employer", "Defendant employer name (PA-005)", source="respondent.employer_name"
    ),
    FormField(
        "respondent_employer_address",
        "Defendant work address (PA-005)",
        source="respondent.employer_address",
    ),
    FormField(
        "respondent_vehicle",
        "Defendant vehicle make/model/year (PA-005)",
        source="respondent.vehicle_make_model",
    ),
    FormField(
        "respondent_vehicle_color",
        "Defendant vehicle color (PA-005)",
        source="respondent.vehicle_color",
    ),
    FormField(
        "respondent_vehicle_plate",
        "Defendant vehicle registration / plate (PA-005)",
        source="respondent.vehicle_plate",
    ),
    # 3 — Defendant's military service
    FormField(
        "defendant_military",
        "Defendant's military service (in / not in / unable to determine)",
        source="me.defendant_military",
        note="Form requires selecting one; intake records what the petitioner knows.",
    ),
    # 4 — Relationship basis
    *_RELATIONSHIP_FIELDS,
    # 5/6 — Parents of minor children + custody/residence
    FormField(
        "parents_children",
        "Plaintiff and defendant are parents of these minor children",
        source="protected_persons.children[]",
        note="Names only; the form wants each child's DOB / gender / present address — MEG2.",
    ),
    FormField(
        "custody_residence",
        "Custody / residence of the minor children (§6)",
        source=None,
        note="Primary-residence, third-party-custody, and 5-year-residence tables are not "
        "collected — MEG3.",
    ),
    # 7 — Public assistance and child support
    FormField(
        "public_assistance",
        "Public assistance / DHHS support contact (§7)",
        source=None,
        note="Not collected by intake — MEG4.",
    ),
    # 8/9 — Other court cases / actions
    FormField(
        "other_cases",
        "Other court cases involving the parties (§§8-9)",
        source="prior_orders.exists",
        note="Protective-order existence only; the custody/divorce/criminal case detail tables "
        "are not collected — MEG5.",
    ),
    FormField("other_cases_detail", "Other cases (free text)", source="me.other_cases_detail"),
    # 10 — Temporary (ex parte) order election
    *_TEMPORARY_ORDER_FIELDS,
    # 11 — Defendant access / possession / use of weapons
    *_WEAPON_ACCESS_FIELDS,
    FormField(
        "weapon_detail",
        "Weapon description / location (§11)",
        source="me.weapon_detail",
        note="Also fed by Tier-1 firearm.locations[] when firearms are involved.",
    ),
    FormField(
        "weapon_locations",
        "Firearm locations (Tier-1)",
        source="firearm.locations[]",
    ),
    FormField(
        "weapon_ever_used",
        "Defendant ever used a weapon to intimidate / threaten / abuse (§11)",
        source="me.weapon_ever_used",
    ),
    FormField(
        "weapon_used_detail",
        "What happened with the weapon (§11)",
        source="me.weapon_used_detail",
    ),
    # 12 — Abuse narrative
    FormField(
        "abuse_narrative",
        "Why the plaintiff is asking for protection (§12)",
        source="incidents[].narrative",
        required=True,
        note="Survivor's own words — passed through verbatim (guardrail G-08).",
    ),
    FormField("abuse_date", "Date of the abuse", source="incidents[].date"),
    FormField("abuse_location", "Where the abuse happened", source="incidents[].location"),
    FormField("abuse_witnesses", "Who was there", source="incidents[].witnesses_present"),
    FormField("abuse_injury", "Injuries described", source="incidents[].injury"),
    # Relief — orders a-q + conditional details
    *_RELIEF_FIELDS,
    FormField(
        "order_h_residence_address",
        "Residence the defendant must leave (order h)",
        source="me.residence_address",
    ),
    FormField(
        "order_i_property_detail",
        "Personal property / pets / animals to protect (order i)",
        source="me.property_detail",
    ),
    FormField(
        "order_e_stay_distance_detail",
        "Specified distance / location (order e)",
        source="me.stay_distance_detail",
    ),
    FormField(
        "order_q_other_detail",
        "Other relief requested (order q)",
        source="me.relief_other_detail",
    ),
    # Verification
    FormField(
        "signature",
        "Plaintiff signature (printed name)",
        source="petitioner.legal_name",
        required=True,
        note="Sworn under penalty of perjury; notarized (or filed electronically with the "
        "certification) at filing.",
    ),
)


def _resolve(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """ME resolver — adds the relationship / temporary-order / weapon / relief membership rules."""
    if f.source in _MEMBERSHIP and f.source in answers:
        value = answers[f.source]
        if isinstance(value, list):
            wanted = _MEMBERSHIP[f.source].get(f.item)
            return ("checked" if wanted in value else None), (
                STATUS_FILLED if wanted in value else STATUS_NOT_COLLECTED
            )
    return resolve_basic(f, answers)


def assemble(answers: dict[str, Any]) -> dict[str, Any]:
    """Map intake answers onto ME PA-001 PFA complaint (auditable map, never a PDF)."""
    return assemble_form(
        form_id=FORM_ID,
        revision=FORM_REVISION,
        jurisdiction=JURISDICTION,
        fields=ME_PFA_FIELDS,
        answers=answers,
        resolve=_resolve,
    )
