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

## Assumptions & known gaps (read before building the real client)

This mock's schema is a **best-effort guess**, not a verified match against
live SARVAM AI docs — the environment this was built in did not have
access to fetch/verify https://docs.sarvam.ai/ against a live API. Before
or while building the real client in issue #19:

- Confirm the actual SARVAM endpoint paths (`/v1/chat/completions` and
  `/v1/embeddings` are guesses based on the common OpenAI-compatible
  convention SARVAM's docs are described as following).
- Confirm exact request/response field names — SARVAM may use different
  field names, nested differently, or return extra required fields.
- Confirm authentication header shape (this mock does not check for or
  require any `Authorization` / API key header at all — anything is
  accepted, since the point is to avoid needing live credentials locally).
- Confirm real embedding dimensionality per model (this mock hardcodes 384).
- If the real API's shape drifts meaningfully from this mock, update
  `app/main.py` here to match, so local dev/CI stays representative of
  production behavior.

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
