"""Service-token authorization.

lea-be-core sends `Authorization: Bearer <token>` on every internal call.
We compare against `env.SERVICE_TOKEN` in constant time. A failed match
returns a 401 problem response and the caller's request is dropped.

Constant-time comparison matters: a fast `==` leaks token bytes via timing.
"""

from __future__ import annotations

import hmac
from typing import Any

from lib.responses import problem_response


def authorize(request: Any, env: Any) -> Any | None:
    """Return None when authorized, else a problem response to short-circuit."""
    expected = getattr(env, "SERVICE_TOKEN", None)
    if not expected:
        return problem_response(500, "misconfigured", "SERVICE_TOKEN not set")

    header = request.headers.get("Authorization") or ""
    if not header.startswith("Bearer "):
        return problem_response(401, "unauthorized", "missing bearer token")

    presented = header[len("Bearer ") :]
    if not hmac.compare_digest(presented, expected):
        return problem_response(401, "unauthorized", "invalid bearer token")

    return None
