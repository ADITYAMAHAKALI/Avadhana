#!/usr/bin/env bash
#
# create-secrets.sh — create/update local k8s Secrets from the repo-root .env
#
# Part of issue #50 ("Local secrets management"). See
# infra/k8s/scripts/README.md for full documentation.
#
# What this does:
#   Reads .env at the repo root (gitignored, never committed) and applies two
#   Kubernetes Secrets into the avadhana-dev namespace:
#     - avadhana-postgres-secret  (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
#     - avadhana-app-secret       (DATABASE_URL, REDIS_URL, JWT_SECRET, SARVAM_API_KEY)
#
# Safe to re-run: uses `kubectl create --dry-run=client -o yaml | kubectl apply -f -`
# so existing secrets are updated in place (not duplicated, no errors on rerun).
# Re-run after editing .env to push changed values into the cluster.
#
# Usage:
#   ./infra/k8s/scripts/create-secrets.sh
#
# Prerequisite: kubectl's current context must already point at the local dev
# cluster (kind-avadhana-dev). This script does not switch context for you —
# it just uses whatever `kubectl config current-context` currently resolves
# to, and aborts if it doesn't look like the expected dev context. Run
# `kubectl config use-context kind-avadhana-dev` first if needed.
#
# This script intentionally never echoes secret values to stdout/logs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

NAMESPACE="${KUBE_NAMESPACE:-avadhana-dev}"
EXPECTED_CONTEXT="kind-avadhana-dev"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found." >&2
  echo "Copy .env.example to .env and fill in local values first:" >&2
  echo "  cp .env.example .env" >&2
  exit 1
fi

CURRENT_CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
if [[ "${CURRENT_CONTEXT}" != "${EXPECTED_CONTEXT}" ]]; then
  echo "ERROR: kubectl current-context is '${CURRENT_CONTEXT:-<none>}', expected '${EXPECTED_CONTEXT}'." >&2
  echo "Run: kubectl config use-context ${EXPECTED_CONTEXT}" >&2
  exit 1
fi

# Load .env into the environment of this script only (subshell-safe, does not
# leak into the caller's shell). Lines are simple KEY=VALUE pairs, no export
# needed beyond this process.
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# SARVAM_API_KEY is allowed to be blank when SARVAM_USE_MOCK=true (the default
# for local dev/CI, see .env.example and issue #51) — no live API key is
# needed to run against the mock. All other vars below are always required.
required_vars=(
  POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
  DATABASE_URL REDIS_URL JWT_SECRET
)
missing=()
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("${var}")
  fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: the following variables are missing or empty in ${ENV_FILE}:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi
if [[ -z "${SARVAM_API_KEY:-}" ]]; then
  if [[ "${SARVAM_USE_MOCK:-}" == "true" ]]; then
    echo "NOTE: SARVAM_API_KEY is blank (SARVAM_USE_MOCK=true) — proceeding with an empty value for that key." >&2
  else
    echo "ERROR: SARVAM_API_KEY is blank but SARVAM_USE_MOCK is not 'true'. Set a real key or set SARVAM_USE_MOCK=true." >&2
    exit 1
  fi
fi

echo "Applying avadhana-postgres-secret to namespace '${NAMESPACE}'..."
kubectl create secret generic avadhana-postgres-secret \
  --namespace "${NAMESPACE}" \
  --from-literal=POSTGRES_DB="${POSTGRES_DB}" \
  --from-literal=POSTGRES_USER="${POSTGRES_USER}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
echo "  done (keys: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)"

echo "Applying avadhana-app-secret to namespace '${NAMESPACE}'..."
kubectl create secret generic avadhana-app-secret \
  --namespace "${NAMESPACE}" \
  --from-literal=DATABASE_URL="${DATABASE_URL}" \
  --from-literal=REDIS_URL="${REDIS_URL}" \
  --from-literal=JWT_SECRET="${JWT_SECRET}" \
  --from-literal=SARVAM_API_KEY="${SARVAM_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
echo "  done (keys: DATABASE_URL, REDIS_URL, JWT_SECRET, SARVAM_API_KEY)"

echo "Secrets applied successfully. No secret values were printed."
