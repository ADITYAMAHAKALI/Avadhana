#!/usr/bin/env bash
#
# port-forward-watchdog.sh — keep `kubectl port-forward svc/backend-api` alive
#
# Why this exists: local dev pods restart on their own from time to time
# (e.g. the Podman VM cycling while idle), and every pod restart silently
# kills any running `kubectl port-forward` — the process just dies with no
# obvious signal beyond the frontend's next request failing with
# ECONNREFUSED. This loop checks the forwarded port every few seconds and
# restarts `kubectl port-forward` whenever it's down, so you don't have to
# notice the failure and restart it by hand.
#
# Usage:
#   ./infra/k8s/scripts/port-forward-watchdog.sh
#   ./infra/k8s/scripts/port-forward-watchdog.sh 8001 backend-api 8000  # custom local port
#
# Run this in its own terminal (or background it) and leave it running for
# the duration of your local dev session. Ctrl-C stops it (and the
# port-forward it's managing).

set -euo pipefail

LOCAL_PORT="${1:-8000}"
SERVICE="${2:-backend-api}"
REMOTE_PORT="${3:-8000}"
NAMESPACE="${KUBE_NAMESPACE:-avadhana-dev}"

PF_PID=""

cleanup() {
  if [[ -n "$PF_PID" ]] && kill -0 "$PF_PID" 2>/dev/null; then
    kill "$PF_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

is_forward_alive() {
  # A dead port-forward means nothing is listening on LOCAL_PORT at all —
  # curl fails to even connect (exit 7), which is distinct from the backend
  # itself returning an error status (which would mean the forward is fine).
  curl -sS -o /dev/null --max-time 2 "http://localhost:${LOCAL_PORT}/healthz"
}

start_forward() {
  echo "[watchdog] starting: kubectl port-forward svc/${SERVICE} ${LOCAL_PORT}:${REMOTE_PORT} -n ${NAMESPACE}"
  kubectl port-forward "svc/${SERVICE}" "${LOCAL_PORT}:${REMOTE_PORT}" -n "${NAMESPACE}" \
    >/tmp/avadhana-port-forward-"${SERVICE}".log 2>&1 &
  PF_PID=$!
}

start_forward

while true; do
  if ! kill -0 "$PF_PID" 2>/dev/null || ! is_forward_alive; then
    echo "[watchdog] port-forward to ${SERVICE} is down, restarting..."
    cleanup
    start_forward
    sleep 2 # give kubectl a moment to establish before the next health check
  fi
  sleep 5
done
