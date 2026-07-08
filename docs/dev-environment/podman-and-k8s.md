# Podman + local Kubernetes (issue #40)

## Podman

Already installed via Podman Desktop (`/opt/podman/bin/podman`), not Homebrew. Machine:

```
podman machine list
NAME                    VM TYPE     CPUS  MEMORY    DISK SIZE
podman-machine-default  libkrun     4     3.725GiB  46GiB
```

Started/managed via Podman Desktop or `podman machine start podman-machine-default`.

## Local Kubernetes distribution: kind (Podman provider)

Chosen over Podman Desktop's built-in Kubernetes extension and minikube because:
- Fully CLI-scriptable — required for the one-command bring-up (#52) and CI (#53).
- Plain kubectl/manifest workflow, matching the raw k8s manifests planned in #45-48 (no extra abstraction layer).
- No GUI dependency for cluster lifecycle, even though Podman Desktop remains available for inspection.

Installed via `brew install kind`.

To run kind against Podman instead of Docker, set:

```
export KIND_EXPERIMENTAL_PROVIDER=podman
```

Verified working:

```
$ KIND_EXPERIMENTAL_PROVIDER=podman kind get clusters
using podman due to KIND_EXPERIMENTAL_PROVIDER
enabling experimental podman provider
No kind clusters found.
```

## Cluster (issue #41)

Created with:

```
export KIND_EXPERIMENTAL_PROVIDER=podman
kind create cluster --name avadhana-dev
```

This sets the kubectl context to `kind-avadhana-dev`. The `avadhana-dev` namespace was created and set as the context's default:

```
kubectl create namespace avadhana-dev
kubectl config set-context kind-avadhana-dev --namespace=avadhana-dev
```

Verify anytime with:

```
kubectl cluster-info --context kind-avadhana-dev
kubectl get nodes
kubectl config current-context   # should print kind-avadhana-dev
```

To tear down: `KIND_EXPERIMENTAL_PROVIDER=podman kind delete cluster --name avadhana-dev`.

## Environment variables

`.env.example` at the repo root documents all local dev env vars (Postgres, Redis, Backend API, AI Coordinator Worker, Moderation service, SARVAM AI). Copy it to `.env` (gitignored, never commit) and fill in real values — SARVAM defaults to `SARVAM_USE_MOCK=true` so local dev/CI never needs live credentials (issue #51).
