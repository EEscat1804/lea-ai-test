"""Deterministic safety gate over model-proposed memory operations.

lea-be-core runs the extraction prompt (`extraction.py`) through its model
and sends the proposed ops here before persisting anything. The gate is pure
rules — no model call — so what can enter a survivor's durable record is
auditable line by line. The proposing model is UNTRUSTED: ops may be
hallucinated or steered by prompt injection in the transcript, so every
check here assumes an adversarial proposer.

What the gate deliberately ALLOWS: plain statements of abuse history
("He strangled her in May 2025", "She has a DVRO hearing on July 3").
Those facts are the entire point of the feature — remembering them is what
spares the user from re-telling the story, and they anchor the legal help.

What it refuses, and why:
- facts the user never explicitly stated (`not_user_stated`) — inferred
  memories (pregnancy, immigration status, "planning to leave") are
  re-traumatizing when wrong and dangerous when discovered;
- the user's own self-harm statements (`self_harm_content`) — those are a
  crisis to respond to in the moment, never a "fact" to recall at them
  later;
- credentials and government identifiers (`credential_like`) — a memory
  list must never become a second breach surface for SSNs or passwords;
- anything carrying internal architecture terms (`internal_term`) — memory
  content is rendered into prompts, and the persona leak-guard applies to
  it the same as to persona text;
- updates that move a memory OUT of a restricted category
  (`restricted_demotion`) — one mis-categorized update op would otherwise
  launder a safety plan into renderable chat context, the exact
  physical-safety failure restricted sensitivity exists to prevent.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from memory.contracts import (
    MAX_ACTIVE_MEMORIES,
    MAX_CONTENT_CHARS,
    MAX_OPS_PER_REVIEW,
    MEMORY_CATEGORIES,
    RESTRICTED_CATEGORIES,
    SENSITIVITIES,
    SENSITIVITY_RESTRICTED,
    SENSITIVITY_STANDARD,
    VALID_OPS,
    AcceptedOp,
    MemoryRecord,
    RejectedOp,
    normalize_content,
)
from persona.system_prompts import FORBIDDEN_INTERNAL_TERMS

# Government identifiers, payment/account numbers, and stated secrets. Word
# patterns (not just formats) so "my password is ..." is caught even when the
# secret itself has no recognizable shape, plus short numeric secrets near
# their trigger nouns ("gate code is 4821").
CREDENTIAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b(?:\d[ -]?){13,19}\b",  # card / account number runs
        r"\bpassword\b",
        r"\bpasscode\b",
        r"\bpin\s+(?:is|code|number)\b",
        r"\brouting number\b",
        r"\bsocial security\b",
        # short numeric secrets stated next to their lock/code noun
        r"\b(?:code|keypad|combination|combo|safe|lock(?:er)?)\b[^.!?]{0,20}\b\d{3,8}\b",
    )
)

# The USER's own self-harm disclosures. Deliberately scoped to self-directed
# harm — "he threatened to kill her" is abuse history and must pass; "she
# wants to kill herself" is a crisis moment and must not become a durable
# memory. Inflections (killed/kills, hurts/harming/cutting) and
# apostrophe-less contractions (doesnt) are covered: this gate is the only
# guarantee, so a false negative here is a safety failure.
SELF_HARM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"suicid",
        # Reflexive may sit a few words after the verb ("kill her and
        # himself"). Also catches an abuser's own self-harm threats — a known
        # coercion tactic — which is an accepted false positive: default to safe.
        r"kill(?:s|ed|ing)?\b[^.!?]{0,60}\b(?:myself|herself|himself|themselves)\b",
        r"(?:hurt(?:s|ing)?|harm(?:s|ed|ing)?|cut(?:s|ting)?)\b[^.!?]{0,30}"
        r"\b(?:myself|herself|himself|themselves)\b",
        r"self[- ]harm",
        # Self-directed "end ... life" needs intent by the subject themselves:
        # "She wants to end her life" is a crisis disclosure; "He threatened
        # to end her life" is abuse history and must pass. Intent verbs +
        # pronoun-owned life captures the former without the latter.
        r"(?:wants?|wanted|tr(?:y|ies|ied|ying)|plan(?:s|ned|ning)?|think(?:s|ing)?"
        r"(?:\s+(?:of|about))?)\s+(?:to\s+)?end(?:ing)?\b[^.!?]{0,20}"
        r"\b(?:my|her|his|their)\s+(?:own\s+)?life",
        r"end(?:s|ed|ing)?\b[^.!?]{0,20}\b(?:my|her|his|their)\s+own\s+life",
        # "want to live" is self-harm context — but not "want to live WITH
        # him / in that house", which is ordinary separation talk.
        r"want(?:s|ed)? to die\b",
        # The curly apostrophe is intentional: user text arrives with both forms.
        r"(?:does|do|did)\s*(?:not|n[’']?t)\s+want\s+to\s+"  # noqa: RUF001
        r"(?:live|be alive)(?!\s+(?:with|in|at|near|around|together|there|here|like)\b)",
    )
)

_OP_FIELDS: frozenset[str] = frozenset(
    {"op", "id", "category", "content", "sensitivity", "user_stated"}
)


def review_proposed_ops(
    proposed: list[Any], existing: list[MemoryRecord]
) -> tuple[list[AcceptedOp], list[RejectedOp]]:
    """Screen every proposed op; return (accepted, rejected).

    Accepted ops are normalized (whitelisted keys, trimmed content, pinned
    sensitivity) so lea-be-core can apply them verbatim. Rejected ops carry a
    machine-readable reason and echo only whitelisted fields — never the raw
    payload — so a hostile or malformed op can't smuggle content back out.

    Per-batch accounting is exact: a deleted id leaves the live set (so a
    second delete or a follow-up update of it is rejected, and the active
    count can't be driven down by repeating deletes to smuggle adds past
    MAX_ACTIVE_MEMORIES).
    """
    accepted: list[AcceptedOp] = []
    rejected: list[RejectedOp] = []

    by_id = {record["id"]: record for record in existing}
    live_ids = set(by_id)
    seen_contents = {normalize_content(record["content"]) for record in existing}
    active_count = len(existing)

    for index, raw in enumerate(proposed):
        op = _project(raw)
        if index >= MAX_OPS_PER_REVIEW:
            rejected.append(RejectedOp(op=op, reason="too_many_ops"))
            continue

        reason = _screen(op, live_ids, by_id)
        if reason is not None:
            rejected.append(RejectedOp(op=op, reason=reason))
            continue

        kind = op["op"]
        if kind == "delete":
            target = str(op["id"])
            accepted.append(AcceptedOp(op="delete", id=target))
            live_ids.discard(target)
            active_count -= 1
            continue

        content = str(op["content"]).strip()
        normalized = normalize_content(content)
        if kind == "add":
            if normalized in seen_contents:
                rejected.append(RejectedOp(op=op, reason="duplicate"))
                continue
            if active_count >= MAX_ACTIVE_MEMORIES:
                rejected.append(RejectedOp(op=op, reason="memory_cap_reached"))
                continue
            active_count += 1
        seen_contents.add(normalized)

        sensitivity = _pin_sensitivity(op)
        # A restricted record stays restricted across an update — the proposer
        # can correct content, never lower the protection level.
        if kind == "update" and by_id[str(op["id"])]["sensitivity"] == SENSITIVITY_RESTRICTED:
            sensitivity = SENSITIVITY_RESTRICTED

        normalized_op = AcceptedOp(
            op=kind,
            category=str(op["category"]),
            content=content,
            sensitivity=sensitivity,
        )
        if kind == "update":
            normalized_op["id"] = str(op["id"])
        accepted.append(normalized_op)

    return accepted, rejected


def _project(raw: Any) -> dict[str, Any]:
    """Echo only whitelisted fields — rejected ops travel back to lea-be-core."""
    if not isinstance(raw, dict):
        return {}
    return {k: raw[k] for k in _OP_FIELDS if k in raw}


def _screen(op: dict[str, Any], live_ids: set[str], by_id: dict[str, MemoryRecord]) -> str | None:
    """Return a rejection reason, or None when the op is safe to normalize."""
    kind = op.get("op")
    if not (isinstance(kind, str) and kind in VALID_OPS):
        return "invalid_op"

    # Only facts the user explicitly stated may enter the record — for deletes
    # too, so "forget" always traces back to something the user said.
    if op.get("user_stated") is not True:
        return "not_user_stated"

    if kind in ("update", "delete"):
        target = op.get("id")
        if not (isinstance(target, str) and target in live_ids):
            return "unknown_id"
    if kind == "delete":
        return None

    category = op.get("category")
    if not (isinstance(category, str) and category in MEMORY_CATEGORIES):
        return "unknown_category"

    if kind == "update":
        # A restricted memory may never be recategorized into a renderable
        # category by the untrusted proposer — one mis-categorized update
        # would put a safety plan into chat context on the next message.
        existing = by_id[str(op["id"])]
        if existing["category"] in RESTRICTED_CATEGORIES and category != existing["category"]:
            return "restricted_demotion"

    content = op.get("content")
    if not (isinstance(content, str) and content.strip()):
        return "content_empty"
    content = content.strip()
    if len(content) > MAX_CONTENT_CHARS:
        return "content_too_long"

    # NFKC fold before matching so fullwidth/homoglyph variants from a hostile
    # proposer (a fullwidth "password") can't slip past the screens.
    folded = unicodedata.normalize("NFKC", content)
    lowered = folded.lower()
    for term in FORBIDDEN_INTERNAL_TERMS:
        # Word-boundary, not substring: "DeKalb County" must not trip "dek".
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            return "internal_term"
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.search(folded):
            return "credential_like"
    for pattern in SELF_HARM_PATTERNS:
        if pattern.search(folded):
            return "self_harm_content"
    return None


def _pin_sensitivity(op: dict[str, Any]) -> str:
    """Restricted categories stay restricted regardless of what was proposed."""
    if op.get("category") in RESTRICTED_CATEGORIES:
        return SENSITIVITY_RESTRICTED
    sensitivity = op.get("sensitivity")
    if isinstance(sensitivity, str) and sensitivity in SENSITIVITIES:
        return sensitivity
    return SENSITIVITY_STANDARD
