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

import re

from guardrails.contracts import FeatureResult
from guardrails.rules import LANGUAGE_COACH_SCRIPTS, RESP
from guardrails.session import SessionState

DEFAULT_PERSONA = """\
You are Lea — a compassionate, calm legal companion for survivors of
domestic, sexual, and tech-facilitated violence. You help users understand
their legal options without giving formal legal advice.

Hard rules:
- Never minimize what the user describes.
- If the user describes imminent harm, surface emergency resources first.
- Defer to licensed professionals for jurisdiction-specific legal advice.
- Match the user's language; default to plain English when unclear.

Naming harm:
- When the user describes manipulation, control, or abuse — in any relationship,
  including friends, family, or coworkers — name the pattern plainly and early,
  especially if they ask. Putting language to it helps them trust their own read.
- Name behaviors and tactics, never a clinical diagnosis. Do not label anyone
  with a personality disorder from a description.
- Acknowledge and validate, and hold the line on these guardrails — but still
  answer the question in the same turn. Never make the user send a follow-up
  just to get the response they already asked for.
"""

CRISIS_PATTERN = (
    r"\b(er|e\.r\.|emergenc\w*|hospital[s]?|hoptal|hospitall|clinic|"
    r"doctor[s]?|911|physician|icu|medic|paramedic|急診|醫院)\b"
)


def get_persona_prompt(name: str) -> str:
    if name == "default":
        return DEFAULT_PERSONA
    return DEFAULT_PERSONA


class PersonaFeatureManager:
    """OOP interface encapsulation managing persona behavior and textual modes."""

    def match_and_execute(self, pl: str, session: SessionState) -> FeatureResult | None:
        # -----------------------------------------------------------------------
        # MODE ACTIVATIONS — G-11, G-12, G-15
        # Regex (not substring) so natural phrasings match, e.g.
        # "could you switch to trusted friend mode" or "what should i say".
        # -----------------------------------------------------------------------
        if any(
            re.search(p, pl)
            for p in (
                r"trusted[ -]friend mode",
                r"talk (to me )?(like|as) a friend",
            )
        ):
            session.trusted_friend_mode = True
            session.expert_mode = False
            return FeatureResult(RESP["G11_activate"], 0)

        if any(re.search(p, pl) for p in (r"expert mode", r"clinical mode")):
            session.expert_mode = True
            session.trusted_friend_mode = False
            return FeatureResult(RESP["G12_activate"], 0)

        if any(
            re.search(p, pl)
            for p in (
                r"language coach",
                r"give me (sentences|scripts|words)",
                r"what (should|do) i say",
                r"tell me exactly what to say",
            )
        ):
            session.language_coach_mode = True
            script = self._generate_language_script(pl)
            return FeatureResult(script, 0)

        return None

    def _generate_language_script(self, prompt_lower: str) -> str:
        """G-15: generate actual sentences based on who the user is talking to."""
        if any(w in prompt_lower for w in ["police", "officer", "911", "cop"]):
            return str(LANGUAGE_COACH_SCRIPTS["police"])
        if any(w in prompt_lower for w in ["clerk", "courthouse", "file", "filing"]):
            return str(LANGUAGE_COACH_SCRIPTS["clerk"])
        if any(w in prompt_lower for w in ["judge", "hearing", "court", "testify"]):
            return str(LANGUAGE_COACH_SCRIPTS["judge"])
        return (
            "To give you the right sentences, tell me who you're speaking to: "
            "police, a court clerk, a judge, or someone else? "
            "And what's the key thing you need to communicate?"
        )

    def apply_mode_constraints(self, text: str, session: SessionState, prompt: str) -> str:
        """Applies prompt-dependent formatting criteria structural constraints."""
        mode = getattr(session, "response_mode", "")
        has_crisis = bool(
            re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text
        )

        if mode == "Direct":
            if has_crisis:
                return str(RESP["crisis_mode_Direct"])
            # Strip only performative openers — NOT genuine acknowledgment. "I hear you"
            # is empathy the user wants kept (2026-05 feedback: replies felt templatized
            # and cold); leaving it in keeps Direct mode warm without padding.
            fillers = [
                r"^that's a really important question[^.]*\.",
                r"^i'm so relieved to hear[^.]*\.",
            ]
            for pattern in fillers:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+", " ", text).strip()
            sentences = re.split(r"(?<=[.!?])\s+", text)
            # Cap raised 3 -> 6: validate-then-educate now answers in ONE turn, so the
            # response carries both the validation and the substance. A 3-sentence cap
            # truncated the actual answer; 6 keeps it whole while still trimming rambling.
            if len(sentences) > 6:
                text = " ".join(sentences[:6])
            return text

        if mode == "Gentle":
            if has_crisis:
                return str(RESP["crisis_mode_Gentle"])
            text = re.sub(r"\s+", " ", text).strip()
            return text.replace(
                "Are you safe to talk right now?", "\n\nAre you safe to talk right now?"
            )

        if mode == "Strong":
            if has_crisis:
                return str(RESP["crisis_mode_Strong"])
            text = re.sub(r"\s+", " ", text).strip()
            return text.replace(
                "Are you safe to talk right now?",
                "Ensure you are in a secure location before continuing this conversation.",
            )

        if mode == "Warm":
            if has_crisis:
                return str(RESP["crisis_mode_Warm"])
            return re.sub(r"\s+", " ", text).strip()

        if mode == "Crisis":
            if has_crisis:
                return str(RESP["crisis_mode_Crisis"])
            return re.sub(r"\s+", " ", text).strip()

        if session.trusted_friend_mode:
            text = re.sub(r"^[ \t]*[-•*][ \t]*", "", text, flags=re.MULTILINE)
            text = re.sub(r"^[ \t]*\d+\.[ \t]*", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s+[-•*]\s+", " ", text)
            text = re.sub(r"\s+\d+\.\s+", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            text = " ".join(sentences[:5]) if len(sentences) > 5 else " ".join(sentences)

            question_count = text.count("?")
            if question_count > 1:
                parts = text.rsplit("?", question_count - 1)
                text = parts[0] + "?" + parts[-1].replace("?", ".")
            return text

        return text
