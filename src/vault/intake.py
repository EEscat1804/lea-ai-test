"""Vault intake state machine.

The Vault is LEA's structured DV-survivor petition flow. A user walks through
jurisdiction-specific questions (47 US jurisdictions per the DVRO Multi-State
Intake Question Flow) and the answers are assembled into a court-ready DVRO
petition by `src.vault.petition`.

Owners: Pranav, Aaron. This module owns the *state* of intake; lea-be-core
persists the encrypted answers and serves the resulting document.

Stateless contract:
- Request:  { session_id, jurisdiction, current_step?, answers: {...} }
- Response: { next_step | done, prompt?, schema?, validation_errors? }

The next-step decision is pure: given (jurisdiction, answers-so-far),
return the next question. State lives in lea-be-core's DB; lea-ai is a
function from state → next prompt.
"""

from __future__ import annotations

from typing import Any

from lib.responses import json_response, problem_response

SUPPORTED_JURISDICTIONS = {
    "CA", "NY", "TX", "FL", "IL",
}


async def handle_intake_step(body: dict[str, Any], env: Any) -> Any:
    session_id = body.get("session_id")
    jurisdiction = body.get("jurisdiction")
    answers = body.get("answers", {})

    if not isinstance(session_id, str) or not session_id:
        return problem_response(400, "bad_request", "session_id is required")
    if jurisdiction not in SUPPORTED_JURISDICTIONS:
        return problem_response(
            400,
            "unsupported_jurisdiction",
            f"jurisdiction must be one of {sorted(SUPPORTED_JURISDICTIONS)}",
        )
    if not isinstance(answers, dict):
        return problem_response(400, "bad_request", "answers must be an object")

    # TODO(pranav, aaron): replace with real per-jurisdiction question graph.
    next_step = _stub_next_step(jurisdiction, answers)
    return json_response(next_step)


def _stub_next_step(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Placeholder linear flow. Real impl will be per-jurisdiction graphs."""
    if "petitioner_name" not in answers:
        return {
            "step": "petitioner_name",
            "prompt": "What is your full legal name?",
            "schema": {"type": "string", "minLength": 1, "maxLength": 200},
        }
    if "incident_summary" not in answers:
        return {
            "step": "incident_summary",
            "prompt": "Briefly describe what happened. You can take your time.",
            "schema": {"type": "string", "minLength": 1, "maxLength": 5000},
        }
    return {"step": "done", "jurisdiction": jurisdiction}
