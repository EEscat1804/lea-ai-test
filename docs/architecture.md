# lea-ai — Architecture

Living doc. Source of truth lives in this repo (`docs/architecture.md`);
Notion copy is a mirror, may lag. Update both when material changes happen.

**Last meaningful change**: 2026-05-25 — initial scaffold + Aaron Wang's guardrails v2 ported.

---

## What this service is

LEA's AI brain. Stateless Python service on Cloudflare Workers. Called by `lea-be-core` over signed HTTPS — **never** exposed directly to mobile clients, browser sessions, or the internet at large.

The whole product serves survivors of **domestic, sexual, and tech-facilitated violence**. Every code path in lea-ai is one hop from crisis-grade user data. Privacy and safety are not features bolted on later — they are the floor that every design decision is measured against.

## Where it sits

```
┌──────────────────────┐
│  legali-lea-mobile   │  Flutter app
│  (App Store, Play)   │
└──────────┬───────────┘
           │ HTTPS, Supabase JWT
           ▼
┌──────────────────────┐
│  lea-be-core         │  Hono on Cloudflare Workers
│  - Auth (Supabase)   │  - Owns DB writes, encryption keys
│  - Encryption at-rest│  - Owns voice WebSocket termination
│  - R2 / KV / DO      │  - Owns usage limits, push notifications
│  - Voice WS proxy    │  - Calls lea-ai for AI decisions
└──────────┬───────────┘
           │ HTTPS, Bearer SERVICE_TOKEN
           ▼
┌──────────────────────┐
│  lea-ai (this repo)  │  Python on Cloudflare Workers
│  - Guardrails        │  - STATELESS
│  - Vault intake FSM  │  - No DB, no keys, no user identity
│  - Persona prompts   │  - No user-facing traffic
└──────────────────────┘
```

**Key invariant**: lea-ai does not authenticate users. lea-be-core authenticates the user, decides what to send lea-ai, and persists what comes back. If you find yourself reaching for a session cookie or JWT in lea-ai, stop and push the work back to lea-be-core.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Matches `legali-rag` and `team-legali-ai` ecosystem (LangChain, presidio, etc.). Aaron and Kabir are Python-fluent. |
| Runtime | Cloudflare Workers (Pyodide) | Same edge as `lea-be-core` → low-latency RPC. Stays on Cloudflare per the off-AWS migration arc. |
| HTTP routing | Manual `if path == ...` in `worker.py` | No mature Hono-equivalent for Python yet. Routing is trivial; one entrypoint, six endpoints. |
| Response objects | `from workers import Response` | Cloudflare's official Python SDK helper. Re-exported from `lib/responses.py` so tests can run outside workerd. |
| Linting | ruff | Single tool for format + lint. `pyproject.toml` per-file ignores let the user-facing copy keep curly quotes / em-dashes. |
| Type checking | mypy --strict | No `Any` outside the `js` / `workers` boundary. |
| Tests | pytest | 43 tests as of v0.1.0; tier-3 cascade is parameterized so adding rules adds coverage. |
| Deploy | wrangler 4.94 + GH Actions | Push to `release/staging` auto-deploys staging; production via `workflow_dispatch`. |

### Compatibility-date pin

`wrangler.jsonc` sets `compatibility_date: "2024-09-23"`. Newer dates (≥ 2025) require an explicit `workers-py>=1.90` dependency from `requirements.txt`, which Pyodide's package resolution does not reliably honor. The older date auto-bundles the `workers` SDK and Just Works. Bump only when Cloudflare's docs say a specific feature you need is gated behind a newer date.

## Endpoints

All `/v1/*` endpoints require `Authorization: Bearer <SERVICE_TOKEN>`. The token is verified in constant time (`hmac.compare_digest`). `/health` and `/version` are unauthenticated for uptime monitoring.

| Method + path | Owner module | Purpose |
|---|---|---|
| `GET /health` | `worker.py` | Liveness probe. `{"status":"ok","service":"lea-ai"}` |
| `GET /version` | `worker.py` | Version + environment. `{"version":"0.1.0","env":"staging"}` |
| `POST /v1/lea/process` | `guardrails/classifier.py` | **Main entry.** Full router output — text response + tier + updated session. |
| `POST /v1/guardrails/classify` | `guardrails/classifier.py` | Classification-only view — `{classification, tier, categories}` without user-facing text. Use for pre-LLM filtering. |
| `POST /v1/vault/intake` | `vault/intake.py` | DVRO intake state machine. Given `(jurisdiction, answers)`, returns the next question. Stub today; per-jurisdiction graphs land per PR. |
| `GET /v1/persona/prompt?persona=<name>` | `persona/system_prompts.py` | Returns the LEA system prompt. Caller uses it as the model's system instruction. |

### `/v1/lea/process` contract

Request:
```json
{
  "text": "user message text",
  "session": {
    "user_state": "CA",
    "trusted_friend_mode": false,
    "tier3_fired_this_session": false,
    "risk_factors": [],
    "pending_education": null
    // ...any SessionState field. Optional; defaults to fresh state.
  }
}
```

Response:
```json
{
  "response": "...",      // text to show user (already mode-formatted)
  "tier": 0,              // 0=safe, 1=guidance, 2=elevated, 3=crisis
  "show_quick_exit": true,
  "vault_write_requires_consent": false,
  "session": { /* updated SessionState — caller persists this */ }
}
```

Error shape (RFC 7807-ish, matches `lea-be-core`'s `BaseError` contract):
```json
{"code":"bad_request","detail":"text is required"}
```

## Module layout

```
src/
├── worker.py                # CF entry: route dispatch + auth gate + JSON body
├── lib/
│   ├── auth.py              # Constant-time SERVICE_TOKEN comparison
│   └── responses.py         # JSON / problem+json helpers (workers.Response wrapper)
├── guardrails/
│   ├── session.py           # SessionState dataclass — G-07/G-13/G-14 state
│   ├── rules.py             # Pure data: G01..G20 triggers, RESP templates,
│   │                        # CLINICAL_TERMS, TACTIC_PATTERNS, RISK_FACTOR_TRIGGERS,
│   │                        # LANGUAGE_COACH_SCRIPTS
│   ├── router.py            # process_message + 10 helpers
│   └── classifier.py        # HTTP surface — wraps router for /v1/guardrails/classify
│                            # and /v1/lea/process
├── vault/
│   ├── intake.py            # DVRO multi-state question-graph (stub)
│   └── petition.py          # Court-ready petition assembly (placeholder)
└── persona/
    └── system_prompts.py    # System-prompt registry — edits are code reviews

tests/
├── test_persona.py          # Persona regression — safety-rule assertions
├── test_vault_intake.py     # Vault state-machine stubs
├── test_guardrails.py       # 31 regression tests pinning the cascade
└── audit/
    ├── corpus.csv           # 1,520-row DV-scenario corpus (Aaron Wang)
    └── run_audit.py         # Offline harness, stdlib csv (no pandas in prod)
```

## Guardrails subsystem (the meat of v0.1.0)

20 rules across 5 categories per the engineering spec (`lea_ai_guardrails_spec.html`):

| Category | Rules | Severity |
|---|---|---|
| Crisis & safety detection | G-01..G-04 | Critical (Tier 3) |
| Trauma-informed response | G-05..G-10 | Critical–Important |
| Mode-specific controls | G-11, G-12, G-15 | Guidance–Info |
| Hard refusals | G-16, G-17, G-18 | Critical |
| Privacy & safety design | G-19, G-20 | Critical |

### The cascade

`router.process_message` walks a five-tier cascade, in order:

1. **Tier 3 — Imminent safety.** G-04 (strangulation, more specific) → G-01 (general imminent danger) → G-02 (suicide) → G-03 (child safety). Once any of these fire, `session.tier3_fired_this_session = True` and `build_response(..., preserve_labels=True)` returns the canonical response. **No lower-tier block can downgrade a Tier-3 match.**
2. **Bright-line refusals.** Out-of-scope: outcome prediction, third-party impersonation, couples-therapy framing (G-16), abuser-inner-life speculation (G-17), burden-shift framing (G-18).
3. **G-20 device security.** With G-20 trigger + physical-stalking pattern, compose both warnings.
4. **Trauma-informed responses.** G-05 self-doubt → validation. G-08 quoted speech → validate-then-educate (G-07 sequencing). G-09 trauma bonding → same.
5. **Mode activations + on-demand features.** G-11 friend mode, G-12 expert mode, G-15 language coach, G-13 tactic analysis, G-14 risk assessment.
6. **Tier 2 — depth.** Restraining-order how-to, protective-order violations, stalking, firearm + threat, immigration coercion, financial coercion, custody threats, post-filing procedure.
7. **Default.** Generic supportive fallback.

### SessionState

A dataclass passed in and returned out of every `/v1/lea/process` call. Carries:

- **Vault context**: `user_state`, `user_county`, `has_children`, `is_married`, `firearm_access`, `strangulation_disclosed`, `immigration_risk`
- **Safety flags** (sticky for the session): `tier3_fired_this_session`, `tier2_fired_this_session`, `resource_surfaced_this_session`
- **Mode controls**: `trusted_friend_mode`, `expert_mode`, `language_coach_mode`
- **Risk accumulators**: `risk_factors: list[str]`
- **Sequencing slots**: `pending_education: str | None` (for G-07 turn-1/turn-2 split)
- **Consent gate**: `data_storage_consent` (G-20 — gate Vault writes)

lea-be-core owns persistence. Every response includes the updated session; lea-be-core writes it back to its store keyed by user/chat session ID.

## Vault subsystem (v0.1.0 stub)

DVRO Multi-State Intake Question Flow — 47 US jurisdictions. PRD lives in Notion (`DVRO Multi-State Intake Question Flow`). California is the v1 reference jurisdiction; other 46 added per PR with both intake graph + petition template in the same change.

Current state machine is a placeholder (`vault/intake.py:_stub_next_step`) that walks `petitioner_name` → `incident_summary` → `done`. Real per-jurisdiction graphs land via `vault.petition.assemble_petition`.

## Persona subsystem (v0.1.0)

One default persona at `persona/system_prompts.py:DEFAULT_PERSONA`. Regression tests assert:
- The string contains "legal advice" (no formal legal advice rail)
- The string contains "emergency" (crisis-routing rail)

Edits to the persona must keep both assertions passing — they are the contract with `lea-be-core` that the persona never silently loses its safety rails.

## Auth + integration

### Service token

`lea-be-core` and `lea-ai` share one secret per environment:
- `wrangler secret put SERVICE_TOKEN --env staging` on lea-ai
- Same value as a Worker secret in `lea-be-core` (named whatever its env var convention uses)
- Constant-time compare in `src/lib/auth.py` — never `==` on tokens

Token rotation:
1. Generate new token: `python3 -c "import secrets; print(secrets.token_hex(32))"`
2. Set on lea-ai first: `wrangler secret put SERVICE_TOKEN --env <env>`
3. Set on lea-be-core within 60s (overlap window — both old + new accepted briefly is fine because lea-ai only accepts the new one but the rollover gap is the risk window)
4. After both deploys propagate (~30s on Cloudflare), the old token is dead

Tokens are never committed. Never logged. The `_build_session` helper in `classifier.py` only deserializes whitelisted SessionState fields — extra keys are dropped silently, so a malicious payload can't smuggle a `__class__` or `secret_token` field.

### Why HTTPS, not Cloudflare service binding

Service binding (worker-to-worker direct RPC) would be ~10ms faster and avoid the public internet hop. We chose signed HTTPS because:
- Portable: if lea-ai ever moves off Cloudflare (e.g., AWS for GPU access on a heavier model), the contract doesn't change.
- Auditable: requests show in Cloudflare logs with proper method/path/status; bindings are opaque.
- Forces the auth boundary to be explicit and testable from outside Cloudflare.

Revisit if p99 latency on `lea-be-core → lea-ai` becomes a chat-experience problem.

## Deploy topology

| Env | Worker name | Domain | Branch | Trigger |
|---|---|---|---|---|
| local | n/a | `localhost:8787` via `wrangler dev` | any | manual |
| staging | `lea-ai-staging` | `staging-ai.lea.legali.ai` | `release/staging` | auto on push |
| production | `lea-ai-production` | `ai.lea.legali.ai` | `main` | `workflow_dispatch` only |

Custom domains created via `wrangler.jsonc` route entries (`custom_domain: true`). DNS records auto-provisioned in the `legali.ai` zone on first deploy.

GH Actions secrets (repo-level, `Legali-AI/lea-ai`):
- `CLOUDFLARE_API_TOKEN` — scoped to Workers Scripts:Edit + Workers Routes:Edit on `legali.ai`
- `CLOUDFLARE_ACCOUNT_ID` — the `Dev@legali.ai's Account` ID

CI (`ci.yml`) runs on every push + PR to `main` and `release/staging`:
1. Set up Python 3.12
2. Install `requirements-dev.txt`
3. `ruff check src tests`
4. `mypy src`
5. `pytest`

Deploy (`deploy.yml`) runs on push to `release/staging` (auto) or manual dispatch for production. Wrangler is the only deploy mechanism.

## Testing strategy

### Unit tests (in-repo, run on every PR)

| File | Tests | Pins |
|---|---|---|
| `test_persona.py` | 4 | DEFAULT_PERSONA references "legal advice" + "emergency"; unknown personas fall back to default |
| `test_vault_intake.py` | 8 | First step is `petitioner_name`; required-fields gate the `done` step; stub flow uniform across supported jurisdictions |
| `test_guardrails.py` | 31 | Tier-3 unavoidable; G-04 precedence over G-01; cascade order; G-07 turn-1/turn-2; G-11 sentence cap + bullet strip; G-13 tactic detection; G-14 risk thresholds; G-19 always signaled; G-20 SECURITY NOTICE preserved |

### Offline audit (run before promoting major guardrails changes)

`tests/audit/run_audit.py` walks the 1,520-row corpus and prints `(prompt, tier, response)` per row. Currently informational — does not assert. **Pre-prod TODO**: convert to pass/fail with a `Expected Tier` column added to the CSV, anchored to known-good outputs. Then run in CI.

### What is NOT covered

- **No live LLM testing.** Tier-3 detection is regex-only today (P1.3 follow-up — model-based safety net). A real test corpus against the deployed Gemini call would catch paraphrase/leetspeak misses.
- **No load testing.** Single-request latency is fine on Workers; concurrent behavior unknown.
- **No fuzzing.** `matches_any` is called with arbitrary user input; regex DoS risk is low (no nested quantifiers) but not formally verified.
- **No FE integration test.** The contract with `lea-be-core` is documented but not exercised end-to-end in CI.

## Safety floor — non-negotiables

These are not preferences. They are properties the codebase enforces structurally.

1. **Stateless.** No KV puts, no D1, no Durable Objects, no R2. Adding any storage layer breaks the auth boundary (lea-ai would suddenly need to know who the user is).
2. **No user auth, ever.** Only `lea-be-core` calls in. Adding a JWT verification path here would mean `lea-ai` now has its own user model, which contradicts (1).
3. **Tier-3 takes precedence over everything.** No optimization, no mode override, no consent gate can suppress a G-01..G-04 match. Regression tests pin this.
4. **No user-text logging in prod.** `observability.enabled = true` in `wrangler.jsonc` is for shapes/timings, not content.
5. **Guardrail edits require regression tests.** Every change to `rules.py` or `router.py` must keep `tests/test_guardrails.py` passing — and if a new rule is added, a new parametrized test row goes in the same PR.
6. **Persona edits require their own regression.** `tests/test_persona.py` pins the legal-advice + emergency rails.

## Open follow-ups (v1.1)

Tracked as inline comments on commit `a82e7eeec9` and in `/Users/anneregina/legali/aaron-evaluator-review.md`:

| ID | What | Owner |
|---|---|---|
| P1.1 | ✅ pandas → stdlib csv (done in port) | Anne |
| P1.2 | Multi-state defaults — California fallback in 2 places | Aaron + Pranav |
| P1.3 | Model-based Tier-3 safety net behind regex first-pass | Aaron + Kabir |
| P2.1 | `matches_any` should surface `re.error` not fall back silently | Aaron |
| P2.2 | Document the word-boundary policy per `G##_TRIGGERS` block | Aaron |
| P2.3 | `SessionState.last_tier3_rule: str \| None` for downstream branching | Aaron |
| P2.4 | PII redactor in audit harness before any real-data runs | Aaron |
| P3.1 | Inline pytest assertions on the audit corpus (expected-tier column) | Aaron |
| P3.2 | Extract `compose(primary, *addons)` helper for composite responses | Aaron |
| P3.3 | Co-locate triggers with their response templates per rule | Aaron |

## Things this doc does NOT cover yet

- **Vault PRD.** Lives in Notion. When the multi-state intake graph schema is finalized, the per-jurisdiction question structure goes in `docs/vault-schema.md` and is referenced here.
- **Voice integration.** Voice WS termination stays in `lea-be-core` for v1. If voice moves to lea-ai later, this doc grows a section.
- **Observability dashboards.** Cloudflare's built-in observability is on; no Grafana / Datadog wiring yet. Add when traffic patterns require it.
- **Rate limiting.** No per-caller limit; `lea-be-core` is the only caller and enforces usage limits user-side. Add a Cloudflare WAF rule if a second caller is ever added.

## Pointers for new contributors

1. Read this doc.
2. Read `CLAUDE.md` (it's the operational rules: stateless, safety floor, per-jurisdiction logic, Pyodide constraints).
3. Read `tests/test_guardrails.py` — the regression suite tells you what *must not* change.
4. Read `src/guardrails/router.py:process_message` — the cascade order is the contract.
5. Local setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && pytest`.
6. First change: pick a P2.x follow-up from above, open a PR branched off `release/staging`. CI will tell you if you broke a safety rail.

Questions go to `#dev-discussion` under `team-lea-project` in the Legali Devs Discord. Engineering Manager: Anne.
