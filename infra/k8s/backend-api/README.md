# Backend API — Kubernetes manifests (local dev)

Deployment + Service + ConfigMap for the Backend API (`services/backend-api/`),
wired to the Postgres/Redis service DNS names via `avadhana-app-secret`
(see `infra/k8s/scripts/create-secrets.sh`). Local dev only — see CLAUDE.md
"Local Development Environment" section.

## What's here

- `configmap.yaml` — `avadhana-backend-api-config`: non-secret env vars
  (`ENVIRONMENT`, `LOG_LEVEL`, `SARVAM_API_BASE_URL`, `SARVAM_USE_MOCK`,
  `BACKEND_API_PORT`), matching `.env.example`.
- `deployment.yaml` — `backend-api`, 1 replica, image `avadhana/backend-api:dev`,
  env sourced via `envFrom` from both the ConfigMap above and the
  `avadhana-app-secret` Secret (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`,
  `SARVAM_API_KEY`). Readiness/liveness probes hit `GET /healthz` on :8000.
- `service.yaml` — ClusterIP Service `backend-api`, port 8000 → targetPort 8000.
  Other services resolve this at
  `backend-api.avadhana-dev.svc.cluster.local:8000`.

## Prerequisites

- `avadhana-app-secret` and `avadhana-postgres-secret` already exist in the
  `avadhana-dev` namespace (created by `infra/k8s/scripts/create-secrets.sh`
  from the repo-root `.env`).
- Postgres and Redis Deployments/StatefulSets are already applied and Running
  (`infra/k8s/postgres/`, `infra/k8s/redis/`).

## Build + load the image into kind (podman provider)

kind clusters can't pull images from nowhere — a locally-built image not
published to any registry has to be loaded into the kind node directly. This
cluster uses the **podman** provider, which has a naming gotcha with
`kind load docker-image`: see below.

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman

# 1. Build the image
podman build -t avadhana/backend-api:dev -f services/backend-api/Containerfile services/backend-api/
```

### `kind load docker-image` does NOT work directly here

Podman tags locally-built images with an implicit `localhost/` prefix
(`localhost/avadhana/backend-api:dev`), but `kind load docker-image
avadhana/backend-api:dev` looks for the image under the exact name given and
fails with:

```
ERROR: image: "avadhana/backend-api:dev" not present locally
```

### Working method: tag explicitly, then `kind load image-archive`

The Deployment references the image as `avadhana/backend-api:dev`, which
kubelet resolves against the implicit default registry, i.e.
`docker.io/avadhana/backend-api:dev`. If you `kind load image-archive` a tar
that only contains the `localhost/...` tag, the pod will fail with
`ImagePullBackOff` / `pull access denied ... docker.io/avadhana/backend-api`
even though `crictl images` on the node shows the image present — the tag on
the node just doesn't match what kubelet is asking for.

Fix: retag to the `docker.io/...` form **before** saving the archive, so the
tag baked into the tar matches what the Deployment/kubelet expect:

```bash
# 2. Retag so the image name matches what the Deployment references
#    (avadhana/backend-api:dev -> resolves to docker.io/avadhana/backend-api:dev)
podman tag localhost/avadhana/backend-api:dev docker.io/avadhana/backend-api:dev

# 3. Save to an archive and load it into the kind node
podman save docker.io/avadhana/backend-api:dev -o /tmp/backend-api.tar
kind load image-archive /tmp/backend-api.tar --name avadhana-dev

# 4. Clean up the archive (optional)
rm -f /tmp/backend-api.tar
```

Verify the image landed with the right tag on the node:

```bash
podman exec avadhana-dev-control-plane crictl images | grep backend-api
# expect: docker.io/avadhana/backend-api   dev   <id>   197MB
```

`imagePullPolicy: IfNotPresent` in `deployment.yaml` means kubelet will use
this node-local image and never attempt an actual registry pull, as long as
the tag matches exactly.

**If you rebuild the image**, repeat steps 1–3 (retag + resave + reload) and
then `kubectl delete pod -l app=backend-api -n avadhana-dev` to force the
Deployment to pick up the new image (same tag, so it won't restart on its
own).

## Apply

```bash
kubectl apply -f infra/k8s/backend-api/
```

## Verify

```bash
# Pod becomes Ready
kubectl wait --for=condition=Ready pod -l app=backend-api -n avadhana-dev --timeout=90s

# No crash / env errors in logs
kubectl logs -l app=backend-api -n avadhana-dev

# End-to-end from inside the cluster, via the Service DNS name
kubectl run debug-curl --image=curlimages/curl:latest --restart=Never -n avadhana-dev \
  --command -- curl -s -w '\nHTTP_STATUS:%{http_code}\n' \
  http://backend-api.avadhana-dev.svc.cluster.local:8000/healthz
kubectl logs debug-curl -n avadhana-dev
kubectl delete pod debug-curl -n avadhana-dev
# expect: {"status":"ok"}  HTTP_STATUS:200
```

Confirmed working as of this writing: pod `1/1 Running`, readiness/liveness
probes passing, `GET /healthz` returns `{"status":"ok"}` (HTTP 200) when
curled from a throwaway in-cluster pod via the Service DNS name.
