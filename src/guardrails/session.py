"""Per-conversation guardrails state.

`SessionState` carries everything lea-ai knows about a user within a session.
lea-be-core owns persistence — every `/v1/lea/process` response returns the
updated session and the caller writes it back to its store.

Authored by Aaron Wang; restructured from `evaluator.py` v2 into this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    """All Lea knows about a user this session.

    Vault data (state, county, children, married, etc.) anchors the depth
    of jurisdiction-specific responses. Safety flags carry across turns so
    a Tier-3 event can't be unintentionally downgraded later.
    """

    # Vault context
    user_state: str = ""
    user_county: str = ""
    has_children: bool = False
    num_children: int = 0
    is_married: bool = False
    firearm_access: bool = False
    strangulation_disclosed: bool = False
    immigration_risk: bool = False

    # Safety tracking — once True, persists for the session
    tier3_fired_this_session: bool = False
    tier2_fired_this_session: bool = False
    resource_surfaced_this_session: bool = False

    # Mode controls (G-11, G-12, G-15)
    trusted_friend_mode: bool = False
    expert_mode: bool = False
    language_coach_mode: bool = False

    # G-14 risk-scoring inputs accumulated across turns
    risk_factors: list[str] = field(default_factory=list)

    # G-20: explicit consent gate — Vault writes require this True
    data_storage_consent: bool = False

    # G-07: validation-before-education sequencer.
    # When non-None, holds the deferred education text from the prior turn.
    pending_education: str | None = None
