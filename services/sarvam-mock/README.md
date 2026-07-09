# SARVAM Mock

Local mock/stub of the SARVAM AI API (FastAPI, Python 3.12 + uvicorn),
scaffolded for GitHub issue #51 (part of epic #39, "Local Kubernetes Dev
Environment (Podman)").

This service exists **only** to stand in for the real SARVAM AI API
(https://docs.sarvam.ai/) during local dev and CI, per `CLAUDE.md`:

> SARVAM AI calls should be stubbable/mockable locally so development and
> CI don't require live API credentials or burn real cost.

It is **not** the real SARVAM client integration. That's a separate, later
effort — issues #19-27 (client integration, summarization, checklist
generation, off-topic detection) — which will build real code that calls
out to either this mock or the live SARVAM API, selected via
`SARVAM_USE_MOCK` (see "Wiring to `.env.example`" below).

No real ML happens here. Every response is canned or deterministically
generated from the request — no external calls, no model inference.

## Endpoints

- `GET /healthz` → `{"status": "ok"}` — liveness/readiness probe.
- `GET /` → basic service identity payload (`service`, `version`).
- `POST /v1/chat/completions` → canned chat-completion response.
- `POST /v1/embeddings` → deterministic fixed-length pseudo-random vector(s).

### `POST /v1/chat/completions`

**Assumed request shape** (best-effort guess, modeled on the general
chat-completions shape SARVAM's docs describe, which is roughly
OpenAI-compatible):

```json
{
  "model": "sarvam-m",
  "messages": [
    {"role": "user", "content": "Summarize this discussion..."}
  ],
  "temperature": 0.7,
  "max_tokens": 512
}
```

Any extra fields (`top_p`, `stream`, etc.) are accepted and ignored rather
than rejected, since real callers may pass SARVAM- or OpenAI-shaped extras
we haven't modeled.

**Response shape** (canned, deterministic — echoes the last `user` message
content back wrapped in a fixed marker string, plus a rough token count
based on word splitting):

```json
{
  "id": "mock-chatcmpl-<uuid>",
  "object": "chat.completion",
  "created": 1735689600,
  "model": "sarvam-m",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "[MOCK RESPONSE] Received 1 message(s), echoing last: Summarize this discussion..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 4, "completion_tokens": 9, "total_tokens": 13}
}
```

This is good enough for local dev/CI to exercise the summarization
(#20), checklist-generation (#21), and off-topic-detection (#22) code
paths end-to-end without hitting real SARVAM or incurring cost.

### `POST /v1/embeddings`

**Assumed request shape:**

```json
{"input": "some text to embed", "model": "sarvam-embed"}
```

`input` may be a single string or a list of strings (batched).

**Response shape** — one embedding per input string, dimensions fixed at
`384` (chosen as a plausible smaller-model embedding size; adjust in
`app/main.py` -> `EMBEDDING_DIMENSIONS` if the real SARVAM embedding model
turns out to use a different size, e.g. 768):

```json
{
  "object": "list",
  "model": "sarvam-embed",
  "data": [
    {"object": "embedding", "index": 0, "embedding": [0.123, -0.456, ...]}
  ],
  "usage": {"prompt_tokens": 4, "total_tokens": 4}
}
```

**Determinism**: each vector is derived from a SHA-256 hash of the input
string (see `_deterministic_vector` in `app/main.py`). The same input text
always produces the same vector, and different inputs produce different
(but not semantically meaningful) vectors. This is intentional — it's
useful for locally exercising similarity / merge-conflict-detection logic
(the AI Coordination Architecture's "Problem Hierarchy & Merging" area in
`CLAUDE.md`) with stable, repeatable fixtures, even though the vectors
carry no real semantic content.

## Assumptions & known gaps (verified against live docs in issue #19)

This mock's `/v1/chat/completions` shape was a guess, later checked against
SARVAM's live API reference and OpenAPI spec (https://docs.sarvam.ai/)
while building the real client (`services/ai-coordinator-worker/impl/sarvam_client.py`,
issue #19). Findings:

- **Chat completions**: `POST /v1/chat/completions` and the
  request/response shape modeled here (`messages`, `choices[0].message`,
  `usage.{prompt,completion}_tokens`) are confirmed close to the real API.
  Real models are `sarvam-30b` and `sarvam-105b` — this mock accepts any
  `model` string, so it doesn't need to know the real values, but the real
  client defaults to `sarvam-105b`.
- **Auth header**: the real API requires `api-subscription-key: <key>`
  (**not** `Authorization: Bearer`). This mock still does not check for or
  require any header at all — anything is accepted, since the point is to
  avoid needing live credentials locally. The real client
  (`impl/sarvam_client.py`) sends the correct header name.
- **Embeddings — NOT REAL**: SARVAM AI's public API has **no embeddings
  endpoint**. `POST /v1/embeddings` here is **mock-only** — it does not
  correspond to anything in the real SARVAM API and the real client does
  not implement it. It's kept as a local fixture for exercising
  similarity/merge-conflict-detection code *shapes* (CLAUDE.md's "Problem
  Hierarchy & Merging"), but that feature will need a different real
  strategy (e.g. deriving similarity via chat-completion prompts with
  structured output, or a different embeddings provider) before it can
  work against production. Don't assume this endpoint has a real backing
  API — it's flagged here so nobody builds production logic against it by
  mistake.
- Real embedding dimensionality (previous open question) is now moot given
  the point above — no real SARVAM embedding model exists to match against.

## Wiring to `.env.example`

The repo root `.env.example` already defines:

```
SARVAM_API_BASE_URL=https://api.sarvam.ai
SARVAM_USE_MOCK=true
```

When `SARVAM_USE_MOCK=true` (the local dev/CI default), the real SARVAM
client (built in issue #19) should point `SARVAM_API_BASE_URL` at this
mock service instead of the real SARVAM API — e.g., once deployed into the
local k8s cluster:

```
SARVAM_API_BASE_URL=http://sarvam-mock.avadhana-dev.svc.cluster.local:8080
```

This service listens on port `8080` inside its container to match that
convention. The actual k8s Service/Deployment manifest that exposes it
under that DNS name is separate scaffolding work (tracked under epic #39,
not part of this issue).

## Build

```
podman build -t avadhana/sarvam-mock:dev -f services/sarvam-mock/Containerfile services/sarvam-mock
```

## Run locally

```
podman run -d --rm -p 18080:8080 --name sarvam-mock avadhana/sarvam-mock:dev

curl localhost:18080/healthz

curl -X POST localhost:18080/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"test","messages":[{"role":"user","content":"hello"}]}'

curl -X POST localhost:18080/v1/embeddings \
  -H 'content-type: application/json' \
  -d '{"input":"hello"}'

podman stop sarvam-mock
```

Or without a container, from this directory: `pip install -e .` then
`uvicorn app.main:app --reload --port 8080`.
