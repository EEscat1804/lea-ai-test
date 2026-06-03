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
    with pytest.raises(NotImplementedError):
        assemble_petition("NY", _CA_ANSWERS)


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
    resp = asyncio.run(handle_petition_request({"jurisdiction": "NY", "answers": {}}, env=None))
    assert resp["status"] == 400
    assert json.loads(resp["body"])["code"] == "unsupported_jurisdiction"


def test_handler_rejects_non_dict_answers():
    resp = asyncio.run(
        handle_petition_request({"jurisdiction": "CA", "answers": "nope"}, env=None)
    )
    assert resp["status"] == 400
    assert json.loads(resp["body"])["code"] == "bad_request"
