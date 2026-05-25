import pytest

from src.vault.intake import SUPPORTED_JURISDICTIONS, _stub_next_step


def test_first_step_asks_for_petitioner_name() -> None:
    step = _stub_next_step("CA", {})
    assert step["step"] == "petitioner_name"


def test_step_after_name_asks_for_incident() -> None:
    step = _stub_next_step("CA", {"petitioner_name": "Jane Doe"})
    assert step["step"] == "incident_summary"


def test_finishes_when_all_required_answered() -> None:
    answers = {"petitioner_name": "Jane Doe", "incident_summary": "..."}
    step = _stub_next_step("CA", answers)
    assert step["step"] == "done"
    assert step["jurisdiction"] == "CA"


@pytest.mark.parametrize("jurisdiction", sorted(SUPPORTED_JURISDICTIONS))
def test_first_step_consistent_across_jurisdictions(jurisdiction: str) -> None:
    """Until per-jurisdiction graphs land, the stub flow must be uniform."""
    step = _stub_next_step(jurisdiction, {})
    assert step["step"] == "petitioner_name"
