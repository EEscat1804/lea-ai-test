"""Vault petition assembly.

Takes a completed intake (jurisdiction + answers) and produces the
court-ready DVRO petition mapping for that jurisdiction. Each jurisdiction
has its own form(s) (CA: DV-100/DV-110, etc.); the per-jurisdiction mappings
live in `vault.forms.*`.

CA (DV-100) is the reference implementation. Other jurisdictions land the
same way: add a `vault.forms.<state>` module and dispatch to it here.

This module returns a structured field map, not a PDF — lea-be-core renders
it onto the official fillable form. See `vault.forms.ca` for the
contract and the marker discipline (`[FACT NEEDED]`, review flags).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lib.responses import json_response, problem_response
from vault.forms import ca, ga, hi, ma, md, nc, ny, pa, tx, va, wa

# jurisdiction -> assembler. Add a state here when its forms package lands.
_ASSEMBLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "CA": ca.assemble,
    "WA": wa.assemble,
    "VA": va.assemble,
    "TX": tx.assemble,
    "PA": pa.assemble,
    "NC": nc.assemble,
    "NY": ny.assemble,
    "MA": ma.assemble,
    "MD": md.assemble,
    "HI": hi.assemble,
    "GA": ga.assemble,
}


def supported_jurisdictions() -> frozenset[str]:
    """Jurisdictions with a petition assembler wired up today."""
    return frozenset(_ASSEMBLERS)


def assemble_petition(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Return the assembled petition mapping for a jurisdiction.

    Called once intake reports `done`. Raises NotImplementedError for a
    jurisdiction whose form module has not landed yet, so a missing state is a
    loud failure rather than a silently empty form.
    """
    assembler = _ASSEMBLERS.get(jurisdiction)
    if assembler is None:
        raise NotImplementedError(
            f"petition assembly not yet implemented for jurisdiction {jurisdiction!r}; "
            f"supported: {sorted(_ASSEMBLERS)}"
        )
    return assembler(answers)


async def handle_petition_request(body: dict[str, Any], env: Any) -> Any:
    """`POST /v1/vault/petition` — assemble the petition mapping for a finished intake.

    Body: `{ jurisdiction, answers }`. The returned `gaps` list tells lea-be-core
    whether the form is filing-ready; an empty `gaps` means every required field
    is present.
    """
    jurisdiction = body.get("jurisdiction")
    answers = body.get("answers", {})

    if jurisdiction not in supported_jurisdictions():
        return problem_response(
            400,
            "unsupported_jurisdiction",
            f"petition assembly supports {sorted(supported_jurisdictions())}",
        )
    if not isinstance(answers, dict):
        return problem_response(400, "bad_request", "answers must be an object")

    return json_response(assemble_petition(jurisdiction, answers))
