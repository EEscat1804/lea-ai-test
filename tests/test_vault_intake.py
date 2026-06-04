from vault.intake import determine_next_step

# Tier-1 answers, complete. Helpers below layer Tier-2 fields on top so the
# jurisdiction-gate regressions read as "given X is answered, what's asked next".
_TIER1_COMPLETE = {
    "petitioner.legal_name": "Jane Doe",
    "petitioner.dob": "1990-01-01",
    "petitioner.safe_mailing_address": "Addr",
    "petitioner.safe_phone": "123",
    "petitioner.safe_email": "jane@safe.com",
    "respondent.legal_name": "John Doe",
    "respondent.last_known_address": "Addr",
    "relationship.type": "Dating",
    "relationship.live_together_now": False,
    "relationship.lived_together_past": True,
    "relationship.children_in_common": False,
    "incidents[].date": "2026-05-01",
    "incidents[].location": "Somewhere",
    "incidents[].narrative": "Text",
    "incidents[].witnesses_present": "None",
    "incidents[].police_called": False,
    "incidents[].weapon_involved": False,
    "incidents[].injury": "None",
    "incidents[].pattern_frequency": "Once",
    "protected_persons.children[]": "None",
    "firearm.respondent_has_access": False,
    "prior_orders.exists": False,
}


def _answers(**overrides: object) -> dict[str, object]:
    return {**_TIER1_COMPLETE, **overrides}


# Every CA Tier-2 field answered, up to (but not including) the orders-requested
# step. Used to test the DV-100 items 10-28 intake flow.
_CA_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.gender": "female",
    "petitioner.interpreter_language": "English",
    "petitioner.disability_accommodation": "None",
    "respondent.height": "6'0",
    "respondent.weight": "180",
    "respondent.eye_color": "Green",
    "respondent.hair_color": "Blonde",
    "respondent.distinguishing_marks": "None",
    "respondent.employer_name": "Corp",
    "respondent.employer_address": "Addr",
    "respondent.vehicle_make_model": "Truck",
    "respondent.vehicle_color": "White",
    "respondent.vehicle_plate": "123",
    "respondent.immigration_status_known": False,
    "respondent.prior_criminal_history": False,
    # New: respondent identity (2b-2e) + no extra incidents, so the next ask is orders.
    "respondent.age": "35",
    "respondent.dob": "1991-03-02",
    "respondent.gender": "male",
    "respondent.race": "not disclosed",
    "incidents.add_2": False,
}


def test_ca_asks_respondent_identity_before_orders() -> None:
    answers = {
        k: v
        for k, v in _CA_THROUGH_TIER2.items()
        if k not in {"respondent.age", "respondent.dob", "respondent.gender",
                     "respondent.race", "incidents.add_2"}
    }
    step = determine_next_step("CA", answers)
    assert step["step"] == "respondent.age"


def test_ca_married_filer_asked_marriage_status() -> None:
    answers = {**_CA_THROUGH_TIER2, "relationship.type": "married"}
    step = determine_next_step("CA", answers)
    assert step["step"] == "relationship.marriage_intact"


def test_ca_additional_incident_collected_when_requested() -> None:
    answers = {**_CA_THROUGH_TIER2, "incidents.add_2": True}
    step = determine_next_step("CA", answers)
    assert step["step"] == "incident_2.date"


def test_ca_property_control_asks_describe_then_why() -> None:
    base = {**_CA_THROUGH_TIER2, "selected_reliefs_intents": ["property_control"]}
    step = determine_next_step("CA", base)
    assert step["step"] == "relief.property_describe"
    step = determine_next_step("CA", {**base, "relief.property_describe": "the car"})
    assert step["step"] == "relief.property_why"


def test_ca_asks_which_orders_after_tier2() -> None:
    step = determine_next_step("CA", _CA_THROUGH_TIER2)
    assert step["step"] == "selected_reliefs_intents"
    assert "stay_away" in step["schema"]["items"]["enum"]


def test_ca_stay_away_asks_places_then_distance() -> None:
    base = {**_CA_THROUGH_TIER2, "selected_reliefs_intents": ["stay_away"]}
    step = determine_next_step("CA", base)
    assert step["step"] == "relief.stay_away_places"

    step = determine_next_step("CA", {**base, "relief.stay_away_places": ["home"]})
    assert step["step"] == "relief.stay_away_distance_yards"


def test_ca_move_out_asks_address() -> None:
    answers = {**_CA_THROUGH_TIER2, "selected_reliefs_intents": ["move_out"]}
    step = determine_next_step("CA", answers)
    assert step["step"] == "relief.move_out_address"


def test_ca_orders_with_no_detail_needed_completes() -> None:
    # no_abuse needs no follow-up; with support not requested, intake is done.
    answers = {**_CA_THROUGH_TIER2, "selected_reliefs_intents": ["no_abuse"]}
    step = determine_next_step("CA", answers)
    assert step["step"] == "done"


def test_ca_child_support_order_still_gates_ssn() -> None:
    answers = {**_CA_THROUGH_TIER2, "selected_reliefs_intents": ["child_support"]}
    step = determine_next_step("CA", answers)
    assert step["step"] == "petitioner.ssn"


# ---------------------------------------------------------------------------
# Jurisdiction-gate sync with the DVRO Multi-State Intake doc.
# Q24 minor filing = CA/TX (not NY/FL); Q31-35 physical & Q41-43 vehicle = CA/FL
# (not NY/TX). Regressions against the old {CA,NY,TX,FL} copy-paste.
# ---------------------------------------------------------------------------


def test_ny_minor_does_not_get_minor_filing_path() -> None:
    # NY is NOT in the doc's Q24 list — a NY minor must skip the minor-filing step.
    step = determine_next_step("NY", _answers(**{"petitioner.dob": "2010-01-01"}))
    assert step["step"] != "petitioner.minor_filing_path"


def test_fl_minor_does_not_get_minor_filing_path() -> None:
    # FL is NOT in the doc's Q24 list either.
    step = determine_next_step("FL", _answers(**{"petitioner.dob": "2010-01-01"}))
    assert step["step"] != "petitioner.minor_filing_path"


def test_tx_skips_physical_description() -> None:
    # TX is NOT in the doc's Q31-35 set. With interpreter answered, the next ask
    # must be employer (the block right after physical), never respondent.height.
    step = determine_next_step("TX", _answers(**{"petitioner.interpreter_language": "English"}))
    assert step["step"] == "respondent.employer_name"


def test_tx_skips_vehicle_description() -> None:
    # TX is NOT in the doc's Q41-43 set. With employer answered, the next ask must
    # be the law-enforcement question, never respondent.vehicle_make_model.
    step = determine_next_step(
        "TX",
        _answers(
            **{
                "petitioner.interpreter_language": "English",
                "respondent.employer_name": "Corp",
                "respondent.employer_address": "Addr",
            }
        ),
    )
    assert step["step"] == "respondent.is_law_enforcement"


def test_fl_still_asks_physical_description() -> None:
    # FL IS in the doc's Q31-35 set — the fix must not over-correct.
    step = determine_next_step(
        "FL",
        _answers(
            **{
                "petitioner.race": "skip",
                "petitioner.gender": "skip",
                "petitioner.interpreter_language": "English",
                "petitioner.disability_accommodation": "None",
            }
        ),
    )
    assert step["step"] == "respondent.height"


def test_fl_requires_petitioner_race_field() -> None:
    # Strict 27-state regulatory framework alignment for FL
    mock_tier1_done = {
        "petitioner.legal_name": "Jane Doe",
        "petitioner.dob": "1990-01-01",
        "petitioner.safe_mailing_address": "Addr",
        "petitioner.safe_phone": "123",
        "petitioner.safe_email": "jane@safe.com",
        "respondent.legal_name": "John Doe",
        "respondent.last_known_address": "Addr",
        "relationship.type": "Dating",
        "relationship.live_together_now": False,
        "relationship.lived_together_past": True,
        "relationship.children_in_common": False,
        "incidents[].date": "2026-05-01",
        "incidents[].location": "Miami, FL",
        "incidents[].narrative": "Text",
        "incidents[].witnesses_present": "None",
        "incidents[].police_called": False,
        "incidents[].weapon_involved": False,
        "incidents[].injury": "None",
        "incidents[].pattern_frequency": "Once",
        "protected_persons.children[]": "None",
        "firearm.respondent_has_access": False,
        "prior_orders.exists": False,
    }
    step = determine_next_step("FL", mock_tier1_done)
    assert step["step"] == "petitioner.race"


# Every FL Tier-2 field answered, up to (but not including) the FL relief block,
# so the gate regressions read as "given Tier-2 is done, what's asked next".
_FL_THROUGH_TIER2 = _answers(
    **{
        "petitioner.race": "not disclosed",
        "petitioner.gender": "female",
        "petitioner.interpreter_language": "English",
        "petitioner.disability_accommodation": "none",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.employer_hours": "9-5",
        "respondent.vehicle_make_model": "Honda Civic",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.is_law_enforcement": False,
        "respondent.is_active_military": False,
        "respondent.prior_criminal_history": False,
    }
)


def test_fl_asks_county_then_relief_after_tier2() -> None:
    # FL collects its county first, then the relief list.
    step = determine_next_step("FL", _FL_THROUGH_TIER2)
    assert step["step"] == "fl.county"
    step = determine_next_step("FL", {**_FL_THROUGH_TIER2, "fl.county": "Miami-Dade"})
    assert step["step"] == "fl.relief"


def test_fl_exclusive_residence_asks_address() -> None:
    answers = {
        **_FL_THROUGH_TIER2,
        "fl.county": "Miami-Dade",
        "fl.relief": ["exclusive_residence"],
    }
    step = determine_next_step("FL", answers)
    assert step["step"] == "fl.residence_address"


def test_fl_no_detail_relief_completes() -> None:
    # A relief set needing no follow-up reaches done (no support => no SSN gate).
    answers = {
        **_FL_THROUGH_TIER2,
        "fl.county": "Miami-Dade",
        "fl.relief": ["no_dv", "no_contact"],
    }
    step = determine_next_step("FL", answers)
    assert step["step"] == "done"


def test_fl_support_relief_gates_ssn() -> None:
    # Requesting support via fl.relief triggers the SSN gate, same as CA's
    # selected_reliefs_intents path.
    answers = {
        **_FL_THROUGH_TIER2,
        "fl.county": "Miami-Dade",
        "fl.relief": ["child_support"],
    }
    step = determine_next_step("FL", answers)
    assert step["step"] == "petitioner.ssn"


# Every DE Tier-2 field answered, up to (but not including) the DE block, so the
# gate regressions read as "given Tier-2 is done, what's asked next".
_DE_THROUGH_TIER2 = _answers(
    **{
        "petitioner.interpreter_language": "English",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.dob": "1985-01-01",
    }
)


def test_de_asks_county_then_residency() -> None:
    step = determine_next_step("DE", _DE_THROUGH_TIER2)
    assert step["step"] == "de.county"
    step = determine_next_step("DE", {**_DE_THROUGH_TIER2, "de.county": "kent"})
    assert step["step"] == "de.respondent_is_de_resident"


def test_de_nonresident_asks_for_de_connection() -> None:
    answers = {**_DE_THROUGH_TIER2, "de.county": "kent", "de.respondent_is_de_resident": False}
    step = determine_next_step("DE", answers)
    assert step["step"] == "de.de_connection"


def test_de_resident_skips_connection_and_asks_acts() -> None:
    answers = {**_DE_THROUGH_TIER2, "de.county": "kent", "de.respondent_is_de_resident": True}
    step = determine_next_step("DE", answers)
    assert step["step"] == "de.abuse_acts"


def test_de_extended_duration_asks_aggravating_factors() -> None:
    answers = {
        **_DE_THROUGH_TIER2,
        "de.county": "kent",
        "de.respondent_is_de_resident": True,
        "de.abuse_acts": ["physical_injury"],
        "de.relief": ["no_abuse"],
        "de.extended_duration": True,
    }
    step = determine_next_step("DE", answers)
    assert step["step"] == "de.aggravating_factors"


def test_de_completes_after_relief_without_extension() -> None:
    # No detail-needing relief and no extension => intake reaches done (DE is not
    # in the SSN-for-support set).
    answers = {
        **_DE_THROUGH_TIER2,
        "de.county": "kent",
        "de.respondent_is_de_resident": True,
        "de.abuse_acts": ["physical_injury"],
        "de.relief": ["no_abuse"],
        "de.extended_duration": False,
    }
    step = determine_next_step("DE", answers)
    assert step["step"] == "done"


# Every DC Tier-2 field answered (just the unconditional employer block), up to
# the DC block, so the gate regressions read as "given Tier-2 is done, what next".
_DC_THROUGH_TIER2 = _answers(
    **{
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
    }
)


def test_dc_asks_nexus_then_incident_then_relief() -> None:
    step = determine_next_step("DC", _DC_THROUGH_TIER2)
    assert step["step"] == "dc.petitioner_dc_nexus"
    step = determine_next_step("DC", {**_DC_THROUGH_TIER2, "dc.petitioner_dc_nexus": True})
    assert step["step"] == "dc.incident_in_dc"
    step = determine_next_step(
        "DC",
        {**_DC_THROUGH_TIER2, "dc.petitioner_dc_nexus": True, "dc.incident_in_dc": True},
    )
    assert step["step"] == "dc.relief"


def test_dc_stay_away_other_places_asks_detail() -> None:
    answers = {
        **_DC_THROUGH_TIER2,
        "dc.petitioner_dc_nexus": True,
        "dc.incident_in_dc": True,
        "dc.relief": ["stay_away"],
        "dc.stay_away_places": ["home", "other_places"],
    }
    step = determine_next_step("DC", answers)
    assert step["step"] == "dc.stay_away_other_places"


def test_dc_completes_after_relief_without_details() -> None:
    # No detail-needing relief => done (DC is not in the SSN-for-support set).
    answers = {
        **_DC_THROUGH_TIER2,
        "dc.petitioner_dc_nexus": True,
        "dc.incident_in_dc": True,
        "dc.relief": ["no_abuse", "emergency_tpo"],
    }
    step = determine_next_step("DC", answers)
    assert step["step"] == "done"


# Every CT Tier-2 field answered (CT is in the interpreter gate, is a
# physical-description AND vehicle state, plus the unconditional employer block,
# plus its own respondent dob/race/gender), up to the CT judicial-district step.
_CT_THROUGH_TIER2 = _answers(
    **{
        "petitioner.interpreter_language": "English",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.vehicle_make_model": "Honda",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1985-01-01",
        "respondent.race": "not disclosed",
        "respondent.gender": "male",
    }
)


def test_ct_asks_interpreter_language() -> None:
    # CT's JD-FM-137 has interpreter fields, so CT is in the interpreter gate.
    base = {k: v for k, v in _CT_THROUGH_TIER2.items() if k != "petitioner.interpreter_language"}
    step = determine_next_step("CT", base)
    assert step["step"] == "petitioner.interpreter_language"


def test_ct_asks_respondent_description_then_district() -> None:
    # After the shared physical/vehicle blocks, CT collects respondent dob/race/
    # gender, then its judicial district.
    base = {
        k: v
        for k, v in _CT_THROUGH_TIER2.items()
        if k not in ("respondent.dob", "respondent.race", "respondent.gender")
    }
    step = determine_next_step("CT", base)
    assert step["step"] == "respondent.dob"
    step = determine_next_step("CT", _CT_THROUGH_TIER2)
    assert step["step"] == "ct.judicial_district"


def test_ct_asks_relief_after_district() -> None:
    step = determine_next_step("CT", {**_CT_THROUGH_TIER2, "ct.judicial_district": "Hartford"})
    assert step["step"] == "ct.relief"


def test_ct_custody_asks_visitation() -> None:
    answers = {**_CT_THROUGH_TIER2, "ct.judicial_district": "Hartford", "ct.relief": ["custody"]}
    step = determine_next_step("CT", answers)
    assert step["step"] == "ct.visitation"


def test_ct_ends_at_ex_parte_then_done() -> None:
    answers = {**_CT_THROUGH_TIER2, "ct.judicial_district": "Hartford", "ct.relief": ["no_abuse"]}
    step = determine_next_step("CT", answers)
    assert step["step"] == "ct.ex_parte"
    step = determine_next_step("CT", {**answers, "ct.ex_parte": True})
    assert step["step"] == "done"


# Every CO Tier-2 field answered (CO is a physical-description state, plus the
# unconditional employer block), up to the CO county step.
_CO_THROUGH_TIER2 = _answers(
    **{
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
    }
)


def test_co_asks_county_then_basis_then_imminent_danger() -> None:
    step = determine_next_step("CO", _CO_THROUGH_TIER2)
    assert step["step"] == "co.county"
    step = determine_next_step("CO", {**_CO_THROUGH_TIER2, "co.county": "Denver"})
    assert step["step"] == "co.basis"
    step = determine_next_step(
        "CO", {**_CO_THROUGH_TIER2, "co.county": "Denver", "co.basis": ["domestic_abuse"]}
    )
    assert step["step"] == "co.imminent_danger"


def test_co_stay_away_asks_distance_then_places() -> None:
    base = {
        **_CO_THROUGH_TIER2,
        "co.county": "Denver",
        "co.basis": ["domestic_abuse"],
        "co.imminent_danger": ["harm_life_health"],
        "co.relief": ["stay_away"],
    }
    step = determine_next_step("CO", base)
    assert step["step"] == "co.stay_away_distance_yards"
    step = determine_next_step("CO", {**base, "co.stay_away_distance_yards": 100})
    assert step["step"] == "co.stay_away_places"


def test_co_completes_after_simple_relief() -> None:
    answers = {
        **_CO_THROUGH_TIER2,
        "co.county": "Denver",
        "co.basis": ["domestic_abuse"],
        "co.imminent_danger": ["harm_life_health"],
        "co.relief": ["no_abuse"],
    }
    step = determine_next_step("CO", answers)
    assert step["step"] == "done"


# Every AR Tier-2 field answered (AR is a physical-description AND vehicle state,
# is in the interpreter and prior-criminal gates, plus the unconditional employer
# block, plus its own respondent dob/race/gender), up to the AR county step.
_AR_THROUGH_TIER2 = _answers(
    **{
        "petitioner.interpreter_language": "English",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.vehicle_make_model": "Honda",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.prior_criminal_history": False,
        "respondent.dob": "1985-01-01",
        "respondent.race": "not disclosed",
        "respondent.gender": "male",
    }
)


def test_ar_prior_criminal_history_is_asked() -> None:
    # AR was added to the prior-criminal-history gate (form item 6).
    base = {
        k: v for k, v in _AR_THROUGH_TIER2.items() if k != "respondent.prior_criminal_history"
    }
    step = determine_next_step("AR", base)
    assert step["step"] == "respondent.prior_criminal_history"


def test_ar_asks_county_then_relief() -> None:
    step = determine_next_step("AR", _AR_THROUGH_TIER2)
    assert step["step"] == "ar.county"
    step = determine_next_step("AR", {**_AR_THROUGH_TIER2, "ar.county": "Pulaski"})
    assert step["step"] == "ar.relief"


def test_ar_exclude_residence_asks_address_then_owner() -> None:
    base = {**_AR_THROUGH_TIER2, "ar.county": "Pulaski", "ar.relief": ["exclude_residence"]}
    step = determine_next_step("AR", base)
    assert step["step"] == "ar.residence_address"
    step = determine_next_step("AR", {**base, "ar.residence_address": "12 Oak St"})
    assert step["step"] == "ar.residence_owner"


def test_ar_completes_after_simple_relief() -> None:
    answers = {**_AR_THROUGH_TIER2, "ar.county": "Pulaski", "ar.relief": ["custody"]}
    step = determine_next_step("AR", answers)
    assert step["step"] == "done"


# AK is in none of the doc's physical/vehicle/minor sets, so only the
# unconditional employer block (and the AK block's respondent DOB) precede the
# AK court-location step.
_AK_THROUGH_TIER2 = _answers(
    **{
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.dob": "1985-01-01",
    }
)


def test_ak_asks_court_location_then_order_type_then_children() -> None:
    step = determine_next_step("AK", _AK_THROUGH_TIER2)
    assert step["step"] == "ak.court_location"
    step = determine_next_step("AK", {**_AK_THROUGH_TIER2, "ak.court_location": "Anchorage"})
    assert step["step"] == "ak.order_type"
    step = determine_next_step(
        "AK",
        {**_AK_THROUGH_TIER2, "ak.court_location": "Anchorage", "ak.order_type": ["ex_parte"]},
    )
    assert step["step"] == "ak.children_in_household"


def test_ak_long_term_order_asks_long_term_protections() -> None:
    answers = {
        **_AK_THROUGH_TIER2,
        "ak.court_location": "Anchorage",
        "ak.order_type": ["long_term"],
        "ak.children_in_household": False,
        "ak.protections": ["no_dv"],
    }
    step = determine_next_step("AK", answers)
    assert step["step"] == "ak.long_term_protections"


def test_ak_ex_parte_only_skips_long_term_protections() -> None:
    # An ex-parte-only request never asks for §6 long-term protections; it ends at
    # the law-enforcement assistance step, then done.
    answers = {
        **_AK_THROUGH_TIER2,
        "ak.court_location": "Anchorage",
        "ak.order_type": ["ex_parte"],
        "ak.children_in_household": False,
        "ak.protections": ["no_dv"],
    }
    step = determine_next_step("AK", answers)
    assert step["step"] == "ak.le_assistance"
    step = determine_next_step("AK", {**answers, "ak.le_assistance": []})
    assert step["step"] == "done"


def test_ak_children_in_household_asks_custody() -> None:
    answers = {
        **_AK_THROUGH_TIER2,
        "ak.court_location": "Anchorage",
        "ak.order_type": ["ex_parte"],
        "ak.children_in_household": True,
        "ak.protections": ["no_dv"],
    }
    step = determine_next_step("AK", answers)
    assert step["step"] == "ak.custody"


# AL is in the minor-filing set only (not physical/vehicle), so only the
# unconditional employer block (and the AL block's respondent DOB) precede the
# AL county step.
_AL_THROUGH_TIER2 = _answers(
    **{
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.dob": "1985-01-01",
    }
)


def test_al_asks_county_then_request_type_then_abuse_acts() -> None:
    step = determine_next_step("AL", _AL_THROUGH_TIER2)
    assert step["step"] == "al.county"
    step = determine_next_step("AL", {**_AL_THROUGH_TIER2, "al.county": "Jefferson"})
    assert step["step"] == "al.request_type"
    step = determine_next_step(
        "AL",
        {**_AL_THROUGH_TIER2, "al.county": "Jefferson", "al.request_type": ["protection_order"]},
    )
    assert step["step"] == "al.abuse_acts"


def test_al_exclude_residence_asks_residence_basis() -> None:
    answers = {
        **_AL_THROUGH_TIER2,
        "al.county": "Jefferson",
        "al.request_type": ["protection_order"],
        "al.abuse_acts": ["injured"],
        "al.ex_parte_relief": ["exclude_residence"],
        "al.final_relief": [],
    }
    step = determine_next_step("AL", answers)
    assert step["step"] == "al.residence_basis"


def test_al_completes_after_simple_relief() -> None:
    answers = {
        **_AL_THROUGH_TIER2,
        "al.county": "Jefferson",
        "al.request_type": ["protection_order"],
        "al.abuse_acts": ["injured"],
        "al.ex_parte_relief": ["enjoin_abuse"],
        "al.final_relief": [],
    }
    step = determine_next_step("AL", answers)
    assert step["step"] == "done"


# WY is a physical-description AND vehicle state, plus the unconditional employer
# block and its own respondent dob/race/gender, up to the WY county step.
_WY_THROUGH_TIER2 = _answers(
    **{
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.vehicle_make_model": "Honda",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1985-01-01",
        "respondent.race": "not disclosed",
        "respondent.gender": "male",
    }
)


def test_wy_asks_county_then_district_then_probation_then_relief() -> None:
    step = determine_next_step("WY", _WY_THROUGH_TIER2)
    assert step["step"] == "wy.county"
    step = determine_next_step("WY", {**_WY_THROUGH_TIER2, "wy.county": "Laramie"})
    assert step["step"] == "wy.judicial_district"
    step = determine_next_step(
        "WY", {**_WY_THROUGH_TIER2, "wy.county": "Laramie", "wy.judicial_district": "First"}
    )
    assert step["step"] == "wy.respondent_probation"


def test_wy_stay_away_asks_distance_then_places() -> None:
    base = {
        **_WY_THROUGH_TIER2,
        "wy.county": "Laramie",
        "wy.judicial_district": "First",
        "wy.respondent_probation": False,
        "wy.relief": ["stay_away"],
    }
    step = determine_next_step("WY", base)
    assert step["step"] == "wy.stay_away_distance"
    step = determine_next_step("WY", {**base, "wy.stay_away_distance": "500 feet"})
    assert step["step"] == "wy.stay_away_places"


def test_wy_ends_at_appearance_then_done() -> None:
    answers = {
        **_WY_THROUGH_TIER2,
        "wy.county": "Laramie",
        "wy.judicial_district": "First",
        "wy.respondent_probation": False,
        "wy.relief": ["personal_conduct"],
    }
    step = determine_next_step("WY", answers)
    assert step["step"] == "wy.appearance"
    step = determine_next_step("WY", {**answers, "wy.appearance": "in_person"})
    assert step["step"] == "done"


# WI is in the interpreter gate and is a physical-description AND vehicle state,
# plus the unconditional employer block and its own respondent dob/race/gender,
# up to the WI county step.
_WI_THROUGH_TIER2 = _answers(
    **{
        "petitioner.interpreter_language": "English",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.vehicle_make_model": "Honda",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1985-01-01",
        "respondent.race": "not disclosed",
        "respondent.gender": "male",
    }
)


def test_wi_asks_county_then_imminent_danger_then_relief() -> None:
    step = determine_next_step("WI", _WI_THROUGH_TIER2)
    assert step["step"] == "wi.county"
    step = determine_next_step("WI", {**_WI_THROUGH_TIER2, "wi.county": "Dane"})
    assert step["step"] == "wi.imminent_danger"
    step = determine_next_step(
        "WI", {**_WI_THROUGH_TIER2, "wi.county": "Dane", "wi.imminent_danger": True}
    )
    assert step["step"] == "wi.relief"


def test_wi_other_relief_asks_detail() -> None:
    answers = {
        **_WI_THROUGH_TIER2,
        "wi.county": "Dane",
        "wi.imminent_danger": True,
        "wi.relief": ["other"],
    }
    step = determine_next_step("WI", answers)
    assert step["step"] == "wi.relief_other"


def test_wi_completes_after_additional_requests() -> None:
    answers = {
        **_WI_THROUGH_TIER2,
        "wi.county": "Dane",
        "wi.imminent_danger": True,
        "wi.relief": ["no_abuse"],
        "wi.injunction_duration": "",
        "wi.additional_requests": [],
    }
    step = determine_next_step("WI", answers)
    assert step["step"] == "done"


# WV is in the disability gate and is a physical-description AND vehicle state,
# plus the unconditional employer block and its own respondent dob/race/gender,
# up to the WV county step.
_WV_THROUGH_TIER2 = _answers(
    **{
        "petitioner.disability_accommodation": "none",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "1 Work Way",
        "respondent.vehicle_make_model": "Honda",
        "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1985-01-01",
        "respondent.race": "not disclosed",
        "respondent.gender": "male",
    }
)


def test_wv_asks_county_then_acts_then_duration() -> None:
    step = determine_next_step("WV", _WV_THROUGH_TIER2)
    assert step["step"] == "wv.county"
    step = determine_next_step("WV", {**_WV_THROUGH_TIER2, "wv.county": "Kanawha"})
    assert step["step"] == "wv.abuse_acts"
    step = determine_next_step(
        "WV", {**_WV_THROUGH_TIER2, "wv.county": "Kanawha", "wv.abuse_acts": ["physical_harm"]}
    )
    assert step["step"] == "wv.po_duration"


def test_wv_one_year_asks_duration_reasons() -> None:
    answers = {
        **_WV_THROUGH_TIER2,
        "wv.county": "Kanawha",
        "wv.abuse_acts": ["physical_harm"],
        "wv.po_duration": "1_year",
    }
    step = determine_next_step("WV", answers)
    assert step["step"] == "wv.duration_reasons"


def test_wv_90_day_skips_duration_reasons_and_asks_permissive() -> None:
    answers = {
        **_WV_THROUGH_TIER2,
        "wv.county": "Kanawha",
        "wv.abuse_acts": ["physical_harm"],
        "wv.po_duration": "90_day",
    }
    step = determine_next_step("WV", answers)
    assert step["step"] == "wv.permissive_relief"


def test_wv_completes_after_permissive() -> None:
    answers = {
        **_WV_THROUGH_TIER2,
        "wv.county": "Kanawha",
        "wv.abuse_acts": ["physical_harm"],
        "wv.po_duration": "90_day",
        "wv.permissive_relief": ["no_abuse"],
    }
    step = determine_next_step("WV", answers)
    assert step["step"] == "done"


def test_ssn_conditional_trigger_on_support_relief() -> None:
    # Terminal conditional trigger validation for requested reliefs
    mock_all_done_but_ssn = {
        "petitioner.legal_name": "Jane Doe",
        "petitioner.dob": "1990-01-01",
        "petitioner.safe_mailing_address": "Addr",
        "petitioner.safe_phone": "123",
        "petitioner.safe_email": "jane@safe.com",
        "respondent.legal_name": "John Doe",
        "respondent.last_known_address": "Addr",
        "relationship.type": "Dating",
        "relationship.live_together_now": False,
        "relationship.lived_together_past": True,
        "relationship.children_in_common": False,
        "incidents[].date": "2026-05-01",
        "incidents[].location": "Austin, TX",
        "incidents[].narrative": "Text",
        "incidents[].witnesses_present": "None",
        "incidents[].police_called": False,
        "incidents[].weapon_involved": False,
        "incidents[].injury": "None",
        "incidents[].pattern_frequency": "Once",
        "protected_persons.children[]": "None",
        "firearm.respondent_has_access": False,
        "prior_orders.exists": False,
        "petitioner.interpreter_language": "English",
        "respondent.height": "6'0",
        "respondent.weight": "180",
        "respondent.eye_color": "Green",
        "respondent.hair_color": "Blonde",
        "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp",
        "respondent.employer_address": "Addr",
        "respondent.vehicle_make_model": "Truck",
        "respondent.vehicle_color": "White",
        "respondent.vehicle_plate": "123",
        "respondent.is_law_enforcement": False,
        "respondent.prior_criminal_history": False,
        "respondent.prior_dv_finding": False,
        "respondent.parental_rights_terminated": False,
        # TX orders block (now precedes the SSN gate) — answered so we reach it.
        "tx.terms": ["no_family_violence"],
        "tx.exclusive_residence": False,
        "tx.ex_parte": True,
        "tx.phone_transfer": False,
        "tx.confidential": True,
        "selected_reliefs_intents": ["child_support"],
    }
    step = determine_next_step("TX", mock_all_done_but_ssn)
    assert step["step"] == "petitioner.ssn"


def test_first_step_asks_for_petitioner_name() -> None:
    step = determine_next_step("CA", {})
    assert step["step"] == "petitioner.legal_name"


def test_il_redirects_immediately_after_tier1() -> None:
    mock_tier1_done = {
        "petitioner.legal_name": "Jane Doe",
        "petitioner.dob": "1990-01-01",
        "petitioner.safe_mailing_address": "Addr",
        "petitioner.safe_phone": "123",
        "petitioner.safe_email": "jane@safe.com",
        "respondent.legal_name": "John Doe",
        "respondent.last_known_address": "Addr",
        "relationship.type": "Dating",
        "relationship.live_together_now": False,
        "relationship.lived_together_past": True,
        "relationship.children_in_common": False,
        "incidents[].date": "2026-05-01",
        "incidents[].location": "Chicago, IL",
        "incidents[].narrative": "Text",
        "incidents[].witnesses_present": "None",
        "incidents[].police_called": False,
        "incidents[].weapon_involved": False,
        "incidents[].injury": "None",
        "incidents[].pattern_frequency": "Once",
        "protected_persons.children[]": "None",
        "firearm.respondent_has_access": False,
        "prior_orders.exists": False,
    }
    step = determine_next_step("IL", mock_tier1_done)
    assert step["step"] == "handoff"
    assert step["action"] == "redirect"


def test_no_paper_states_all_redirect_after_tier1() -> None:
    # The states with no physical DVRO form (per the boss) take the handoff path.
    for state in ("AZ", "IL", "KS", "NJ"):
        step = determine_next_step(state, _TIER1_COMPLETE)
        assert step["step"] == "handoff", state
        assert step["action"] == "redirect"


def test_wa_is_accepted_and_first_step_is_petitioner_name() -> None:
    # WA is a supported (form-mapped) jurisdiction, not a handoff or rejection.
    step = determine_next_step("WA", {})
    assert step["step"] == "petitioner.legal_name"


# Every WA field answered, up to (but not including) the restraints step.
_WA_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.interpreter_language": "English",
    "petitioner.disability_accommodation": "None",
    "respondent.height": "6'0",
    "respondent.weight": "180",
    "respondent.eye_color": "Brown",
    "respondent.hair_color": "Black",
    "respondent.distinguishing_marks": "None",
    "respondent.employer_name": "Corp",
    "respondent.employer_address": "Addr",
    "respondent.vehicle_make_model": "Sedan",
    "respondent.vehicle_color": "Blue",
    "respondent.vehicle_plate": "ABC123",
    "respondent.dob": "1988-02-02",
    "respondent.age_band": "18_or_over",
    "wa.jurisdiction_basis": ["lives_here"],
}


def test_wa_asks_restraints_after_tier2() -> None:
    step = determine_next_step("WA", _WA_THROUGH_TIER2)
    assert step["step"] == "wa.restraints"
    assert "stay_away" in step["schema"]["items"]["enum"]


def test_wa_stay_away_asks_places_then_distance() -> None:
    base = {**_WA_THROUGH_TIER2, "wa.restraints": ["stay_away"]}
    step = determine_next_step("WA", base)
    assert step["step"] == "wa.stay_away_places"
    step = determine_next_step("WA", {**base, "wa.stay_away_places": ["residence"]})
    assert step["step"] == "wa.stay_away_distance_feet"


_TX_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.interpreter_language": "English",
    "respondent.employer_name": "Corp",
    "respondent.employer_address": "Addr",
    "respondent.is_law_enforcement": False,
    "respondent.prior_criminal_history": False,
    "respondent.prior_dv_finding": False,
    "respondent.parental_rights_terminated": False,
}


def test_tx_asks_terms_after_tier2() -> None:
    step = determine_next_step("TX", _TX_THROUGH_TIER2)
    assert step["step"] == "tx.terms"
    assert "prohibit_firearm" in step["schema"]["items"]["enum"]


def test_tx_stay_away_asks_who_then_distance() -> None:
    base = {**_TX_THROUGH_TIER2, "tx.terms": ["no_go_within_distance"]}
    step = determine_next_step("TX", base)
    assert step["step"] == "tx.stay_away_places"
    step = determine_next_step("TX", {**base, "tx.stay_away_places": ["applicant"]})
    assert step["step"] == "tx.stay_away_distance_yards"


def test_tx_reaches_done_when_fully_answered() -> None:
    answers = {
        **_TX_THROUGH_TIER2,
        "tx.terms": ["no_family_violence", "prohibit_firearm"],
        "tx.exclusive_residence": False,
        "tx.ex_parte": True,
        "tx.phone_transfer": False,
        "tx.confidential": True,
    }
    step = determine_next_step("TX", answers)
    assert step["step"] == "done"


_PA_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "respondent.height": "6'0", "respondent.weight": "180", "respondent.eye_color": "Brown",
    "respondent.hair_color": "Black", "respondent.distinguishing_marks": "None",
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
    "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
}


def test_pa_asks_relief_after_tier2() -> None:
    step = determine_next_step("PA", _PA_THROUGH_TIER2)
    assert step["step"] == "pa.relief"
    assert "relinquish_firearms" in step["schema"]["items"]["enum"]


def test_pa_evict_follow_up() -> None:
    answers = {**_PA_THROUGH_TIER2, "pa.relief": ["evict"]}
    step = determine_next_step("PA", answers)
    assert step["step"] == "pa.evict_residence"


def test_pa_reaches_done_when_fully_answered() -> None:
    answers = {**_PA_THROUGH_TIER2, "pa.relief": ["restrain_abuse", "no_contact"]}
    step = determine_next_step("PA", answers)
    assert step["step"] == "done"


_NY_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.interpreter_language": "English",
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
    "respondent.is_law_enforcement": False,
    "respondent.prior_criminal_history": False,
}


def test_ny_asks_county_then_relief() -> None:
    step = determine_next_step("NY", _NY_THROUGH_TIER2)
    assert step["step"] == "ny.county"
    step = determine_next_step("NY", {**_NY_THROUGH_TIER2, "ny.county": "Kings"})
    assert step["step"] == "ny.relief"
    assert "surrender_firearms" in step["schema"]["items"]["enum"]


def test_ny_reaches_done_when_fully_answered() -> None:
    answers = {**_NY_THROUGH_TIER2, "ny.county": "Kings", "ny.relief": ["stay_away", "no_contact"]}
    step = determine_next_step("NY", answers)
    assert step["step"] == "done"


_MA_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.interpreter_language": "English",
    "respondent.height": "6'0", "respondent.weight": "180", "respondent.eye_color": "Brown",
    "respondent.hair_color": "Black", "respondent.distinguishing_marks": "None",
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
    "respondent.vehicle_make_model": "Sedan", "respondent.vehicle_color": "Blue",
    "respondent.vehicle_plate": "ABC123",
    "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
}


def test_ma_asks_abuse_then_relief() -> None:
    step = determine_next_step("MA", _MA_THROUGH_TIER2)
    assert step["step"] == "ma.abuse_types"
    answered = {**_MA_THROUGH_TIER2, "ma.abuse_types": ["physical_harm"]}
    step = determine_next_step("MA", answered)
    assert step["step"] == "ma.relief"
    assert "address_off_home" in step["schema"]["items"]["enum"]


def test_ma_compensation_follow_up() -> None:
    answers = {**_MA_THROUGH_TIER2, "ma.abuse_types": ["physical_harm"],
               "ma.relief": ["compensation"]}
    step = determine_next_step("MA", answers)
    assert step["step"] == "ma.compensation"


def test_ma_reaches_done_when_fully_answered() -> None:
    answers = {**_MA_THROUGH_TIER2, "ma.abuse_types": ["physical_harm"],
               "ma.relief": ["stop_abusing", "no_contact", "address_off_home"]}
    step = determine_next_step("MA", answers)
    assert step["step"] == "done"


_MD_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "petitioner.interpreter_language": "English",
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
    "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
}


def test_md_asks_abuse_then_relief() -> None:
    step = determine_next_step("MD", _MD_THROUGH_TIER2)
    assert step["step"] == "md.abuse_acts"
    answered = {**_MD_THROUGH_TIER2, "md.abuse_acts": ["punching"]}
    step = determine_next_step("MD", answered)
    assert step["step"] == "md.relief"
    assert "leave_home" in step["schema"]["items"]["enum"]


def test_md_leave_home_follow_up() -> None:
    answers = {**_MD_THROUGH_TIER2, "md.abuse_acts": ["punching"], "md.relief": ["leave_home"]}
    step = determine_next_step("MD", answers)
    assert step["step"] == "md.home_address"


def test_md_reaches_done_when_fully_answered() -> None:
    answers = {**_MD_THROUGH_TIER2, "md.abuse_acts": ["punching"],
               "md.relief": ["no_abuse", "no_contact"]}
    step = determine_next_step("MD", answers)
    assert step["step"] == "done"


_HI_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
}


def test_hi_asks_abuse_then_harm_then_relief() -> None:
    step = determine_next_step("HI", _HI_THROUGH_TIER2)
    assert step["step"] == "hi.abuse_acts"
    a = {**_HI_THROUGH_TIER2, "hi.abuse_acts": ["choke"]}
    step = determine_next_step("HI", a)
    assert step["step"] == "hi.harm_types"
    a = {**a, "hi.harm_types": ["physical_harm"]}
    step = determine_next_step("HI", a)
    assert step["step"] == "hi.relief"
    assert "dv_intervention" in step["schema"]["items"]["enum"]


def test_hi_abuse_other_follow_up() -> None:
    answers = {**_HI_THROUGH_TIER2, "hi.abuse_acts": ["other"]}
    step = determine_next_step("HI", answers)
    assert step["step"] == "hi.abuse_other"


def test_hi_reaches_done_when_fully_answered() -> None:
    answers = {**_HI_THROUGH_TIER2, "hi.abuse_acts": ["choke"], "hi.harm_types": ["physical_harm"],
               "hi.relief": ["no_contact", "vacate"], "hi.duration": "1 year"}
    step = determine_next_step("HI", answers)
    assert step["step"] == "done"


_GA_THROUGH_TIER2 = {
    **_TIER1_COMPLETE,
    "respondent.height": "6'0", "respondent.weight": "180", "respondent.eye_color": "Brown",
    "respondent.hair_color": "Black", "respondent.distinguishing_marks": "None",
    "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
    "respondent.vehicle_make_model": "Sedan", "respondent.vehicle_color": "Blue",
    "respondent.vehicle_plate": "ABC123",
    "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
    "ga.county": "Fulton",
}


def test_ga_asks_county_then_relief() -> None:
    base = {k: v for k, v in _GA_THROUGH_TIER2.items() if k != "ga.county"}
    step = determine_next_step("GA", base)
    assert step["step"] == "ga.county"
    step = determine_next_step("GA", _GA_THROUGH_TIER2)
    assert step["step"] == "ga.relief"
    assert "address_confidential" in step["schema"]["items"]["enum"]


def test_ga_vacate_follow_up() -> None:
    answers = {**_GA_THROUGH_TIER2, "ga.relief": ["vacate"]}
    step = determine_next_step("GA", answers)
    assert step["step"] == "ga.residence_address"


def test_ga_reaches_done_when_fully_answered() -> None:
    answers = {**_GA_THROUGH_TIER2, "ga.relief": ["no_abuse", "no_contact", "address_confidential"]}
    step = determine_next_step("GA", answers)
    assert step["step"] == "done"


def test_nc_asks_county_then_relief() -> None:
    base = {**_TIER1_COMPLETE, "petitioner.interpreter_language": "English",
            "respondent.employer_name": "Corp", "respondent.employer_address": "Addr"}
    step = determine_next_step("NC", base)
    assert step["step"] == "nc.county"
    step = determine_next_step("NC", {**base, "nc.county": "Wake"})
    assert step["step"] == "nc.relief"
    assert "surrender_firearms" in step["schema"]["items"]["enum"]


def test_nc_stay_away_follow_up() -> None:
    answers = {**_TIER1_COMPLETE, "petitioner.interpreter_language": "English",
               "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
               "nc.county": "Wake", "nc.relief": ["stay_away"]}
    step = determine_next_step("NC", answers)
    assert step["step"] == "nc.stay_away_places"


def test_nc_reaches_done_when_fully_answered() -> None:
    answers = {**_TIER1_COMPLETE, "petitioner.interpreter_language": "English",
               "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
               "nc.county": "Wake", "nc.relief": ["no_abuse", "no_contact"]}
    step = determine_next_step("NC", answers)
    assert step["step"] == "done"


def test_va_is_accepted_and_asks_conditions() -> None:
    # VA walks Tier-1 + physical/employer/vehicle + the VA respondent-description
    # questions, then asks which conditions to request.
    answers = {
        **_TIER1_COMPLETE,
        "respondent.height": "6'0", "respondent.weight": "180", "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black", "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
        "respondent.vehicle_make_model": "Sedan", "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
        "va.preliminary_order": True,
    }
    step = determine_next_step("VA", answers)
    assert step["step"] == "va.conditions"
    assert "companion_animal" in step["schema"]["items"]["enum"]


def test_va_companion_animal_follow_up() -> None:
    answers = {
        **_TIER1_COMPLETE,
        "respondent.height": "6'0", "respondent.weight": "180", "respondent.eye_color": "Brown",
        "respondent.hair_color": "Black", "respondent.distinguishing_marks": "None",
        "respondent.employer_name": "Corp", "respondent.employer_address": "Addr",
        "respondent.vehicle_make_model": "Sedan", "respondent.vehicle_color": "Blue",
        "respondent.vehicle_plate": "ABC123",
        "respondent.dob": "1988-02-02", "respondent.race": "n/a", "respondent.gender": "male",
        "va.preliminary_order": True, "va.conditions": ["companion_animal"],
    }
    step = determine_next_step("VA", answers)
    assert step["step"] == "va.companion_animal"


def test_wa_reaches_done_when_fully_answered() -> None:
    answers = {
        **_WA_THROUGH_TIER2,
        "wa.restraints": ["no_harm", "no_contact"],
        "wa.temporary_order": True,
        "wa.weapons_surrender": False,
        "wa.order_length": "one_year",
        "wa.firearms_restoration_notice": "notify",
        "wa.past_incidents": "None",
        "wa.evidence_types": ["pictures"],
    }
    step = determine_next_step("WA", answers)
    assert step["step"] == "done"


def test_ca_dynamic_relationship_options() -> None:
    mock_partial = {
        "petitioner.legal_name": "Jane Doe",
        "petitioner.dob": "1990-01-01",
        "petitioner.safe_mailing_address": "Addr",
        "petitioner.safe_phone": "123",
        "petitioner.safe_email": "jane@safe.com",
        "respondent.legal_name": "John Doe",
        "respondent.last_known_address": "Addr",
    }
    step = determine_next_step("CA", mock_partial)
    assert step["step"] == "relationship.type"
    assert "enum" in step["schema"]
    assert "engaged" in step["schema"]["enum"]


def test_ca_minor_filing_path_trigger() -> None:
    mock_tier1_done_minor = {
        "petitioner.legal_name": "Jane Doe",
        "petitioner.dob": "2010-01-01",
        "petitioner.safe_mailing_address": "Addr",
        "petitioner.safe_phone": "123",
        "petitioner.safe_email": "jane@safe.com",
        "respondent.legal_name": "John Doe",
        "respondent.last_known_address": "Addr",
        "relationship.type": "Dating",
        "relationship.live_together_now": False,
        "relationship.lived_together_past": True,
        "relationship.children_in_common": False,
        "incidents[].date": "2026-05-01",
        "incidents[].location": "Los Angeles, CA",
        "incidents[].narrative": "Text",
        "incidents[].witnesses_present": "None",
        "incidents[].police_called": False,
        "incidents[].weapon_involved": False,
        "incidents[].injury": "None",
        "incidents[].pattern_frequency": "Once",
        "protected_persons.children[]": "None",
        "firearm.respondent_has_access": False,
        "prior_orders.exists": False,
    }
    step = determine_next_step("CA", mock_tier1_done_minor)
    assert step["step"] == "petitioner.minor_filing_path"
