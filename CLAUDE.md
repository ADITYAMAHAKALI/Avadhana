# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Avadhana** (अवधान — undivided, focused attention) is a commitment-first social platform for civic and social problem-solving. The core philosophy inverts the attention-maximization model of traditional social media by enforcing *depth over breadth* through hard technical constraints.

**Key reads**: See `Avadhana_Product_Specification.pdf` for the complete specification, including the product thesis, core mechanics, user flows, and open risks.

## Project Tracking

Work is tracked in **GitHub Issues** (`ADITYAMAHAKALI/Avadhana`), not in this file. `TODO.md` mirrors the backlog locally, grouped by epic, for a quick read without leaving the editor. Structure: 7 epics, each with native GitHub sub-issues (real parent/child links, not just checklists):

- **#39 Local Kubernetes Dev Environment (Podman)** — immediate focus, most detailed (15 sub-issues). Start here.
- **#3** Core Commitment System · **#10** Problem Management & Hierarchy · **#18** AI Coordination Layer (SARVAM) · **#28** Problem-Specific Feed & Interactions · **#35** Gamification & Reputation · **#55** Security & Moderation Safety

Before proposing new work or opening new issues, check the relevant epic first — it likely already has a matching sub-issue.

## Core Platform Philosophy

The platform's entire design is built around a single contrarian bet: that focused commitment produces outcomes, while frictionless breadth produces spectators.

Three key constraints that must never be compromised:

1. **The 3-slot system**: Users can actively work on at most 3 problems at any time. The system actively *resists* adding a fourth problem, not gently discourages it. This is the friction that forces prioritization.

2. **The 90-day commitment lock**: Once a slot is spent on a problem, it cannot be freed before day 90—no early exit, no exceptions. This prevents the platform from recreating the shallow drop-in/drop-out behavior it's designed to avoid.

3. **Commitment-gated voice**: Only users who have spent a slot on a problem can comment, vote, or influence its direction. Non-committed users can read and share externally, but their opinion does not carry decision-making weight. This is the anti-dilution mechanic.

When you encounter a feature request or design question that weakens these constraints, the answer is "no." The friction is the feature.

## Key Architectural Decisions

### Problem Tiers (S–D classification)
Problems are classified into five tiers based on estimated time or money to resolution:
- **S**: Systemic / national (policy change, large funding, legal battles)
- **A**: Large regional (city- or districtwide effort)
- **B**: Community-scale (neighborhood or defined local group)
- **C**: Small and local (handful of people)
- **D**: Individually actionable (quick, low-resource wins)

Tier classification is subjective at creation time and can be re-assessed by committed members as information emerges. This will be a source of friction and disputes—plan for lightweight governance around this.

### Roles Within a Problem
Users who commit to a problem choose one of three roles:
- **Thinker**: Research, strategy, framing, proposing approaches. No execution or funding required.
- **Actor**: On-ground execution—filing RTIs, organizing, meeting officials, legal action. No personal funding required.
- **Backer**: Financial contribution. No time commitment to thinking or acting required.

Committed Member is the baseline for having real voice and is automatically granted by spending a slot.

### Feed Model
- **No algorithmic global feed**: Unlike Instagram/X/Reddit, there is no engagement-optimized newsfeed.
- **Personal feed is narrow**: A user's feed shows only the (at most 3) problems they've committed to.
- **Discovery is deliberate**: Users search by topic, location, or tier. Discovery is opt-in and effortful, not passive scrolling.

This is the platform's central design departure from existing social platforms.

### Problem-Specific Feed & Interactions
Each problem has its own feed — not a global timeline. Interactions available within a problem's feed:

- **Post, comment, like, poll** (create/vote): standard discussion primitives, gated by commitment (see Commitment-Gated Voice above)
- **Share**: open to everyone, including non-committed visitors — this is the external-discovery/recruitment mechanic, not a voice mechanic
- **Invoke Agent**: committed members (typically a coordinator/moderator) trigger the AI coordination agent on-demand (see AI Coordination Architecture below)
- **Pick up a task / create a task / handover a task**: task-level actions on top of the AI-generated or manually created checklist; handover reassigns a task to another committed member (with their acceptance)
- **Donate money**: financial contribution tied to the Backer role — **open design question**: does donating require spending a focus slot as a committed Backer, or can any user donate without committing? The spec's strict anti-dilution rule (Section 4.5) says only committed members have voice, but doesn't directly address whether frictionless donation from non-committed supporters undermines or is exempt from that rule. Needs a product decision before building.
- **Upload assets**: photos, documents, evidence relevant to the problem (e.g., RTI response scans, before/after photos) — gated by commitment, same as posting

All of these (except Share) should respect the commitment-gated voice principle by default; treat any exception (like open donation) as something that needs an explicit decision, not an assumption.

## Gamification & Reputation

The platform rewards *follow-through*, not *activity*. This must not become a second incentive system that undermines the commitment mechanic — do not reward posting frequency, streaks, or other breadth/engagement metrics the way mainstream social platforms do.

- **Badges**: awarded for depth-oriented milestones — e.g. first commitment made, a problem marked resolved, a full 90-day cycle completed without abandoning, resolving problems at increasing tiers (a badge for resolving an S-tier problem should mean much more than one for a D-tier problem).
- **Reputation score**: already present on the User entity (see ERD). Should move on resolution/abandonment events, not on likes/comments/post volume.
- **Abandonment is a negative signal, not neutral**: consistent with the spec's existing "reputational cost to walking away" (Section 6.4), abandoned commitments should visibly count against a user's profile and never be counterbalanced by badges for something unrelated (e.g., a "prolific poster" badge would contradict the platform's thesis).
- **Profile**: surfaces current committed problems (up to 3), badge collection, reputation score, and commitment history (resolved/abandoned/continued) — this is the user's public accountability record, not a vanity page.

## Critical Open Issues (From Spec Section 9)

Pay attention to these risks during development. They may require product decisions, not just engineering:

1. **Cold start problem**: Early problems need critical mass in all three roles (Thinker/Actor/Backer) before the 3-slot restriction feels valuable. Plan for how to seed initial problems.

2. **Hard lock frustration**: A user stuck on a stagnant problem for 90 days with zero progress may disengage. The spec notes this may require an "exceptional early-exit path with a real reputational cost"—not easy to build, needs careful design.

3. **Tier subjectivity**: Initial tier estimates will often be wrong. The reclassification process must be lightweight enough to actually get used, or the system breaks down.

4. **Legal liability**: Real-world actions (RTI filings, legal cases) organized through the platform raise jurisdiction-specific legal questions. This needs specialist legal review *before* the Actor role is enabled publicly.

5. **Growth tension**: The entire mechanic depends on restricting behavior that every competing platform maximizes. Go-to-market will need to sell the friction as the value, not hide it. Engineering should resist any pressure to "soften" the constraints for growth.

## AI Coordination Architecture

Avadhana extends the commitment-first spec with an AI coordination layer. The AI is not a replacement for human judgment—it enforces structure and detects drift. Humans make decisions.

### AI Agent Capabilities

- **Invoked on-demand**: A "coordinator" role or moderator can trigger the AI agent to run periodic operations (every 3–6 hours).
- **Summarization**: Digest discussion and progress into concise summaries for committed members.
- **Checklist generation**: Create markdown task checklists from unstructured discussion; identify actionable items.
- **Auto-blocking off-topic**: Detect and block contributions that drift from the problem's scope. Non-negotiable for maintaining focus.
- **Appeal mechanism**: Users can appeal auto-blocks. Appeals feed back into model calibration—this is how you improve detection over time.

### Off-Topic Detection & Moderation

This is critical because the entire platform's value depends on preventing dilution. Auto-blocking is the right call, but:

- You will get false positives early. Plan for rapid iteration and user feedback.
- The appeal process must be frictionless (users should appeal easily) but tracked (appeals data trains the model).
- Consider a two-tier approach: high-confidence blocks are auto-applied; lower-confidence flags go to a human moderator queue for review.
- Each problem may have different scope definitions. The AI needs to learn per-problem, not globally.

### Problem Hierarchy & Merging

Problems are organized as trees (single parent, aiming for max 3 levels: root → child → grandchild), but the structure can expand to a graph if needed.

**Problem Relationships:**
- A problem can have sub-problems (child problems created when a parent problem is decomposed).
- Sub-problems can be merged when they're recognized as overlapping.
- Merging uses git-like methodology: two problem branches, conflict detection, human resolution of overlaps.

**Merge Mechanics:**
- Committed members from both problems are preserved (union, not one or the other).
- Task assignments remain attached to their original problems unless explicitly reassigned.
- Discussion history from both problems is preserved (not deleted).
- Conflicts occur when: same task appears in both problems, or the same person is assigned to conflicting roles.
- Conflict resolution requires human intervention—the system flags, but humans decide.

**Why this matters:** As problems evolve, people discover overlap. The merge mechanism lets the platform adapt without forcing re-commitment or loss of progress.

### Model Stack & Inference

- **LLMs**: SARVAM AI provides language models for summarization, checklist generation, and off-topic detection. Significantly cheaper than OpenAI; latency varies by model choice.
- **Embeddings**: **SARVAM AI has no embeddings endpoint** — verified against SARVAM's live API reference and OpenAPI spec while building the real client (issue #19; see `services/sarvam-mock/README.md` "Assumptions & known gaps" for the full record). Any feature needing real vector embeddings (semantic search, problem similarity for merge-conflict detection, the Solution Marketplace's matching engine below) needs a *different* embeddings provider — see "Solution Marketplace Architecture" below for the concrete decision made there. Don't assume SARVAM covers this.
- **Async architecture**: AI agent runs on a schedule, not blocking user requests. Use a job queue (Celery, Bull, RQ, etc.) for invocations.
- **Cost optimization**: Batch summarization and checklist generation in scheduled jobs, not per-request. Monitor SARVAM API usage and costs closely during early beta.
- **Calibration loop**: Off-topic appeals data → model fine-tuning → improved detection over time. Consider whether fine-tuning or prompt engineering will be sufficient, or if you need custom model training later.
- **Rate limiting & quotas**: Set up strict rate limits on AI agent invocation to avoid runaway costs. Prioritize essential operations (off-topic blocking, summaries) over nice-to-haves (task assignment suggestions).

## Solution Marketplace Architecture

A second product surface, added alongside the civic commitment-first platform: a two-sided B2B/B2G marketplace matching enterprise/government **RFPs** (problem postings with structured requirements) to a repository of **Solutions** (published by providers), using a multi-attribute, multi-embedding ranking engine. Lives in the product as its own top-level tab ("Marketplace"), separate from "Discover" (civic problems).

**This is a deliberate architectural boundary, not an oversight**: the Marketplace is *independent* of the 3-slot / 90-day-lock / commitment-gated-voice mechanic. Posting an RFP, publishing a Solution, or browsing matches never spends a focus slot and is never locked for 90 days — that mechanic exists to force depth over breadth in *personal* civic commitment, and doesn't map onto a company evaluating vendor solutions. Forcing marketplace activity through the civic commitment system would either break the B2B flow or dilute the meaning of a "commitment" for everyone else. The one deliberate bridge between the two systems is the "promote to community" flow below — once an RFP crosses that bridge, the resulting civic Problem plays by the civic rules like any other.

### Two resolution modes per RFP

A buyer publishing an RFP chooses (or enables both) how it gets resolved:

- **Community-driven** (`resolution_mode: community`): the RFP is promoted into a real civic `Problem` (tier, location, category — same as any Problem). From that point on it's fully subject to the standard mechanic: committed members spend focus slots, the 90-day lock applies, only committed members have voice, and any monetization (e.g. Backer donations) is whatever the committed members work out themselves — the Marketplace doesn't dictate terms here. `RFP.promoted_problem_id` links back to the originating RFP for traceability, but the Problem itself doesn't know or care it came from the Marketplace.
- **Marketplace matching** (`resolution_mode: marketplace`): the RFP is scored against the Solution repository by the matching engine (below) and the buyer gets a ranked shortlist of solution providers to engage directly — a one-to-one procurement flow, not a community effort.
- `resolution_mode: both` is allowed — nothing stops a buyer from promoting to the community *and* getting matched to vendors simultaneously.

### Domain model

New entities (additive — none of this touches the existing User/Problem/Commitment schema, aside from the optional `RFP.promoted_problem_id` FK):

- **Organization**: the account type for enterprises/agencies/solution providers — deliberately *not* the same as a civic `User`. A `User` can hold an `OrganizationMembership` (role: admin/member) in one or more Organizations and acts on the Organization's behalf when posting RFPs or Solutions. Carries `rfp_free_quota_used` / `rfp_free_quota_limit` and `billing_status` for the monetization model below.
- **RFP**: `organization_id`, `title`, `description`, budget range, timeline, industry, geography, `resolution_mode`, `visibility` (public / invite-only — some buyers will want a private RFP matched only to select providers), `status`, `promoted_problem_id` (nullable), `is_billable` (set once the posting Organization's free quota is exceeded).
- **RFPRequirement**: structured, per-RFP requirement rows (`attribute_key`, `attribute_value`, `weight`, `is_hard_constraint`). Hard constraints (e.g. a required compliance certification) filter candidates out entirely before ranking; weighted/soft requirements just influence score.
- **Solution**: `organization_id` (the provider), `title`, `description`, `category_tags`, `status`. **Always free to publish** — this is the supply side / lead-gen surface for providers, never gated.
- **SolutionAttribute**: structured attribute rows mirroring `RFPRequirement`'s `attribute_key` vocabulary where possible, so deterministic attribute-match scoring compares like-for-like keys.
- **EmbeddingVector**: `owner_type` (rfp/solution), `owner_id`, `embedding_space` (named — e.g. `summary`, `technical_spec`, `industry_context` — RFP and Solution embeddings are only ever compared *within* the same named space, never across), `vector`, `model_name`, `model_version`, `generated_at`. Insert-only like every other audit-style table in this codebase — a content edit generates a new embedding row, old ones are kept, not overwritten.
- **MatchRun**: one row per matching computation for an RFP (`triggered_by`, `model_versions_used`, `started_at`/`completed_at`, `status`) — immutable audit trail, same pattern as `AIInvocation`.
- **SolutionMatch**: the ranked output of a `MatchRun` — `final_rrf_score`, `rank`, and a `signal_scores`/`signal_ranks` JSON breakdown per signal (attribute-match, each embedding space) so a buyer can see *why* a match happened. Explainability here matters for the same trust reasons moderation transparency matters elsewhere in this codebase.
- **BillingEvent**: immutable log of free-quota consumption and billable postings (`organization_id`, `rfp_id`, `event_type`, `amount`, `occurred_at`). Actual payment processing (Stripe or similar) is explicitly out of scope for the first pass — this just tracks usage/quota state cleanly enough that billing can be wired in later without a schema change.

### Matching engine: multi-attribute, multi-embedding RRF fusion

On RFP publish (or re-publish after an edit), a matching job runs asynchronously (job queue, not blocking the request — same pattern as AI coordination):

1. **Hard-constraint filtering**: cheap SQL filter — drop any Solution that fails an `is_hard_constraint` RFPRequirement before doing any ranking work.
2. **Per-signal scoring** against the remaining candidates:
   - Structured attribute-match score: deterministic, weighted overlap between `RFPRequirement` and `SolutionAttribute` rows — no ML involved.
   - One semantic similarity score per named `embedding_space` (e.g. `summary`, `technical_spec`) — cosine similarity between the RFP's and each candidate Solution's vector in that space.
3. **Rank, don't just score, each signal**: for each signal, sort all candidates and take each Solution's rank (position), not its raw score — this is what makes Reciprocal Rank Fusion work without needing to normalize incompatible scales (a 0-1 cosine similarity and a weighted attribute-overlap score aren't directly comparable, but ranks are).
4. **Fuse via (weighted) RRF**: `score(solution) = Σ_i weight_i · 1/(k + rank_i(solution))` across all signals `i`, with `k` = 60 (the standard RRF constant) unless tuning says otherwise. Store the fused score, the rank, and the full per-signal breakdown on `SolutionMatch`.
5. Surface the top-K ranked matches to the buyer (and optionally notify matched providers).

### Embeddings provider

SARVAM AI has no embeddings endpoint (see "Model Stack & Inference" above) — the matching engine needs a dedicated embeddings source. Decision: bring in a **second** embeddings provider (OpenAI, Cohere, or a self-hosted sentence-transformers model — final pick is an implementation detail, not an architectural one) used *only* for Marketplace embeddings, alongside SARVAM for chat/summarization/off-topic work elsewhere. Store vectors in **Postgres via the `pgvector` extension** rather than standing up a separate vector database — the platform is already on Postgres for everything else, and a second stateful data store is disproportionate cost for a solo-dev project at this stage (same reasoning CLAUDE.md already applies elsewhere against over-engineering the data tier early).

### Monetization

- **Solution publishing: always free.** This is the provider-acquisition/advertising surface — charging providers to list would kill the supply side before it exists.
- **RFP posting: free for an Organization's first 100 RFPs, billed per-RFP after that** (`Organization.rfp_free_quota_used` vs `rfp_free_quota_limit`, default 100). Crossing the threshold sets `RFP.is_billable = true` and logs a `BillingEvent`; the actual payment step (charging a card, invoicing) is a separate, later piece of work — this phase only needs the quota tracking and the paywall gate to exist cleanly.

### Service boundaries (solo-dev pragmatism)

Consistent with how Moderation got its own Containerfile before its logic was actually split out of the Backend API process: the Marketplace's HTTP surface (RFP/Solution/Organization CRUD, browsing matches) starts as new routers/models *inside* `backend-api` — a clearly separate module (`app/models/marketplace/`, `app/routers/marketplace/`, its own migration lineage) rather than a new deployed service, to avoid the operational overhead of yet another service for a solo dev. It's structured so it *can* be extracted into its own service later without a rework, the same promise already made for Moderation. The async matching job reuses the existing Redis/RQ job-queue infrastructure in `ai-coordinator-worker` (same broker, a distinctly-named `marketplace-matching` queue, its own job handler module) rather than standing up a dedicated worker service — architecturally the same shape of problem (background job, calls an external AI API, writes immutable results) as the AI coordination jobs already there.

### Open questions

- **Free-tier abuse**: nothing yet stops an Organization from creating many Organizations to keep resetting the 100-RFP free quota. Needs the same kind of abuse-safeguard thinking already flagged in "Known Unknowns" below for civic problem creation.
- **Cross-Organization visibility**: should a Solution's provider see *which* RFPs it matched against (helps them tune their listing) even for invite-only RFPs, or does invite-only mean fully opaque to non-invited providers?
- **Embedding space vocabulary**: the named embedding spaces above (`summary`, `technical_spec`, `industry_context`) are a starting proposal, not a final schema — the real set should come from looking at actual RFP/Solution content once there's some to look at.
- **RRF weight tuning**: initial per-signal weights (`weight_i`) will be a guess; needs the same kind of calibration-loop thinking already applied to off-topic detection once real match outcomes (did the buyer actually engage the top match?) start coming in.

## Development Stack & Structure

*(To be finalized during setup—this section is a template for initial decisions)*

When setting up the project, document:
- Frontend framework and version
- Backend API design and authentication approach
- Database schema, especially:
  - Commitment lock mechanism (how is the 90-day clock tracked? when does it fire?)
  - Problem hierarchy and relationships (parent/child pointers, merge history)
  - Off-topic moderation queue and appeals
  - AI agent invocation history and results (summaries, checklists, blocks)
- Job queue system for async AI agent invocation (Celery, Bull, RQ, etc.)
- Testing strategy for the core constraints (slot system, commitment lock enforcement) **and** AI coordination (off-topic detection accuracy, merge conflict handling)
- Deployment & environment setup (VPS, serverless, Kubernetes?)
- SARVAM AI integration and rate limiting

### Critical Database Entities
Beyond the spec's problems, roles, and commitments, the AI coordination layer requires:

- **Moderation events**: Auto-blocked messages, block reason, confidence score, user appeal, appeal outcome, date.
- **Problem relationships**: Parent-child links, merge history (which problems were merged into which, when, by whom).
- **AI coordination history**: Invocation timestamp, type (summarize/checklist/block), SARVAM API usage, results stored.
- **Task assignments**: Who is assigned to what task, their role in the problem, task status, due date (if any).
- **Problem lineage**: Track when a problem was split or merged, maintain immutable history for auditing.

All moderation actions and AI operations should be immutable—never update or delete, only insert new records. This is essential for auditing and model calibration.

## Common Development Tasks

### Running Tests
*(Add command once test suite is set up)*

### Building & Deploying
*(Add command once build system is established)*

### Code Style & Linting
*(Document linting rules, pre-commit hooks, etc.)*

### Invoking the AI Coordinator
- Triggered by: Moderator/coordinator role via UI, or scheduled job (every 3–6 hours)
- Outputs: Problem summary, task checklist, flagged off-topic contributions
- Enqueue job in [queue system] for async processing
- Results written to database; notify committed members

### Handling Off-Topic Blocks & Appeals
- AI flags off-topic contribution with confidence score
- High-confidence blocks: auto-applied, user notified, appeal link provided
- Lower-confidence flags: sent to moderation queue for human review
- Appeals: captured in database with reasoning; fed back into model calibration pipeline

## Key Features & Their Constraints

When implementing features, keep these in mind:

### Problem Creation
- User proposes problem statement, scope, location, and initial tier
- Problem becomes searchable immediately
- Tier can be re-assessed by committed members with threshold agreement
- Tier re-assessment must be lightweight (governance-wise) or it won't get used

### Commitment & Slot Management
- Committing to a problem spends one of three slots and starts the 90-day clock
- The system must *block* a fourth commitment if all three slots are occupied (error message, not soft discouragement)
- Track the 90-day lock expiration date; when it fires, prompt the user to mark resolved, mark abandoned, or continue
- Mark abandoned must be visible on the user's profile (reputational cost is the point)

### Commitment-Gated Discussion
- Distinguish between "committed members" (who can comment/vote/influence) and "readers/followers" (who can read and share externally)
- Committed members can always see and participate in a problem's discussion
- Non-members should see the problem's progress but not have a "comment" or "vote" button—explain why on hover/UX

### External Discovery & Visitor Flow
- Share links should allow non-members to read a problem's progress
- When a visitor tries to comment, redirect to commitment + role selection
- Committing via a share link consumes a slot and locks the user into the 90-day commitment

### Problem Decomposition & Composition
- **Split**: A committed member can propose splitting a problem into sub-problems when scope becomes too broad. Requires threshold agreement from committed members.
- **Merge**: Two sub-problems can be merged when recognized as overlapping. Uses git-like conflict detection; overlaps require human resolution (same task in both, conflicting role assignments, etc.).
- **Hierarchy preservation**: Merging two children can create or update their parent relationship. Aim for 3-level max depth; allow graph-like structure if necessary.

### AI-Generated Task Management
- AI generates markdown checklists from problem discussion and progress updates
- Checklists are suggestions, not commands—committed members review and refine
- AI can propose task assignments based on person's expressed expertise and available bandwidth (inferred from their other committed problems)
- Task assignments are separate from roles (a Thinker and an Actor can both be assigned to the same task; Backers typically do not take task assignments unless explicitly needed for execution)

## Testing & Verification Strategy

Focus testing on the constraints:

- **Slot system**: Verify that users cannot add a fourth problem while all three slots are full. Test that the error message is clear.
- **90-day lock**: Verify that the commitment cannot be freed before 90 days. Test the checkpoint flow (resolve/abandon/continue).
- **Commitment-gated voice**: Verify that non-committed readers cannot comment/vote but committed members can. Check that abandoned status shows on profiles.
- **Tier disputes**: When the feature is built, test that tier reclassification requires threshold agreement and is lightweight to propose.

**AI Coordination Testing:**
- **Off-topic detection accuracy**: Build a test suite of on-topic and off-topic comments per problem type. Measure precision/recall; acceptable false-positive rate is low (you can afford to upset committed members, not to suppress them).
- **Appeal flow**: Verify that users can appeal blocks easily and appeals are tracked for model retraining.
- **Problem merging**: Test conflict detection (same task, overlapping role assignments). Verify committed members from both problems are merged correctly. Test that discussion history is preserved.
- **Checklist generation**: Spot-check that AI checklists are accurate and actionable. Test with real problem discussions, not synthetic data.
- **Task assignment suggestions**: Verify that proposed assignments consider current commitment load and person's past performance.

## Local Development Environment

**Immediate focus (before any cloud/VPS work): all services run locally on Kubernetes via Podman.** The VPS/Docker Compose deployment described later in this doc and in `architecture/06-deployment-infrastructure.drawio.png` is the eventual production target, not where development starts — track this work under the "Local Kubernetes Dev Environment (Podman)" epic on GitHub.

- Each service (Backend API, AI Coordinator Worker, Moderation) gets its own Containerfile from day one, even before Moderation is actually split out of the Backend API process — this keeps the image-build path consistent and avoids a rework later.
- Postgres and Redis run as local k8s Deployments/StatefulSets for dev — not representative of the production data tier (which should move to a managed DB service per the scale path).
- SARVAM AI calls should be stubbable/mockable locally so development and CI don't require live API credentials or burn real cost.
- Secrets locally come from k8s Secrets sourced from an uncommitted `.env` — same non-negotiable rule as production (see Security section below), just a lighter-weight mechanism for a single dev machine.

## Security & Solo-Dev Architecture

Because you're building solo initially and security is non-negotiable:

### API Key & Secret Management
- SARVAM API keys must never be committed. Use environment variables or secrets management (e.g., `.env` with `.gitignore`, or cloud secrets manager).
- Rotate keys regularly and monitor for unauthorized usage.
- Log all AI API calls (for auditing and cost tracking). Do not log the full request/response if it contains user data.

### Auto-Blocking & Moderation Safety
- **Audit logging**: Every auto-block, appeal, and appeal outcome must be logged with: blocked message, confidence score, reason, appeal outcome, any model retraining triggered.
- **Appeal fraud**: Monitor for patterns where users systematically appeal valid blocks to poison model calibration. Throttle appeals per user.
- **Transparency**: Committed members can view moderation logs for their problem (which messages were blocked, why). This builds trust.
- **Human override**: Moderators (initially you) can always override auto-blocks and reverse decisions. This is critical during beta.

### Database & Scaling for Solo Dev
- Use migrations (Alembic, Flyway, etc.) from day one. As the solo dev, you'll be the only one writing migrations, but the discipline saves you later.
- Problem hierarchy (parent/child relationships) and merge history should be immutable—never delete old relationships, only mark them inactive. This is essential for auditing problem evolution.
- Job queue (Celery, Bull, RQ) keeps AI invocations from blocking the main app. Start with in-process for development; move to a separate worker process or service as load increases.

### Solo Dev → Team Transition
- Document everything: how to invoke the AI coordinator, how to review off-topic appeals, how to handle merge conflicts.
- Code should be structured so that adding a second developer doesn't require a major refactor. Avoid "magic" or clever solutions; prefer clarity.

## Known Unknowns

The specification deliberately leaves these open; address them as you build:

1. **Abuse safeguards**: What prevents low-effort problem creation or coordinated brigading of role structure? Plan content moderation policies. (AI auto-blocking for off-topic is one safeguard; may need additional rate limiting or reputation scoring.)
2. **Legal disclaimers**: RTI filings and legal cases organized through Actors need appropriate disclaimers and legal review before going public.
3. **Resolution verification**: The spec says marking "resolved" should require more than one user's claim. Design a lightweight verification process among committed members.
4. **Tier rubric concreteness**: The tier classifications (S–D) need concrete, testable terms (estimated hours / estimated funding ranges) so classification is consistent across problems.
5. **Model drift**: How do you detect when SARVAM model updates degrade off-topic detection accuracy? Monitor appeal rates and false-positive patterns.

## References

- **Specification**: `Avadhana_Product_Specification.pdf` (Sections 4–7 detail core mechanics; Section 9 lists open risks)
- **Success Metrics** (Section 8): % of committed problems resolved by day 90, committed-to-observer ratio per problem, role distribution, slot re-commitment rate
- **Next Steps** (Section 10): Validate core mechanic with 5–10 real local problems before full platform build; draft concrete tier rubric; get legal review on Actor role; design core screens

## What This Platform Is Not

- A social network optimized for engagement or growth-at-all-costs
- A discussion forum where anyone can weigh in on any topic
- A petition platform (Change.org comparison in Section 3.1)
- A place for casual awareness without execution infrastructure

It's a disciplined problem-solving workspace where commitment is the price of entry and the mechanism for maintaining focus.
