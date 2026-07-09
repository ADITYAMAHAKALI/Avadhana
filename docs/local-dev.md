# Local Development Setup

Step-by-step guide to running the full Avadhana stack locally on Kubernetes via Podman. See `docs/dev-environment/podman-and-k8s.md` for the rationale behind these tool choices (why kind over minikube/Podman Desktop's built-in Kubernetes, why `kubectl port-forward` over an ingress controller, etc.) — this doc is the "how", that one is the "why".

## 1. Install Podman

Install via [Podman Desktop](https://podman-desktop.io/) or Homebrew (`brew install podman`), then start a machine:

```
podman machine init      # first time only
podman machine start
podman machine list      # confirm it's "Currently running"
```

## 2. Install kind

```
brew install kind
```

kind talks to Docker by default. Point it at Podman instead by exporting this in every shell you run `kind`/`make` commands from (or add it to your shell profile):

```
export KIND_EXPERIMENTAL_PROVIDER=podman
```

## 3. Configure environment variables

```
cp .env.example .env
```

Fill in real values as needed. For a first run, the defaults are enough — `SARVAM_USE_MOCK=true` means no live SARVAM AI credentials are required. `.env` is gitignored; never commit it.

## 4. Bring up the full stack

```
make dev-up
```

This one command (see the root `Makefile`, issue #52):
1. Creates the `avadhana-dev` kind cluster if it doesn't already exist, and sets your kubectl context to it.
2. Creates the `avadhana-dev` namespace.
3. Generates k8s Secrets (`avadhana-postgres-secret`, `avadhana-app-secret`) from your local `.env` via `infra/k8s/scripts/create-secrets.sh` — safe to re-run any time you edit `.env`.
4. Applies the Postgres and Redis manifests and waits for both to be ready.
5. Builds every service's container image with Podman (`backend-api`, `moderation`, `ai-coordinator-worker`, `sarvam-mock`).
6. Loads the images that have k8s manifests (`backend-api`, `ai-coordinator-worker`, `sarvam-mock`) into the kind node — `moderation` still builds and runs standalone for now (no manifest yet; it isn't split out of the backend yet).
7. Applies the Backend API, AI Coordinator Worker, and SARVAM mock manifests, force-restarts all three Deployments (needed because they reference a static `:dev` image tag — `kubectl apply` alone won't roll pods onto a freshly built image if the manifest text didn't change), and waits for all three to be ready.
8. Runs `alembic upgrade head` inside the `backend-api` pod (`make migrate`) so the schema actually exists — the container ships Alembic specifically for this, but nothing ran it automatically before this step existed. Safe to re-run any time; Alembic no-ops once the schema is current.

Takes a few minutes on first run (image builds, cluster bootstrap); subsequent runs are much faster since Podman caches image layers and `kind create cluster` / `kubectl apply` are no-ops if the cluster/resources already exist.

## 5. Verify

```
make dev-status
```

Expect five pods `Running`: `postgres-0`, `redis-...`, `backend-api-...`, `ai-coordinator-worker-...`, `sarvam-mock-...`.

Reach the Backend API from your host:

```
kubectl port-forward svc/backend-api 8000:8000 -n avadhana-dev
```

In another terminal:

```
curl http://localhost:8000/healthz
# {"status":"ok"}
```

See `infra/k8s/backend-api/PORT-FORWARDING.md` for why `port-forward` was chosen over an ingress controller for local dev (issue #49), and how to use the same pattern for Postgres/Redis if you need a direct local connection (e.g. `psql`, `redis-cli`).

## 6. Everyday commands

```
make dev-status                       # pod/service overview
make dev-logs SERVICE=backend-api     # tail logs for a given service (label: app=<name>)
make dev-down                         # delete the kind cluster entirely
```

After editing a service's code, rebuild and reload just that image, then restart its deployment:

```
podman build -t avadhana/backend-api:dev -f services/backend-api/Containerfile services/backend-api/
podman tag localhost/avadhana/backend-api:dev docker.io/avadhana/backend-api:dev
podman save docker.io/avadhana/backend-api:dev -o /tmp/avadhana-backend-api.tar
kind load image-archive /tmp/avadhana-backend-api.tar --name avadhana-dev
kubectl rollout restart deployment/backend-api -n avadhana-dev
kubectl rollout status deployment/backend-api -n avadhana-dev --timeout=120s
make migrate   # only needed if you added/changed a model + migration
```

(The retag-before-save step matters — see the comment above `load-images` in the `Makefile` for why: Podman's local image store tags builds as `localhost/...`, but the kind node's containerd resolves a bare `avadhana/<service>:dev` image ref against `docker.io/...`. Skip it and you'll get `ImagePullBackOff`.)

Just re-running `make dev-up` does all of this for every service in one shot (rebuild, reload, restart, migrate) — the manual sequence above is only worth it when you want to iterate on a single service without waiting on the others.

## 7. CI

Every PR and push to `main` runs `.github/workflows/ci.yaml` (issue #53): builds all four service Containerfiles and validates every manifest under `infra/k8s/**/*.yaml` with `kubeconform`. Run the same checks locally before pushing if you want a head start:

```
podman build -f services/backend-api/Containerfile services/backend-api/
kubeconform -strict -summary infra/k8s/**/*.yaml
```

## Troubleshooting

- **`make dev-up` hangs on a `rollout status` step** — check `make dev-status` and `make dev-logs SERVICE=<name>` for the stuck pod. A common cause is a stale/missing Secret — re-run `./infra/k8s/scripts/create-secrets.sh` after confirming `.env` has all required values.
- **`ImagePullBackOff` on a freshly built image** — you likely skipped the `docker.io/` retag step; see section 6 above.
- **`kind`/`podman` command not found or can't connect** — confirm `podman machine list` shows a running machine, and that `KIND_EXPERIMENTAL_PROVIDER=podman` is exported in your current shell.
- **`/healthz` returns 200 but every real endpoint 500s with `relation "users" does not exist` (or similar)** — the schema was never migrated. `make dev-up` runs `make migrate` automatically now, but if you're driving the individual Make targets by hand (or exec'd into an old pod), run `make migrate` yourself.
