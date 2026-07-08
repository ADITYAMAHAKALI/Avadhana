# k8s scripts (local dev)

Helper scripts for the local `kind`-via-Podman dev cluster (`kind-avadhana-dev`
context, `avadhana-dev` namespace). See CLAUDE.md "Local Development
Environment" and the "Local Kubernetes Dev Environment (Podman)" epic (#39).

## `create-secrets.sh` — local secrets management (issue #50)

Reads the repo-root `.env` (gitignored, never committed — copy it from
`.env.example` if you don't have one yet) and creates/updates two Kubernetes
Secrets in the `avadhana-dev` namespace:

| Secret                      | Keys                                                              | Consumed by |
|------------------------------|--------------------------------------------------------------------|-------------|
| `avadhana-postgres-secret`  | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`               | `infra/k8s/postgres/statefulset.yaml` |
| `avadhana-app-secret`       | `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `SARVAM_API_KEY`       | backend-api, ai-coordinator-worker (issues #47, #48) |

Non-secret config (`SARVAM_API_BASE_URL`, `SARVAM_USE_MOCK`, `ENVIRONMENT`,
`LOG_LEVEL`, port numbers, etc.) is **not** included here — that belongs in a
ConfigMap, built alongside the backend-api / ai-coordinator-worker Deployment
manifests (#47, #48), not in this script.

### Usage

```bash
# One-time: make sure kubectl points at the local dev cluster
kubectl config use-context kind-avadhana-dev

# Create or update both secrets from .env
./infra/k8s/scripts/create-secrets.sh
```

Safe to re-run any time you edit `.env` — it uses the standard
`kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -`
pattern, so existing secrets are updated in place rather than duplicated or
erroring out. Applying updated `avadhana-postgres-secret` values does not
restart the `postgres-0` pod by itself (env vars from Secrets aren't
hot-reloaded into a running container) — restart the pod manually if you
change Postgres credentials and need the running container to pick them up.

The script:
- Fails fast with a clear message if `.env` is missing, or if `kubectl`'s
  current context isn't `kind-avadhana-dev` (it does not switch contexts for
  you, to avoid accidentally writing secrets into the wrong cluster).
- Never prints secret values to stdout/logs.

### Prerequisite

`kubectl` must already be pointed at the `kind-avadhana-dev` context. The
script checks this and aborts with instructions if it isn't.

## Path to production secrets management

The `.env` → k8s Secret flow above is **local-dev-only** and intentionally
lightweight: plaintext values on a single developer's machine, base64-encoded
(not encrypted) once inside the cluster. This is not adequate for production
and should not be extended to any shared or cloud environment as-is. Options
to evaluate when production deployment work starts (see CLAUDE.md
"Development Stack & Structure" / eventual VPS or cloud target):

- **[sealed-secrets](https://github.com/bitnami-labs/sealed-secrets)** (Bitnami Labs) — encrypts secrets client-side so the encrypted `SealedSecret` CRD can be committed to git safely; a cluster-side controller decrypts on apply. Good fit if we stay Kubernetes-native in production.
- **[SOPS](https://github.com/getsops/sops)** (age or PGP-encrypted secrets in git) — encrypts individual values in a YAML/JSON file that's safe to commit; decrypted at deploy time via a key held outside the repo. More general-purpose than sealed-secrets (not k8s-specific).
- **Cloud KMS-backed secrets manager** — AWS Secrets Manager, GCP Secret Manager, or equivalent, depending on where the production VPS/cloud deployment lands (see `architecture/06-deployment-infrastructure.drawio.png`). Secrets live outside git entirely and are pulled at runtime or injected via a CSI driver / init container.

No decision has been made yet — this is a placeholder for a follow-up issue,
not an implementation.
