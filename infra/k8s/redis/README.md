# Redis (local dev)

Local-dev-only Kubernetes manifests for Redis, per issue #46. Single-replica
`Deployment` (`redis:7-alpine`) and a `ClusterIP` `Service` named `redis` in the
`avadhana-dev` namespace, listening on 6379. Used both as a general cache and as the
job queue broker for AI Coordinator Worker invocations (see `.env.example`
`REDIS_URL`).

Service DNS name (matches `.env.example`):
`redis.avadhana-dev.svc.cluster.local:6379`

## No auth, no persistence — intentional for local dev

- **No password / auth**: kept simple since the cluster isn't exposed outside the
  local kind network. Do not carry this into production.
- **No PersistentVolumeClaim**: local dev job-queue/cache data doesn't need to
  survive pod restarts — it's fine (and arguably preferable) for Redis to come back
  empty after a restart or `kubectl delete`/re-apply, since that matches how the dev
  environment is meant to be torn down and recreated freely. If a future workflow
  needs durable local queue state across restarts, add a PVC + `--appendonly yes`
  then; not needed today.

## Apply

```bash
kubectl apply -f infra/k8s/redis/
```

## Verify

```bash
kubectl get pods -n avadhana-dev -l app=redis
kubectl wait --for=condition=Ready pod -l app=redis -n avadhana-dev --timeout=90s
kubectl exec -n avadhana-dev -it deploy/redis -- redis-cli ping
```

## Tear down / recreate

```bash
kubectl delete -f infra/k8s/redis/
```
