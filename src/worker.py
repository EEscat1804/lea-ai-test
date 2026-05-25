"""lea-ai entrypoint.

Cloudflare Python Worker. Routes incoming HTTPS requests to feature modules.
All endpoints require a `Authorization: Bearer <SERVICE_TOKEN>` header from
lea-be-core; lea-ai never accepts unauthenticated user traffic.
"""

from __future__ import annotations

from src.guardrails.classifier import classify_message
from src.lib.auth import authorize
from src.lib.responses import json_response, problem_response
from src.persona.system_prompts import get_persona_prompt
from src.vault.intake import handle_intake_step


async def on_fetch(request, env):  # type: ignore[no-untyped-def]
    """Cloudflare Workers entrypoint."""
    url = request.url
    method = request.method
    path = _path_of(url)

    if path == "/health":
        return json_response({"status": "ok", "service": "lea-ai"})

    if path == "/version":
        return json_response({"version": "0.1.0", "env": env.ENVIRONMENT})

    auth_err = authorize(request, env)
    if auth_err is not None:
        return auth_err

    if path == "/v1/guardrails/classify" and method == "POST":
        body = await request.json()
        return await classify_message(body, env)

    if path == "/v1/vault/intake" and method == "POST":
        body = await request.json()
        return await handle_intake_step(body, env)

    if path == "/v1/persona/prompt" and method == "GET":
        persona = _query_param(url, "persona") or "default"
        return json_response({"prompt": get_persona_prompt(persona)})

    return problem_response(404, "not_found", f"no route for {method} {path}")


def _path_of(url: str) -> str:
    after_scheme = url.split("://", 1)[-1]
    return "/" + after_scheme.split("/", 1)[1].split("?", 1)[0] if "/" in after_scheme else "/"


def _query_param(url: str, key: str) -> str | None:
    if "?" not in url:
        return None
    query = url.split("?", 1)[1]
    for pair in query.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            if k == key:
                return v
    return None
