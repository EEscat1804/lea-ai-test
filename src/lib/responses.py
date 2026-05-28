"""Shared response builders.

`workers.Response` is the Cloudflare Python Workers SDK response type.
Outside workerd (tests, type-checking) the import is faked so functions
remain unit-testable.
"""

from __future__ import annotations

import json
from typing import Any
try:
    from workers import Response  
except ImportError:
    Response = None  


def json_response(payload: dict[str, Any], status: int = 200) -> Any:
    body = json.dumps(payload)
    if Response is None:
        return {"status": status, "body": body}
    return Response(body, status=status, headers={"Content-Type": "application/json"})


def problem_response(status: int, code: str, detail: str) -> Any:
    """RFC 7807 problem+json shape — matches lea-be-core's error contract."""
    return json_response({"code": code, "detail": detail}, status=status)
