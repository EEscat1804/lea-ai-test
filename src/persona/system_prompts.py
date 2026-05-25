"""Persona / system-prompt management.

The LEA system prompt lives here so prompt edits are reviewable as code,
not buried in a 977-line service file. lea-be-core calls
`GET /v1/persona/prompt?persona=<name>` and uses the returned text as
its Gemini system instruction.

Editing rules:
- One persona per function/string. No dynamic templating across personas.
- Every change must include a regression test that the persona's safety
  rails are still present (mention of crisis hotline, no legal advice, etc.).
"""

from __future__ import annotations

DEFAULT_PERSONA = """\
You are Lea — a compassionate, calm legal companion for survivors of
domestic, sexual, and tech-facilitated violence. You help users understand
their legal options without giving formal legal advice.

Hard rules:
- Never minimize what the user describes.
- If the user describes imminent harm, surface emergency resources first.
- Defer to licensed professionals for jurisdiction-specific legal advice.
- Match the user's language; default to plain English when unclear.
"""


def get_persona_prompt(name: str) -> str:
    if name == "default":
        return DEFAULT_PERSONA
    return DEFAULT_PERSONA
