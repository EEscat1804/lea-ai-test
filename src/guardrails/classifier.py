"""Guardrails HTTP surface.

Wraps `router.process_message` for the `/v1/guardrails/classify` and
`/v1/lea/process` endpoints. The router does the real work; this module
only handles request validation, SessionState (de)serialization, and the
RFC 7807 error contract.
"""

from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any

from guardrails.router import process_message
from guardrails.session import SessionState
from lib.responses import json_response, problem_response


def _build_session(payload: Any) -> SessionState:
    """Build a SessionState from an optional `session` dict in the request body."""
    if not isinstance(payload, dict):
        return SessionState()
    valid_keys = {f.name for f in fields(SessionState)}
    filtered = {k: v for k, v in payload.items() if k in valid_keys}
    return SessionState(**filtered)


def _serialize_session(session: SessionState) -> dict[str, Any]:
    return asdict(session)


async def classify_message(body: dict[str, Any], env: Any) -> Any:
    """`/v1/guardrails/classify` — classification-only view onto the router.

    Returns just `{tier, categories, classification, show_quick_exit}` without
    the user-facing response text — useful for callers that want pre-LLM
    filtering before they decide whether to invoke the model.
    """
    text = body.get("text")
    direction = body.get("direction", "input")
    if not isinstance(text, str) or not text:
        return problem_response(400, "bad_request", "text is required")
    if direction not in ("input", "output"):
        return problem_response(400, "bad_request", "direction must be input|output")

    session = _build_session(body.get("session"))
    result = process_message(text, session)

    classification = {0: "safe", 1: "guidance", 2: "elevated", 3: "crisis"}.get(
        result["tier"], "safe"
    )

    return json_response(
        {
            "classification": classification,
            "tier": result["tier"],
            "direction": direction,
            "categories": session.risk_factors,
            "show_quick_exit": result["show_quick_exit"],
        }
    )


async def process_message_endpoint(body: dict[str, Any], env: Any) -> Any:
    """`/v1/lea/process` — full router output including the user-facing response text."""
    text = body.get("text")
    if not isinstance(text, str) or not text:
        return problem_response(400, "bad_request", "text is required")

    session = _build_session(body.get("session"))
    result = process_message(text, session)

    return json_response(
        {
            "response": result["response"],
            "tier": result["tier"],
            "is_override": result["is_override"],
            "show_quick_exit": result["show_quick_exit"],
            "vault_write_requires_consent": result["vault_write_requires_consent"],
            "session": _serialize_session(result["session"]),
        }
    )
