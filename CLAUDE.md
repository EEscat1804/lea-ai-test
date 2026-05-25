# CLAUDE.md — lea-ai

## What this repo is

LEA's AI brain. Python on Cloudflare Workers. **Internal service** — called by `lea-be-core` over signed HTTPS, never by mobile or web directly.

The whole product is built for **survivors of domestic, sexual, and tech-facilitated violence**. Treat every code path as potentially carrying crisis-grade data. Privacy and safety are not features — they are the floor.

## What lea-ai owns

1. **Vault** — DVRO petition intake state machine (47 US jurisdictions). Pure function `(jurisdiction, answers-so-far) → next question`. State lives in lea-be-core's DB; we are stateless.
2. **Guardrails** — input/output safety classifiers (crisis detection, legal-advice overreach, PII leak detection).
3. **Persona** — system-prompt registry. Prompt edits are code reviews, not config tweaks.

## What lea-ai does NOT own

- Auth, encryption keys, sessions, user identity, DB writes, payments, push, voice WS termination, R2 uploads — all in `lea-be-core`.
- Anything that requires storing user-attributable data. This service is stateless.
- Mobile-facing API surfaces. Mobile talks to lea-be-core; only lea-be-core talks here.

## Stack

- Python 3.12 on Cloudflare Workers (Pyodide runtime).
- Routing is manual in `src/worker.py` (no Hono equivalent for Python yet).
- Auth: `Authorization: Bearer <SERVICE_TOKEN>` on every endpoint except `/health` and `/version`. Compared in constant time.
- Errors: RFC 7807 problem+json — matches lea-be-core's contract.

## Critical rules

### Never broaden the trust surface

- This worker only authenticates **lea-be-core**, never a user. Adding a JWT path or accepting user-issued tokens here is a security regression — the whole reason lea-ai is separate is that lea-be-core owns user auth.
- Don't import lea-be-core's secrets, DEKs, or session signing keys. We don't decrypt user data here.

### Stateless or nothing

- No `kv.put`, no D1, no Durable Objects. lea-be-core is the single source of truth for state.
- If a feature seems to need state on this side, push back to lea-be-core or pass the state in the request.

### Guardrails and persona are safety-critical

- **Every change to `src/persona/system_prompts.py` must keep the regression tests passing** (`tests/test_persona.py`) — they assert the legal-advice and emergency-resources guardrails are still mentioned. Don't delete the assertions when "improving" the prompt.
- **Crisis detection in guardrails MUST default to safe.** If the classifier is unsure, classify as `crisis` and let lea-be-core's UX layer decide how to soft-handle. False positives on a crisis check are fine; false negatives are not.
- Never log user message text in production. The Worker has `observability.enabled` but that's for shapes/timings, not content.

### Multi-state branching

- DVRO law differs per jurisdiction. **Hard-code per-jurisdiction logic** rather than trying to generalize — wrong-jurisdiction advice is a hard fail.
- Don't add a jurisdiction until both its intake graph and its petition template land in the same PR.

### Don't pull in heavyweight Python deps

- Pyodide on Workers has a curated package list ([Cloudflare's supported packages](https://developers.cloudflare.com/workers/languages/python/packages/)). Many native-extension libs do not work.
- Audit every `requirements.txt` addition: does it run on Pyodide? If unsure, test locally with `wrangler dev` first.
- Keep `requirements.txt` minimal. Dev-only tools belong in `requirements-dev.txt`.

## Conventions

- Imports: `from __future__ import annotations` at the top of every module.
- Types: `mypy --strict`. No `Any` outside `js` boundary.
- Ruff is the formatter and linter — `ruff check` and `ruff format`.
- Tests mirror `src/` layout. Use `pytest` markers liberally for slow tests.
- Commit messages: `type(scope): short` (e.g. `feat(vault): add CA intake graph`).

## Integration with lea-be-core

- Endpoint pattern: `POST /v1/<feature>/<action>` for mutations, `GET /v1/<feature>/<resource>` for reads.
- Request bodies: JSON, validated via Pydantic models (where possible — keep an eye on Pyodide compat).
- Response bodies on success: feature-specific shape.
- Response bodies on error: `{"code": "<machine-readable>", "detail": "<human-readable>"}` with appropriate HTTP status — matches the BaseError/ApiError contract used by lea-be-core's FE.

## When in doubt

- Privacy > convenience.
- Safety classifier false-positive > false-negative.
- Hard-coded per-jurisdiction logic > clever generalization.
- Ask in `#dev-discussion` under `team-lea-project` on Discord.
