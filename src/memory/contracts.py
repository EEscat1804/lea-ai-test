"""Memory contracts shared across the `/v1/memory/*` endpoints.

A "memory" is ONE durable, user-stated fact that lets Lea pick up where a
past conversation left off, so a survivor never has to re-tell their story —
re-explaining trauma session after session is itself a harm.

lea-ai never stores any of this. lea-be-core sends the user's full memory
list with each request and persists whatever the review gate accepts — the
same state-in/state-out pattern as guardrails `SessionState`. Records are
whitelist-deserialized at the boundary: unknown keys are dropped, malformed
records are skipped, and nothing here ever widens what lea-ai is trusted
with (no user identifiers beyond the opaque per-memory id).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

# Category names are part of the cross-service contract with lea-be-core's
# memory store and the mobile memory screen — additions are fine, renames are
# a breaking change.
MEMORY_CATEGORIES: frozenset[str] = frozenset(
    {
        "situation",  # the relationship / abuse situation itself
        "people",  # people who matter to the case: children, support network
        "legal",  # case facts: jurisdiction, case numbers, hearings, orders
        "safety",  # safety planning / escape logistics — ALWAYS restricted
        "wellbeing",  # health or therapy facts the user chose to share
        "preferences",  # how they want Lea to talk to them (name, language)
    }
)

# Categories whose discovery is highest-lethality if blurted or shoulder-surfed
# (safety plans, escape timing). These are forced to "restricted" sensitivity
# and are NEVER rendered into chat context — they exist only for the
# authenticated memory screen in the app.
RESTRICTED_CATEGORIES: frozenset[str] = frozenset({"safety"})

SENSITIVITY_STANDARD = "standard"
SENSITIVITY_RESTRICTED = "restricted"
SENSITIVITIES: frozenset[str] = frozenset({SENSITIVITY_STANDARD, SENSITIVITY_RESTRICTED})

# One fact, one plain sentence. The cap is a data-minimization control as much
# as a prompt-budget one: a memory list is a dossier of the user's case, and
# every stored character raises discovery/breach exposure.
MAX_CONTENT_CHARS = 300
MAX_ACTIVE_MEMORIES = 100
MAX_OPS_PER_REVIEW = 25

VALID_OPS: frozenset[str] = frozenset({"add", "update", "delete"})


class MemoryRecord(TypedDict):
    """An existing memory as persisted by lea-be-core."""

    id: str  # opaque backend UUID — lea-ai never mints or interprets these
    category: str
    content: str
    sensitivity: str
    source: str  # "chat" (extracted) | "user" (typed in the memory screen)
    noted_on: str  # ISO date the fact was recorded — provenance for recall


class AcceptedOp(TypedDict, total=False):
    """A normalized, safety-screened op lea-be-core may apply to its store."""

    op: str  # add | update | delete
    id: str  # present for update/delete
    category: str
    content: str
    sensitivity: str


class RejectedOp(TypedDict):
    """A proposed op the review gate refused, with a machine-readable reason."""

    op: dict[str, Any]
    reason: str


_RECORD_FIELDS: frozenset[str] = frozenset(
    {"id", "category", "content", "sensitivity", "source", "noted_on"}
)

_WHITESPACE_RE = re.compile(r"\s+")


def parse_memories(payload: Any) -> list[MemoryRecord]:
    """Whitelist-deserialize the caller's memory list.

    Unknown keys are dropped and malformed records are skipped rather than
    failing the request — a single bad row must not take down recall for the
    whole session. Restricted-category records are re-pinned to restricted
    sensitivity no matter what was stored.
    """
    if not isinstance(payload, list):
        return []
    records: list[MemoryRecord] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        record = _parse_record(raw)
        if record is not None:
            records.append(record)
    return records


def _parse_record(raw: dict[str, Any]) -> MemoryRecord | None:
    rid = raw.get("id")
    category = raw.get("category")
    content = raw.get("content")
    if not (isinstance(rid, str) and rid):
        return None
    if not (isinstance(category, str) and category in MEMORY_CATEGORIES):
        return None
    if not (isinstance(content, str) and content.strip()):
        return None

    sensitivity = raw.get("sensitivity")
    if category in RESTRICTED_CATEGORIES:
        sensitivity = SENSITIVITY_RESTRICTED
    elif not (isinstance(sensitivity, str) and sensitivity in SENSITIVITIES):
        sensitivity = SENSITIVITY_STANDARD

    source = raw.get("source")
    if not (isinstance(source, str) and source):
        source = "chat"
    noted_on = raw.get("noted_on")
    if not isinstance(noted_on, str):
        noted_on = ""

    return MemoryRecord(
        id=rid,
        category=category,
        content=content.strip()[:MAX_CONTENT_CHARS],
        sensitivity=sensitivity,
        source=source,
        noted_on=noted_on,
    )


def normalize_content(content: str) -> str:
    """Canonical form for duplicate detection: case- and spacing-insensitive."""
    lowered = _WHITESPACE_RE.sub(" ", content.strip().lower())
    return lowered.rstrip(".")
