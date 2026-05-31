"""Shared contracts for the guardrails feature-dispatch pipeline.

`FeatureResult` is the return type every `GuardrailFeature.match_and_execute`
implementation hands back to the router. Using a typed NamedTuple instead of a
bare tuple means the dispatch loop reads fields by name and a future field
can't silently fall through length-based branching.
"""

from __future__ import annotations

from typing import NamedTuple


class FeatureResult(NamedTuple):
    """A feature manager's match result.

    `text` + `tier` are the full contract. SECURITY NOTICE / ACTION NEEDED labels
    survive formatting because `apply_mode_constraints` only normalizes whitespace
    and never strips them — no per-result opt-in flag is needed.
    """

    text: str
    tier: int
