# Connecting lea-ai to lea-be-core (and the Vault)

Working doc for the "connect the AI to the backend" task. Covers: how the
backend calls lea-ai, where the Vault data actually lives today, and the one
product decision that needs the team/manager (privacy vs. survives-device-loss).

**Last updated**: 2026-05-30

---

## 1. The shape of the connection

```
 mobile / web  ──►  lea-be-core  ──►  lea-ai
 (the user)         (Hono/Workers,    (stateless Python Worker:
                     owns auth + DB)    guardrails, persona, Vault intake)
```

- The user **never** talks to lea-ai. Mobile/web talk to lea-be-core; only
  lea-be-core talks to lea-ai. That boundary is the whole reason lea-ai is a
  separate service — it never authenticates a user, only the backend.
- Auth is one shared secret: every lea-ai request carries
  `Authorization: Bearer <SERVICE_TOKEN>`, compared in constant time. In
  lea-be-core that secret is `LEA_AI_SERVICE_TOKEN`; in lea-ai it is
  `SERVICE_TOKEN`. **They must be the same value.**
- lea-ai is **stateless**. It never stores anything. The backend passes in all
  the state (the intake `answers`, the guardrails `session`) and lea-ai returns
  the updated copy for the backend to persist.

### lea-ai endpoints (all require the bearer token except `/health`, `/version`)

| Endpoint | Purpose |
|---|---|
| `POST /v1/vault/intake` | Advance the DVRO intake one step: `(jurisdiction, answers) → next question / done` |
| `POST /v1/lea/process` | Full guardrails turn: returns user-facing text + `tier` + updated `session` |
| `POST /v1/guardrails/classify` | Classification only (no user copy) — for pre-LLM filtering |
| `GET /v1/persona/prompt?persona=&mode=` | Compose a persona system prompt for Gemini |
| `POST /v1/memory/context` | Render the "what you already know about this user" block from `{memories, monitored_device}` — restricted (safety-plan) memories never render; empty string when monitored or nothing renders |
| `POST /v1/memory/extraction-prompt` | `{memories} → {prompt, response_schema}` for lea-be-core's post-session Gemini extraction call |
| `POST /v1/memory/review` | Deterministic safety gate: `{proposed, memories} → {accepted, rejected}` — nothing may be persisted without passing it |

Memory storage, consent (opt-in, default off), and AES-256-GCM encryption at
rest live in lea-be-core (`lea_memories` / `lea_memory_settings`,
`LEA_MEMORY_ENCRYPTION_KEY`, no plaintext fallback). lea-ai stays stateless:
memories ride the request in both directions, exactly like guardrails
`session`. All three endpoints are POST — memory payloads must never ride a
query string into request logs.

User-typed memories (the app's memory screen) are screened through
`POST /v1/memory/review` too — lea-be-core sends a synthetic add op and
refuses the save (fail closed) when lea-ai is unreachable, so the
credential/self-harm/internal-term screens hold on every write path.

**Known gap — `monitored_device`:** lea-ai suppresses all recall when the
flag is true, and lea-be-core's client passes it through, but no detector in
lea-be-core's chat path produces the signal yet, so it is always false
today. Wiring a G-20/monitored-device signal into
`memoryService.getRecallContext(userId, { monitoredDevice })` is tracked
follow-up work; until then the suppression is plumbing, not protection.

---

## 2. What was wired on the backend (this task)

Matched lea-be-core's existing `infra/ai` + FCM client conventions. Nothing is
committed — review the diff before merging.

- **`src/infra/ai/lea-ai-client.ts`** — typed `createLeaAiClient(env)` with one
  method per endpoint. AbortController timeout, transient-aware error mapping to
  `AppError`, and it never logs request/response bodies (crisis-grade content).
- **`src/types/env.ts`** — added `LEA_AI_BASE_URL` + `LEA_AI_SERVICE_TOKEN` to
  `AppBindings` (follows the existing `FCM_*` direct-read pattern; not added to
  the per-request zod schema so a missing value can't 500 every request — the
  client fails loud only when actually called).
- **`wrangler.jsonc`** — `LEA_AI_BASE_URL` dev var (add staging/prod overrides).
- **`.dev.vars.example`** — `LEA_AI_SERVICE_TOKEN` placeholder.

### Using it from a route (example)

```ts
import { createLeaAiClient } from '@/infra/ai/lea-ai-client'

const lea = createLeaAiClient(c.env)
const next = await lea.vaultIntake({
  session_id: intakeSessionId,
  jurisdiction: 'CA',
  current_step: body.current_step,
  answers,                    // the FULL accumulated answers, loaded from OUR DB
})
// persist `answers` (account-bound) BEFORE returning `next` to the client
return c.json(ok({ next }), 200)
```

### Setup checklist

```bash
# In lea-ai: set the shared token
wrangler secret put SERVICE_TOKEN            # (per env)
# In lea-be-core: same value + point at the deployed lea-ai
wrangler secret put LEA_AI_SERVICE_TOKEN     # (per env)
# set LEA_AI_BASE_URL var per env in wrangler.jsonc (staging/production blocks)
```

---

## 3. The data-loss concern — "if the abuser destroys the phone"

**The fear:** the Vault is stored on the device, so a destroyed/confiscated
phone means the survivor loses all their evidence.

**What the code actually does today (good news):** the Vault is **not**
device-local. It already lives server-side, bound to the account:

- `lea_vault_entries` is a Postgres (Supabase) table keyed by `user_id`
  (`drizzle/schemas/lea-vault.ts`). The data is on the server, not the phone.
- Sensitive fields are encrypted with **server-side envelope encryption**
  (`src/core/crypto/dek.ts`, `key-loader.ts`): a master key `LEA_MASTER_KEY`
  (the KEK) wraps a per-user data key (DEK). The wrapped DEK is stored in the DB;
  the KEK lives in the Worker env. On any read the server loads the KEK, fetches
  the user's wrapped DEK, unwraps it, and decrypts.

The consequence is exactly what you want: **the keys live with the account on
the server, not on the device.** Log in on a new phone → the server can decrypt
and serve the Vault. A destroyed device loses nothing that was synced.

This is the same model the big assistants (ChatGPT / Gemini / Claude) use:
data stored server-side per account, encrypted at rest with provider-managed
keys, served to any device after login. The trade-off is that it is **not**
zero-knowledge — the server is technically able to decrypt.

### Authoritative answer (confirmed in `docs/encryption.md` §8.3, §9)

The Vault is actually **two surfaces**, and they have different durability:

| Surface | Encryption | Survives device loss? |
|---|---|---|
| **Vault entries** (structured data: `victim_info`, incidents, etc.) | Server-held envelope (KEK/DEK), account-bound. *Flag `ENCRYPT_VAULT` is not yet flipped, so today they're plaintext-at-rest — still server-side.* | ✅ **Yes** — recoverable on any device after login |
| **Vault files** (uploaded binaries in R2) | Truly zero-knowledge — client-side AES-256 before upload, server has no key | ❌ **No** — if the device-held key is lost, the file is unrecoverable |

So the "stored only on the device" fear is **mostly already solved**: the
*structured* evidence is account-bound and survives. The gap is **uploaded
files** — those are zero-knowledge by design, so a lost device key loses them.

### What's left to verify / decide

1. **Verify (mobile-FE question):** does the mobile app *sync* vault entries to
   `POST /api/lea/vault/entries`, or keep a local-only copy? The backend supports
   durable account-bound storage; if the app isn't pushing to it, that's the gap,
   and the fix is in the mobile app.

2. **Decide (product/legal — needs the manager):** for **vault files**, the
   zero-knowledge design means device-key loss = file loss. If survivors must be
   able to recover *files* on a new device, the team needs a key-recovery path
   (e.g. a user recovery code, or moving file-key custody to the server envelope
   scheme like entries use) — a real privacy-vs-durability safety call.

---

## 4. Persisting the Vault intake (recommended)

Because the goal is "data follows the account, not the device," the intake
`answers` should be persisted **server-side, account-bound** — *not* held only
in the app and replayed each turn. Two options:

- **A. Reuse `lea_vault_entries`** — store the in-progress `answers` map in one
  of the encrypted JSONB columns (e.g. `miscellaneous`) under the user. No
  migration; rides the existing encryption + cross-device recovery for free.
  Simplest path to "it survives device loss." **Recommended to start.**
- **B. A dedicated `lea_vault_intake_sessions` table** — `(id, user_id,
  jurisdiction, answers jsonb, current_step, created_at, updated_at)`. Cleaner
  separation, but needs a Drizzle migration + repo + team review.

Either way the route flow is: load answers from our DB → call
`lea.vaultIntake({...})` → save the merged answers (encrypted, account-bound) →
return the next step. The survivor can then resume intake on any device.

---

## 5. Open items for the manager

1. Privacy model decision (server-recoverable vs zero-knowledge vs hybrid) — §3.2.
2. Confirm the mobile app syncs the Vault to the server (vs local-only) — §3.1.
3. Intake persistence: option A (reuse entries) or B (new table) — §4.
4. Provision `SERVICE_TOKEN` / `LEA_AI_SERVICE_TOKEN` and `LEA_AI_BASE_URL` per
   environment, and the deployed lea-ai URLs.

*Material that would help: the mobile-FE Vault storage code, and any existing
data-retention / privacy policy for the Vault.*
