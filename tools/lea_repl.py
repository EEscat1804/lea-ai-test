"""Local REPL for talking to Lea's guardrails + persona engine.

A developer harness — NOT the product. The real conversational layer (Gemini
generation) lives in lea-be-core; this drives `guardrails.router.process_message`
directly so you can watch the tiered safety cascade respond to real phrasing,
without a network, a token, or wrangler.

Run from the repo root:

    python tools/lea_repl.py

Type a message as a survivor might. Slash commands:

    /mode <Direct|Gentle|Strong|Warm|Crisis>   switch Lea's voice
    /persona                                    show the composed system prompt
    /session                                    show the carried safety state
    /reset                                      start a fresh session
    /help                                       list commands
    /quit                                       exit

The SessionState carries across turns on purpose: a Tier-3 disclosure sets
safety flags that must persist, exactly as lea-be-core would store and replay them.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

# Make `src/` importable when run as a plain script (mirrors pytest's pythonpath).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from guardrails.router import process_message
from guardrails.session import SessionState
from persona.system_prompts import RESPONSE_MODES, compose_system_prompt

TIER_LABEL = {0: "safe", 1: "guidance", 2: "elevated", 3: "CRISIS"}

BANNER = """\
─────────────────────────────────────────────────────────────
 Lea — local guardrails harness (dev only, not the product)
 Type as a survivor might. /help for commands, /quit to exit.
─────────────────────────────────────────────────────────────"""


def _render(prompt: str, session: SessionState) -> SessionState:
    """Run one turn through the router and print Lea's response + metadata."""
    result = process_message(prompt, session)
    tier = result["tier"]
    label = TIER_LABEL.get(tier, "safe")

    print(f"\nLea › {result['response']}\n")
    flags = [f"tier={tier} ({label})"]
    if result["show_quick_exit"]:
        flags.append("quick-exit:on")
    if session.risk_factors:
        flags.append("risk=" + ",".join(session.risk_factors))
    print("  [" + "  ".join(flags) + "]")
    # The router returns the updated session; carry it forward so flags persist.
    return result["session"]


def _handle_command(line: str, session: SessionState) -> SessionState | None:
    """Process a /command. Returns the (possibly new) session, or None to quit."""
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        return None

    if cmd == "/help":
        print(__doc__.split("Slash commands:")[1].split("The SessionState")[0].rstrip())
        return session

    if cmd == "/reset":
        print("  (session reset)")
        return SessionState()

    if cmd == "/mode":
        if arg not in RESPONSE_MODES:
            print(f"  unknown mode {arg!r}; choose one of {sorted(RESPONSE_MODES)}")
            return session
        session.response_mode = arg
        print(f"  (voice → {arg})")
        return session

    if cmd == "/persona":
        print("\n" + compose_system_prompt("default", session.response_mode) + "\n")
        return session

    if cmd == "/session":
        for key, value in asdict(session).items():
            if value not in ("", False, 0, [], None):
                print(f"  {key} = {value!r}")
        return session

    print(f"  unknown command {cmd!r}; try /help")
    return session


def main() -> None:
    print(BANNER)
    session = SessionState()
    while True:
        try:
            line = input("\nyou › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTake care of yourself.")
            return
        if not line:
            continue
        if line.startswith("/"):
            result = _handle_command(line, session)
            if result is None:
                print("Take care of yourself.")
                return
            session = result
            continue
        session = _render(line, session)


if __name__ == "__main__":
    main()
