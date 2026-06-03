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
