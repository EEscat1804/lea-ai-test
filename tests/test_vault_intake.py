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
