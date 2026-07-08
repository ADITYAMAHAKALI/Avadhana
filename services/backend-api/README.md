# Backend API

Avadhana's core Backend API service (FastAPI, Python 3.12). Currently a
placeholder skeleton — just a `/` identity endpoint and a `/healthz`
health check, scaffolded for containerization (issue #42). No database
connection or real business logic yet; that lands with later issues
(e.g. #6 Commitment creation flow, #11 Problem schema).

## Build

```
podman build -t avadhana/backend-api -f services/backend-api/Containerfile services/backend-api
```

## Run locally

```
podman run --rm -p 8000:8000 avadhana/backend-api
curl localhost:8000/healthz
```

Or without a container, from this directory: `pip install -e .` then
`uvicorn app.main:app --reload`.

## Dependency injection convention

This service follows an interface/impl DI pattern — apply it to every
future endpoint, not just health/identity:

- `app/interfaces/` — abstract ports, one per file, defined as
  `typing.Protocol` (structural typing, PEP 544). Prefer this over
  `abc.ABC`: no inheritance boilerplate, implementations stay decoupled.
- `app/impl/` — concrete implementations, one per file, named after the
  interface they satisfy (e.g. `impl/health.py` implements
  `interfaces/health.py`'s `HealthCheckPort`). No `abc.ABC` inheritance
  required — Protocols are duck-typed.
- `app/main.py` is the **composition root**. Route handlers depend on the
  *interface* type via `Depends(provider_fn)` and never construct or
  import a concrete `impl` class inline in the handler body. Provider
  functions currently live in `main.py` itself (the service is small);
  move them to `app/dependencies.py` once `main.py` gets crowded with
  real endpoints (commitments, problems, etc.).

When adding a real endpoint (e.g. commitment creation, problem schema),
define its port in `interfaces/`, implement it in `impl/`, and wire it
into the route via a provider — don't write business logic straight into
the route handler.
