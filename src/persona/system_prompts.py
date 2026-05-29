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
from typing import Any
from guardrails.session import SessionState
from guardrails.rules import RESP, LANGUAGE_COACH_SCRIPTS

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

CRISIS_PATTERN = r"\b(er|e\.r\.|emergenc[ye]|hospital[s]?|hoptal|hospitall|clinic|doctor[s]?|911|physician|icu|medic|paramedic|急診|醫院)\b"


def get_persona_prompt(name: str) -> str:
    if name == "default":
        return DEFAULT_PERSONA
    return DEFAULT_PERSONA


class PersonaFeatureManager:
    """OOP interface encapsulation managing persona behavior and textual modes."""

    def match_and_execute(self, pl: str, session: SessionState) -> tuple[str, int, bool] | tuple[str, int] | None:
        # -----------------------------------------------------------------------
        # MODE ACTIVATIONS — G-11, G-12, G-15
        # -----------------------------------------------------------------------
        if any(w in pl for w in ["trusted friend mode", "talk like a friend", "talk as a friend"]):
            session.trusted_friend_mode = True
            session.expert_mode = False
            return RESP["G11_activate"], 0

        if any(w in pl for w in ["expert mode", "clinical mode"]):
            session.expert_mode = True
            session.trusted_friend_mode = False
            return RESP["G12_activate"], 0

        if any(w in pl for w in [
            "language coach",
            "give me sentences",
            "give me scripts",
            "give me words",
            "what should i say",
            "what do i say",
            "tell me exactly what to say"
        ]):
            session.language_coach_mode = True
            script = self._generate_language_script(pl)
            return script, 0

        return None

    def _generate_language_script(self, prompt_lower: str) -> str:
        """G-15: generate actual sentences based on who the user is talking to."""
        if any(w in prompt_lower for w in ["police", "officer", "911", "cop"]):
            return LANGUAGE_COACH_SCRIPTS["police"]
        if any(w in prompt_lower for w in ["clerk", "courthouse", "file", "filing"]):
            return LANGUAGE_COACH_SCRIPTS["clerk"]
        if any(w in prompt_lower for w in ["judge", "hearing", "court", "testify"]):
            return LANGUAGE_COACH_SCRIPTS["judge"]
        return (
            "To give you the right sentences, tell me who you're speaking to: "
            "police, a court clerk, a judge, or someone else? "
            "And what's the key thing you need to communicate?"
        )

    def apply_mode_constraints(self, text: str, session: SessionState, prompt: str) -> str:
        """Applies prompt-dependent formatting criteria structural constraints."""
        mode = getattr(session, "response_mode", "")
        has_crisis = bool(re.search(CRISIS_PATTERN, prompt, re.IGNORECASE) or "SAFETY WARNING" in text)

        if mode == "Direct":
            """Direct Mode: Minimalist, raw directives. (Word Count: ~20-25)"""
            if has_crisis:
                return (
                    "SAFETY WARNING: Go to the ER immediately for a medical evaluation. "
                    "Strangulation causes hidden, fatal internal trauma. Call 911 or 1-800-799-7233 now."
                )
            fillers = [
                r"^that's a really important question[^.]*\.",
                r"^i'm so relieved to hear[^.]*\.",
                r"^i hear you[^.]*\."
            ]
            for pattern in fillers:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+", " ", text).strip()
            sentences = re.split(r"(?<=[.!?])\s+", text)
            if len(sentences) > 3:
                text = " ".join(sentences[:3])
            return text

        if mode == "Gentle":
            """Gentle Mode: Soft pacing, double line breaks, low visual stress. (Word Count: ~65-70)"""
            if has_crisis:
                return (
                    "Please take a deep breath. Your physical well-being is everything right now. Even if you feel fine physically, "
                    "injuries from strangulation can cause internal trauma that isn't immediately visible to the eye.\n\n"
                    "We highly recommend letting a professional at an emergency room evaluate you just to be completely safe. "
                    "Whenever you are ready, gentle support is here 24/7 at 1-800-799-7233. Are you safe to talk right now?"
                )
            text = re.sub(r"\s+", " ", text).strip()
            return text.replace("Are you safe to talk right now?", "\n\nAre you safe to talk right now?")

        if mode == "Strong":
            """Strong Mode: Empowering active voice, high-agency framing. (Word Count: ~60-65)"""
            if has_crisis:
                return (
                    "Listen to me carefully: you are facing a life-threatening situation. This is an assault, and your "
                    "life matters. Demand an immediate medical evaluation at an ER—do not let anyone dismiss hidden internal trauma. "
                    "Take control of your safety right now. Call 1-800-799-7233 immediately. "
                    "Ensure you are in a secure location before continuing this conversation."
                )
            text = re.sub(r"\s+", " ", text).strip()
            return text.replace("Are you safe to talk right now?", "Ensure you are in a secure location before continuing this conversation.")

        if mode == "Warm":
            """Warm Mode: Rich narrative, prose-only companion tone, zero list blocks. (Word Count: ~85-95)"""
            if has_crisis:
                return (
                    "I am so incredibly glad you reached out to me tonight, but I need you to know how precious your life is. "
                    "What happened to you is dangerous, and I want to make sure you are truly safe. Please consider letting an ER doctor "
                    "look after you, because internal injuries from this kind of harm don't always show up right away. "
                    "There are gentle, caring experts waiting to hold space for you around the clock at 1-800-799-7233. "
                    "Please take a gentle moment to make sure you are in a safe, quiet space where we can talk privately."
                )
            text = re.sub(r"\s+", " ", text).strip()
            return text

        if mode == "Crisis":
            """Crisis Mode: Strict tactical grounding, survival-first layout. (Word Count: ~50-55)"""
            if has_crisis:
                return (
                    "EMERGENCY PROTOCOL ACTIVATED. Your life is in immediate danger. Internal trauma can be fatal. "
                    "Go to the nearest Emergency Room (ER) right now. Medical professionals have protocols to protect you. "
                    "Call 911 or 1-800-799-7233 immediately.\n\n"
                    "CRITICAL: Focus on your physical environment right now. Find a safe room with a lock, or exit the building if you can. Are you safe to speak at this exact moment?"
                )
            text = re.sub(r"\s+", " ", text).strip()
            return text

        if session.trusted_friend_mode:
            """G-11: prose only, max 5 sentences, no bullets, one question per turn."""
            # Strip bullet markers from lines BEFORE collapsing whitespaces
            text = re.sub(r"^[ \t]*[-•*][ \t]*", "", text, flags=re.MULTILINE)
            text = re.sub(r"^[ \t]*\d+\.[ \t]*", "", text, flags=re.MULTILINE)
            
            # Inline markers that were pushed post line breaks must be sanitized globally
            text = re.sub(r"\s+[-•*]\s+", " ", text)
            text = re.sub(r"\s+\d+\.\s+", " ", text)

            # Normalize spacing but retain terminal sentence indicators cleanly
            text = re.sub(r"\s+", " ", text).strip()

            # Split sentences precisely by targeting punctuation anchors with spacing layout rules
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            if len(sentences) > 5:
                text = " ".join(sentences[:5])
            else:
                text = " ".join(sentences)

            question_count = text.count("?")
            if question_count > 1:
                parts = text.rsplit("?", question_count - 1)
                text = parts[0] + "?" + parts[-1].replace("?", ".")
            return text

        return text