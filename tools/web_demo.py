"""A real, runnable web app for Lea — over the live guardrails engine.

This is a LOCAL DEMO, not the production surface. In production, the public never
talks to lea-ai directly: mobile/web → lea-be-core → lea-ai (that boundary is the
whole point of this service). This harness exists so you can *experience* what Lea
feels like to a person in the dark — the warmth, the crisis routing, the always-there
quick exit — without standing up the whole stack.

It runs the exact same `guardrails.router.process_message` the real service uses, so
what you see here is what the engine actually does. Stdlib only — no new dependencies.

Run from the repo root, then open the printed URL:

    python tools/web_demo.py            # serves on http://127.0.0.1:8800
    python tools/web_demo.py 9000       # custom port

The server is stateless, exactly like lea-ai: the browser holds the SessionState and
sends it back each turn, the way lea-be-core would persist and replay it.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from guardrails.router import process_message
from guardrails.session import SessionState

INDEX_HTML = (Path(__file__).resolve().parent / "web" / "index.html").read_text(encoding="utf-8")

_TIER_LABEL = {0: "safe", 1: "guidance", 2: "elevated", 3: "crisis"}
_VALID_KEYS = {f.name for f in fields(SessionState)}


def _build_session(raw: Any) -> SessionState:
    """Rebuild SessionState from the browser's echoed dict, ignoring stray keys."""
    if not isinstance(raw, dict):
        return SessionState()
    return SessionState(**{k: v for k, v in raw.items() if k in _VALID_KEYS})


def _process(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one turn through the real router and shape the JSON the UI expects."""
    text = payload.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return {"error": "text is required"}

    session = _build_session(payload.get("session"))
    mode = payload.get("response_mode")
    if isinstance(mode, str) and mode:
        session.response_mode = mode

    result = process_message(text, session)
    return {
        "response": result["response"],
        "tier": result["tier"],
        "classification": _TIER_LABEL.get(result["tier"], "safe"),
        "show_quick_exit": result["show_quick_exit"],
        "session": asdict(result["session"]),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        # Never log request bodies — they may carry crisis-grade content. Stay quiet.
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/api/process":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, b'{"error":"invalid json"}', "application/json")
            return
        body = json.dumps(_process(payload)).encode("utf-8")
        self._send(200, body, "application/json; charset=utf-8")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8800
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Lea demo is alive → {url}")
    print("  (local only · same guardrails engine as production · Ctrl-C to stop)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. Take care of yourself.\n")
        server.server_close()


if __name__ == "__main__":
    main()
