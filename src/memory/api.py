"""HTTP surface for `/v1/memory/*`.

Same shape as the guardrails surface: handlers take the parsed JSON body and
`env`, validate, delegate to pure functions, and answer in the shared
response contract. All three endpoints are POST — memory payloads are user
data and must never ride a query string into request logs.
"""

from __future__ import annotations

from typing import Any

from lib.responses import json_response, problem_response
from memory.contracts import parse_memories
from memory.extraction import EXTRACTION_RESPONSE_SCHEMA, build_extraction_prompt
from memory.recall import compose_memory_context
from memory.review import review_proposed_ops


async def handle_extraction_prompt(body: dict[str, Any], env: Any) -> Any:
    """`/v1/memory/extraction-prompt` — prompt + schema for the extraction call."""
    memories = parse_memories(body.get("memories", []))
    return json_response(
        {
            "prompt": build_extraction_prompt(memories),
            "response_schema": EXTRACTION_RESPONSE_SCHEMA,
        }
    )


async def handle_review(body: dict[str, Any], env: Any) -> Any:
    """`/v1/memory/review` — deterministic safety gate over proposed ops."""
    proposed = body.get("proposed")
    if not isinstance(proposed, list):
        return problem_response(400, "bad_request", "proposed must be a list of memory ops")
    memories = parse_memories(body.get("memories", []))
    accepted, rejected = review_proposed_ops(proposed, memories)
    return json_response({"accepted": accepted, "rejected": rejected})


async def handle_context(body: dict[str, Any], env: Any) -> Any:
    """`/v1/memory/context` — the rendered system-prompt memory block."""
    memories = parse_memories(body.get("memories", []))
    # Truthiness, not `is True`: if lea-be-core ever sends "true" as a string,
    # the safe failure is suppressing recall, never quietly keeping it on.
    monitored = bool(body.get("monitored_device", False))
    return json_response({"context": compose_memory_context(memories, monitored)})
