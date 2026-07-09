# One-command local dev bring-up/tear-down for the Kubernetes-via-Podman
# environment (see docs/dev-environment/podman-and-k8s.md and GitHub epic #39).
#
# Quick start:
#   cp .env.example .env   # first time only, then fill in real values
#   make dev-up
#   kubectl port-forward svc/backend-api 8000:8000 -n avadhana-dev
#   make dev-down           # tear down when finished

CLUSTER_NAME := avadhana-dev
NAMESPACE := avadhana-dev
KIND_CONTEXT := kind-$(CLUSTER_NAME)
export KIND_EXPERIMENTAL_PROVIDER := podman

# Services with a k8s Deployment. sarvam-mock joined this list once issue
# #19 (real SARVAM AI client) landed — ai-coordinator-worker now calls it
# in-cluster whenever SARVAM_USE_MOCK=true.
DEPLOYED_SERVICES := backend-api ai-coordinator-worker sarvam-mock
# All buildable services, deployed or not — kept in sync with .github/workflows/ci.yaml's build matrix.
ALL_SERVICES := backend-api moderation ai-coordinator-worker sarvam-mock

.PHONY: dev-up dev-down dev-status dev-logs cluster-up secrets build-images load-images apply-data apply-apps

dev-up: cluster-up secrets apply-data build-images load-images apply-apps
	@echo ""
	@echo "Avadhana local dev stack is up in namespace $(NAMESPACE)."
	@echo "Reach the Backend API with:"
	@echo "  kubectl port-forward svc/backend-api 8000:8000 -n $(NAMESPACE)"
	@echo "Then: curl http://localhost:8000/healthz"

dev-down:
	kind delete cluster --name $(CLUSTER_NAME)

dev-status:
	kubectl get pods,svc -n $(NAMESPACE)

# Usage: make dev-logs SERVICE=backend-api
dev-logs:
	kubectl logs -l app=$(SERVICE) -n $(NAMESPACE) --tail=100 -f

cluster-up:
	@if ! kind get clusters 2>/dev/null | grep -qx '$(CLUSTER_NAME)'; then \
		kind create cluster --name $(CLUSTER_NAME); \
	else \
		echo "kind cluster $(CLUSTER_NAME) already exists, skipping create"; \
	fi
	kubectl config use-context $(KIND_CONTEXT)
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl config set-context $(KIND_CONTEXT) --namespace=$(NAMESPACE)

# Secrets must exist before Postgres starts (it reads them at container
# start), so this runs before apply-data, and again is safe to re-run any
# time .env changes (idempotent).
secrets:
	./infra/k8s/scripts/create-secrets.sh

apply-data:
	kubectl apply -f infra/k8s/postgres/
	kubectl apply -f infra/k8s/redis/
	kubectl rollout status statefulset/postgres -n $(NAMESPACE) --timeout=120s
	kubectl rollout status deployment/redis -n $(NAMESPACE) --timeout=90s

build-images:
	@for svc in $(ALL_SERVICES); do \
		echo "Building $$svc..."; \
		podman build -t avadhana/$$svc:dev -f services/$$svc/Containerfile services/$$svc/ || exit 1; \
	done

# kind can't pull these images from anywhere (they're local-only), so they
# have to be loaded into the kind node directly. Two podman-specific
# gotchas discovered the hard way, both worth keeping here:
#   1. `kind load docker-image` fails outright against podman — podman's
#      local store tags images as `localhost/...`, which kind's docker-image
#      loader doesn't handle. Use `kind load image-archive` instead.
#   2. That alone still isn't enough: containerd on the kind node resolves
#      a Deployment's bare `avadhana/<svc>:dev` image ref against
#      `docker.io/...`, not `localhost/...`. Without re-tagging to
#      `docker.io/avadhana/<svc>:dev` before `podman save`, pods come up
#      ImagePullBackOff even though the image is sitting right there in
#      the node's containerd cache.
load-images:
	@for svc in $(DEPLOYED_SERVICES); do \
		echo "Loading $$svc into kind..."; \
		podman tag localhost/avadhana/$$svc:dev docker.io/avadhana/$$svc:dev; \
		podman save docker.io/avadhana/$$svc:dev -o /tmp/avadhana-$$svc.tar; \
		kind load image-archive /tmp/avadhana-$$svc.tar --name $(CLUSTER_NAME); \
		rm -f /tmp/avadhana-$$svc.tar; \
	done

apply-apps:
	kubectl apply -f infra/k8s/backend-api/
	kubectl apply -f infra/k8s/ai-coordinator-worker/
	kubectl apply -f infra/k8s/sarvam-mock/
	kubectl rollout status deployment/backend-api -n $(NAMESPACE) --timeout=120s
	kubectl rollout status deployment/ai-coordinator-worker -n $(NAMESPACE) --timeout=120s
	kubectl rollout status deployment/sarvam-mock -n $(NAMESPACE) --timeout=120s
