# lea-ai

LEA's AI brain. Python on Cloudflare Workers. Called by [`lea-be-core`](https://github.com/Legali-AI/lea-be-core) over signed HTTPS — never exposed to user traffic directly.

## What it owns

| Surface | Endpoint | Status |
|---|---|---|
| Health | `GET /health`, `GET /version` | scaffold |
| **Vault** intake state machine | `POST /v1/vault/intake` | scaffold — owners: Pranav, Aaron |
| **Guardrails** input/output classification | `POST /v1/guardrails/classify` | scaffold — owners: Aaron, Kabir |
| **Persona** system-prompt registry | `GET /v1/persona/prompt?persona=<name>` | scaffold |

## What it does NOT own

- Auth, user accounts, encryption keys, DB writes, payments, push, voice WS — those stay in `lea-be-core`.
- Direct mobile traffic. Mobile (`legali-lea-mobile-fe`) talks to `lea-be-core`; only `lea-be-core` talks to `lea-ai`.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check src tests
mypy src

# Dev server (requires wrangler):
npm i -g wrangler
wrangler dev
```

## Deploy

- `push` to `release/staging` → auto-deploys staging via `.github/workflows/deploy.yml`
- Production: `workflow_dispatch` with `environment=production`

## Repo layout

```
src/
├── worker.py             # routes (CF Worker entry)
├── lib/
│   ├── auth.py           # service-token verification
│   └── responses.py      # JSON / RFC 7807 helpers
├── guardrails/
│   └── classifier.py     # input/output safety classification
├── vault/
│   ├── intake.py         # per-jurisdiction question graph
│   └── petition.py       # final petition assembly
└── persona/
    └── system_prompts.py # LEA system prompt
tests/                    # pytest, mirrors src/
```

## Conventions

- Every PR uses `.github/pull_request_template.md`.
- Guardrail and persona changes **must** include a regression test that asserts the safety rule still holds.
- Tokens / API keys: `wrangler secret put <NAME>` per environment. Never committed.
