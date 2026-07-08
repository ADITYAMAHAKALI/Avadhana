# Postgres (local dev)

Local-dev-only Kubernetes manifests for PostgreSQL, per issue #45. Single-replica
`StatefulSet` (`postgres:16-alpine`) with a small `PersistentVolumeClaim` (2Gi) and a
`ClusterIP` `Service` named `postgres` in the `avadhana-dev` namespace, listening on
5432. This is deliberately not HA, not tuned, and not representative of the
production data tier (see CLAUDE.md "Local Development Environment" — production
should move to a managed DB service).

Service DNS name (matches `.env.example`):
`postgres.avadhana-dev.svc.cluster.local:5432`

## Prerequisite: secret must exist first

The StatefulSet reads `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` from a
Secret named `avadhana-postgres-secret` — it is **not** defined in this directory and
must exist in the `avadhana-dev` namespace before applying, or the pod will fail to
start (`CreateContainerConfigError`).

Create/update it from your local `.env` (see `.env.example` if you don't have one
yet) using the shared secrets script from issue #50:

```bash
./infra/k8s/scripts/create-secrets.sh
```

This also creates/updates `avadhana-app-secret` (used by backend-api and
ai-coordinator-worker). See `infra/k8s/scripts/README.md` for full details,
including the idempotent apply pattern and the path to a real secrets manager
for production. The script is safe to re-run any time you change `.env`.

## Apply

```bash
kubectl apply -f infra/k8s/postgres/
```

## Verify

```bash
kubectl get pods -n avadhana-dev -l app=postgres
kubectl wait --for=condition=Ready pod -l app=postgres -n avadhana-dev --timeout=90s
kubectl exec -n avadhana-dev -it postgres-0 -- pg_isready -U avadhana -d avadhana
```

## Tear down / recreate

```bash
kubectl delete -f infra/k8s/postgres/
# PVC is not deleted by the above (StatefulSet volumeClaimTemplates persist by
# design) — delete it explicitly if you want a truly clean slate:
kubectl delete pvc -n avadhana-dev -l app=postgres
```
