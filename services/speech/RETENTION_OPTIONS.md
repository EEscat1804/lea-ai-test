# Data Retention & PII Handling — Options (decision needed)

**Status: unresolved. Do not deploy this service against real call audio until
someone with product/legal authority picks one of these (or a variant) and
signs off.** This document exists to surface the decision, not make it —
nothing below has been implemented.

## Why this matters

This service may process caller audio from a domestic-violence support
context. That audio, and its transcript, can contain some of the most
sensitive information a person shares — names, locations, threats, abuse
details. Retention policy here isn't a normal engineering tradeoff; a wrong
default can put a caller at real physical risk (e.g. if an abuser gains
access to logs or a backup). This needs a decision from whoever owns privacy/
legal/product for LEA, not an engineering default.

## Current behavior (as shipped, unchanged by this document)

No persistence exists today. Audio is decoded in memory, sent to the model,
and discarded when the request completes — nothing is written to disk, no
database, no object storage. This is true of the application code. It is
**not** automatically true of the surrounding infrastructure:

- Uvicorn's default access logs record the request line (path, status, size)
  but not the file body — verified safe today, but worth re-checking if
  logging config ever changes.
- Any future APM/error-tracking integration (Sentry, Datadog, etc.) could
  capture request bodies or local variables (including audio bytes or
  transcript text) in a crash report unless explicitly configured not to.
  **Whichever option below is chosen, this needs an explicit "never capture
  request bodies or transcript content" rule wherever monitoring is added.**
- Cloud load balancer / reverse proxy logs upstream of this service are
  outside this service's control and outside the scope of this document.

## Options

### Option A — No persistence, anywhere, ever (current de facto behavior, made explicit policy)
- Audio and transcript exist only for the duration of a single request; never
  written to disk, database, or long-term logs, by policy as well as by code.
- **Pros:** simplest to reason about; smallest breach surface; no retention
  infrastructure to secure or audit; no data-deletion obligations later.
- **Cons:** zero ability to investigate a bad transcription, debug a missed
  guardrail trigger, or support any future audit/QA/training need. If a
  caller is harmed and a transcript existed for even a moment, there's no
  record to review afterward — that cuts both ways (nothing to subpoena,
  but also nothing to learn from).

### Option B — Ephemeral, in-memory only, short TTL (e.g. minutes)
- Transcript (not raw audio) held in memory (not disk) for a short window —
  e.g. to let a caller-facing UI show "did I say that right?" or let a human
  reviewer glance at the current session — then dropped, never durably
  stored.
- **Pros:** enables near-term debugging/UX without creating a durable data
  store; smaller breach surface than persistent storage (nothing survives a
  process restart).
- **Cons:** still a live copy of sensitive data in process memory for that
  window — needs its own access controls; "in-memory only" is easy to get
  wrong (e.g. accidentally logged, accidentally swapped to disk); doesn't
  support any retrospective audit past the TTL.

### Option C — Encrypted at rest, explicit TTL, audited access
- Transcript and/or audio stored encrypted, with a defined retention window
  (e.g. 30/90 days) and automatic deletion after, access logged and
  restricted to a named role.
- **Pros:** supports real operational needs — QA on guardrail accuracy,
  incident review, compliance evidence if ever required.
- **Cons:** by far the largest undertaking — encryption key management,
  access control, deletion-on-schedule infrastructure, breach-notification
  exposure while data exists, and likely a legal/compliance review of its
  own (data processing agreements, state-specific DV-survivor data
  protections, etc.). This is not something to stand up quickly.

## Recommendation framing (not a decision)

If forced to guess at intent: a support product handling DV-related
disclosures should probably default toward **Option A or B** unless there is
a concrete, named operational need (e.g. a specific QA program) that
justifies Option C's overhead and risk. But this is exactly the kind of
judgment call that should be made explicitly by product/legal, not inferred
by whoever happened to write the transcription service.

## What to do with this document

Route to whoever owns privacy/legal decisions for LEA. Once a decision is
made, update this file with the chosen option and open a follow-up
implementation ticket — this document should not go stale as "the open
question" once it's actually been answered.
