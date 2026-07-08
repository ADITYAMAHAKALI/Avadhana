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

Proper local secrets tooling (sourcing values from a gitignored `.env`) is tracked in
issue #50 ("Local secrets management") and isn't built yet. Until then, create the
secret manually, using the same values as `.env.example` / your local `.env`:

```bash
kubectl create secret generic avadhana-postgres-secret \
  --namespace avadhana-dev \
  --from-literal=POSTGRES_DB=avadhana \
  --from-literal=POSTGRES_USER=avadhana \
  --from-literal=POSTGRES_PASSWORD=changeme
```

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
