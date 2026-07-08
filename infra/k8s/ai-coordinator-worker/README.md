# AI Coordinator Worker (local dev)

Local-dev-only Kubernetes manifests for the AI Coordinator Worker, per issue
#48 (epic #39). Deploys the RQ (Redis Queue) worker skeleton from
`services/ai-coordinator-worker/` as a background `Deployment` in the
`avadhana-dev` namespace — **not** an HTTP service, so there is no
`service.yaml` here (see "No Service — intentional" below).

## Files

- `configmap.yaml` — `avadhana-ai-coordinator-worker-config`: non-secret env
  vars (`ENVIRONMENT`, `LOG_LEVEL`, `SARVAM_API_BASE_URL`, `SARVAM_USE_MOCK`,
  `AI_COORDINATOR_INVOCATION_INTERVAL_HOURS`), values matched to
  `.env.example`.
- `deployment.yaml` — `ai-coordinator-worker` Deployment, 1 replica by
  default, image `avadhana/ai-coordinator-worker:dev`. Env vars are wired in
  via `envFrom` from both the ConfigMap above and the `avadhana-app-secret`
  Secret (for `REDIS_URL`, plus `DATABASE_URL` / `JWT_SECRET` /
  `SARVAM_API_KEY` for future job types — see
  `infra/k8s/scripts/create-secrets.sh`).

## No Service — intentional

This worker is a **background consumer**, not a network-addressable
process: it opens an outbound connection to Redis and blocks listening for
jobs on the `ai-coordinator` queue. It exposes no port and answers no
requests, so there is deliberately no `service.yaml` in this directory —
nothing should ever need to reach this pod by DNS/ClusterIP. If that ever
changes (e.g. a future health-check HTTP endpoint), add a Service then.

## No liveness/readiness probe — why

The container has no HTTP server, so an HTTP probe is out. A basic `exec`
liveness probe (e.g. `pgrep python`) was considered and skipped: it can only
prove the process didn't crash outright, not that the RQ worker is actually
still connected to Redis and processing jobs — so it would add
container-restart churn without real signal. `kubectl logs` (see
Verify below) and RQ's own job/queue state in Redis are the real signal for
now. Revisit once the worker exposes a genuine health check alongside the
real SARVAM job types (issues #19-27).

## Build the image

```bash
podman build -t avadhana/ai-coordinator-worker:dev \
  -f services/ai-coordinator-worker/Containerfile services/ai-coordinator-worker/
```

## Load the image into the kind cluster

kind clusters can't pull `avadhana/ai-coordinator-worker:dev` from anywhere
— it only exists in the local Podman image store — so it must be loaded
into the kind node directly.

**What actually worked in this environment:** `kind load docker-image`
failed (`image: "avadhana/ai-coordinator-worker:dev" not present locally`)
because Podman stores locally-built images with an implicit `localhost/`
repository prefix (`localhost/avadhana/ai-coordinator-worker:dev`), which
`kind load docker-image` does not resolve against the unqualified name. The
working path was `kind load image-archive`, **with one extra gotcha**: the
image must be re-tagged to the fully-qualified `docker.io/...` form *before*
saving, otherwise the pod fails to start with `ImagePullBackOff` /
`insufficient_scope: authorization failed` — because `deployment.yaml`
references the image as `avadhana/ai-coordinator-worker:dev` (no registry),
and containerd on the kind node normalizes that unqualified name to
`docker.io/avadhana/ai-coordinator-worker:dev` when deciding whether it
already has a matching image cached, not `localhost/...`. If the archive
was saved under the `localhost/` tag, the names don't match and kubelet
falls through to a real registry pull attempt (which fails, since
`avadhana/ai-coordinator-worker` doesn't exist on Docker Hub).

Full working sequence:

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman

# Build (produces localhost/avadhana/ai-coordinator-worker:dev in Podman's store)
podman build -t avadhana/ai-coordinator-worker:dev \
  -f services/ai-coordinator-worker/Containerfile services/ai-coordinator-worker/

# Re-tag to the fully-qualified docker.io form the Deployment's unqualified
# image ref resolves to on the kind node — this step is required, not optional.
podman tag localhost/avadhana/ai-coordinator-worker:dev docker.io/avadhana/ai-coordinator-worker:dev

# Save + load via image-archive (kind load docker-image does not work with
# the podman provider in this environment — see above)
podman save docker.io/avadhana/ai-coordinator-worker:dev -o /tmp/ai-coordinator-worker.tar
kind load image-archive /tmp/ai-coordinator-worker.tar --name avadhana-dev
```

Verify the node actually has it before applying manifests:

```bash
podman exec avadhana-dev-control-plane crictl images | grep ai-coordinator-worker
# expect a line starting with: docker.io/avadhana/ai-coordinator-worker   dev
```

If you rebuild the image after a code change, repeat the tag → save → load
steps and then `kubectl delete pod -n avadhana-dev -l app=ai-coordinator-worker`
so the Deployment picks up the new image (`imagePullPolicy: IfNotPresent`
means it won't refresh on its own).

## Apply

```bash
kubectl apply -f infra/k8s/ai-coordinator-worker/
```

## Verify

```bash
kubectl get pods -n avadhana-dev -l app=ai-coordinator-worker
kubectl wait --for=condition=Ready pod -l app=ai-coordinator-worker -n avadhana-dev --timeout=90s
kubectl logs -n avadhana-dev -l app=ai-coordinator-worker
```

Expected log output (confirms Redis connection + queue subscription, no
crash/env errors):

```
Worker rq:worker:<id> started with PID 1, version 1.16.2
Subscribing to channel rq:pubsub:<id>
*** Listening on ai-coordinator...
Cleaning registries for queue: ai-coordinator
```

### End-to-end job verification

The worker pod already has `redis`/`rq` installed (same image), so you can
exec into it directly to enqueue a real job against the live Redis instead
of standing up a separate debug pod:

```bash
POD=$(kubectl get pods -n avadhana-dev -l app=ai-coordinator-worker -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n avadhana-dev "$POD" -- python -c "
from redis import Redis
from rq import Queue
import os
conn = Redis.from_url(os.environ['REDIS_URL'])
q = Queue('ai-coordinator', connection=conn)
job = q.enqueue('worker.ping_job')
print(job.id)
"
```

Then check the job finished and the worker logged it:

```bash
kubectl exec -n avadhana-dev "$POD" -- python -c "
from redis import Redis
from rq.job import Job
import os
conn = Redis.from_url(os.environ['REDIS_URL'])
job = Job.fetch('<job-id-from-above>', connection=conn)
print(job.get_status(), job.return_value())
"
kubectl logs -n avadhana-dev "$POD" --tail=20
```

Confirmed locally: job status `finished`, result `pong`, and the worker pod
log showed both `worker.ping_job() (<job-id>)` and `Job OK (<job-id>)`
lines.

## Scale path: mapping `replicas` to CLAUDE.md's cost/throughput guidance

CLAUDE.md's "AI Coordination Architecture" section describes this worker as
running on a schedule (every 3–6 hours) or on-demand, deliberately
**async and non-blocking** — the point of the job-queue architecture is that
invocation volume can grow independently of the request path. The scaling
knob for that growth is `replicas` in `deployment.yaml`:

- **Manual, local-dev scaling** (what this issue covers): bump the replica
  count, either by editing `deployment.yaml` (`replicas: 1` → `replicas: N`)
  and re-applying, or directly:

  ```bash
  kubectl scale deployment/ai-coordinator-worker --replicas=3 -n avadhana-dev
  ```

- **Why this is safe/idiomatic**: RQ workers are stateless job consumers —
  each replica independently connects to the same Redis instance and calls
  `BLPOP`-style blocking pops against the shared `ai-coordinator` queue.
  Redis guarantees a given job is only handed to one worker, so N replicas
  naturally **load-balance** queued jobs across themselves with zero extra
  coordination code, no leader election, and no risk of double-processing a
  job under normal operation. This is the standard RQ horizontal-scaling
  pattern, not something specific to this codebase.

- **How this maps to CLAUDE.md's cost guidance**: the "Rate limiting &
  quotas" / "Cost optimization" guidance in CLAUDE.md is about capping
  *SARVAM API spend*, not worker replica count — those are orthogonal knobs.
  Adding replicas increases *throughput* (how fast the queue drains under
  load), while rate limits and batching (once real SARVAM-backed jobs land,
  issues #19-27) cap *spend per job*. Scale replicas to keep the queue from
  backing up; keep rate limits in place regardless of replica count so a
  traffic spike can't translate directly into an uncapped SARVAM bill.

- **Local dev default is 1 replica** because there's no real job volume yet
  (only the placeholder `ping_job`) — this keeps local resource usage low.
  Production/staging environments would set this based on observed queue
  depth (e.g. via `rq info` or a queue-depth metric) once real SARVAM job
  types exist.

## Tear down / recreate

```bash
kubectl delete -f infra/k8s/ai-coordinator-worker/
```
