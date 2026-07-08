# Moderation Service

Minimal FastAPI skeleton for Avadhana's Moderation service (Python 3.12 + uvicorn).
No real off-topic detection or auto-block logic yet — that lands in later issues
(#23-26). For now this only exposes `GET /` (service identity) and `GET /healthz`
(liveness/readiness probe).

## Build

```
podman build -t avadhana/moderation -f services/moderation/Containerfile services/moderation
```

## Run locally

```
podman run -d --rm -p 8001:8001 --name moderation avadhana/moderation
curl localhost:8001/healthz
```

## Why this is already a standalone service

Moderation logic currently lives conceptually alongside the Backend API and
hasn't been split out into its own runtime yet. Per `CLAUDE.md`: each service
(Backend API, AI Coordinator Worker, Moderation) gets its own Containerfile
from day one, even before Moderation is actually split out of the Backend API
process — this keeps the image-build path consistent across services and
avoids a rework later when the real split happens.

## Interface/impl dependency injection convention

This service follows the same DI convention as the other backend services:

- `app/interfaces/` — abstract ports, one `typing.Protocol` per file (e.g.
  `HealthCheckPort` in `app/interfaces/health.py`). Protocol (structural
  typing) is preferred over `abc.ABC` — it avoids inheritance boilerplate
  and keeps implementations decoupled/duck-typed.
- `app/impl/` — concrete implementations of those ports, one class per file
  (e.g. `StaticHealthCheckService` in `app/impl/health.py`).
- `app/dependencies.py` — provider functions (e.g. `get_health_service()`)
  that construct and return a concrete impl, typed as the interface.
- `app/main.py` is the composition root: route handlers take the interface
  type via `Depends(provider_function)` and never import or construct a
  concrete implementation inline.

When real moderation logic (off-topic detection, auto-block, appeals —
issues #23-26) lands, add a new interface + impl + provider following this
same pattern rather than writing logic directly inside a route handler.
