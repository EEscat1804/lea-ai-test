"""Vault petition assembly.

Takes a completed intake (jurisdiction + answers) and produces the
court-ready DVRO petition for that jurisdiction. Each jurisdiction has
its own forms (CA: DV-100/DV-110, etc.) — those templates live under
`templates/<jurisdiction>/` (to be added by the team).

This module is intentionally empty in v0.1.0 — Pranav + Aaron will land
the first jurisdiction (CA) as the reference implementation, then
broaden to the remaining 46.
"""

from __future__ import annotations

from typing import Any


def assemble_petition(jurisdiction: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Return the assembled petition for a jurisdiction.

    Not wired into routes yet; called once intake is complete.
    """
    raise NotImplementedError("petition assembly lands with the first jurisdiction (CA)")
