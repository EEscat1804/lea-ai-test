"""lea-ai entrypoint.

Cloudflare Python Worker. Routes incoming HTTPS requests to feature modules.
All endpoints require a `Authorization: Bearer <SERVICE_TOKEN>` header from
lea-be-core; lea-ai never accepts unauthenticated user traffic.
"""

from __future__ import annotations

from typing import Any

from guardrails.classifier import classify_message, process_message_endpoint
from lib.auth import authorize
from lib.responses import json_response, problem_response
from memory.api import handle_context, handle_extraction_prompt, handle_review
from persona.system_prompts import compose_system_prompt
from vault.intake import handle_intake_step
from vault.petition import handle_petition_request


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
        body = await _read_json_body(request)
        return await classify_message(body, env)

    if path == "/v1/lea/process" and method == "POST":
        body = await _read_json_body(request)
        return await process_message_endpoint(body, env)

    if path == "/v1/vault/intake" and method == "POST":
        body = await _read_json_body(request)
        return await handle_intake_step(body, env)

    if path == "/v1/vault/petition" and method == "POST":
        body = await _read_json_body(request)
        return await handle_petition_request(body, env)

    if path == "/v1/memory/extraction-prompt" and method == "POST":
        body = await _read_json_body(request)
        return await handle_extraction_prompt(body, env)

    if path == "/v1/memory/review" and method == "POST":
        body = await _read_json_body(request)
        return await handle_review(body, env)

    if path == "/v1/memory/context" and method == "POST":
        body = await _read_json_body(request)
        return await handle_context(body, env)

    if path == "/v1/persona/prompt" and method == "GET":
        persona = _query_param(url, "persona") or "default"
        mode = _query_param(url, "mode") or ""
        return json_response({"prompt": compose_system_prompt(persona, mode)})

    return problem_response(404, "not_found", f"no route for {method} {path}")


async def _read_json_body(request: Any) -> dict[str, Any]:
    """`request.json()` returns a Pyodide JsProxy; convert to a real Python dict."""
    raw = await request.json()
    if hasattr(raw, "to_py"):
        return raw.to_py()  # type: ignore[no-any-return]
    return raw  # type: ignore[no-any-return]


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
