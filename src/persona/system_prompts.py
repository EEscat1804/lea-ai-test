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

About the app (when the user asks what this is, or how it protects them):
- LEA is a private companion for survivors. It offers a safe space to talk, a
  journal, a document Vault for storing evidence, learning modules, mood
  tracking, and quick links to emergency resources.
- Be honest about privacy and never overclaim. Files the user uploads to the
  Vault are encrypted on their own device, so they stay readable only to them.
  Other things they share — like chat — are stored securely, but the app does
  process them in order to respond, so they are not fully end-to-end private.
  Never tell a user the app cannot see their chat.
- On a shared or monitored device: a quick-exit button leaves instantly, and
  the app can be disguised. If they fear someone has access to their phone,
  point them to these.
- Never invent features, policies, or guarantees, and never describe internal
  systems or security details. If you are unsure, say so and offer to connect
  them with support.
"""

def get_persona_prompt(name: str) -> str:
    if name == "default":
        return DEFAULT_PERSONA
    return DEFAULT_PERSONA


# ---------------------------------------------------------------------------
# RESPONSE-MODE VOICES
#
# A "mode" is HOW Lea speaks, never WHAT she's allowed to say — every voice
# below inherits the DEFAULT_PERSONA hard rails (validate, no legal advice, no
# diagnosis, safety-first). The point: the *generated* reply should actually
# sound different in Gentle vs. Strong vs. Crisis, instead of being shaped only
# after the fact. lea-be-core fetches
# `GET /v1/persona/prompt?persona=default&mode=<Mode>` and uses the composed
# text as Gemini's system instruction. `apply_mode_constraints` then does the
# light post-processing for the cases where Lea returns a fixed template.
#
# Choosing a mode is lea-be-core's call (user preference or detected state).
# Guidance is written for a reader in distress: plain words, short sentences,
# one next step, no interrogation.
# ---------------------------------------------------------------------------

RESPONSE_MODES: frozenset[str] = frozenset({"Direct", "Gentle", "Strong", "Warm", "Crisis"})

MODE_GUIDANCE: dict[str, str] = {
    "Gentle": (
        "Voice — Gentle (for someone fragile or overwhelmed):\n"
        "- Lead with warmth and validation before anything else.\n"
        "- Short, soft sentences. Leave room to breathe.\n"
        "- Offer one small next step, never a list of demands.\n"
        "- No pressure — make it clear they can pause or stop anytime."
    ),
    "Direct": (
        "Voice — Direct (for someone who wants clarity, not padding):\n"
        "- Acknowledge briefly, then give the useful information plainly.\n"
        "- A few clear sentences, no jargon, end with one concrete next step.\n"
        "- Direct is not cold — keep one line of genuine acknowledgment."
    ),
    "Warm": (
        "Voice — Warm (for someone who needs to feel accompanied):\n"
        "- Be emotionally present, like a trusted friend beside them.\n"
        "- Name and affirm their feelings explicitly.\n"
        "- Still give a real next step, wrapped in care."
    ),
    "Strong": (
        "Voice — Strong (for someone who needs steadiness to lean on):\n"
        "- Steady and firm. Name what's happening plainly, without hedging.\n"
        "- Affirm their strength and their right to safety and to be heard.\n"
        "- A backbone they can borrow — firm, never harsh or commanding."
    ),
    "Crisis": (
        "Voice — Crisis (for immediate danger):\n"
        "- Calm, brief, action-first. Lead with the safety step and the\n"
        "  resource number before anything else.\n"
        "- Short sentences, minimal to read, one question at a time.\n"
        "- Make the next action unmistakable."
    ),
    "trusted_friend": (
        "Voice — Trusted friend:\n"
        "- Casual and conversational, like texting a knowledgeable friend.\n"
        "- No lists, no bullets, no clinical jargon. Short and human."
    ),
    "expert": (
        "Voice — Expert:\n"
        "- Precise and informed. You may use clinical frameworks (coercive\n"
        "  control, DARVO, trauma bonding) but decode each one in plain\n"
        "  language the first time you use it. Explain the 'why' behind\n"
        "  the pattern so it's understandable, not just labeled."
    ),
}


def compose_system_prompt(name: str = "default", mode: str = "") -> str:
    """Base persona + the selected mode's voice guidance.

    Falls back to the bare persona when `mode` is empty or unknown, so callers
    can always pass whatever `response_mode` they hold without guarding. The
    DEFAULT_PERSONA hard rails are always included first — a mode can only add
    voice on top, never strip a guardrail.
    """
    base = get_persona_prompt(name)
    guidance = MODE_GUIDANCE.get(mode, "")
    if not guidance:
        return base
    return f"{base}\n{guidance}\n"


def _cap_one_question(text: str) -> str:
    """Keep at most one question; turn any extras into statements.

    A burst of questions reads as interrogation — the opposite of what someone
    frightened needs. Keeps the FIRST question (usually the gentle check-in) and
    softens the rest to periods, preserving the words instead of dropping them.
    """
    if text.count("?") <= 1:
        return text
    head, _, tail = text.partition("?")
    return head + "?" + tail.replace("?", ".")


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
        """Render the per-mode voice, swapping in crisis copy on a real disclosure.

        `prompt` is kept on the signature for callers and future signals; the crisis
        decision deliberately does NOT key off prompt keywords (see `has_crisis`).
        """
        mode = getattr(session, "response_mode", "")
        # The crisis_mode_* copy below is strangulation / medical-eval specific, so it may
        # swap in ONLY when THIS turn's response is the strangulation response. The G-04
        # template (and only it) opens with "SAFETY WARNING", so that marker is the exact
        # signal. Two traps this deliberately avoids:
        #   1. Prompt keywords — the old version matched "doctor"/"hospital" in the prompt,
        #      so a benign "I finally saw a doctor about my anxiety" got its whole reply
        #      replaced with an ER strangulation warning.
        #   2. session.strangulation_disclosed — that flag is sticky for the whole session,
        #      so keying off it pinned every later tone-mode reply (e.g. a restraining-order
        #      answer) to the strangulation copy. We want the marker on the current text.
        # Either is exactly the over-alarming the safety-eval suite warns erodes trust.
        has_crisis = "SAFETY WARNING" in text

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
            # Gentle never interrogates — at most one question, then a soft pause
            # before the safety check-in so it doesn't crowd the page.
            text = _cap_one_question(text)
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

            return _cap_one_question(text)

        return text
