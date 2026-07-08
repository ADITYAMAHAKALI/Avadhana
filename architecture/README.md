# Avadhana — Architecture Diagrams

All diagrams are authored in [draw.io](https://www.drawio.com/) (`.drawio` XML). Each PNG is exported with the diagram embedded, so opening the `.png` directly in draw.io desktop recovers the full editable diagram — you don't need to hunt for the source file just to make a small edit.

## Main diagram set

`avadhana-architecture.drawio` is a single multi-page file. Open it in draw.io desktop and use the page tabs at the bottom, or view the individual page exports below without opening draw.io:

| # | Page | Export | Covers |
|---|------|--------|--------|
| 1 | High-Level System Architecture | [01-system-architecture.drawio.png](01-system-architecture.drawio.png) | Client → Gateway → Backend/Moderation services → Job Queue → AI Coordinator Worker → Postgres/Redis, SARVAM AI as an external dependency, trust boundary |
| 2 | Domain Data Model (ERD) | [02-domain-erd.drawio.png](02-domain-erd.drawio.png) | High-level overview ERD spanning all modules: User, FocusSlot, Commitment, Problem, ProblemRelationship, ModerationEvent, AIInvocation, TaskAssignment |
| 3 | AI Coordination Agent Flow | [03-ai-coordination-flow.drawio.png](03-ai-coordination-flow.drawio.png) | End-to-end flowchart: trigger → job queue → SARVAM calls → summarize/checklist/off-topic-score → auto-block vs. flag-for-review → appeal → calibration |
| 4 | Problem Hierarchy — Split & Merge | [04-problem-hierarchy-merge.drawio.png](04-problem-hierarchy-merge.drawio.png) | Git-graph-style visualization of splitting a problem into sub-problems and merging them back, including conflict detection and resolution |
| 5 | User Flow (Sequence) | [05-user-flow-sequence.drawio.png](05-user-flow-sequence.drawio.png) | Onboarding → problem search → commitment (spends a slot, starts the 90-day clock) → checkpoint prompt at day 90 |
| 6 | Deployment — Solo-Dev Scalable Setup | [06-deployment-infrastructure.drawio.png](06-deployment-infrastructure.drawio.png) | Single-VPS Docker Compose topology, CI/CD, secrets, logging, and the scale-out path as the team grows |

## Per-module ER diagrams (`modules/`)

More detailed, field-level ER diagrams than the high-level overview in page 2 — one per bounded module. Entities defined in another module appear as dashed "external" stub tables (id only) so each diagram stays readable on its own.

| # | Module | Export | Entities |
|---|--------|--------|----------|
| 1 | User & Commitment | [modules/01-user-commitment.drawio.png](modules/01-user-commitment.drawio.png) | User, FocusSlot, Commitment, CommitmentCheckpoint |
| 2 | Problem & Hierarchy | [modules/02-problem-hierarchy.drawio.png](modules/02-problem-hierarchy.drawio.png) | Problem, ProblemRelationship, TierReclassification, MergeConflict |
| 3 | Moderation & Appeals | [modules/03-moderation-appeals.drawio.png](modules/03-moderation-appeals.drawio.png) | ModerationEvent, Appeal, ModerationCalibrationRecord, ProblemScopeDefinition |
| 4 | AI Coordination & Task Assignment | [modules/04-ai-coordination-tasks.drawio.png](modules/04-ai-coordination-tasks.drawio.png) | AIInvocation, ProblemSummary, ChecklistItem, TaskAssignment |

## Editing

- Install draw.io desktop: `brew install --cask drawio` (macOS) or see [releases](https://github.com/jgraph/drawio-desktop/releases).
- Open `avadhana-architecture.drawio` for the main set, or any file under `modules/` for a single-module ERD.
- After editing, re-export with the diagram embedded so the PNG stays self-contained:
  ```
  drawio -x -f png -e -s 1.5 --page-index <n> -o <name>.drawio.png avadhana-architecture.drawio
  ```
  (`--page-index` is 1-based; omit it for single-page module files.)

## Status

These diagrams reflect the architecture as scoped in `CLAUDE.md` as of 2026-07-08, including the AI coordination layer (SARVAM AI), problem split/merge mechanics, and moderation/appeals flow. They do **not** yet cover the gamification (badges/reputation) or problem-feed interaction set (polls, task handover, donations, asset uploads) added afterward — see `CLAUDE.md` for that scope pending its own diagram pass.
