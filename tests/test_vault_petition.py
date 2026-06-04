import asyncio
import json
from datetime import datetime

import pytest

from vault.forms import ca
from vault.petition import (
    assemble_petition,
    handle_petition_request,
    supported_jurisdictions,
)

# A completed CA intake (Tier-1 core + the CA fields the petition reads).
_CA_ANSWERS = {
    "petitioner.legal_name": "Jane Doe",
    "petitioner.dob": "1990-01-01",
    "petitioner.safe_mailing_address": "PO Box 5, Oakland, CA 94601",
    "petitioner.safe_phone": "510-555-0100",
    "petitioner.safe_email": "jane@safe.example",
    "respondent.legal_name": "John Roe",
    "relationship.type": "dating",
    "relationship.live_together_now": False,
    "relationship.lived_together_past": True,
    "relationship.children_in_common": False,
    "incidents[].date": "2026-05-01",
    "incidents[].narrative": "He grabbed my phone and would not let me leave.",
    "incidents[].witnesses_present": "A neighbor",
    "incidents[].police_called": True,
    "incidents[].weapon_involved": False,
    "incidents[].injury": "Bruised wrist",
    "incidents[].pattern_frequency": "Weekly",
    "protected_persons.children[]": "None",
    "firearm.respondent_has_access": False,
    "prior_orders.exists": False,
}


def test_dispatch_unsupported_jurisdiction_raises():
    # A state without a forms module must fail loudly, not return an empty form.
    # AZ is a handoff jurisdiction (e-files through a state portal) with no form
    # package — assembly must raise, never return an empty form.
    with pytest.raises(NotImplementedError):
        assemble_petition("AZ", _CA_ANSWERS)


def test_ca_is_supported():
    assert "CA" in supported_jurisdictions()


def test_assemble_returns_form_metadata():
    out = assemble_petition("CA", _CA_ANSWERS)
    assert out["form"] == "DV-100"
    assert out["jurisdiction"] == "CA"
    assert out["revision"] == "2025-01-01"


def test_direct_fields_mapped_from_intake():
    fields = assemble_petition("CA", _CA_ANSWERS)["fields"]
    assert fields["1a"]["value"] == "Jane Doe"
    assert fields["1a"]["status"] == "filled"
    assert fields["2a"]["value"] == "John Roe"
    assert fields["5f"]["value"].startswith("He grabbed my phone")


def test_petitioner_age_is_derived_from_dob():
    fields = assemble_petition("CA", _CA_ANSWERS)["fields"]
    # DOB is Jan 1, so the birthday has always passed by any later date this year.
    expected = datetime.now().year - 1990
    assert fields["1b"]["value"] == str(expected)
    assert fields["1b"]["status"] == "filled"


def test_relationship_enum_checks_correct_box():
    fields = assemble_petition("CA", _CA_ANSWERS)["fields"]
    # "dating" => item 3d checked, 3b (married) not.
    assert fields["3d"]["value"] == "checked"
    assert fields["3b"]["status"] != "filled"


def test_lived_together_past_checks_item_3g():
    fields = assemble_petition("CA", _CA_ANSWERS)["fields"]
    assert fields["3g"]["value"] == "checked"


def test_missing_required_field_is_fact_needed_not_guessed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("CA", answers)
    assert out["fields"]["1a"]["value"] == "[FACT NEEDED]"
    assert out["fields"]["1a"]["status"] == "fact_needed"
    assert "1a" in out["gaps"]


def test_respondent_identifiers_absent_are_not_collected():
    # When this answer set omits respondent age/DOB/gender/race they surface as
    # not_collected — never silently blank or pulled from the petitioner's data.
    fields = assemble_petition("CA", _CA_ANSWERS)["fields"]
    for item in ("2b", "2c", "2d", "2e"):
        assert fields[item]["status"] == "not_collected"


def test_respondent_identity_maps_when_provided():
    answers = {
        **_CA_ANSWERS,
        "respondent.age": "40",
        "respondent.dob": "1986-02-02",
        "respondent.gender": "male",
        "respondent.race": "Latino",
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["2b"]["value"] == "40"
    assert fields["2d"]["value"] == "male"
    assert fields["2e"]["value"] == "Latino"


def test_married_intact_checks_3b_former_checks_3c():
    intact = {**_CA_ANSWERS, "relationship.type": "married", "relationship.marriage_intact": True}
    former = {**_CA_ANSWERS, "relationship.type": "married", "relationship.marriage_intact": False}
    fb = assemble_petition("CA", intact)["fields"]
    ff = assemble_petition("CA", former)["fields"]
    assert fb["3b"]["value"] == "checked"
    assert fb["3c"]["status"] != "filled"
    assert ff["3c"]["value"] == "checked"
    assert ff["3b"]["status"] != "filled"


def test_additional_incident_maps_to_items_6_and_7():
    answers = {
        **_CA_ANSWERS,
        "incident_2.date": "2026-04-01",
        "incident_2.narrative": "He followed me home.",
        "incident_3.date": "2026-03-10",
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["6a"]["value"] == "2026-04-01"
    assert fields["6f"]["value"] == "He followed me home."
    assert fields["7a"]["value"] == "2026-03-10"


def test_protected_why_maps():
    answers = {**_CA_ANSWERS, "protected_persons.why": "He has threatened the kids."}
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["8_why"]["value"] == "He has threatened the kids."


def test_order_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "selected_reliefs_intents": ["property_control", "pay_debts", "transfer_phone"],
        "relief.property_describe": "the family car",
        "relief.debts": ["Rent owed to landlord $1200"],
        "relief.transfer_phone_numbers": ["408-555-0199"],
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["17_describe"]["value"] == "the family car"
    assert fields["22_items"]["value"] == ["Rent owed to landlord $1200"]
    assert fields["28_numbers"]["value"] == ["408-555-0199"]


def test_petitioner_gender_does_not_leak_into_respondent_gender():
    # Regression: respondent gender (2d) reads respondent.gender, never the
    # petitioner's. A petitioner.gender answer must not fill 2d.
    answers = {**_CA_ANSWERS, "petitioner.gender": "female"}
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["2d"]["status"] == "not_collected"
    assert fields["2d"]["value"] is None


def test_no_orders_selected_leaves_boxes_unchecked():
    # With no orders selected, the request boxes are simply unchecked (not gaps).
    out = assemble_petition("CA", _CA_ANSWERS)
    for item in ("10", "11", "12", "13", "16"):
        assert out["fields"][item]["status"] == "not_collected"


def test_selected_reliefs_intents_checks_support_boxes():
    answers = {**_CA_ANSWERS, "selected_reliefs_intents": ["child_support"]}
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["24"]["value"] == "checked"
    assert fields["25"]["status"] != "filled"  # spousal not requested


def test_selected_orders_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "selected_reliefs_intents": ["no_abuse", "no_contact", "stay_away"],
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["10"]["value"] == "checked"
    assert fields["11"]["value"] == "checked"
    assert fields["12"]["value"] == "checked"
    # An order that wasn't selected stays unchecked.
    assert fields["13"]["status"] == "not_collected"


def test_stay_away_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "selected_reliefs_intents": ["stay_away"],
        "relief.stay_away_places": ["home", "work"],
        "relief.stay_away_distance_yards": 150,
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["12_places"]["value"] == ["home", "work"]
    assert fields["12_distance"]["value"] == 150


def test_move_out_address_maps():
    answers = {
        **_CA_ANSWERS,
        "selected_reliefs_intents": ["move_out"],
        "relief.move_out_address": "123 Main St, Oakland, CA",
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["13"]["value"] == "checked"
    assert fields["13_address"]["value"] == "123 Main St, Oakland, CA"


def test_protect_animals_list_maps():
    answers = {
        **_CA_ANSWERS,
        "selected_reliefs_intents": ["protect_animals"],
        "relief.animals[]": ["Rex (dog)", "Whiskers (cat)"],
    }
    fields = assemble_petition("CA", answers)["fields"]
    assert fields["16"]["value"] == "checked"
    assert fields["16_list"]["value"] == ["Rex (dog)", "Whiskers (cat)"]


def test_review_items_surface_for_attorney():
    out = assemble_petition("CA", _CA_ANSWERS)
    # Relationship checkboxes and the address split need legal confirmation.
    assert "1c" in out["review_items"]
    assert "3d" in out["review_items"]


def test_ca_field_table_items_are_unique():
    items = [f.item for f in ca.CA_DV100_FIELDS]
    assert len(items) == len(set(items))


# --- Washington PO 001 ---


def test_wa_is_supported():
    assert "WA" in supported_jurisdictions()


def test_wa_assemble_returns_form_metadata():
    out = assemble_petition("WA", _CA_ANSWERS)
    assert out["form"] == "PO 001"
    assert out["jurisdiction"] == "WA"
    assert out["revision"] == "2026-01"


def test_wa_maps_tier1_fields():
    fields = assemble_petition("WA", _CA_ANSWERS)["fields"]
    assert fields["caption_petitioner"]["value"] == "Jane Doe"
    assert fields["3_name"]["value"] == "John Roe"
    assert fields["18_narrative"]["value"].startswith("He grabbed my phone")


def test_wa_order_type_is_domestic_violence():
    fields = assemble_petition("WA", _CA_ANSWERS)["fields"]
    assert fields["1"]["value"] == "Domestic Violence (PTORPRT)"
    assert "1" in assemble_petition("WA", _CA_ANSWERS)["review_items"]


def test_wa_selected_restraints_check_their_boxes():
    answers = {**_CA_ANSWERS, "wa.restraints": ["no_harm", "stay_away"]}
    fields = assemble_petition("WA", answers)["fields"]
    assert fields["14A"]["value"] == "checked"  # no_harm
    assert fields["14D"]["value"] == "checked"  # stay_away
    assert fields["14B"]["status"] == "not_collected"  # no_contact not selected


def test_wa_restraint_detail_and_wa_specific_fields_map():
    answers = {
        **_CA_ANSWERS,
        "wa.restraints": ["stay_away"],
        "wa.stay_away_places": ["residence", "workplace"],
        "wa.stay_away_distance_feet": 1000,
        "respondent.age_band": "18_or_over",
        "wa.temporary_order": True,
        "wa.order_length": "one_year",
        "wa.jurisdiction_basis": ["lives_here"],
    }
    fields = assemble_petition("WA", answers)["fields"]
    assert fields["14D_places"]["value"] == ["residence", "workplace"]
    assert fields["14D_distance"]["value"] == 1000
    assert fields["3_age"]["value"] == "18_or_over"
    assert fields["12"]["value"] is True
    assert fields["16"]["value"] == "one_year"
    assert fields["9"]["value"] == ["lives_here"]


def test_wa_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("WA", answers)
    assert out["fields"]["caption_petitioner"]["value"] == "[FACT NEEDED]"
    assert "caption_petitioner" in out["gaps"]


def test_wa_field_table_items_are_unique():
    from vault.forms import wa

    items = [f.item for f in wa.WA_PO001_FIELDS]
    assert len(items) == len(set(items))


# --- Virginia DC-383 ---


def test_va_is_supported_and_metadata():
    assert "VA" in supported_jurisdictions()
    out = assemble_petition("VA", _CA_ANSWERS)
    assert out["form"] == "DC-383"
    assert out["jurisdiction"] == "VA"


def test_va_maps_core_fields():
    fields = assemble_petition("VA", _CA_ANSWERS)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["2"]["value"].startswith("He grabbed my phone")
    assert fields["5"]["value"] is False  # firearm.respondent_has_access


def test_va_conditions_check_their_boxes():
    answers = {**_CA_ANSWERS, "va.conditions": ["no_violence", "companion_animal"]}
    fields = assemble_petition("VA", answers)["fields"]
    assert fields["cond_violence"]["value"] == "checked"
    assert fields["cond_animal"]["value"] == "checked"
    assert fields["cond_contact"]["status"] == "not_collected"


def test_va_preliminary_and_animal_detail_map():
    answers = {
        **_CA_ANSWERS,
        "va.preliminary_order": True,
        "va.conditions": ["companion_animal"],
        "va.companion_animal": "Rex (dog)",
        "respondent.race": "not disclosed",
    }
    fields = assemble_petition("VA", answers)["fields"]
    assert fields["preliminary_order"]["value"] is True
    assert fields["cond_animal_desc"]["value"] == "Rex (dog)"
    assert fields["desc_race"]["value"] == "not disclosed"


def test_va_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("VA", answers)
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_va_field_table_items_are_unique():
    from vault.forms import va

    items = [f.item for f in va.VA_DC383_FIELDS]
    assert len(items) == len(set(items))


# --- Texas Application for Protective Order ---


def test_tx_is_supported_and_metadata():
    assert "TX" in supported_jurisdictions()
    out = assemble_petition("TX", _CA_ANSWERS)
    assert out["form"] == "TX-APO"
    assert out["jurisdiction"] == "TX"


def test_tx_maps_core_and_affidavit_fields():
    fields = assemble_petition("TX", _CA_ANSWERS)["fields"]
    assert fields["1_applicant"]["value"] == "Jane Doe"
    assert fields["1_respondent"]["value"] == "John Roe"
    assert fields["2_family_violence"]["value"] == "checked"
    assert fields["aff_incident_narrative"]["value"].startswith("He grabbed my phone")


def test_tx_terms_check_their_boxes():
    answers = {**_CA_ANSWERS, "tx.terms": ["no_family_violence", "prohibit_firearm"]}
    fields = assemble_petition("TX", answers)["fields"]
    assert fields["8a"]["value"] == "checked"  # no_family_violence
    assert fields["8k"]["value"] == "checked"  # prohibit_firearm
    assert fields["8m"]["status"] == "not_collected"  # protect_pet not selected


def test_tx_children_orders_and_ex_parte_map():
    answers = {
        **_CA_ANSWERS,
        "tx.children_orders": ["child_support", "no_removal_jurisdiction"],
        "tx.ex_parte": True,
        "tx.confidential": True,
    }
    fields = assemble_petition("TX", answers)["fields"]
    assert fields["12_child_support"]["value"] == "checked"
    assert fields["12_possession_schedule"]["status"] == "not_collected"
    assert fields["13_ex_parte"]["value"] is True
    assert fields["14_confidential"]["value"] is True


def test_tx_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("TX", answers)
    assert out["fields"]["1_applicant"]["value"] == "[FACT NEEDED]"
    assert "1_applicant" in out["gaps"]


def test_tx_field_table_items_are_unique():
    from vault.forms import tx

    items = [f.item for f in tx.TX_APO_FIELDS]
    assert len(items) == len(set(items))


# --- Pennsylvania Petition for Protection from Abuse ---


def test_pa_is_supported_and_metadata():
    assert "PA" in supported_jurisdictions()
    out = assemble_petition("PA", _CA_ANSWERS)
    assert out["form"] == "PA-PFA"
    assert out["jurisdiction"] == "PA"


def test_pa_maps_core_fields():
    fields = assemble_petition("PA", _CA_ANSWERS)["fields"]
    assert fields["1_plaintiff"]["value"] == "Jane Doe"
    assert fields["2_defendant"]["value"] == "John Roe"
    assert fields["3_on_behalf"]["value"] == "myself"
    assert fields["15_immediate_danger"]["value"] == "checked"
    assert fields["11_incident_narrative"]["value"].startswith("He grabbed my phone")


def test_pa_relief_checks_their_boxes():
    answers = {**_CA_ANSWERS, "pa.relief": ["restrain_abuse", "relinquish_firearms"]}
    fields = assemble_petition("PA", answers)["fields"]
    assert fields["relief_a"]["value"] == "checked"  # restrain_abuse
    assert fields["relief_g"]["value"] == "checked"  # relinquish_firearms
    assert fields["relief_e"]["status"] == "not_collected"  # no_contact not selected


def test_pa_evict_detail_maps():
    answers = {**_CA_ANSWERS, "pa.relief": ["evict"], "pa.evict_residence": "5 Pine St"}
    fields = assemble_petition("PA", answers)["fields"]
    assert fields["relief_b"]["value"] == "checked"
    assert fields["relief_b_residence"]["value"] == "5 Pine St"


def test_pa_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("PA", answers)
    assert out["fields"]["1_plaintiff"]["value"] == "[FACT NEEDED]"
    assert "1_plaintiff" in out["gaps"]


def test_pa_field_table_items_are_unique():
    from vault.forms import pa

    items = [f.item for f in pa.PA_PFA_FIELDS]
    assert len(items) == len(set(items))


# --- North Carolina Complaint for DV Protective Order ---


def test_nc_is_supported_and_metadata():
    assert "NC" in supported_jurisdictions()
    out = assemble_petition("NC", {**_CA_ANSWERS, "nc.county": "Wake"})
    assert out["form"] == "AOC-CV-303"
    assert out["jurisdiction"] == "NC"


def test_nc_maps_core_fields():
    fields = assemble_petition("NC", {**_CA_ANSWERS, "nc.county": "Wake"})["fields"]
    assert fields["plaintiff"]["value"] == "Jane Doe"
    assert fields["defendant"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Wake"
    assert fields["2_acts_in_nc"]["value"] == "checked"
    assert fields["5_abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_nc_relief_checks_their_boxes():
    answers = {**_CA_ANSWERS, "nc.county": "Wake", "nc.relief": ["no_abuse", "surrender_firearms"]}
    fields = assemble_petition("NC", answers)["fields"]
    assert fields["r3"]["value"] == "checked"  # no_abuse
    assert fields["r13"]["value"] == "checked"  # surrender_firearms
    assert fields["r8"]["status"] == "not_collected"  # no_contact not selected


def test_nc_relief_detail_maps():
    answers = {
        **_CA_ANSWERS, "nc.county": "Wake",
        "nc.relief": ["stay_away", "vehicle"],
        "nc.stay_away_places": ["residence", "work"],
        "nc.vehicle": "blue sedan",
    }
    fields = assemble_petition("NC", answers)["fields"]
    assert fields["r7_places"]["value"] == ["residence", "work"]
    assert fields["r9_vehicle"]["value"] == "blue sedan"


def test_nc_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NC", {**answers, "nc.county": "Wake"})
    assert out["fields"]["plaintiff"]["value"] == "[FACT NEEDED]"
    assert "plaintiff" in out["gaps"]


def test_nc_field_table_items_are_unique():
    from vault.forms import nc

    items = [f.item for f in nc.NC_AOC303_FIELDS]
    assert len(items) == len(set(items))


# --- New York Family Offense Petition ---


def test_ny_is_supported_and_metadata():
    assert "NY" in supported_jurisdictions()
    out = assemble_petition("NY", {**_CA_ANSWERS, "ny.county": "Kings"})
    assert out["form"] == "UCS-FC8-2"
    assert out["jurisdiction"] == "NY"


def test_ny_maps_core_fields_and_confidential_default():
    fields = assemble_petition("NY", {**_CA_ANSWERS, "ny.county": "Kings"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["4_narrative"]["value"].startswith("He grabbed my phone")
    # Address confidentiality defaults to Yes — a protection-minded default.
    assert fields["1_address_confidential"]["value"] == "Yes"


def test_ny_offense_checklist_is_left_to_attorney():
    # Item 4 offense classification is legal characterization — not guessed.
    fields = assemble_petition("NY", {**_CA_ANSWERS, "ny.county": "Kings"})["fields"]
    assert fields["4_offenses"]["status"] == "not_collected"
    assert "4_offenses" in assemble_petition("NY", {**_CA_ANSWERS, "ny.county": "Kings"})[
        "review_items"
    ]


def test_ny_relief_and_order_of_protection_derived():
    answers = {
        **_CA_ANSWERS,
        "ny.county": "Kings",
        "ny.relief": ["stay_away", "surrender_firearms"],
    }
    fields = assemble_petition("NY", answers)["fields"]
    assert fields["r_stay_away"]["value"] == "checked"
    assert fields["r_surrender"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"
    # The parent "order of protection" box checks when any condition is requested.
    assert fields["10b_order_protection"]["value"] == "checked"


def test_ny_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NY", {**answers, "ny.county": "Kings"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ny_field_table_items_are_unique():
    from vault.forms import ny

    items = [f.item for f in ny.NY_FOP_FIELDS]
    assert len(items) == len(set(items))


# --- Massachusetts Chapter 209A Complaint ---


def test_ma_is_supported_and_metadata():
    assert "MA" in supported_jurisdictions()
    out = assemble_petition("MA", _CA_ANSWERS)
    assert out["form"] == "TC0061-209A"
    assert out["jurisdiction"] == "MA"


def test_ma_maps_core_and_defendant_info():
    answers = {**_CA_ANSWERS, "respondent.height": "6ft", "respondent.gender": "male"}
    fields = assemble_petition("MA", answers)["fields"]
    assert fields["c_plaintiff"]["value"] == "Jane Doe"
    assert fields["aff_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["dif_height"]["value"] == "6ft"
    assert fields["dif_sex"]["value"] == "male"


def test_ma_plaintiff_home_address_never_collected():
    # Protection by design: the survivor's home address is never collected, so it
    # cannot reach the (public) complaint.
    fields = assemble_petition("MA", _CA_ANSWERS)["fields"]
    assert fields["pci_home_address"]["status"] == "not_collected"
    assert fields["pci_home_address"]["value"] is None


def test_ma_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ma.abuse_types": ["physical_harm", "fear_imminent"],
        "ma.relief": ["stop_abusing", "address_off_home"],
    }
    fields = assemble_petition("MA", answers)["fields"]
    assert fields["ab_physical_harm"]["value"] == "checked"
    assert fields["ab_fear_imminent"]["value"] == "checked"
    assert fields["ab_sexual_coercion"]["status"] == "not_collected"
    assert fields["r_stop_abusing"]["value"] == "checked"
    assert fields["r_address_off_home"]["value"] == "checked"


def test_ma_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MA", answers)
    assert out["fields"]["c_plaintiff"]["value"] == "[FACT NEEDED]"
    assert "c_plaintiff" in out["gaps"]


def test_ma_field_table_items_are_unique():
    from vault.forms import ma

    items = [f.item for f in ma.MA_209A_FIELDS]
    assert len(items) == len(set(items))


# --- Maryland Petition for Protection from Domestic Violence ---


def test_md_is_supported_and_metadata():
    assert "MD" in supported_jurisdictions()
    out = assemble_petition("MD", _CA_ANSWERS)
    assert out["form"] == "CC-DC-DV-001"
    assert out["jurisdiction"] == "MD"


def test_md_maps_core_and_addendum():
    answers = {**_CA_ANSWERS, "respondent.gender": "male", "respondent.dob": "1985-01-01"}
    fields = assemble_petition("MD", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["2_details"]["value"].startswith("He grabbed my phone")
    assert fields["petition_dv"]["value"] == "checked"
    assert fields["add_sex"]["value"] == "male"


def test_md_address_confidential_defaults_on():
    # Protection-minded: the petitioner's address is withheld by default.
    fields = assemble_petition("MD", _CA_ANSWERS)["fields"]
    assert fields["address_confidential"]["value"] == "checked"


def test_md_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "md.abuse_acts": ["punching", "choking_strangling"],
        "md.relief": ["no_abuse", "leave_home"],
    }
    fields = assemble_petition("MD", answers)["fields"]
    assert fields["ab_punching"]["value"] == "checked"
    assert fields["ab_choking"]["value"] == "checked"
    assert fields["ab_stabbing"]["status"] == "not_collected"
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_leave_home"]["value"] == "checked"


def test_md_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MD", answers)
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_md_field_table_items_are_unique():
    from vault.forms import md

    items = [f.item for f in md.MD_DV001_FIELDS]
    assert len(items) == len(set(items))


# --- Hawai'i Petition for an Order for Protection ---


def test_hi_is_supported_and_metadata():
    assert "HI" in supported_jurisdictions()
    out = assemble_petition("HI", _CA_ANSWERS)
    assert out["form"] == "1F-P-752A"
    assert out["jurisdiction"] == "HI"


def test_hi_maps_core_and_age_band():
    fields = assemble_petition("HI", _CA_ANSWERS)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["6_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["self_represented"]["value"] == "checked"
    # DOB 1990 => adult
    assert fields["2_age_band"]["value"] == "adult_18_or_older"


def test_hi_abuse_harm_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "hi.abuse_acts": ["choke", "punch"],
        "hi.harm_types": ["physical_harm", "coercive_control"],
        "hi.relief": ["no_contact", "vacate"],
    }
    fields = assemble_petition("HI", answers)["fields"]
    assert fields["ab_choke"]["value"] == "checked"
    assert fields["ab_punch"]["value"] == "checked"
    assert fields["ab_grab"]["status"] == "not_collected"
    assert fields["harm_coercive"]["value"] == "checked"
    assert fields["r_no_contact"]["value"] == "checked"
    assert fields["r_vacate"]["value"] == "checked"


def test_hi_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("HI", answers)
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_hi_field_table_items_are_unique():
    from vault.forms import hi

    items = [f.item for f in hi.HI_FOP_FIELDS]
    assert len(items) == len(set(items))


# --- Georgia Petition for Family Violence Protective Order ---


def test_ga_is_supported_and_metadata():
    assert "GA" in supported_jurisdictions()
    out = assemble_petition("GA", {**_CA_ANSWERS, "ga.county": "Fulton"})
    assert out["form"] == "SC-26"
    assert out["jurisdiction"] == "GA"


def test_ga_maps_core_and_sealed_fact_sheet():
    answers = {**_CA_ANSWERS, "ga.county": "Fulton", "respondent.gender": "male",
               "respondent.height": "6ft"}
    fields = assemble_petition("GA", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["4_acts"]["value"].startswith("He grabbed my phone")
    assert fields["1_county"]["value"] == "Fulton"
    # Respondent identifiers land on the sealed fact sheet.
    assert fields["conf_resp_sex"]["value"] == "male"
    assert fields["conf_resp_height"]["value"] == "6ft"


def test_ga_relief_checks_their_boxes():
    answers = {**_CA_ANSWERS, "ga.county": "Fulton",
               "ga.relief": ["no_abuse", "address_confidential", "fvip"]}
    fields = assemble_petition("GA", answers)["fields"]
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_address_confidential"]["value"] == "checked"
    assert fields["r_fvip"]["value"] == "checked"
    assert fields["r_custody"]["status"] == "not_collected"


def test_ga_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("GA", {**answers, "ga.county": "Fulton"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ga_field_table_items_are_unique():
    from vault.forms import ga

    items = [f.item for f in ga.GA_SC26_FIELDS]
    assert len(items) == len(set(items))


# --- Florida Petition for Injunction for Protection Against DV ---


def test_fl_is_supported_and_metadata():
    assert "FL" in supported_jurisdictions()
    out = assemble_petition("FL", {**_CA_ANSWERS, "fl.county": "Miami-Dade"})
    assert out["form"] == "12.980(a)"
    assert out["jurisdiction"] == "FL"


def test_fl_maps_core_and_respondent_description():
    answers = {**_CA_ANSWERS, "fl.county": "Miami-Dade",
               "respondent.gender": "male", "respondent.height": "6ft"}
    fields = assemble_petition("FL", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Miami-Dade"
    assert fields["statement_narrative"]["value"].startswith("He grabbed my phone")
    # Respondent description (for service) reads the respondent's own data.
    assert fields["desc_sex"]["value"] == "male"
    assert fields["desc_height"]["value"] == "6ft"


def test_fl_address_confidential_and_immediate_danger_default_on():
    # Protection-minded: address withheld; the petition asserts immediate danger.
    out = assemble_petition("FL", {**_CA_ANSWERS, "fl.county": "Miami-Dade"})
    fields = out["fields"]
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["immediate_danger"]["value"] == "checked"
    # Both are attorney-confirmed (relationship basis too).
    assert "immediate_danger" in out["review_items"]
    assert "relationship_basis" in out["review_items"]


def test_fl_relief_checks_their_boxes():
    answers = {**_CA_ANSWERS, "fl.county": "Miami-Dade",
               "fl.relief": ["no_dv", "surrender_firearms"]}
    fields = assemble_petition("FL", answers)["fields"]
    assert fields["r_no_dv"]["value"] == "checked"
    assert fields["r_surrender_firearms"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"  # not selected


def test_fl_relief_detail_maps():
    answers = {**_CA_ANSWERS, "fl.county": "Miami-Dade",
               "fl.relief": ["exclusive_residence", "other"],
               "fl.residence_address": "9 Bay St, Miami, FL",
               "fl.other_relief": "Return my passport"}
    fields = assemble_petition("FL", answers)["fields"]
    assert fields["r_exclusive_residence"]["value"] == "checked"
    assert fields["r_exclusive_residence_address"]["value"] == "9 Bay St, Miami, FL"
    assert fields["r_other_detail"]["value"] == "Return my passport"


def test_fl_petitioner_gender_does_not_leak_into_respondent_sex():
    # Regression: respondent sex (desc_sex) reads respondent.gender, never the
    # petitioner's — mirrors the CA 2d guard.
    answers = {**_CA_ANSWERS, "fl.county": "Miami-Dade", "petitioner.gender": "female"}
    fields = assemble_petition("FL", answers)["fields"]
    assert fields["desc_sex"]["status"] == "not_collected"
    assert fields["desc_sex"]["value"] is None


def test_fl_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("FL", {**answers, "fl.county": "Miami-Dade"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_fl_field_table_items_are_unique():
    from vault.forms import fl

    items = [f.item for f in fl.FL_12980A_FIELDS]
    assert len(items) == len(set(items))


# --- Delaware Petition for Order of Protection from Abuse ---


def test_de_is_supported_and_metadata():
    assert "DE" in supported_jurisdictions()
    out = assemble_petition("DE", {**_CA_ANSWERS, "de.county": "new_castle"})
    assert out["form"] == "Form 450"
    assert out["jurisdiction"] == "DE"


def test_de_maps_core_fields():
    fields = assemble_petition("DE", {**_CA_ANSWERS, "de.county": "new_castle"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "new_castle"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_de_confidential_address_defaults_on():
    # Residence always; children only when present (protection-minded).
    base = assemble_petition("DE", {**_CA_ANSWERS, "de.county": "new_castle"})["fields"]
    assert base["conf_residence"]["value"] == "checked"
    # _CA_ANSWERS has protected_persons.children[] == "None" => no children.
    assert base["conf_children"]["status"] == "not_collected"
    with_kids = assemble_petition(
        "DE", {**_CA_ANSWERS, "de.county": "new_castle", "protected_persons.children[]": "Sam (8)"}
    )["fields"]
    assert with_kids["conf_children"]["value"] == "checked"


def test_de_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "de.county": "new_castle",
        "de.abuse_acts": ["physical_injury", "financial_dependency"],
        "de.relief": ["no_abuse", "companion_animal"],
    }
    fields = assemble_petition("DE", answers)["fields"]
    assert fields["ab_physical_injury"]["value"] == "checked"
    assert fields["ab_financial_dependency"]["value"] == "checked"
    assert fields["ab_trespassing"]["status"] == "not_collected"
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_companion_animal"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"


def test_de_stay_away_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "de.county": "new_castle",
        "de.relief": ["stay_away", "exclusive_residence"],
        "de.stay_away_places": ["petitioner", "home"],
        "de.residence_address": "7 King St, Dover, DE",
    }
    fields = assemble_petition("DE", answers)["fields"]
    assert fields["r_stay_away"]["value"] == "checked"
    assert fields["sa_petitioner"]["value"] == "checked"
    assert fields["sa_workplace"]["status"] == "not_collected"
    assert fields["r_exclusive_residence_address"]["value"] == "7 King St, Dover, DE"


def test_de_aggravating_factors_map():
    answers = {
        **_CA_ANSWERS,
        "de.county": "new_castle",
        "de.extended_duration": True,
        "de.aggravating_factors": ["deadly_weapon", "ongoing_danger"],
    }
    fields = assemble_petition("DE", answers)["fields"]
    assert fields["r_extended_duration"]["value"] is True
    assert fields["ag_deadly_weapon"]["value"] == "checked"
    assert fields["ag_prior_convictions"]["status"] == "not_collected"


def test_de_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("DE", {**answers, "de.county": "new_castle"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_de_field_table_items_are_unique():
    from vault.forms import de

    items = [f.item for f in de.DE_FORM450_FIELDS]
    assert len(items) == len(set(items))


# --- District of Columbia Civil Protection Order petition ---


def test_dc_is_supported_and_metadata():
    assert "DC" in supported_jurisdictions()
    out = assemble_petition("DC", _CA_ANSWERS)
    assert out["form"] == "DC-CPO-Petition"
    assert out["jurisdiction"] == "DC"


def test_dc_maps_core_fields_and_substitute_address():
    fields = assemble_petition("DC", _CA_ANSWERS)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["incident_a_narrative"]["value"].startswith("He grabbed my phone")
    # Substitute address requested by default; only the safe mailing address maps.
    assert fields["substitute_address"]["value"] == "checked"
    assert fields["petitioner_substitute_address"]["value"].startswith("PO Box 5")


def test_dc_nexus_fields_map():
    answers = {**_CA_ANSWERS, "dc.petitioner_dc_nexus": True, "dc.incident_in_dc": True}
    fields = assemble_petition("DC", answers)["fields"]
    assert fields["petitioner_dc_nexus"]["value"] is True
    assert fields["incident_in_dc"]["value"] is True


def test_dc_relief_and_subchecklists_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "dc.relief": ["no_abuse", "stay_away", "no_contact", "counseling"],
        "dc.stay_away_places": ["person", "home"],
        "dc.contact_methods": ["telephone", "electronic"],
        "dc.counseling_types": ["domestic_violence"],
    }
    fields = assemble_petition("DC", answers)["fields"]
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["sa_person"]["value"] == "checked"
    assert fields["sa_vehicle"]["status"] == "not_collected"
    assert fields["contact_telephone"]["value"] == "checked"
    assert fields["contact_writing"]["status"] == "not_collected"
    assert fields["couns_dv"]["value"] == "checked"
    assert fields["r_emergency_tpo"]["status"] == "not_collected"  # not selected


def test_dc_relief_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "dc.relief": ["vacate", "property_possession", "other"],
        "dc.vacate_home_basis": "own_together",
        "dc.property_description": "the family laptop",
        "dc.other_relief": "Return my immigration documents",
    }
    fields = assemble_petition("DC", answers)["fields"]
    assert fields["vacate_home_basis"]["value"] == "own_together"
    assert fields["property_description"]["value"] == "the family laptop"
    assert fields["other_detail"]["value"] == "Return my immigration documents"


def test_dc_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("DC", answers)
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_dc_field_table_items_are_unique():
    from vault.forms import dc

    items = [f.item for f in dc.DC_CPO_FIELDS]
    assert len(items) == len(set(items))


# --- Connecticut Application for Relief from Abuse ---


def test_ct_is_supported_and_metadata():
    assert "CT" in supported_jurisdictions()
    out = assemble_petition("CT", {**_CA_ANSWERS, "ct.judicial_district": "Hartford"})
    assert out["form"] == "JD-FM-137"
    assert out["jurisdiction"] == "CT"


def test_ct_maps_core_fields():
    fields = assemble_petition("CT", {**_CA_ANSWERS, "ct.judicial_district": "Hartford"})["fields"]
    assert fields["applicant"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["judicial_district"]["value"] == "Hartford"
    assert fields["affidavit_narrative"]["value"].startswith("He grabbed my phone")


def test_ct_interpreter_maps_for_applicant():
    answers = {**_CA_ANSWERS, "ct.judicial_district": "Hartford",
               "petitioner.interpreter_language": "Spanish"}
    fields = assemble_petition("CT", answers)["fields"]
    assert fields["applicant_interpreter"]["value"] == "Spanish"
    # The form has a respondent interpreter field too, which intake does not collect.
    assert fields["respondent_interpreter"]["status"] == "not_collected"


def test_ct_home_address_never_collected():
    # Protection by design: the applicant's home address can never reach the form.
    fields = assemble_petition("CT", {**_CA_ANSWERS, "ct.judicial_district": "Hartford"})["fields"]
    assert fields["applicant_home_address"]["status"] == "not_collected"
    assert fields["applicant_home_address"]["value"] is None


def test_ct_relief_codes_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ct.judicial_district": "Hartford",
        "ct.relief": ["no_abuse", "stay_100_yards", "protect_animals"],
    }
    fields = assemble_petition("CT", answers)["fields"]
    assert fields["CT01"]["value"] == "checked"  # no_abuse
    assert fields["CT16"]["value"] == "checked"  # stay_100_yards
    assert fields["CT31"]["value"] == "checked"  # protect_animals
    assert fields["CT05"]["status"] == "not_collected"  # no_contact not selected


def test_ct_custody_visitation_derived():
    answers = {
        **_CA_ANSWERS,
        "ct.judicial_district": "Hartford",
        "ct.relief": ["custody"],
        "ct.visitation": "without_visitation",
    }
    fields = assemble_petition("CT", answers)["fields"]
    assert fields["CT20"]["value"] == "checked"
    assert fields["CT22_without_visitation"]["value"] == "checked"
    assert fields["CT21_with_visitation"]["status"] != "filled"


def test_ct_further_order_detail_maps():
    answers = {
        **_CA_ANSWERS,
        "ct.judicial_district": "Hartford",
        "ct.relief": ["further_order"],
        "ct.further_order_detail": "Return my car",
    }
    fields = assemble_petition("CT", answers)["fields"]
    assert fields["item3_further_order"]["value"] == "checked"
    assert fields["item3_detail"]["value"] == "Return my car"


def test_ct_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("CT", {**answers, "ct.judicial_district": "Hartford"})
    assert out["fields"]["applicant"]["value"] == "[FACT NEEDED]"
    assert "applicant" in out["gaps"]


def test_ct_field_table_items_are_unique():
    from vault.forms import ct

    items = [f.item for f in ct.CT_JDFM137_FIELDS]
    assert len(items) == len(set(items))


# --- Colorado Complaint/Motion for Civil Protection Order ---


def test_co_is_supported_and_metadata():
    assert "CO" in supported_jurisdictions()
    out = assemble_petition("CO", {**_CA_ANSWERS, "co.county": "Denver"})
    assert out["form"] == "JDF 402"
    assert out["jurisdiction"] == "CO"


def test_co_maps_core_fields():
    fields = assemble_petition("CO", {**_CA_ANSWERS, "co.county": "Denver"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Denver"
    assert fields["incident_recent_narrative"]["value"].startswith("He grabbed my phone")


def test_co_confidential_address_defaults_on():
    fields = assemble_petition("CO", {**_CA_ANSWERS, "co.county": "Denver"})["fields"]
    assert fields["confidential_address"]["value"] == "checked"


def test_co_basis_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "co.county": "Denver",
        "co.basis": ["domestic_abuse", "stalking"],
        "co.relief": ["no_abuse", "firearm_relinquish"],
    }
    fields = assemble_petition("CO", answers)["fields"]
    assert fields["basis_domestic_abuse"]["value"] == "checked"
    assert fields["basis_stalking"]["value"] == "checked"
    assert fields["basis_sexual_assault"]["status"] == "not_collected"
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_firearm_relinquish"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"


def test_co_stay_away_detail_maps():
    answers = {
        **_CA_ANSWERS,
        "co.county": "Denver",
        "co.relief": ["stay_away"],
        "co.stay_away_distance_yards": 100,
        "co.stay_away_places": ["home", "work"],
    }
    fields = assemble_petition("CO", answers)["fields"]
    assert fields["stay_away_distance"]["value"] == 100
    assert fields["sa_home"]["value"] == "checked"
    assert fields["sa_school"]["status"] == "not_collected"


def test_co_court_type_needs_legal_review():
    out = assemble_petition("CO", {**_CA_ANSWERS, "co.county": "Denver"})
    assert out["fields"]["court_type"]["status"] == "not_collected"
    assert "court_type" in out["review_items"]


def test_co_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("CO", {**answers, "co.county": "Denver"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_co_field_table_items_are_unique():
    from vault.forms import co

    items = [f.item for f in co.CO_JDF402_FIELDS]
    assert len(items) == len(set(items))


# --- Arkansas Petition and Affidavit for an Order of Protection ---


def test_ar_is_supported_and_metadata():
    assert "AR" in supported_jurisdictions()
    out = assemble_petition("AR", {**_CA_ANSWERS, "ar.county": "Pulaski"})
    assert out["form"] == "AR-OP-Petition"
    assert out["jurisdiction"] == "AR"


def test_ar_maps_core_and_derives_age():
    fields = assemble_petition("AR", {**_CA_ANSWERS, "ar.county": "Pulaski"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Pulaski"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    # Petitioner age derived from DOB (1990-01-01).
    assert fields["petitioner_age"]["value"] == str(datetime.now().year - 1990)


def test_ar_omit_address_defaults_on():
    fields = assemble_petition("AR", {**_CA_ANSWERS, "ar.county": "Pulaski"})["fields"]
    assert fields["omit_address"]["value"] == "checked"


def test_ar_relief_checks_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ar.county": "Pulaski",
        "ar.relief": ["exclude_residence", "child_support"],
    }
    fields = assemble_petition("AR", answers)["fields"]
    assert fields["r_exclude_residence"]["value"] == "checked"
    assert fields["r_child_support"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"


def test_ar_relief_detail_maps():
    answers = {
        **_CA_ANSWERS,
        "ar.county": "Pulaski",
        "ar.relief": ["exclude_residence"],
        "ar.residence_address": "12 Oak St, Little Rock",
        "ar.residence_owner": "both",
    }
    fields = assemble_petition("AR", answers)["fields"]
    assert fields["residence_address"]["value"] == "12 Oak St, Little Rock"
    assert fields["residence_owner"]["value"] == "both"


def test_ar_respondent_description_maps():
    answers = {
        **_CA_ANSWERS,
        "ar.county": "Pulaski",
        "respondent.height": "6ft",
        "respondent.gender": "male",
    }
    fields = assemble_petition("AR", answers)["fields"]
    assert fields["respondent_height"]["value"] == "6ft"
    assert fields["respondent_sex"]["value"] == "male"


def test_ar_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("AR", {**answers, "ar.county": "Pulaski"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ar_field_table_items_are_unique():
    from vault.forms import ar

    items = [f.item for f in ar.AR_OP_FIELDS]
    assert len(items) == len(set(items))


# --- Alaska Petition for Domestic Violence Protective Order ---


def test_ak_is_supported_and_metadata():
    assert "AK" in supported_jurisdictions()
    out = assemble_petition("AK", {**_CA_ANSWERS, "ak.court_location": "Anchorage"})
    assert out["form"] == "DV-100"
    assert out["jurisdiction"] == "AK"


def test_ak_maps_core_fields():
    fields = assemble_petition("AK", {**_CA_ANSWERS, "ak.court_location": "Anchorage"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["court_location"]["value"] == "Anchorage"
    assert fields["dv_narrative"]["value"].startswith("He grabbed my phone")


def test_ak_confidential_defaults_on():
    fields = assemble_petition("AK", {**_CA_ANSWERS, "ak.court_location": "Anchorage"})["fields"]
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["dv128_confidential"]["value"] == "checked"


def test_ak_order_type_and_protections_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ak.court_location": "Anchorage",
        "ak.order_type": ["ex_parte", "long_term"],
        "ak.protections": ["no_dv", "possession_vehicle"],
        "ak.long_term_protections": ["surrender_firearm"],
    }
    fields = assemble_petition("AK", answers)["fields"]
    assert fields["order_ex_parte"]["value"] == "checked"
    assert fields["order_long_term"]["value"] == "checked"
    assert fields["p_no_dv"]["value"] == "checked"
    assert fields["p_possession_vehicle"]["value"] == "checked"
    assert fields["p_no_contact"]["status"] == "not_collected"
    assert fields["lt_surrender_firearm"]["value"] == "checked"


def test_ak_protection_and_le_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "ak.court_location": "Anchorage",
        "ak.protections": ["possession_residence"],
        "ak.residence_address": "5 Tundra Rd, Anchorage, AK",
        "ak.le_assistance": ["possession_residence", "recover_items"],
    }
    fields = assemble_petition("AK", answers)["fields"]
    assert fields["p_possession_residence_address"]["value"] == "5 Tundra Rd, Anchorage, AK"
    assert fields["le_possession_residence"]["value"] == "checked"
    assert fields["le_recover_items"]["value"] == "checked"
    assert fields["le_possession_vehicle"]["status"] == "not_collected"


def test_ak_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("AK", {**answers, "ak.court_location": "Anchorage"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ak_field_table_items_are_unique():
    from vault.forms import ak

    items = [f.item for f in ak.AK_DV100_FIELDS]
    assert len(items) == len(set(items))


# --- Alabama Petition for Protection from Abuse ---


def test_al_is_supported_and_metadata():
    assert "AL" in supported_jurisdictions()
    out = assemble_petition("AL", {**_CA_ANSWERS, "al.county": "Jefferson"})
    assert out["form"] == "C-2"
    assert out["jurisdiction"] == "AL"


def test_al_maps_core_and_derives_ages():
    fields = assemble_petition("AL", {**_CA_ANSWERS, "al.county": "Jefferson"})["fields"]
    assert fields["plaintiff"]["value"] == "Jane Doe"
    assert fields["defendant"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Jefferson"
    assert fields["abuse_description"]["value"].startswith("He grabbed my phone")
    # Plaintiff age derived from DOB; adult-eligible box checked.
    assert fields["plaintiff_age"]["value"] == str(datetime.now().year - 1990)
    assert fields["eligible_adult"]["value"] == "checked"


def test_al_address_confidential_defaults_on():
    fields = assemble_petition("AL", {**_CA_ANSWERS, "al.county": "Jefferson"})["fields"]
    assert fields["address_confidential"]["value"] == "checked"


def test_al_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "al.county": "Jefferson",
        "al.abuse_acts": ["injured", "stalked"],
        "al.ex_parte_relief": ["enjoin_abuse", "exclude_residence"],
        "al.final_relief": ["surrender_firearms"],
    }
    fields = assemble_petition("AL", answers)["fields"]
    assert fields["ab_injured"]["value"] == "checked"
    assert fields["ab_stalked"]["value"] == "checked"
    assert fields["ab_kidnapped"]["status"] == "not_collected"
    assert fields["ep1_enjoin_abuse"]["value"] == "checked"
    assert fields["ep7_exclude_residence"]["value"] == "checked"
    assert fields["f17_surrender_firearms"]["value"] == "checked"
    assert fields["f12_attorney_fees"]["status"] == "not_collected"


def test_al_relief_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "al.county": "Jefferson",
        "al.ex_parte_relief": ["exclude_residence"],
        "al.final_relief": ["vehicle_possession"],
        "al.residence_basis": "owned_both",
        "al.vehicle_description": "blue pickup",
    }
    fields = assemble_petition("AL", answers)["fields"]
    assert fields["residence_basis"]["value"] == "owned_both"
    assert fields["f15_vehicle_description"]["value"] == "blue pickup"


def test_al_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("AL", {**answers, "al.county": "Jefferson"})
    assert out["fields"]["plaintiff"]["value"] == "[FACT NEEDED]"
    assert "plaintiff" in out["gaps"]


def test_al_field_table_items_are_unique():
    from vault.forms import al

    items = [f.item for f in al.AL_C2_FIELDS]
    assert len(items) == len(set(items))


# --- Wyoming Petition for Domestic Violence Order of Protection ---


def test_wy_is_supported_and_metadata():
    assert "WY" in supported_jurisdictions()
    out = assemble_petition("WY", {**_CA_ANSWERS, "wy.county": "Laramie"})
    assert out["form"] == "PO DV Form 03"
    assert out["jurisdiction"] == "WY"


def test_wy_maps_core_and_respondent_identifiers():
    answers = {**_CA_ANSWERS, "wy.county": "Laramie", "respondent.gender": "male",
               "respondent.height": "6ft", "respondent.vehicle_plate": "WY-123"}
    fields = assemble_petition("WY", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Laramie"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["respondent_gender"]["value"] == "male"
    assert fields["respondent_height"]["value"] == "6ft"
    assert fields["respondent_vehicle_plate"]["value"] == "WY-123"


def test_wy_confidential_defaults_on():
    fields = assemble_petition("WY", {**_CA_ANSWERS, "wy.county": "Laramie"})["fields"]
    assert fields["confidential"]["value"] == "checked"


def test_wy_relief_checks_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "wy.county": "Laramie",
        "wy.relief": ["personal_conduct", "no_guns", "pets"],
    }
    fields = assemble_petition("WY", answers)["fields"]
    assert fields["rA_personal_conduct"]["value"] == "checked"
    assert fields["rE_no_guns"]["value"] == "checked"
    assert fields["rJ_pets"]["value"] == "checked"
    assert fields["rB_no_contact"]["status"] == "not_collected"


def test_wy_stay_away_detail_and_appearance_map():
    answers = {
        **_CA_ANSWERS,
        "wy.county": "Laramie",
        "wy.relief": ["stay_away"],
        "wy.stay_away_distance": "500 feet",
        "wy.stay_away_places": ["my_home", "my_work"],
        "wy.appearance": "virtual",
    }
    fields = assemble_petition("WY", answers)["fields"]
    assert fields["rD_stay_away_distance"]["value"] == "500 feet"
    assert fields["sa_my_home"]["value"] == "checked"
    assert fields["sa_children_school"]["status"] == "not_collected"
    assert fields["appearance"]["value"] == "virtual"


def test_wy_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("WY", {**answers, "wy.county": "Laramie"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_wy_field_table_items_are_unique():
    from vault.forms import wy

    items = [f.item for f in wy.WY_PODV03_FIELDS]
    assert len(items) == len(set(items))


# --- Wisconsin Petition for TRO / Injunction (Domestic Abuse) ---


def test_wi_is_supported_and_metadata():
    assert "WI" in supported_jurisdictions()
    out = assemble_petition("WI", {**_CA_ANSWERS, "wi.county": "Dane"})
    assert out["form"] == "CV-402"
    assert out["jurisdiction"] == "WI"


def test_wi_maps_core_fields():
    answers = {**_CA_ANSWERS, "wi.county": "Dane", "respondent.gender": "male",
               "respondent.height": "6ft"}
    fields = assemble_petition("WI", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Dane"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["respondent_sex"]["value"] == "male"
    assert fields["respondent_height"]["value"] == "6ft"


def test_wi_relief_populates_both_tro_and_injunction():
    # The single intake selection checks the matching box in BOTH sub-lists.
    answers = {**_CA_ANSWERS, "wi.county": "Dane", "wi.relief": ["no_abuse", "no_contact"]}
    fields = assemble_petition("WI", answers)["fields"]
    assert fields["tro_no_abuse"]["value"] == "checked"
    assert fields["inj_no_abuse"]["value"] == "checked"
    assert fields["tro_no_contact"]["value"] == "checked"
    assert fields["inj_no_contact"]["value"] == "checked"
    assert fields["tro_avoid_residence"]["status"] == "not_collected"
    assert fields["inj_avoid_residence"]["status"] == "not_collected"


def test_wi_additional_requests_and_duration_map():
    answers = {
        **_CA_ANSWERS,
        "wi.county": "Dane",
        "wi.injunction_duration": "2 years",
        "wi.additional_requests": ["wireless_transfer", "sheriff_assist"],
    }
    fields = assemble_petition("WI", answers)["fields"]
    assert fields["injunction_duration"]["value"] == "2 years"
    assert fields["add_wireless"]["value"] == "checked"
    assert fields["add_sheriff"]["value"] == "checked"
    assert fields["add_permanent"]["status"] == "not_collected"


def test_wi_imminent_danger_and_schedule_default_map():
    answers = {**_CA_ANSWERS, "wi.county": "Dane", "wi.imminent_danger": True}
    fields = assemble_petition("WI", answers)["fields"]
    assert fields["imminent_danger"]["value"] is True
    assert fields["schedule_injunction_if_denied"]["value"] == "checked"


def test_wi_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("WI", {**answers, "wi.county": "Dane"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_wi_field_table_items_are_unique():
    from vault.forms import wi

    items = [f.item for f in wi.WI_CV402_FIELDS]
    assert len(items) == len(set(items))


# --- West Virginia DV Petition for Temporary Emergency Protective Order ---


def test_wv_is_supported_and_metadata():
    assert "WV" in supported_jurisdictions()
    out = assemble_petition("WV", {**_CA_ANSWERS, "wv.county": "Kanawha"})
    assert out["form"] == "MDVTPET"
    assert out["jurisdiction"] == "WV"


def test_wv_maps_core_and_respondent_identifiers():
    answers = {**_CA_ANSWERS, "wv.county": "Kanawha", "respondent.gender": "male",
               "respondent.height": "6ft"}
    fields = assemble_petition("WV", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Kanawha"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["respondent_sex"]["value"] == "male"
    assert fields["respondent_height"]["value"] == "6ft"


def test_wv_confidential_and_abused_default_on():
    fields = assemble_petition("WV", {**_CA_ANSWERS, "wv.county": "Kanawha"})["fields"]
    assert fields["confidential"]["value"] == "checked"
    assert fields["abused"]["value"] == "checked"
    # Petitioner home address and SSN are never collected.
    assert fields["petitioner_address"]["status"] == "not_collected"
    assert fields["petitioner_ssn"]["status"] == "not_collected"


def test_wv_acts_and_permissive_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "wv.county": "Kanawha",
        "wv.abuse_acts": ["physical_harm", "sexual_assault"],
        "wv.permissive_relief": ["no_abuse", "no_contact"],
    }
    fields = assemble_petition("WV", answers)["fields"]
    assert fields["ab_physical_harm"]["value"] == "checked"
    assert fields["ab_sexual_assault"]["value"] == "checked"
    assert fields["ab_held_confined"]["status"] == "not_collected"
    assert fields["pr_no_abuse"]["value"] == "checked"
    assert fields["pr_no_contact"]["value"] == "checked"
    assert fields["pr_custody"]["status"] == "not_collected"


def test_wv_duration_and_reasons_map():
    answers = {
        **_CA_ANSWERS,
        "wv.county": "Kanawha",
        "wv.po_duration": "1_year",
        "wv.duration_reasons": ["violated_prior_po", "totality"],
    }
    fields = assemble_petition("WV", answers)["fields"]
    assert fields["requested_duration"]["value"] == "1_year"
    assert fields["dr_violated_prior_po"]["value"] == "checked"
    assert fields["dr_totality"]["value"] == "checked"
    assert fields["dr_dv_conviction"]["status"] == "not_collected"


def test_wv_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("WV", {**answers, "wv.county": "Kanawha"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_wv_field_table_items_are_unique():
    from vault.forms import wv

    items = [f.item for f in wv.WV_MDVTPET_FIELDS]
    assert len(items) == len(set(items))


# --- Utah Request for Protective Order ---


def test_ut_is_supported_and_metadata():
    assert "UT" in supported_jurisdictions()
    out = assemble_petition("UT", {**_CA_ANSWERS, "ut.county": "Salt Lake"})
    assert out["form"] == "Request for Protective Order"
    assert out["jurisdiction"] == "UT"
    assert out["revision"] == "2022-04-11"


def test_ut_maps_core_and_describe_respondent_fields():
    answers = {
        **_CA_ANSWERS,
        "ut.county": "Salt Lake",
        "respondent.gender": "male",
        "respondent.race": "not disclosed",
        "respondent.dob": "1985-02-03",
        "respondent.height": "6'0",
        "respondent.eye_color": "brown",
        "respondent.vehicle_make_model": "Ford F-150",
    }
    fields = assemble_petition("UT", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Salt Lake"
    assert fields["respondent_sex"]["value"] == "male"
    assert fields["respondent_race"]["value"] == "not disclosed"
    assert fields["respondent_height"]["value"] == "6'0"
    assert fields["respondent_vehicle"]["value"] == "Ford F-150"
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_ut_relief_checklist_checks_its_boxes():
    answers = {
        **_CA_ANSWERS,
        "ut.county": "Utah",
        "ut.relief": ["personal_conduct", "stay_away", "support_expenses"],
    }
    fields = assemble_petition("UT", answers)["fields"]
    assert fields["8_personal_conduct"]["value"] == "checked"
    assert fields["11_stay_away"]["value"] == "checked"
    assert fields["21_support_expenses"]["value"] == "checked"
    assert fields["9_no_contact"]["status"] == "not_collected"
    assert fields["25_guardian_children"]["status"] == "not_collected"


def test_ut_relief_subchecklists_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "ut.county": "Davis",
        "ut.relief": ["stay_away", "support_expenses", "law_enforcement_assist"],
        "ut.stay_away_distance": "500 feet",
        "ut.stay_away_locations": ["home", "work"],
        "ut.support_types": ["child_support", "medical_half"],
        "ut.child_support_amount": "$400",
        "ut.law_enforcement_tasks": ["obtain_custody"],
    }
    fields = assemble_petition("UT", answers)["fields"]
    assert fields["11_distance"]["value"] == "500 feet"
    assert fields["11_sa_home"]["value"] == "checked"
    assert fields["11_sa_school"]["status"] == "not_collected"
    assert fields["21a_child_support"]["value"] == "checked"
    assert fields["21a_amount"]["value"] == "$400"
    assert fields["21b_spousal_support"]["status"] == "not_collected"
    assert fields["23b_obtain_custody"]["value"] == "checked"
    assert fields["23a_control_property"]["status"] == "not_collected"


def test_ut_respondent_ssn_not_collected():
    fields = assemble_petition("UT", {**_CA_ANSWERS, "ut.county": "Weber"})["fields"]
    assert fields["respondent_ssn"]["value"] is None
    assert fields["respondent_ssn"]["status"] == "not_collected"


def test_ut_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("UT", {**answers, "ut.county": "Cache"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ut_field_table_items_are_unique():
    from vault.forms import ut

    items = [f.item for f in ut.UT_RPO_FIELDS]
    assert len(items) == len(set(items))


# --- South Dakota Petition and Affidavit for a Protection Order ---


def test_sd_is_supported_and_metadata():
    assert "SD" in supported_jurisdictions()
    out = assemble_petition("SD", {**_CA_ANSWERS, "sd.county": "Minnehaha"})
    assert out["form"] == "UJS-091A"
    assert out["jurisdiction"] == "SD"
    assert out["revision"] == "2021-07"


def test_sd_maps_core_fields():
    fields = assemble_petition("SD", {**_CA_ANSWERS, "sd.county": "Minnehaha"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Minnehaha"
    assert fields["petitioner_county"]["value"] == "Minnehaha"
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_sd_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "sd.county": "Pennington",
        "sd.abuse_acts": ["caused_harm", "credible_threat"],
        "sd.relief": ["restrain_abuse", "no_contact", "parenting_classes"],
    }
    fields = assemble_petition("SD", answers)["fields"]
    assert fields["ab_caused_harm"]["value"] == "checked"
    assert fields["ab_credible_threat"]["value"] == "checked"
    assert fields["ab_followed"]["status"] == "not_collected"
    assert fields["1_restrain_abuse"]["value"] == "checked"
    assert fields["10_no_contact"]["value"] == "checked"
    assert fields["8_parenting_classes"]["value"] == "checked"
    assert fields["3_exclude_residence"]["status"] == "not_collected"


def test_sd_relief_subchecklists_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "sd.county": "Brown",
        "sd.relief": ["stay_away", "support", "set_duration"],
        "sd.stay_away_distance": "100 yards",
        "sd.stay_away_targets": ["petitioner", "employment"],
        "sd.support_types": ["child_support"],
        "sd.child_support_amount": "$300",
        "sd.duration": "5 years",
    }
    fields = assemble_petition("SD", answers)["fields"]
    assert fields["4_stay_away_distance"]["value"] == "100 yards"
    assert fields["4a_petitioner"]["value"] == "checked"
    assert fields["4d_employment"]["value"] == "checked"
    assert fields["4c_residence"]["status"] == "not_collected"
    assert fields["7_child_support"]["value"] == "checked"
    assert fields["7_child_support_amount"]["value"] == "$300"
    assert fields["7_spousal_support"]["status"] == "not_collected"
    assert fields["2_duration"]["value"] == "5 years"


def test_sd_yes_no_dk_history_maps():
    answers = {
        **_CA_ANSWERS,
        "sd.county": "Lincoln",
        "sd.respondent_violated_po": "yes",
        "sd.violated_po_whom": "a prior partner",
        "sd.respondent_threatened_weapon": "dont_know",
    }
    fields = assemble_petition("SD", answers)["fields"]
    assert fields["q_violated_po"]["value"] == "yes"
    assert fields["q_violated_po_whom"]["value"] == "a prior partner"
    assert fields["q_threatened_weapon"]["value"] == "dont_know"


def test_sd_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("SD", {**answers, "sd.county": "Hughes"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_sd_field_table_items_are_unique():
    from vault.forms import sd

    items = [f.item for f in sd.SD_UJS091A_FIELDS]
    assert len(items) == len(set(items))


# --- Tennessee Petition for Order of Protection ---


def test_tn_is_supported_and_metadata():
    assert "TN" in supported_jurisdictions()
    out = assemble_petition("TN", {**_CA_ANSWERS, "tn.county": "Davidson"})
    assert out["form"] == "OP2018-1"
    assert out["jurisdiction"] == "TN"
    assert out["revision"] == "2018-04-30"


def test_tn_maps_core_and_describe_respondent_fields():
    answers = {
        **_CA_ANSWERS,
        "tn.county": "Davidson",
        "respondent.gender": "male",
        "respondent.race": "not disclosed",
        "respondent.dob": "1985-02-03",
        "respondent.hair_color": "brown",
        "respondent.distinguishing_marks": "scar on left hand",
    }
    fields = assemble_petition("TN", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Davidson"
    assert fields["respondent_sex"]["value"] == "male"
    assert fields["respondent_race"]["value"] == "not disclosed"
    assert fields["respondent_features"]["value"] == "scar on left hand"
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_tn_respondent_ssn_not_collected():
    fields = assemble_petition("TN", {**_CA_ANSWERS, "tn.county": "Shelby"})["fields"]
    assert fields["respondent_ssn"]["value"] is None
    assert fields["respondent_ssn"]["status"] == "not_collected"


def test_tn_relief_checklist_checks_its_boxes():
    answers = {
        **_CA_ANSWERS,
        "tn.county": "Knox",
        "tn.relief": ["no_contact", "no_firearms", "costs_fees"],
    }
    fields = assemble_petition("TN", answers)["fields"]
    assert fields["7_no_contact"]["value"] == "checked"
    assert fields["15_no_firearms"]["value"] == "checked"
    assert fields["17_costs_fees"]["value"] == "checked"
    assert fields["8_stay_away"]["status"] == "not_collected"
    assert fields["19_other"]["status"] == "not_collected"


def test_tn_relief_subchecklists_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "tn.county": "Hamilton",
        "tn.relief": ["no_contact", "stay_away", "move_out", "transfer_wireless"],
        "tn.no_contact_who": ["me", "children"],
        "tn.stay_away_places": ["home", "workplace"],
        "tn.move_out_choice": "move_out",
        "tn.wireless_numbers": "615-555-0100",
    }
    fields = assemble_petition("TN", answers)["fields"]
    assert fields["7_contact_me"]["value"] == "checked"
    assert fields["7_contact_children"]["value"] == "checked"
    assert fields["8_sa_home"]["value"] == "checked"
    assert fields["8_sa_anywhere"]["status"] == "not_collected"
    assert fields["13_move_out_choice"]["value"] == "move_out"
    assert fields["18_wireless_numbers"]["value"] == "615-555-0100"


def test_tn_firearm_list_maps_from_shared_gate():
    answers = {
        **_CA_ANSWERS,
        "tn.county": "Davidson",
        "tn.relief": ["no_firearms"],
        "firearm.types[]": ["pistol"],
        "firearm.locations[]": ["bedroom closet"],
    }
    fields = assemble_petition("TN", answers)["fields"]
    assert fields["15_firearm_types"]["value"] == ["pistol"]
    assert fields["15_firearm_locations"]["value"] == ["bedroom closet"]


def test_tn_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("TN", {**answers, "tn.county": "Rutherford"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_tn_field_table_items_are_unique():
    from vault.forms import tn

    items = [f.item for f in tn.TN_OP_FIELDS]
    assert len(items) == len(set(items))


# --- Rhode Island Complaint for an Order of Protection (FC-79) ---


def test_ri_is_supported_and_metadata():
    assert "RI" in supported_jurisdictions()
    out = assemble_petition("RI", {**_CA_ANSWERS, "ri.county": "Providence/Bristol"})
    assert out["form"] == "FC-79"
    assert out["jurisdiction"] == "RI"
    assert out["revision"] == "2025-07"


def test_ri_maps_core_party_fields():
    answers = {
        **_CA_ANSWERS,
        "ri.county": "Kent",
        "respondent.dob": "1985-02-03",
    }
    fields = assemble_petition("RI", answers)["fields"]
    assert fields["plaintiff"]["value"] == "Jane Doe"
    assert fields["defendant"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Kent"
    assert fields["defendant_dob"]["value"] == "1985-02-03"
    assert fields["defendant_address"]["source"] == "respondent.last_known_address"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_ri_address_mapping_is_flagged_for_review():
    # FC-79 has no address-confidentiality checkbox; the §1 street-address mapping
    # from the safe mailing address must be flagged for attorney review (RIG3).
    out = assemble_petition("RI", {**_CA_ANSWERS, "ri.county": "Newport"})
    assert out["fields"]["plaintiff_address"]["source"] == "petitioner.safe_mailing_address"
    assert "plaintiff_address" in out["review_items"]


def test_ri_respondent_ssn_not_a_field():
    # FC-79 never asks for the defendant's SSN — no such field exists on the map.
    fields = assemble_petition("RI", {**_CA_ANSWERS, "ri.county": "Washington"})["fields"]
    assert "defendant_ssn" not in fields


def test_ri_case_type_and_abuse_checklists_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ri.county": "Newport",
        "ri.case_type": ["domestic_abuse"],
        "ri.abuse_types": ["weapon", "caused_harm"],
        "ri.weapon_detail": "a kitchen knife",
    }
    fields = assemble_petition("RI", answers)["fields"]
    assert fields["case_domestic_abuse"]["value"] == "checked"
    assert fields["case_sexual_abuse"]["status"] == "not_collected"
    assert fields["7_weapon"]["value"] == "checked"
    assert fields["7_caused_harm"]["value"] == "checked"
    assert fields["7_stalking"]["status"] == "not_collected"
    assert fields["7_weapon_detail"]["value"] == "a kitchen knife"


def test_ri_relief_checklist_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "ri.county": "Kent",
        "ri.relief": ["no_contact", "vacate", "custody", "pets"],
        "ri.vacate_address": "12 Elm St, Cranston, RI",
        "ri.custody_children": "Sam, age 7",
        "ri.pets_detail": "Biscuit, a beagle",
    }
    fields = assemble_petition("RI", answers)["fields"]
    assert fields["relief_no_contact"]["value"] == "checked"
    assert fields["relief_vacate"]["value"] == "checked"
    assert fields["relief_child_support"]["status"] == "not_collected"
    assert fields["vacate_address"]["value"] == "12 Elm St, Cranston, RI"
    assert fields["custody_children"]["value"] == "Sam, age 7"
    assert fields["pets_detail"]["value"] == "Biscuit, a beagle"


def test_ri_ex_parte_request_is_flagged_for_review():
    answers = {**_CA_ANSWERS, "ri.county": "Newport", "ri.ex_parte": True}
    out = assemble_petition("RI", answers)
    assert out["fields"]["ex_parte_request"]["value"] is True
    assert "ex_parte_request" in out["review_items"]


def test_ri_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("RI", {**answers, "ri.county": "Kent"})
    assert out["fields"]["plaintiff"]["value"] == "[FACT NEEDED]"
    assert "plaintiff" in out["gaps"]


def test_ri_field_table_items_are_unique():
    from vault.forms import ri

    items = [f.item for f in ri.RI_FC79_FIELDS]
    assert len(items) == len(set(items))


# --- Oregon FAPA Restraining Order Petition (ORS 107.700) ---


def test_or_is_supported_and_metadata():
    assert "OR" in supported_jurisdictions()
    out = assemble_petition("OR", {**_CA_ANSWERS, "or.county": "Multnomah"})
    assert out["form"] == "Petition for Restraining Order to Prevent Abuse"
    assert out["jurisdiction"] == "OR"
    assert out["revision"] == "2026-01"


def test_or_maps_core_party_and_age_fields():
    answers = {
        **_CA_ANSWERS,
        "or.county": "Multnomah",
        "respondent.dob": "1985-02-03",
    }
    fields = assemble_petition("OR", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Multnomah"
    # Ages are mapped from DOB (computed downstream at fill time).
    assert fields["petitioner_age"]["source"] == "petitioner.dob"
    assert fields["respondent_age"]["value"] == "1985-02-03"
    # Safe-contact + CIF asserted by design.
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["cif_petitioner"]["value"] == "checked"
    assert fields["contact_address"]["source"] == "petitioner.safe_mailing_address"


def test_or_injured_checkbox_derives_from_incident_injury():
    # _CA_ANSWERS records "Bruised wrist" → I-was-injured is checked.
    fields = assemble_petition("OR", {**_CA_ANSWERS, "or.county": "Lane"})["fields"]
    assert fields["incident_injured"]["value"] == "checked"
    # No injury recorded → the box is left unchecked (not_collected).
    no_injury = {**_CA_ANSWERS, "or.county": "Lane", "incidents[].injury": "None"}
    assert assemble_petition("OR", no_injury)["fields"]["incident_injured"]["value"] is None


def test_or_abuse_and_relief_checklists_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "or.county": "Washington",
        "or.abuse_types": ["physical_injury", "fear_imminent"],
        "or.relief": ["firearms_prohibit", "move_out"],
        "or.move_out_basis": ["sole_name", "spouse_rdp"],
    }
    fields = assemble_petition("OR", answers)["fields"]
    assert fields["4_physical_injury"]["value"] == "checked"
    assert fields["4_fear_imminent"]["value"] == "checked"
    assert fields["4_sexual_force"]["status"] == "not_collected"
    assert fields["7_firearms_prohibit"]["value"] == "checked"
    assert fields["10_move_out"]["value"] == "checked"
    assert fields["10_sole_name"]["value"] == "checked"
    assert fields["10_joint_own"]["status"] == "not_collected"
    assert fields["11_emergency_money"]["status"] == "not_collected"


def test_or_emergency_and_animals_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "or.county": "Clackamas",
        "or.relief": ["emergency_money", "animals"],
        "or.emergency_amount": "750",
        "or.emergency_reason": "Replacing a broken door lock",
        "or.animals_detail": "Rover, a dog",
    }
    fields = assemble_petition("OR", answers)["fields"]
    assert fields["emergency_amount"]["value"] == "750"
    assert fields["emergency_reason"]["value"] == "Replacing a broken door lock"
    assert fields["animals_detail"]["value"] == "Rover, a dog"


def test_or_imminent_danger_flagged_for_review():
    answers = {**_CA_ANSWERS, "or.county": "Marion", "or.imminent_danger": True}
    out = assemble_petition("OR", answers)
    assert out["fields"]["imminent_danger"]["value"] is True
    assert "imminent_danger" in out["review_items"]


def test_or_uccjea_section_is_a_gap():
    fields = assemble_petition("OR", {**_CA_ANSWERS, "or.county": "Lane"})["fields"]
    assert fields["children_uccjea"]["status"] == "not_collected"
    assert fields["dhs_involvement"]["status"] == "not_collected"


def test_or_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("OR", {**answers, "or.county": "Multnomah"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_or_field_table_items_are_unique():
    from vault.forms import oregon

    items = [f.item for f in oregon.OR_FAPA_FIELDS]
    assert len(items) == len(set(items))


# --- Oklahoma AOC Petition for Protective Order (22 O.S. 60.1) ---


def test_ok_is_supported_and_metadata():
    assert "OK" in supported_jurisdictions()
    out = assemble_petition("OK", {**_CA_ANSWERS, "ok.county": "Oklahoma"})
    assert out["form"] == "Petition for Protective Order"
    assert out["jurisdiction"] == "OK"
    assert out["revision"] == "2023-11"


def test_ok_maps_core_and_describe_defendant_fields():
    answers = {
        **_CA_ANSWERS,
        "ok.county": "Tulsa",
        "respondent.gender": "male",
        "respondent.race": "not disclosed",
        "respondent.dob": "1985-02-03",
        "respondent.height": "6'0",
        "respondent.distinguishing_marks": "scar on left hand",
    }
    fields = assemble_petition("OK", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Tulsa"
    assert fields["respondent_sex"]["value"] == "male"
    assert fields["respondent_race"]["value"] == "not disclosed"
    assert fields["respondent_features"]["value"] == "scar on left hand"
    assert fields["incident_description"]["value"].startswith("He grabbed my phone")


def test_ok_respondent_ssn_not_a_field():
    # The AOC petition never asks for the defendant's SSN — no such field exists.
    fields = assemble_petition("OK", {**_CA_ANSWERS, "ok.county": "Cleveland"})["fields"]
    assert "respondent_ssn" not in fields


def test_ok_jurisdiction_actions_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ok.county": "Oklahoma",
        "ok.jurisdiction_basis": ["petitioner_resident", "abuse_in_county"],
        "ok.actions": ["physical_harm", "stalked"],
        "ok.relief": ["no_contact", "surrender_firearms", "attorney_fees"],
    }
    fields = assemble_petition("OK", answers)["fields"]
    assert fields["2_petitioner_resident"]["value"] == "checked"
    assert fields["2_defendant_resident"]["status"] == "not_collected"
    assert fields["3_physical_harm"]["value"] == "checked"
    assert fields["3_harassed"]["status"] == "not_collected"
    assert fields["6_1_no_contact"]["value"] == "checked"
    assert fields["6_13_surrender_firearms"]["value"] == "checked"
    assert fields["6_4_move_out"]["status"] == "not_collected"


def test_ok_relief_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "ok.county": "Tulsa",
        "ok.relief": ["move_out", "transfer_utilities", "attorney_fees"],
        "ok.move_out_address": "100 Main St, Tulsa, OK",
        "ok.transfer_detail": "Electric account + 918-555-0100",
        "ok.attorney_fees_amount": "1500",
    }
    fields = assemble_petition("OK", answers)["fields"]
    assert fields["6_4_move_out_address"]["value"] == "100 Main St, Tulsa, OK"
    assert fields["6_12_transfer_detail"]["value"] == "Electric account + 918-555-0100"
    assert fields["6_15_attorney_fees_amount"]["value"] == "1500"


def test_ok_ex_parte_flagged_for_review():
    answers = {**_CA_ANSWERS, "ok.county": "Oklahoma", "ok.ex_parte": True}
    out = assemble_petition("OK", answers)
    assert out["fields"]["ex_parte"]["value"] is True
    assert "ex_parte" in out["review_items"]


def test_ok_victim_characterization_is_a_gap():
    fields = assemble_petition("OK", {**_CA_ANSWERS, "ok.county": "Tulsa"})["fields"]
    assert fields["victim_characterization"]["status"] == "not_collected"
    assert fields["respondent_dl"]["status"] == "not_collected"


def test_ok_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("OK", {**answers, "ok.county": "Oklahoma"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ok_field_table_items_are_unique():
    from vault.forms import ok

    items = [f.item for f in ok.OK_PO_FIELDS]
    assert len(items) == len(set(items))


# --- Vermont Complaint for Relief from Abuse ---


def test_vt_is_supported_and_metadata():
    assert "VT" in supported_jurisdictions()
    out = assemble_petition("VT", {**_CA_ANSWERS, "vt.unit": "chittenden"})
    assert out["form"] == "400-00150C"
    assert out["jurisdiction"] == "VT"
    assert out["revision"] == "2017-08"


def test_vt_maps_core_fields():
    fields = assemble_petition("VT", {**_CA_ANSWERS, "vt.unit": "chittenden"})["fields"]
    assert fields["plaintiff"]["value"] == "Jane Doe"
    assert fields["defendant"]["value"] == "John Roe"
    assert fields["unit"]["value"] == "chittenden"
    # Defendant physical address comes from the respondent's last-known address.
    assert fields["defendant_address"]["source"] == "respondent.last_known_address"
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["affidavit_narrative"]["value"].startswith("He grabbed my phone")


def test_vt_abuse_and_two_relief_lists_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "vt.unit": "rutland",
        "vt.abuse_acts": ["physical_harm", "stalking"],
        "vt.emergency_relief": ["no_abuse", "no_pet_cruelty"],
        "vt.final_relief": ["child_support", "pet_possession"],
    }
    fields = assemble_petition("VT", answers)["fields"]
    assert fields["ab_physical_harm"]["value"] == "checked"
    assert fields["ab_stalking"]["value"] == "checked"
    assert fields["ab_sexual_assault"]["status"] == "not_collected"
    # Emergency vs Final are independent lists with their own boxes.
    assert fields["em_no_abuse"]["value"] == "checked"
    assert fields["em_no_pet_cruelty"]["value"] == "checked"
    assert fields["fo_child_support"]["value"] == "checked"
    assert fields["fo_pet_possession"]["value"] == "checked"
    # A box selected in Final must not bleed into Emergency.
    assert fields["fo_no_abuse"]["status"] == "not_collected"


def test_vt_existing_proceedings_and_detail_fields_map():
    answers = {
        **_CA_ANSWERS,
        "vt.unit": "windsor",
        "vt.existing_proceedings": ["criminal", "parentage"],
        "vt.emergency_relief": ["stay_away", "leave_residence"],
        "vt.stay_away_distance": "300 feet",
        "vt.residence_address": "9 Maple St, Rutland, VT",
        "vt.residence_tenure": "rented_leased",
    }
    fields = assemble_petition("VT", answers)["fields"]
    assert fields["ep_criminal"]["value"] == "checked"
    assert fields["ep_parentage"]["value"] == "checked"
    assert fields["ep_divorce_separation"]["status"] == "not_collected"
    # One distance answer fills both relief sections' blanks.
    assert fields["em_stay_away_distance"]["value"] == "300 feet"
    assert fields["fo_stay_away_distance"]["value"] == "300 feet"
    assert fields["residence_address"]["value"] == "9 Maple St, Rutland, VT"
    assert fields["residence_tenure"]["value"] == "rented_leased"


def test_vt_children_relief_flag_and_default_off():
    base = assemble_petition("VT", {**_CA_ANSWERS, "vt.unit": "orange"})["fields"]
    # _CA_ANSWERS has no children and no includes_children flag => box stays off.
    assert base["fact_against_children"]["status"] == "not_collected"
    flagged = assemble_petition(
        "VT", {**_CA_ANSWERS, "vt.unit": "orange", "vt.includes_children": True}
    )["fields"]
    assert flagged["fact_against_children"]["value"] == "checked"


def test_vt_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("VT", {**answers, "vt.unit": "essex"})
    assert out["fields"]["plaintiff"]["value"] == "[FACT NEEDED]"
    assert "plaintiff" in out["gaps"]


def test_vt_field_table_items_are_unique():
    from vault.forms import vt

    items = [f.item for f in vt.VT_RFA_FIELDS]
    assert len(items) == len(set(items))


# --- Ohio Petition for Domestic Violence Civil Protection Order ---


def test_oh_is_supported_and_metadata():
    assert "OH" in supported_jurisdictions()
    out = assemble_petition("OH", {**_CA_ANSWERS, "oh.county": "Franklin"})
    assert out["form"] == "10.01-D"
    assert out["jurisdiction"] == "OH"


def test_oh_maps_core_fields():
    fields = assemble_petition("OH", {**_CA_ANSWERS, "oh.county": "Franklin"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Franklin"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    # Petitioner address is the safe mailing address (form is a public record).
    assert fields["petitioner_address"]["value"].startswith("PO Box 5")


def test_oh_who_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "oh.county": "Franklin",
        "oh.who_needs_protection": ["me", "minor_children"],
        "oh.relief": ["no_abuse", "exclusive_residence"],
    }
    fields = assemble_petition("OH", answers)["fields"]
    assert fields["who_me"]["value"] == "checked"
    assert fields["who_minor_children"]["value"] == "checked"
    assert fields["who_other"]["status"] == "not_collected"
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_exclusive_residence"]["value"] == "checked"
    assert fields["r_no_contact"]["status"] == "not_collected"


def test_oh_aggravating_and_relief_detail_map():
    answers = {
        **_CA_ANSWERS,
        "oh.county": "Franklin",
        "oh.aggravating_factors": ["weapons_access", "controlling_stalking"],
        "oh.relief": ["vehicle"],
        "oh.vehicle_detail": "2012 gray Civic",
    }
    fields = assemble_petition("OH", answers)["fields"]
    assert fields["ag_weapons_access"]["value"] == "checked"
    assert fields["ag_controlling_stalking"]["value"] == "checked"
    assert fields["ag_mental_health"]["status"] == "not_collected"
    assert fields["vehicle_detail"]["value"] == "2012 gray Civic"


def test_oh_in_fear_and_full_hearing_default_on():
    fields = assemble_petition("OH", {**_CA_ANSWERS, "oh.county": "Franklin"})["fields"]
    assert fields["in_fear"]["value"] == "checked"
    assert fields["full_hearing"]["value"] == "checked"


def test_oh_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("OH", {**answers, "oh.county": "Franklin"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_oh_field_table_items_are_unique():
    from vault.forms import oh

    items = [f.item for f in oh.OH_DVCPO_FIELDS]
    assert len(items) == len(set(items))


# --- North Dakota Petition for Civil Protection Order ---


def test_nd_is_supported_and_metadata():
    assert "ND" in supported_jurisdictions()
    out = assemble_petition("ND", {**_CA_ANSWERS, "nd.county": "Cass"})
    assert out["form"] == "Petition CPO"
    assert out["jurisdiction"] == "ND"


def test_nd_maps_core_fields():
    fields = assemble_petition("ND", {**_CA_ANSWERS, "nd.county": "Cass"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Cass"
    assert fields["recent_incidents"]["value"].startswith("He grabbed my phone")
    assert fields["victim_petitioner"]["value"] == "checked"


def test_nd_confidential_address_defaults_on():
    fields = assemble_petition("ND", {**_CA_ANSWERS, "nd.county": "Cass"})["fields"]
    assert fields["confidential_address"]["value"] == "checked"


def test_nd_order_types_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "nd.county": "Cass",
        "nd.order_types": ["domestic_violence", "sexual_assault"],
        "nd.relief": ["restrain_contact", "surrender_firearms"],
    }
    fields = assemble_petition("ND", answers)["fields"]
    assert fields["ot_domestic_violence"]["value"] == "checked"
    assert fields["ot_sexual_assault"]["value"] == "checked"
    assert fields["ot_disorderly_conduct"]["status"] == "not_collected"
    assert fields["r_restrain_contact"]["value"] == "checked"
    assert fields["r_surrender_firearms"]["value"] == "checked"
    assert fields["r_custody"]["status"] == "not_collected"


def test_nd_exclude_places_and_detail_map():
    answers = {
        **_CA_ANSWERS,
        "nd.county": "Cass",
        "nd.relief": ["exclude_places"],
        "nd.exclude_places": ["residence", "school"],
        "nd.stay_away_feet": "500",
    }
    fields = assemble_petition("ND", answers)["fields"]
    assert fields["ex_residence"]["value"] == "checked"
    assert fields["ex_school"]["value"] == "checked"
    assert fields["ex_daycare"]["status"] == "not_collected"
    assert fields["stay_away_feet"]["value"] == "500"


def test_nd_respondent_ssn_never_collected():
    fields = assemble_petition("ND", {**_CA_ANSWERS, "nd.county": "Cass"})["fields"]
    assert fields["respondent_ssn"]["status"] == "not_collected"
    assert fields["respondent_ssn"]["value"] is None


def test_nd_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("ND", {**answers, "nd.county": "Cass"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_nd_field_table_items_are_unique():
    from vault.forms import nd

    items = [f.item for f in nd.ND_CPO_FIELDS]
    assert len(items) == len(set(items))


# --- New Mexico Petition for Order of Protection from Domestic Abuse ---


def test_nm_is_supported_and_metadata():
    assert "NM" in supported_jurisdictions()
    out = assemble_petition("NM", {**_CA_ANSWERS, "nm.county": "Bernalillo"})
    assert out["form"] == "4-961"
    assert out["jurisdiction"] == "NM"


def test_nm_maps_core_fields():
    fields = assemble_petition("NM", {**_CA_ANSWERS, "nm.county": "Bernalillo"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Bernalillo"
    assert fields["abuse_description"]["value"].startswith("He grabbed my phone")


def test_nm_confidential_address_defaults_on():
    fields = assemble_petition("NM", {**_CA_ANSWERS, "nm.county": "Bernalillo"})["fields"]
    assert fields["confidential_address"]["value"] == "checked"


def test_nm_relief_checks_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "nm.county": "Bernalillo",
        "nm.relief": ["no_contact_stay_away", "surrender_firearms"],
    }
    fields = assemble_petition("NM", answers)["fields"]
    assert fields["r_no_contact_stay_away"]["value"] == "checked"
    assert fields["r_surrender_firearms"]["value"] == "checked"
    assert fields["r_custody"]["status"] == "not_collected"


def test_nm_relief_detail_and_support_map():
    answers = {
        **_CA_ANSWERS,
        "nm.county": "Bernalillo",
        "nm.relief": ["leave_residence", "support"],
        "nm.residence_address": "9 Mesa Rd, Albuquerque, NM",
        "nm.support_types": ["children"],
    }
    fields = assemble_petition("NM", answers)["fields"]
    assert fields["residence_address"]["value"] == "9 Mesa Rd, Albuquerque, NM"
    assert fields["support_children"]["value"] == "checked"
    assert fields["support_petitioner"]["status"] == "not_collected"


def test_nm_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NM", {**answers, "nm.county": "Bernalillo"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_nm_field_table_items_are_unique():
    from vault.forms import nm

    items = [f.item for f in nm.NM_OP_FIELDS]
    assert len(items) == len(set(items))


# --- New Hampshire Domestic Violence Petition (NHJB-2050-DF) ---


def test_nh_is_supported_and_metadata():
    assert "NH" in supported_jurisdictions()
    out = assemble_petition("NH", {**_CA_ANSWERS, "nh.court_name": "Concord"})
    assert out["form"] == "NHJB-2050-DF"
    assert out["jurisdiction"] == "NH"


def test_nh_maps_core_fields():
    out = assemble_petition("NH", {**_CA_ANSWERS, "nh.court_name": "Concord"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["court_name"]["value"] == "Concord"
    assert fields["statement_of_facts"]["value"].startswith("He grabbed my phone")
    # The relationship basis is mapped but must be attorney-confirmed.
    assert "relationship_basis" in out["review_items"]


def test_nh_immediate_danger_defaults_on():
    fields = assemble_petition("NH", {**_CA_ANSWERS, "nh.court_name": "Concord"})["fields"]
    assert fields["immediate_danger"]["value"] == "checked"
    assert "immediate_danger" in assemble_petition(
        "NH", {**_CA_ANSWERS, "nh.court_name": "Concord"}
    )["review_items"]


def test_nh_relief_and_losses_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "nh.court_name": "Concord",
        "nh.relief": ["no_abuse_contact", "exclusive_vehicle", "pay_losses"],
        "nh.vehicle_detail": "2012 gray Civic",
        "nh.financial_losses": ["medical_dental_optical", "lost_wages"],
    }
    fields = assemble_petition("NH", answers)["fields"]
    assert fields["r_1_no_abuse_contact"]["value"] == "checked"
    assert fields["r_11_exclusive_vehicle"]["value"] == "checked"
    assert fields["r_6_custody"]["status"] == "not_collected"
    assert fields["exclusive_vehicle_detail"]["value"] == "2012 gray Civic"
    assert fields["loss_medical"]["value"] == "checked"
    assert fields["loss_wages"]["value"] == "checked"
    assert fields["loss_property"]["status"] == "not_collected"


def test_nh_court_actions_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "nh.court_name": "Concord",
        "nh.court_actions": ["divorce", "custody"],
        "nh.court_list": "Concord Family Division",
    }
    fields = assemble_petition("NH", answers)["fields"]
    assert fields["court_divorce"]["value"] == "checked"
    assert fields["court_custody"]["value"] == "checked"
    assert fields["court_protective_order"]["status"] == "not_collected"
    assert fields["court_list"]["value"] == "Concord Family Division"


def test_nh_relief_items_are_review_items():
    out = assemble_petition("NH", {**_CA_ANSWERS, "nh.court_name": "Concord"})
    assert "r_1_no_abuse_contact" in out["review_items"]
    assert "relationship_basis" in out["review_items"]


def test_nh_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NH", {**answers, "nh.court_name": "Concord"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_nh_missing_court_name_is_fact_needed():
    out = assemble_petition("NH", _CA_ANSWERS)
    assert out["fields"]["court_name"]["value"] == "[FACT NEEDED]"
    assert "court_name" in out["gaps"]


def test_nh_field_table_items_are_unique():
    from vault.forms import nh

    items = [f.item for f in nh.NH_DV_PETITION_FIELDS]
    assert len(items) == len(set(items))


# --- Montana Sworn Petition for Temporary Order of Protection (AGO Form OVS 3) ---


def test_mt_is_supported_and_metadata():
    assert "MT" in supported_jurisdictions()
    out = assemble_petition("MT", {**_CA_ANSWERS, "mt.county": "Lewis and Clark"})
    assert out["form"] == "OVS 3"
    assert out["jurisdiction"] == "MT"


def test_mt_maps_core_fields():
    out = assemble_petition("MT", {**_CA_ANSWERS, "mt.county": "Lewis and Clark"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Lewis and Clark"
    assert fields["recent_abuse_narrative"]["value"].startswith("He grabbed my phone")
    # Petitioner is always among the protected persons.
    assert fields["protected_myself"]["value"] == "checked"
    assert "relationship_basis" in out["review_items"]


def test_mt_immediate_danger_defaults_on_and_is_review():
    out = assemble_petition("MT", {**_CA_ANSWERS, "mt.county": "Lewis and Clark"})
    assert out["fields"]["immediate_danger"]["value"] == "checked"
    assert "immediate_danger" in out["review_items"]


def test_mt_relief_and_stay_away_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "mt.county": "Lewis and Clark",
        "mt.relief": ["no_violence", "stay_away"],
        "mt.stay_away_feet": "1000",
        "mt.stay_away_places": ["me", "home"],
    }
    fields = assemble_petition("MT", answers)["fields"]
    assert fields["r_1_no_violence"]["value"] == "checked"
    assert fields["r_4_stay_away"]["value"] == "checked"
    assert fields["r_9_counseling"]["status"] == "not_collected"
    assert fields["stay_away_feet"]["value"] == "1000"
    assert fields["sa_me"]["value"] == "checked"
    assert fields["sa_home"]["value"] == "checked"
    assert fields["sa_vehicle"]["status"] == "not_collected"


def test_mt_living_situation_and_possession_detail_map():
    answers = {
        **_CA_ANSWERS,
        "mt.county": "Lewis and Clark",
        "mt.living_situation": ["left_residence"],
        "mt.return_reason": ["get_belongings"],
        "mt.relief": ["possession"],
        "mt.possession_detail": "The pickup truck and my laptop",
    }
    fields = assemble_petition("MT", answers)["fields"]
    assert fields["live_left_residence"]["value"] == "checked"
    assert fields["return_belongings"]["value"] == "checked"
    assert fields["return_live"]["status"] == "not_collected"
    assert fields["possession_detail"]["value"] == "The pickup truck and my laptop"


def test_mt_relief_items_are_review_items():
    out = assemble_petition("MT", {**_CA_ANSWERS, "mt.county": "Lewis and Clark"})
    assert "r_1_no_violence" in out["review_items"]


def test_mt_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MT", {**answers, "mt.county": "Lewis and Clark"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_mt_missing_county_is_fact_needed():
    out = assemble_petition("MT", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_mt_field_table_items_are_unique():
    from vault.forms import mt

    items = [f.item for f in mt.MT_TOP_FIELDS]
    assert len(items) == len(set(items))


# --- Nevada Application for Protection Order Against DV (© 2022) ---


def test_nv_is_supported_and_metadata():
    assert "NV" in supported_jurisdictions()
    out = assemble_petition(
        "NV", {**_CA_ANSWERS, "nv.court_type": "district", "nv.county": "Clark"}
    )
    # No printed form number — descriptive id, flagged NVG1.
    assert out["form"] == "Application for Protection Order - DV"
    assert out["jurisdiction"] == "NV"


def test_nv_maps_core_fields():
    out = assemble_petition(
        "NV", {**_CA_ANSWERS, "nv.court_type": "district", "nv.county": "Clark"}
    )
    fields = out["fields"]
    assert fields["applicant"]["value"] == "Jane Doe"
    assert fields["adverse_party"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Clark"
    assert fields["recent_narrative"]["value"].startswith("He grabbed my phone")
    # Work stay-away maps from the always-collected employer block.
    assert "relationship_basis" in out["review_items"]


def test_nv_address_confidential_defaults_on():
    fields = assemble_petition(
        "NV", {**_CA_ANSWERS, "nv.court_type": "district", "nv.county": "Clark"}
    )["fields"]
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["temporary_order"]["value"] == "checked"
    assert fields["no_personal_info"]["value"] == "checked"


def test_nv_temp_protections_and_extended_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "nv.court_type": "district",
        "nv.county": "Clark",
        "nv.temp_protections": ["prohibited_activities", "current_residence"],
        "nv.order_length": "extended_2yr",
        "nv.extended_relief": ["child_support", "costs_fees"],
    }
    fields = assemble_petition("NV", answers)["fields"]
    assert fields["tp_prohibited_activities"]["value"] == "checked"
    assert fields["tp_current_residence"]["value"] == "checked"
    assert fields["tp_work"]["status"] == "not_collected"
    assert fields["ext_child_support"]["value"] == "checked"
    assert fields["ext_costs_fees"]["value"] == "checked"
    assert fields["ext_rent_mortgage"]["status"] == "not_collected"


def test_nv_who_and_reason_map():
    answers = {
        **_CA_ANSWERS,
        "nv.court_type": "district",
        "nv.county": "Clark",
        "nv.who_needs_protection": ["me", "minor_children"],
        "nv.protection_reason": ["dv_against_me"],
    }
    fields = assemble_petition("NV", answers)["fields"]
    assert fields["who_me"]["value"] == "checked"
    assert fields["who_minor_children"]["value"] == "checked"
    assert fields["reason_dv_me"]["value"] == "checked"
    assert fields["reason_dv_child"]["status"] == "not_collected"


def test_nv_relief_items_are_review_items():
    out = assemble_petition(
        "NV", {**_CA_ANSWERS, "nv.court_type": "district", "nv.county": "Clark"}
    )
    assert "tp_prohibited_activities" in out["review_items"]
    assert "order_length" in out["review_items"]


def test_nv_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NV", {**answers, "nv.court_type": "district", "nv.county": "Clark"})
    assert out["fields"]["applicant"]["value"] == "[FACT NEEDED]"
    assert "applicant" in out["gaps"]


def test_nv_missing_court_type_is_fact_needed():
    out = assemble_petition("NV", {**_CA_ANSWERS, "nv.county": "Clark"})
    assert out["fields"]["court_type"]["value"] == "[FACT NEEDED]"
    assert "court_type" in out["gaps"]


def test_nv_field_table_items_are_unique():
    from vault.forms import nv

    items = [f.item for f in nv.NV_APPLICATION_FIELDS]
    assert len(items) == len(set(items))


# --- Nebraska Petition and Affidavit for Domestic Abuse Protection Order (DC 19:8) ---


def test_ne_is_supported_and_metadata():
    assert "NE" in supported_jurisdictions()
    out = assemble_petition("NE", {**_CA_ANSWERS, "ne.county": "Lancaster"})
    assert out["form"] == "DC 19:8"
    assert out["jurisdiction"] == "NE"


def test_ne_maps_core_fields():
    fields = assemble_petition("NE", {**_CA_ANSWERS, "ne.county": "Lancaster"})["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["court_county"]["value"] == "Lancaster"
    assert fields["incident_narrative"]["value"].startswith("He grabbed my phone")
    # Temporary custody is requested to the petitioner.
    assert fields["custody_to"]["value"] == "Jane Doe"


def test_ne_defaults_address_confidential_and_additional_request():
    fields = assemble_petition("NE", {**_CA_ANSWERS, "ne.county": "Lancaster"})["fields"]
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["filing_myself"]["value"] == "checked"
    assert fields["additional_request"]["value"] == "checked"


def test_ne_petitioner_adult_derives_from_dob():
    # _CA_ANSWERS petitioner.dob is 1990 -> 19+.
    fields = assemble_petition("NE", {**_CA_ANSWERS, "ne.county": "Lancaster"})["fields"]
    assert fields["petitioner_adult"]["value"] == "checked"


def test_ne_relief_checks_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ne.county": "Lancaster",
        "ne.relief": ["no_abuse", "no_firearm", "custody"],
        "ne.custody_days": "30",
    }
    fields = assemble_petition("NE", answers)["fields"]
    assert fields["r_no_abuse"]["value"] == "checked"
    assert fields["r_no_firearm"]["value"] == "checked"
    assert fields["r_custody"]["value"] == "checked"
    assert fields["r_pet_possession"]["status"] == "not_collected"
    assert fields["custody_days"]["value"] == "30"


def test_ne_praecipe_vehicle_and_physical_map():
    answers = {
        **_CA_ANSWERS,
        "ne.county": "Lancaster",
        "respondent.height": "5'11",
        "respondent.vehicle_make_model": "Toyota Camry",
        "respondent.vehicle_plate": "NE-123",
    }
    fields = assemble_petition("NE", answers)["fields"]
    assert fields["respondent_height"]["value"] == "5'11"
    assert fields["praecipe_vehicle_make_model"]["value"] == "Toyota Camry"
    assert fields["praecipe_vehicle_plate"]["value"] == "NE-123"


def test_ne_relief_items_are_review_items():
    out = assemble_petition("NE", {**_CA_ANSWERS, "ne.county": "Lancaster"})
    assert "r_no_abuse" in out["review_items"]
    assert "relationship_basis" in out["review_items"]


def test_ne_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("NE", {**answers, "ne.county": "Lancaster"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ne_missing_county_is_fact_needed():
    out = assemble_petition("NE", _CA_ANSWERS)
    assert out["fields"]["court_county"]["value"] == "[FACT NEEDED]"
    assert "court_county" in out["gaps"]


def test_ne_field_table_items_are_unique():
    from vault.forms import ne

    items = [f.item for f in ne.NE_DAPO_FIELDS]
    assert len(items) == len(set(items))


# --- Maine Complaint for Protection from Abuse (Form PA-001) ---


def test_me_is_supported_and_metadata():
    assert "ME" in supported_jurisdictions()
    out = assemble_petition("ME", {**_CA_ANSWERS, "me.court_location": "Portland"})
    assert out["form"] == "PA-001"
    assert out["jurisdiction"] == "ME"


def test_me_maps_core_fields():
    out = assemble_petition("ME", {**_CA_ANSWERS, "me.court_location": "Portland"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["court_location"]["value"] == "Portland"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    # Maine offers a confidential-address mechanism (PA-015) — derived on, flagged.
    assert fields["address_confidential"]["value"] == "checked"
    assert "address_confidential" in out["review_items"]


def test_me_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "me.court_location": "Portland",
        "me.relationship_basis": ["married", "stalking"],
        "me.relief": ["stop_abuse", "stay_distance"],
        "me.stay_distance_detail": "500 feet from my home",
    }
    fields = assemble_petition("ME", answers)["fields"]
    assert fields["4_spouse"]["value"] == "checked"
    assert fields["4_stalking"]["value"] == "checked"
    assert fields["4_dating_partner"]["status"] == "not_collected"
    assert fields["order_a_stop_abuse"]["value"] == "checked"
    assert fields["order_e_stay_distance"]["value"] == "checked"
    assert fields["order_l_counseling"]["status"] == "not_collected"
    assert fields["order_e_stay_distance_detail"]["value"] == "500 feet from my home"


def test_me_temporary_order_and_weapon_access_map():
    answers = {
        **_CA_ANSWERS,
        "me.court_location": "Portland",
        "me.temporary_order": ["self_danger"],
        "me.weapon_access": ["firearm"],
    }
    fields = assemble_petition("ME", answers)["fields"]
    assert fields["10_self_danger"]["value"] == "checked"
    assert fields["10_not_requesting"]["status"] == "not_collected"
    assert fields["11_firearm"]["value"] == "checked"


def test_me_relief_and_temporary_items_are_review_items():
    out = assemble_petition("ME", {**_CA_ANSWERS, "me.court_location": "Portland"})
    assert "order_a_stop_abuse" in out["review_items"]
    assert "10_self_danger" in out["review_items"]
    assert "4_spouse" in out["review_items"]


def test_me_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("ME", {**answers, "me.court_location": "Portland"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_me_missing_court_location_is_fact_needed():
    out = assemble_petition("ME", _CA_ANSWERS)
    assert out["fields"]["court_location"]["value"] == "[FACT NEEDED]"
    assert "court_location" in out["gaps"]


def test_me_field_table_items_are_unique():
    from vault.forms import me

    items = [f.item for f in me.ME_PFA_FIELDS]
    assert len(items) == len(set(items))


# --- Michigan Petition for Personal Protection Order (Form CC 375) ---


def test_mi_is_supported_and_metadata():
    assert "MI" in supported_jurisdictions()
    out = assemble_petition("MI", {**_CA_ANSWERS, "mi.county": "Wayne"})
    assert out["form"] == "CC 375"
    assert out["jurisdiction"] == "MI"


def test_mi_maps_core_fields():
    out = assemble_petition("MI", {**_CA_ANSWERS, "mi.county": "Wayne"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Wayne"
    assert fields["need_narrative"]["value"].startswith("He grabbed my phone")
    # CC 375 has no confidential-address affidavit — the address is flagged for review.
    assert "petitioner_address" in out["review_items"]


def test_mi_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "mi.county": "Wayne",
        "mi.relationship": ["married", "cohabitants"],
        "mi.relief": ["enter_my_property", "assault"],
        "mi.assault_names": "Jane Doe and her mother",
    }
    fields = assemble_petition("MI", answers)["fields"]
    assert fields["1_married"]["value"] == "checked"
    assert fields["1_cohabitants"]["value"] == "checked"
    assert fields["1_dating"]["status"] == "not_collected"
    assert fields["5a_no_enter_my_property"]["value"] == "checked"
    assert fields["5c_no_assault"]["value"] == "checked"
    assert fields["5k_no_firearm"]["status"] == "not_collected"
    assert fields["5c_assault_names"]["value"] == "Jane Doe and her mother"


def test_mi_stalking_and_animal_acts_map():
    answers = {
        **_CA_ANSWERS,
        "mi.county": "Wayne",
        "mi.relief": ["stalking", "animal_abuse"],
        "mi.stalking_acts": ["following", "contacting_phone"],
        "mi.animal_acts": ["injure"],
    }
    fields = assemble_petition("MI", answers)["fields"]
    assert fields["5e_following"]["value"] == "checked"
    assert fields["5e_contacting_phone"]["value"] == "checked"
    assert fields["5e_placing_object"]["status"] == "not_collected"
    assert fields["5j_injure_animal"]["value"] == "checked"
    assert fields["5j_retain_animal"]["status"] == "not_collected"


def test_mi_ex_parte_maps_and_is_review():
    answers = {**_CA_ANSWERS, "mi.county": "Wayne", "mi.ex_parte": True}
    out = assemble_petition("MI", answers)
    assert out["fields"]["ex_parte"]["value"] is True
    assert "ex_parte" in out["review_items"]


def test_mi_relief_items_are_review_items():
    out = assemble_petition("MI", {**_CA_ANSWERS, "mi.county": "Wayne"})
    assert "5a_no_enter_my_property" in out["review_items"]
    assert "1_married" in out["review_items"]


def test_mi_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MI", {**answers, "mi.county": "Wayne"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_mi_missing_county_is_fact_needed():
    out = assemble_petition("MI", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_mi_field_table_items_are_unique():
    from vault.forms import mi

    items = [f.item for f in mi.MI_PPO_FIELDS]
    assert len(items) == len(set(items))


# --- Iowa Petition for Relief from Domestic Abuse (Rule 17.10 Form 11) ---


def test_ia_is_supported_and_metadata():
    assert "IA" in supported_jurisdictions()
    out = assemble_petition("IA", {**_CA_ANSWERS, "ia.county": "Polk"})
    assert out["form"] == "Rule 17.10 Form 11"
    assert out["jurisdiction"] == "IA"


def test_ia_maps_core_fields():
    out = assemble_petition("IA", {**_CA_ANSWERS, "ia.county": "Polk"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Polk"
    assert fields["recent_abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_ia_relationship_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ia.county": "Polk",
        "ia.relationship_basis": ["intimate_relationship"],
        "ia.abuse_types": ["physical", "threats"],
        "ia.relief": ["stop_abuse", "financial_support"],
        "ia.support_detail": "$800/mo for rent and childcare",
    }
    fields = assemble_petition("IA", answers)["fields"]
    assert fields["7_intimate_relationship"]["value"] == "checked"
    assert fields["8_physical"]["value"] == "checked"
    assert fields["8_sexual"]["status"] == "not_collected"
    assert fields["23c_1_stop_abuse"]["value"] == "checked"
    assert fields["23c_10_financial_support"]["value"] == "checked"
    assert fields["23c_10_support_detail"]["value"] == "$800/mo for rent and childcare"


def test_ia_order_request_and_confidential_map():
    answers = {
        **_CA_ANSWERS,
        "ia.county": "Polk",
        "ia.order_request": ["temporary"],
        "ia.confidential_requests": ["seal_file", "remove_address"],
    }
    out = assemble_petition("IA", answers)
    fields = out["fields"]
    assert fields["23_temporary"]["value"] == "checked"
    assert fields["23_final"]["status"] == "not_collected"
    assert fields["24_seal_file"]["value"] == "checked"
    assert "24_seal_file" in out["review_items"]


def test_ia_relief_items_are_review_items():
    out = assemble_petition("IA", {**_CA_ANSWERS, "ia.county": "Polk"})
    assert "23c_1_stop_abuse" in out["review_items"]
    assert "7_intimate_relationship" in out["review_items"]


def test_ia_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("IA", {**answers, "ia.county": "Polk"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ia_missing_county_is_fact_needed():
    out = assemble_petition("IA", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_ia_field_table_items_are_unique():
    from vault.forms import ia

    items = [f.item for f in ia.IA_RELIEF_FIELDS]
    assert len(items) == len(set(items))


# --- Kentucky Petition/Motion for Order of Protection (AOC-275.1) ---


def test_ky_is_supported_and_metadata():
    assert "KY" in supported_jurisdictions()
    out = assemble_petition("KY", {**_CA_ANSWERS, "ky.county": "Jefferson"})
    assert out["form"] == "AOC-275.1"
    assert out["jurisdiction"] == "KY"


def test_ky_maps_core_and_physical_fields():
    answers = {
        **_CA_ANSWERS,
        "ky.county": "Jefferson",
        "respondent.height": "5'10",
        "respondent.hair_color": "Brown",
    }
    fields = assemble_petition("KY", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Jefferson"
    assert fields["respondent_height"]["value"] == "5'10"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_ky_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ky.county": "Jefferson",
        "ky.relationship_basis": ["married"],
        "ky.caution": ["weapon_involved"],
        "ky.relief": ["no_further_acts", "vacate_residence"],
        "ky.vacate_address": "100 Main St",
    }
    fields = assemble_petition("KY", answers)["fields"]
    assert fields["2_married"]["value"] == "checked"
    assert fields["2_dating_relationship"]["status"] == "not_collected"
    assert fields["caution_weapon_involved"]["value"] == "checked"
    assert fields["relief_no_further_acts"]["value"] == "checked"
    assert fields["relief_vacate_residence"]["value"] == "checked"
    assert fields["relief_vacate_address"]["value"] == "100 Main St"


def test_ky_ex_parte_maps_and_is_review():
    answers = {**_CA_ANSWERS, "ky.county": "Jefferson", "ky.ex_parte": True}
    out = assemble_petition("KY", answers)
    assert out["fields"]["ex_parte"]["value"] is True
    assert "ex_parte" in out["review_items"]


def test_ky_relief_items_are_review_items():
    out = assemble_petition("KY", {**_CA_ANSWERS, "ky.county": "Jefferson"})
    assert "relief_no_further_acts" in out["review_items"]
    assert "2_married" in out["review_items"]


def test_ky_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("KY", {**answers, "ky.county": "Jefferson"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ky_missing_county_is_fact_needed():
    out = assemble_petition("KY", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_ky_field_table_items_are_unique():
    from vault.forms import ky

    items = [f.item for f in ky.KY_OP_FIELDS]
    assert len(items) == len(set(items))


# --- Louisiana Petition for Protection from Abuse (LPOR B) ---


def test_la_is_supported_and_metadata():
    assert "LA" in supported_jurisdictions()
    out = assemble_petition("LA", {**_CA_ANSWERS, "la.parish": "Orleans"})
    assert out["form"] == "LPOR B"
    assert out["jurisdiction"] == "LA"


def test_la_maps_core_fields_and_confidential_address():
    out = assemble_petition("LA", {**_CA_ANSWERS, "la.parish": "Orleans"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["parish"]["value"] == "Orleans"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    # LA offers a confidential-address mechanism (§2a) — derived on, flagged.
    assert fields["address_confidential"]["value"] == "checked"
    assert "address_confidential" in out["review_items"]


def test_la_venue_relationship_abuse_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "la.parish": "Orleans",
        "la.venue": ["abuse_occurred"],
        "la.relationship_basis": ["spouse", "intimate_cohabitant"],
        "la.abuse_types": ["choked", "threatened_weapon"],
        "la.relief": ["no_abuse", "stay_away_residence"],
        "la.residence_address": "55 Bourbon St",
    }
    fields = assemble_petition("LA", answers)["fields"]
    assert fields["5_abuse_occurred"]["value"] == "checked"
    assert fields["6_spouse"]["value"] == "checked"
    assert fields["6_intimate_cohabitant"]["value"] == "checked"
    assert fields["8a_choked"]["value"] == "checked"
    assert fields["8a_slapped"]["status"] == "not_collected"
    assert fields["9a_no_abuse"]["value"] == "checked"
    assert fields["9c_stay_away_residence"]["value"] == "checked"
    assert fields["9c_residence_address"]["value"] == "55 Bourbon St"


def test_la_other_requests_map():
    answers = {
        **_CA_ANSWERS,
        "la.parish": "Orleans",
        "la.other_requests": ["child_support", "counseling"],
    }
    fields = assemble_petition("LA", answers)["fields"]
    assert fields["10_child_support"]["value"] == "checked"
    assert fields["10_counseling"]["value"] == "checked"
    assert fields["10_attorney_fees"]["status"] == "not_collected"


def test_la_relief_items_are_review_items():
    out = assemble_petition("LA", {**_CA_ANSWERS, "la.parish": "Orleans"})
    assert "9a_no_abuse" in out["review_items"]
    assert "6_spouse" in out["review_items"]
    assert "5_abuse_occurred" in out["review_items"]


def test_la_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("LA", {**answers, "la.parish": "Orleans"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_la_missing_parish_is_fact_needed():
    out = assemble_petition("LA", _CA_ANSWERS)
    assert out["fields"]["parish"]["value"] == "[FACT NEEDED]"
    assert "parish" in out["gaps"]


def test_la_field_table_items_are_unique():
    from vault.forms import la

    items = [f.item for f in la.LA_PFA_FIELDS]
    assert len(items) == len(set(items))


# --- Idaho Sworn Petition for Protection Order (CAO DV 1-1) ---


def test_id_is_supported_and_metadata():
    assert "ID" in supported_jurisdictions()
    out = assemble_petition("ID", {**_CA_ANSWERS, "id.county": "Ada"})
    assert out["form"] == "CAO DV 1-1"
    assert out["jurisdiction"] == "ID"


def test_id_maps_core_and_confidential_and_personal_conduct():
    out = assemble_petition("ID", {**_CA_ANSWERS, "id.county": "Ada"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Ada"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    # Confidential address + personal-conduct order are derived on and flagged.
    assert fields["address_confidential"]["value"] == "checked"
    assert fields["7a_personal_conduct"]["value"] == "checked"
    assert "7a_personal_conduct" in out["review_items"]
    assert "address_confidential" in out["review_items"]


def test_id_petition_type_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "id.county": "Ada",
        "id.petition_type": ["domestic_violence", "stalking"],
        "id.relationship_basis": ["spouse"],
        "id.relief": ["stay_away", "move_out"],
        "id.stay_away_places": ["my_residence", "my_workplace_school"],
        "id.move_out_address": "10 Boise Ave",
    }
    fields = assemble_petition("ID", answers)["fields"]
    assert fields["6_domestic_violence"]["value"] == "checked"
    assert fields["6_stalking"]["value"] == "checked"
    assert fields["6_telephone_threats"]["status"] == "not_collected"
    assert fields["2_spouse"]["value"] == "checked"
    assert fields["7b_stay_away"]["value"] == "checked"
    assert fields["7b_my_residence"]["value"] == "checked"
    assert fields["7c_move_out_address"]["value"] == "10 Boise Ave"


def test_id_relief_items_are_review_items():
    out = assemble_petition("ID", {**_CA_ANSWERS, "id.county": "Ada"})
    assert "7b_stay_away" in out["review_items"]
    assert "2_spouse" in out["review_items"]
    assert "6_domestic_violence" in out["review_items"]


def test_id_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("ID", {**answers, "id.county": "Ada"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_id_missing_county_is_fact_needed():
    out = assemble_petition("ID", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_id_field_table_items_are_unique():
    from vault.forms import idaho

    items = [f.item for f in idaho.ID_PO_FIELDS]
    assert len(items) == len(set(items))


# --- Minnesota Petition for Order for Protection (OFP102) ---


def test_mn_is_supported_and_metadata():
    assert "MN" in supported_jurisdictions()
    out = assemble_petition("MN", {**_CA_ANSWERS, "mn.county": "Hennepin"})
    assert out["form"] == "OFP102"
    assert out["jurisdiction"] == "MN"


def test_mn_maps_core_and_confidential_address():
    out = assemble_petition("MN", {**_CA_ANSWERS, "mn.county": "Hennepin"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Hennepin"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["address_confidential"]["value"] == "checked"
    assert "address_confidential" in out["review_items"]


def test_mn_relationship_and_two_relief_tiers_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "mn.county": "Hennepin",
        "mn.relationship_basis": ["married", "child_together"],
        "mn.relief": ["no_harm", "pet_possession"],
        "mn.pet_detail": "Our dog Rex",
        "mn.hearing_relief": ["financial_support", "firearms"],
    }
    fields = assemble_petition("MN", answers)["fields"]
    assert fields["7_married"]["value"] == "checked"
    assert fields["7_child_together"]["value"] == "checked"
    assert fields["15a_no_harm"]["value"] == "checked"
    assert fields["15g_pet_possession"]["value"] == "checked"
    assert fields["15g_pet_detail"]["value"] == "Our dog Rex"
    assert fields["17_financial_support"]["value"] == "checked"
    assert fields["21_firearms"]["value"] == "checked"
    assert fields["18_property"]["status"] == "not_collected"


def test_mn_immediate_danger_maps_and_is_review():
    answers = {**_CA_ANSWERS, "mn.county": "Hennepin", "mn.immediate_danger": True}
    out = assemble_petition("MN", answers)
    assert out["fields"]["immediate_danger"]["value"] is True
    assert "immediate_danger" in out["review_items"]


def test_mn_relief_items_are_review_items():
    out = assemble_petition("MN", {**_CA_ANSWERS, "mn.county": "Hennepin"})
    assert "15a_no_harm" in out["review_items"]
    assert "16_custody_parenting" in out["review_items"]
    assert "7_married" in out["review_items"]


def test_mn_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MN", {**answers, "mn.county": "Hennepin"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_mn_missing_county_is_fact_needed():
    out = assemble_petition("MN", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_mn_field_table_items_are_unique():
    from vault.forms import mn

    items = [f.item for f in mn.MN_OFP_FIELDS]
    assert len(items) == len(set(items))


# --- Mississippi Petition for Domestic Abuse Protection Order (93-21-1) ---


def test_ms_is_supported_and_metadata():
    assert "MS" in supported_jurisdictions()
    out = assemble_petition("MS", {**_CA_ANSWERS, "ms.county": "Hinds"})
    assert out["form"] == "Petition for Domestic Abuse Protection Order"
    assert out["jurisdiction"] == "MS"


def test_ms_maps_core_physical_and_confidential():
    answers = {
        **_CA_ANSWERS,
        "ms.county": "Hinds",
        "respondent.height": "5'9",
        "respondent.eye_color": "Brown",
    }
    out = assemble_petition("MS", answers)
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Hinds"
    assert fields["respondent_height"]["value"] == "5'9"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["address_confidential"]["value"] == "checked"
    assert "address_confidential" in out["review_items"]


def test_ms_relationship_abuse_caution_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "ms.county": "Hinds",
        "ms.relationship_basis": ["current_former_spouse"],
        "ms.abuse_acts": ["stalking_cyberstalking", "sexual_battery_rape"],
        "ms.caution": ["armed_dangerous"],
        "ms.relief": ["prohibit_abuse", "sole_use_residence"],
        "ms.residence_address": "200 Capitol St",
        "ms.chancery_relief": ["custody_support"],
    }
    fields = assemble_petition("MS", answers)["fields"]
    assert fields["1_current_former_spouse"]["value"] == "checked"
    assert fields["5_stalking_cyberstalking"]["value"] == "checked"
    assert fields["5_attempted_bodily_injury"]["status"] == "not_collected"
    assert fields["4_armed_dangerous"]["value"] == "checked"
    assert fields["9_prohibit_abuse"]["value"] == "checked"
    assert fields["9_residence_address"]["value"] == "200 Capitol St"
    assert fields["9c_custody_support"]["value"] == "checked"


def test_ms_emergency_relief_and_review_items():
    answers = {**_CA_ANSWERS, "ms.county": "Hinds", "ms.emergency_relief": True}
    out = assemble_petition("MS", answers)
    assert out["fields"]["emergency_relief"]["value"] is True
    assert "emergency_relief" in out["review_items"]
    assert "9_prohibit_abuse" in out["review_items"]
    assert "1_current_former_spouse" in out["review_items"]


def test_ms_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MS", {**answers, "ms.county": "Hinds"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_ms_missing_county_is_fact_needed():
    out = assemble_petition("MS", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_ms_field_table_items_are_unique():
    from vault.forms import ms

    items = [f.item for f in ms.MS_PO_FIELDS]
    assert len(items) == len(set(items))


# --- Indiana Petition for an Order for Protection (OJA-PO-0100) ---


def test_in_is_supported_and_metadata():
    assert "IN" in supported_jurisdictions()
    out = assemble_petition("IN", {**_CA_ANSWERS, "in.county": "Marion"})
    assert out["form"] == "OJA-PO-0100"
    assert out["jurisdiction"] == "IN"


def test_in_maps_core_and_confidential_and_ex_parte():
    out = assemble_petition("IN", {**_CA_ANSWERS, "in.county": "Marion"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Marion"
    assert fields["incident_narrative"]["value"].startswith("He grabbed my phone")
    assert fields["confidential_address"]["value"] == "checked"
    assert fields["ex_parte"]["value"] == "checked"
    assert "ex_parte" in out["review_items"]


def test_in_victim_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "in.county": "Marion",
        "in.victim_basis": ["dv_family_violence", "stalking"],
        "in.relationship_basis": ["spouse"],
        "in.relief": ["prohibit_dv", "evict"],
        "in.evict_address": "5 Indy Ln",
        "in.hearing_relief": ["child_support"],
    }
    fields = assemble_petition("IN", answers)["fields"]
    assert fields["1a_dv"]["value"] == "checked"
    assert fields["1c_stalking"]["value"] == "checked"
    assert fields["2_spouse"]["value"] == "checked"
    assert fields["9_prohibit_dv"]["value"] == "checked"
    assert fields["9_evict"]["value"] == "checked"
    assert fields["9_evict_address"]["value"] == "5 Indy Ln"
    assert fields["9h_child_support"]["value"] == "checked"


def test_in_relief_items_are_review_items():
    out = assemble_petition("IN", {**_CA_ANSWERS, "in.county": "Marion"})
    assert "9_prohibit_dv" in out["review_items"]
    assert "1a_dv" in out["review_items"]


def test_in_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("IN", {**answers, "in.county": "Marion"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_in_missing_county_is_fact_needed():
    out = assemble_petition("IN", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_in_field_table_items_are_unique():
    from vault.forms import indiana

    items = [f.item for f in indiana.IN_PO_FIELDS]
    assert len(items) == len(set(items))


# --- Missouri Petition for a Court Order of Protection - Adult (AA40) ---


def test_mo_is_supported_and_metadata():
    assert "MO" in supported_jurisdictions()
    out = assemble_petition("MO", {**_CA_ANSWERS, "mo.county": "Jackson"})
    assert out["form"] == "AA40"
    assert out["jurisdiction"] == "MO"


def test_mo_maps_core_physical_and_vehicle():
    answers = {
        **_CA_ANSWERS,
        "mo.county": "Jackson",
        "respondent.height": "5'11",
        "respondent.vehicle_make_model": "Ford F-150",
        "respondent.vehicle_plate": "MO-123",
    }
    fields = assemble_petition("MO", answers)["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Jackson"
    assert fields["respondent_height"]["value"] == "5'11"
    assert fields["respondent_vehicle"]["value"] == "Ford F-150"
    assert fields["respondent_vehicle_plate"]["value"] == "MO-123"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_mo_venue_relationship_acts_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "mo.county": "Jackson",
        "mo.venue": ["i_live"],
        "mo.relationship_basis": ["spouse"],
        "mo.abuse_acts": ["caused_harm", "stalked"],
        "mo.ex_parte_basis": ["immediate_danger"],
        "mo.relief": ["no_dv", "stay_distance"],
        "mo.stay_distance_feet": "500",
        "mo.additional_relief": ["custody", "child_support"],
    }
    fields = assemble_petition("MO", answers)["fields"]
    assert fields["venue_i_live"]["value"] == "checked"
    assert fields["a_spouse"]["value"] == "checked"
    assert fields["b_caused_harm"]["value"] == "checked"
    assert fields["b_stalked"]["value"] == "checked"
    assert fields["b_immediate_danger"]["value"] == "checked"
    assert fields["c1_no_dv"]["value"] == "checked"
    assert fields["c1_stay_distance_feet"]["value"] == "500"
    assert fields["c3_custody"]["value"] == "checked"
    assert fields["c4_child_support"]["value"] == "checked"
    assert fields["c4_attorney_fees"]["status"] == "not_collected"


def test_mo_serious_danger_maps_and_is_review():
    answers = {**_CA_ANSWERS, "mo.county": "Jackson", "mo.serious_danger": True}
    out = assemble_petition("MO", answers)
    assert out["fields"]["c2_serious_danger"]["value"] is True
    assert "c2_serious_danger" in out["review_items"]


def test_mo_relief_items_are_review_items():
    out = assemble_petition("MO", {**_CA_ANSWERS, "mo.county": "Jackson"})
    assert "c1_no_dv" in out["review_items"]
    assert "a_spouse" in out["review_items"]


def test_mo_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("MO", {**answers, "mo.county": "Jackson"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_mo_missing_county_is_fact_needed():
    out = assemble_petition("MO", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_mo_field_table_items_are_unique():
    from vault.forms import mo

    items = [f.item for f in mo.MO_PO_FIELDS]
    assert len(items) == len(set(items))


# --- South Carolina Petition for Family Court Order of Protection (SCCA 425) ---


def test_sc_is_supported_and_metadata():
    assert "SC" in supported_jurisdictions()
    out = assemble_petition("SC", {**_CA_ANSWERS, "sc.county": "Richland"})
    assert out["form"] == "SCCA 425"
    assert out["jurisdiction"] == "SC"


def test_sc_maps_core_fields():
    out = assemble_petition("SC", {**_CA_ANSWERS, "sc.county": "Richland"})
    fields = out["fields"]
    assert fields["petitioner"]["value"] == "Jane Doe"
    assert fields["respondent"]["value"] == "John Roe"
    assert fields["county"]["value"] == "Richland"
    assert fields["abuse_narrative"]["value"].startswith("He grabbed my phone")


def test_sc_venue_relationship_and_relief_check_their_boxes():
    answers = {
        **_CA_ANSWERS,
        "sc.county": "Richland",
        "sc.venue": ["abuse_occurred"],
        "sc.relationship_basis": ["married", "child_in_common"],
        "sc.relief": ["no_abuse", "stay_away", "custody"],
        "sc.stay_away_location": "My workplace",
        "sc.custody_detail": "Our two kids, no visitation",
    }
    fields = assemble_petition("SC", answers)["fields"]
    assert fields["1a_abuse_occurred"]["value"] == "checked"
    assert fields["7a_married"]["value"] == "checked"
    assert fields["7c_child_in_common"]["value"] == "checked"
    assert fields["9a_no_abuse"]["value"] == "checked"
    assert fields["9d_stay_away"]["value"] == "checked"
    assert fields["9d_stay_away_location"]["value"] == "My workplace"
    assert fields["9e_custody_detail"]["value"] == "Our two kids, no visitation"
    assert fields["9i_insurance"]["status"] == "not_collected"


def test_sc_relief_items_are_review_items():
    out = assemble_petition("SC", {**_CA_ANSWERS, "sc.county": "Richland"})
    assert "9a_no_abuse" in out["review_items"]
    assert "7a_married" in out["review_items"]
    assert "1a_abuse_occurred" in out["review_items"]


def test_sc_missing_required_is_fact_needed():
    answers = {k: v for k, v in _CA_ANSWERS.items() if k != "petitioner.legal_name"}
    out = assemble_petition("SC", {**answers, "sc.county": "Richland"})
    assert out["fields"]["petitioner"]["value"] == "[FACT NEEDED]"
    assert "petitioner" in out["gaps"]


def test_sc_missing_county_is_fact_needed():
    out = assemble_petition("SC", _CA_ANSWERS)
    assert out["fields"]["county"]["value"] == "[FACT NEEDED]"
    assert "county" in out["gaps"]


def test_sc_field_table_items_are_unique():
    from vault.forms import sc

    items = [f.item for f in sc.SC_PO_FIELDS]
    assert len(items) == len(set(items))


# --- route handler (POST /v1/vault/petition) ---


def test_handler_returns_assembled_form():
    resp = asyncio.run(
        handle_petition_request({"jurisdiction": "CA", "answers": _CA_ANSWERS}, env=None)
    )
    assert resp["status"] == 200
    payload = json.loads(resp["body"])
    assert payload["form"] == "DV-100"
    assert payload["fields"]["1a"]["value"] == "Jane Doe"


def test_handler_rejects_unsupported_jurisdiction():
    # AZ is a handoff jurisdiction with no petition assembler — the handler 400s.
    resp = asyncio.run(handle_petition_request({"jurisdiction": "AZ", "answers": {}}, env=None))
    assert resp["status"] == 400
    assert json.loads(resp["body"])["code"] == "unsupported_jurisdiction"


def test_handler_rejects_non_dict_answers():
    resp = asyncio.run(
        handle_petition_request({"jurisdiction": "CA", "answers": "nope"}, env=None)
    )
    assert resp["status"] == 400
    assert json.loads(resp["body"])["code"] == "bad_request"
