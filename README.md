# Avadhana

अवधान — *undivided, focused attention*

A commitment-first platform for civic and social problem-solving. Avadhana inverts the dominant social media model — optimized for novelty, breadth, and infinite scroll — by forcing depth instead: every user picks **at most three problems** to work on, and once committed, is **locked in for a minimum of 90 days**. Only people who have actually committed a slot to a problem have a voice in it; everyone else can discover, read, and share, but can't dilute the discussion with uninvested opinion.

The friction is the feature.

## Repository contents

| Path | What it is |
|---|---|
| [`Avadhana_Product_Specification.pdf`](Avadhana_Product_Specification.pdf) | The founding product spec (v1.0): thesis, core mechanics (3-slot system, 90-day lock, problem tiers, roles), user flows, governance, open risks |
| [`CLAUDE.md`](CLAUDE.md) | Working architecture notes for AI-assisted development — the AI coordination layer (SARVAM AI), problem split/merge mechanics, moderation & appeals, gamification, deployment guidance |
| [`architecture/`](architecture/) | Draw.io architecture diagrams: system architecture, domain data model, AI coordination flow, problem hierarchy/merge mechanics, user flow, deployment topology, plus detailed per-module ER diagrams — see [`architecture/README.md`](architecture/README.md) |
| [`services/`](services/) | Backend API, Moderation, AI Coordinator Worker, and a local SARVAM AI mock — one Containerfile per service from day one |
| [`infra/k8s/`](infra/k8s/) | Kubernetes manifests for local dev (Postgres, Redis, Backend API, AI Coordinator Worker) |
| [`docs/local-dev.md`](docs/local-dev.md) | Step-by-step local dev setup: Podman install → cluster up → `make dev-up` → verify |

## Core mechanics (from the spec)

- **3 focus slots**: every user can actively work on at most 3 problems at a time. The system blocks a 4th, it doesn't just discourage it.
- **90-day commitment lock**: once a slot is spent on a problem, it can't be freed before day 90 — no early exit. At the checkpoint, the user marks the problem resolved, abandoned, or continues.
- **Problem tiers (S–D)**: every problem is classified by the scale of time/money needed to resolve it, from systemic/national (S) down to individually actionable (D).
- **Roles**: within a committed problem, a user is a Thinker (research/strategy), Actor (on-ground execution), or Backer (funding).
- **Commitment-gated voice**: anyone can discover, read, and share a problem; only committed members can comment, vote, or influence its direction.

## Beyond the original spec

Development notes in `CLAUDE.md` extend the spec with:

- An **AI coordination layer** (SARVAM AI) that summarizes discussion, generates task checklists, and detects off-topic drift — invoked on-demand or on a schedule, with auto-blocking plus a human appeal/calibration loop.
- **Problem split & merge** mechanics, modeled after git branching: a problem can decompose into sub-problems, and overlapping sub-problems can merge back with conflict detection and human resolution.
- **Gamification & reputation**: badges and reputation that reward follow-through (resolving problems, completing 90-day cycles) rather than posting volume — deliberately not a second engagement-farming system.
- A richer **problem-specific feed**: post, comment, like, poll, share, invoke the AI agent, pick up/create/handover tasks, donate, upload assets.

See `CLAUDE.md` for the full detail and open design questions.

## License

CC0 1.0 Universal — see [`LICENSE`](LICENSE).
