"""Memory-extraction prompt for lea-be-core's model call.

lea-ai makes no model calls. lea-be-core fetches this prompt (with the
user's current memories rendered in, so the model can propose updates and
deletes by id), runs it through its model over the session transcript in
JSON mode, then sends the proposed ops to `/v1/memory/review` before
persisting anything. Keeping the prompt here makes every wording change a
code review with regression tests — exactly like the persona.
"""

from __future__ import annotations

from typing import Any

from memory.contracts import (
    MEMORY_CATEGORIES,
    SENSITIVITIES,
    SENSITIVITY_RESTRICTED,
    MemoryRecord,
)

# Schema for the model's JSON output (Gemini `responseSchema` compatible).
# `user_stated` is required on every op so the no-inference rule is enforced
# structurally — review rejects any op where it is not exactly true.
EXTRACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["add", "update", "delete"]},
                    "id": {"type": "string"},
                    "category": {"type": "string", "enum": sorted(MEMORY_CATEGORIES)},
                    "content": {"type": "string"},
                    "sensitivity": {"type": "string", "enum": sorted(SENSITIVITIES)},
                    "user_stated": {"type": "boolean"},
                },
                "required": ["op", "category", "content", "user_stated"],
            },
        }
    },
    "required": ["ops"],
}

_EXTRACTION_INSTRUCTION = """\
You are the memory-extraction step for Lea, a legal companion for survivors
of domestic, sexual, and tech-facilitated violence. You are NOT chatting
with the user. Read the conversation transcript and decide which durable
facts are worth remembering for future conversations, so the user never has
to re-explain their situation. Re-telling a trauma story is itself harmful;
a good memory spares them that. Output JSON only, matching the schema you
were given. Most conversations add nothing: when nothing qualifies, return
{"ops": []}.

What qualifies as a memory:
- A durable fact the USER EXPLICITLY STATED about their own situation that
  will still matter next week: who is involved, what happened and when,
  case and court facts, what they want to be called, language preference.
- One fact per op, written as one short, neutral, plain-language sentence
  in the third person (e.g. "Her ex-husband Mark moved out in March 2026").
- Record what matters legally and practically, not graphic narrative
  detail. "He has strangled her before, most recently in May 2026" is a
  memory; a blow-by-blow account is not.

Hard rules:
- NEVER infer. If the user did not say it in plain words, it does not
  exist. Do not deduce pregnancy, immigration status, plans to leave,
  mental-health conditions, or anything else from hints. Set
  "user_stated" true only for facts the user themselves stated outright.
- NEVER store the user's own statements about self-harm or suicide as
  memories. Crisis support handles those in the moment; they are not
  facts to recall at the user later.
- NEVER store passwords, PINs, social security numbers, or account
  numbers, even if the user asks you to remember them.
- Skip feelings of the moment, greetings, hypotheticals, questions, and
  anything Lea said. Only the user's own statements count.
- Use category "safety" for safety planning and escape logistics (where
  they would go, when, with what help). Safety memories are never shown
  back in conversation, only in the user's own memory settings.

Categories:
- situation: the relationship and abuse situation itself
- people: people relevant to their case (children, family, support)
- legal: jurisdiction, case numbers, hearing dates, protection orders
- safety: safety planning and escape logistics (always restricted)
- wellbeing: health or therapy facts they chose to share
- preferences: how they want Lea to talk with them

Updating and deleting:
- The user's current memories are listed below with ids. When the
  transcript shows a fact changed or was resolved ("the hearing already
  happened", "we're divorced now"), propose {"op": "update", "id": ...}
  with the corrected sentence, or {"op": "delete", "id": ...} when it no
  longer applies. When the user asks Lea to forget something, propose the
  matching delete.
- Do not re-add a fact that is already in the list.
"""


def build_extraction_prompt(memories: list[MemoryRecord]) -> str:
    """The full system prompt for the extraction model call."""
    return _EXTRACTION_INSTRUCTION + "\n" + _render_current_memories(memories) + "\n"


def _render_current_memories(memories: list[MemoryRecord]) -> str:
    """List current memories with ids so the model can propose update/delete.

    Restricted memories (safety plans, escape logistics) are listed by id and
    category ONLY — their content never reaches the extraction model. This
    prompt leaves lea-be-core for a third-party model provider; a survivor's
    escape plan must not transit there just to enable dedup. The model can
    still propose a delete by id when the user asks to forget.
    """
    if not memories:
        return "Current memories: none yet."
    lines = ["Current memories:"]
    for record in memories:
        if record["sensitivity"] == SENSITIVITY_RESTRICTED:
            lines.append(
                f"- id={record['id']} [{record['category']}] (content withheld - this is a "
                "protected safety memory; propose a delete by id if the user asks to forget it)"
            )
        else:
            lines.append(f"- id={record['id']} [{record['category']}] {record['content']}")
    return "\n".join(lines)
