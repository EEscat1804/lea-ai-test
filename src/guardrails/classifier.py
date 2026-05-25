"""Guardrails — input/output safety classifiers.

Surface for the lea-ai team (Aaron + Kabir) to fill in. Two main jobs:

1. **Pre-LLM classification**: incoming user messages get checked for
   crisis signals (imminent harm, suicidal ideation, abuse-in-progress).
   On a crisis hit, lea-be-core should redirect to hotline UX rather than
   route to chat.
2. **Post-LLM classification**: model outputs get checked for legal-advice
   overreach, jurisdiction-specific accuracy issues, and PII leakage.

This stub returns `{"classification": "safe", "confidence": 1.0}` so the
rest of the stack can be wired end-to-end while the real classifier ships.
"""

from __future__ import annotations

from typing import Any

from lib.responses import json_response, problem_response


async def classify_message(body: dict[str, Any], env: Any) -> Any:
    text = body.get("text")
    direction = body.get("direction", "input")
    if not isinstance(text, str) or not text:
        return problem_response(400, "bad_request", "text is required")
    if direction not in ("input", "output"):
        return problem_response(400, "bad_request", "direction must be input|output")

    # TODO(aaron, kabir): replace with real classifier.
    return json_response(
        {
            "classification": "safe",
            "confidence": 1.0,
            "direction": direction,
            "categories": [],
        }
    )
