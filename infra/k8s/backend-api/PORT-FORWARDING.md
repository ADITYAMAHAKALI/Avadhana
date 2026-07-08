# Local routing (issue #49)

Chosen approach: **`kubectl port-forward`**, not an nginx-ingress controller.

Why: the local `kind` cluster (see `docs/dev-environment/podman-and-k8s.md`) was created with kind's default node config, which has no `extraPortMappings` for an ingress controller to bind to on the host. Retrofitting that means recreating the cluster. `kubectl port-forward` needs zero cluster changes, works today, and issue #49 explicitly allows it as the local-dev alternative to nginx-ingress. Revisit nginx-ingress if/when routing multiple services under one host/port matters (e.g. testing something ingress-specific like path rewrites or TLS termination) — not needed for solo local dev.

## Usage

```
kubectl port-forward svc/backend-api 8000:8000 -n avadhana-dev
```

Leave that running in a terminal, then hit the API from the host at `http://localhost:8000` (e.g. `curl http://localhost:8000/healthz`). Ctrl-C to stop.

Same pattern works for any other Service in the namespace, e.g. Postgres for a local `psql` session:

```
kubectl port-forward svc/postgres 5432:5432 -n avadhana-dev
```

## Verified

```
$ kubectl port-forward svc/backend-api 18000:8000 -n avadhana-dev &
$ curl localhost:18000/healthz
{"status":"ok"}
$ curl localhost:18000/
{"service":"avadhana-backend-api","version":"0.1.0"}
```
