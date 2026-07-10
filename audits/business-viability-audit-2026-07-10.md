# Avadhana — Business Viability Audit (2026-07-10)

Scope: business/GTM/monetization/legal viability of the civic commitment platform and the
Solution Marketplace, as actually built today — not as designed in CLAUDE.md. Findings below
are grounded in the current repo state (`TODO.md`, `git log`, `gh issue list`, and direct reads
of `services/backend-api/app/models/marketplace/*`, `services/backend-api/app/services/*`, and
`services/web/src/*`) as of commit `6188c8e` on `main`.

## Current Status

**Civic core loop (3-slot / 90-day lock / commitment-gated voice): functionally built, not yet
piloted.** TODO.md's "SLC v1 Release Plan" items 1–13 are checked off (auth, FocusSlot
enforcement, commitment creation, checkpoint flow, commitment-gated middleware, audit logging,
problem CRUD/search, feed post/comment/like, share, reputation, profile, VPS deploy scaffolding).
Spot-checked in code: `checkpoint_service.py` and `errors.py` confirm the 90-day lock has no
bypass path anywhere — `LockActiveError` is raised unconditionally, and the module docstring
explicitly warns future contributors not to add a moderator override without a product decision
first. Abandonment is visibly surfaced on the profile (`ProfilePage.tsx`: "N abandonment(s) on
record") and warned about pre-commit (`CommitModal.tsx`: "Abandoning before the minimum counts
against your record"). This is a real, working implementation of the platform's central
differentiator, not just a design doc.

However: **item 14 — "recruit the 5–10 real local problems the spec calls for and pilot" — is
explicitly unchecked and explicitly marked "not started, not an engineering task."** No pilot has
happened. There is no metrics page, no seed-problem tracking issue, no case study, nothing in
`docs/` or GitHub issues that tracks outreach to real Thinkers/Actors/Backers. The entire
"Marketing & Launch" section of TODO.md (landing copy, launch blog post, pilot seeding, metrics
page, HN/PH launch) is unchecked and explicitly "not yet tracked as individual GitHub issues" —
i.e., it exists only as a TODO.md wishlist, with zero GitHub issues filed for any of it. This
means the platform has a working core mechanic and literally zero real-world usage evidence.

**GitHub issue tracking has a bookkeeping gap worth flagging on its own**: TODO.md marks issues
#4–#9, #11, #13, #29, #30, #37, #38, #56, #57, #59, #61 as done (`[x]`), but `gh issue list`
shows all of them still `OPEN` on GitHub (only the 15 sub-issues under epic #39, local-dev, are
actually closed). This isn't a business-viability issue per se, but it means anyone auditing
progress via `gh issue list` alone (rather than TODO.md) would undercount completed work — worth
a hygiene pass (closing finished issues) before this becomes confusing at higher issue volume.

**Solution Marketplace: schema-only, zero business logic, merged same day as this audit.**
`git log` shows the marketplace foundation (`Organization`, `RFP`, `Solution` models + CRUD
routers, commit `41e6cc1`) landed on 2026-07-10 — today. Only 3 of 11 marketplace sub-issues
(#63, #64, #65) have any code; the entire matching engine (#66 attribute scoring, #67 embeddings,
#68 RRF fusion, #69 results UI), the community-promotion bridge (#70), the billing paywall (#71),
the frontend tab (#72), and abuse safeguards (#73) are unbuilt. Read directly:

- `services/backend-api/app/models/marketplace/organization.py`: `rfp_free_quota_used`,
  `rfp_free_quota_limit` (default 100), and `billing_status` (hardcoded to `"active"`, only enum
  value that exists) are plain columns with an explicit docstring: *"no quota-enforcement or
  paywall logic is wired up yet."*
- `services/backend-api/app/models/marketplace/rfp.py`: `is_billable` is a `Boolean` column that
  defaults to `False` with *"no code path sets it True yet"* per its own docstring.
- `services/backend-api/app/services/marketplace_service.py` docstring states outright: *"no
  quota/billing check in `create_rfp` either."*
- `grep` for `stripe`, `payment_intent`, `checkout.session` across the entire repo: zero hits.

So the "first 100 RFPs free, then billed" model is **100% unenforced today** — any Organization
can post unlimited RFPs at zero cost, and there is no payment collection path (Stripe or
otherwise) even if the quota gate existed. This matches CLAUDE.md's own stated scope ("payment
processing is explicitly out of scope for the first pass") — so it's not a surprise regression,
but it does mean the realistic revenue timeline for the Marketplace is currently "not started,"
not "close." Revenue requires, at minimum: #71 (quota gate) landing, a real payment processor
integration (not currently scoped as any GitHub issue at all — see Gaps), and enough Solution
supply + RFP demand for the free tier to matter, which requires the matching engine (#66-69) to
exist first so a paying buyer sees value.

**Legal/liability review: does not exist anywhere in the repo.** `find` for `terms`, `tos`,
`privacy`, `legal` returns nothing — no Terms of Service, no Privacy Policy, no liability
disclaimer of any kind. The `Actor` role (RTI filings, organizing, legal action) is a plain enum
value (`CommitmentRole.ACTOR` in `app/models/commitment.py`) with no feature flag, no gating, no
warning text anywhere in the codebase — it is exactly as available today as `Thinker` or
`Backer`. All references to "RTI" in the codebase are mock fixture data
(`services/web/src/data/mock/fixtures.ts`, `ProblemPage.tsx` sample content) or test bodies, not
actual legal-safety code. CLAUDE.md flags this as Critical Open Issue #4 and says explicitly the
Actor role needs specialist legal review "before the Actor role is enabled publicly" — as of
today it already *is* publicly enabled (the role selector has no gate), so this isn't a future
risk, it's a live one the moment any real user picks Actor and organizes a real-world action.

## Gaps

### Monetization

- [ ] **No payment processor integration exists or is scoped as a GitHub issue.** #71 ("Free-quota
  tracking + billing paywall gate") covers quota tracking + a paywall gate, but nothing in the
  open issues covers actually collecting money (Stripe Checkout/Billing, invoicing, etc.). Without
  this, even a working quota gate just blocks RFP #101 with an error — it doesn't generate
  revenue. **Severity: high, but not urgent** — correctly sequenced behind matching-engine value
  (#66-69) and #71. Recommend filing once #71 is scheduled, so revenue collection isn't
  discovered as a gap only after the paywall ships.
- [ ] **Realistic revenue timeline is effectively "unstarted."** Marketplace code merged today
  (2026-07-10); 8 of 11 marketplace sub-issues remain, including the entire matching engine that
  makes the product valuable enough to pay for. Any GTM plan assuming near-term Marketplace
  revenue should be recalibrated — this is quarters away, not weeks, at solo-dev velocity implied
  by the rest of the backlog. No new issue needed — this is a planning/expectation-setting note,
  not a code gap.

### Free-tier abuse (Marketplace)

- [ ] **One Organization can trivially reset its 100-RFP quota by creating a new Organization** —
  already tracked as **issue #73 ("Free-tier abuse safeguards")**. Confirmed exploitable in
  principle by reading `organization.py`/`marketplace_service.py`: there is no identity binding
  (email domain verification, tax ID, payment method on file, etc.) tying `Organization` creation
  to a real-world entity, and no rate limit on Organization creation itself found in
  `app/core/rate_limit.py`. Cost-if-abused today is theoretically unlimited (unlimited free RFP
  postings), but practically low near-term since there's no real user base yet to abuse it — this
  is a "fix before Marketplace has real traffic" item, not a "fix before merging #63-65" item.
  No new issue filed; referencing #73.

### Cold start / two-sided marketplace bootstrap

- [ ] **No seeding or GTM plan exists for either side of either marketplace (civic or B2B), and
  none of it is tracked as GitHub issues.** TODO.md's own "Marketing & Launch" section is explicit
  that recruiting 5-10 real local problems, seeding initial Thinkers/Actors/Backers, landing page
  copy, and a launch blog post are all "not yet tracked as individual GitHub issues." This is the
  single largest gap between "the mechanic works in code" and "the business has customers."
  **Severity: high, urgent** — filing issue below to convert this TODO.md section into tracked
  work, since it's the most concrete, actionable, and overdue item in the entire audit.
- [ ] **Solution Marketplace supply-side bootstrap has no plan.** CLAUDE.md acknowledges Solution
  publishing is "always free" specifically to solve cold-start on the supply side, but there's no
  tracked plan for *how* the first Solutions get published (direct outreach to vendors? seed
  listings created by the platform operator?) before any RFP can get a non-trivial ranked
  shortlist. Filing a new issue below — this is distinct from #73 (abuse) and from the existing
  matching-engine issues (#66-69), which assume supply already exists.

### Legal/liability exposure

- [ ] **The Actor role is live today with zero legal review, gating, or disclaimer, despite
  CLAUDE.md explicitly saying it needs specialist legal review "before the Actor role is enabled
  publicly."** Confirmed: `CommitmentRole.ACTOR` is selectable with no feature flag anywhere in
  `app/models/commitment.py`, `app/schemas.py`, or the frontend role picker. There is no ToS,
  Privacy Policy, or liability disclaimer anywhere in the repo (`find` for `terms|tos|privacy|legal`
  returns zero files). **Severity: critical, urgent** — this is the single most concrete
  legal-exposure gap found, distinct from a "nice to have someday" item: any real user who signs
  up today, commits as an Actor, and organizes a real RTI filing or legal action does so with the
  platform providing no disclaimer that it isn't a party to and doesn't provide legal backing for
  that action. Filing a new issue below since no existing issue covers this (it's referenced only
  as prose in CLAUDE.md, not tracked as a sub-issue under any epic).
- [ ] **The Marketplace RFP flow has an analogous, currently-undocumented liability question**:
  is Avadhana a party to procurement disputes between an RFP-posting buyer Organization and a
  matched Solution provider? Nothing in `services/backend-api/app/services/marketplace_service.py`
  or the schema addresses this — the matching engine just produces a ranked shortlist and hands it
  to the buyer to "engage directly" (per CLAUDE.md), but there's no explicit disclaimer that
  Avadhana isn't a broker/guarantor of the resulting deal. Lower urgency than the Actor-role gap
  since the matching engine itself isn't built yet (#66-69 all open) — no live transactions can
  happen through it today. Folding into the same new legal/ToS issue below rather than filing a
  second one, since both stem from "no ToS or ai-mediated-liability disclaimer exists yet."

### Retention/churn risk

- [ ] **The 90-day hard lock has zero mitigation built, and this is a deliberate, documented
  choice, not an oversight** — confirmed in `checkpoint_service.py`'s own docstring: *"If you're
  tempted to add [an early-exit override], don't... that's a product decision that hasn't been
  made, not something to slip in as an engineering convenience."* This is architecturally
  consistent with CLAUDE.md's "no exceptions" framing, but it means Critical Open Issue #2 (hard
  lock frustration) remains **fully open as a product decision**, not just unbuilt as code. Given
  zero pilot users exist yet (see Cold Start above), there's no real-world churn data to calibrate
  against — the risk is currently theoretical, but the first pilot users hitting a truly stuck,
  zero-progress problem will generate the platform's very first negative word-of-mouth if this
  isn't at least product-decided (even if the decision is "no early exit, and here's how we
  message that up front") before the pilot launches. **Severity: medium, time-sensitive relative
  to the pilot** — recommend the product decision happen before, not after, recruiting the first
  5-10 real problems, since reversing course after users have already hit the wall is reputationally
  worse than deciding in advance. This is already CLAUDE.md's Critical Open Issue #2; no new issue
  needed, but flagging that it should be resolved (decided, not necessarily built) before pilot
  launch, not deferred indefinitely.

### Competitive positioning

- [ ] **No customer-facing articulation of "why Avadhana over Change.org" exists anywhere.**
  `README.md` states the thesis well ("friction is the feature") but is written for a developer
  audience (repository contents table, architecture links) — there is no landing page, no
  marketing copy, and grep for "Change.org" / "petition" across the repo only matches CLAUDE.md
  and TODO.md (internal planning docs), never a customer-facing file. TODO.md's own "Marketing &
  Launch" checklist already names this gap ("Landing page copy that explains why the constraints
  exist... before asking anyone to sign up") but it's unchecked and untracked as an issue. Folding
  into the GTM-seeding issue filed below rather than a separate issue, since landing copy and pilot
  recruitment are naturally sequenced together (you need the pitch before you can recruit).

### Solo-dev sustainability

- [ ] **Scope assessment: the SLC v1 re-scope decision (2026-07-09, one day before this audit) was
  the right call and is already working as intended** — TODO.md shows AI coordination (#18, 9
  sub-issues), tier reclassification/split/merge (#14-17), polls/task-board/uploads/donations
  (#31-34), and badges (#36) all explicitly deferred post-v1, with reasoning documented inline
  ("more expensive to build than to do by hand at 5-10-problem scale"). This is good triage.
  **However, the Marketplace was merged the same day this re-scope decision was made**, and
  TODO.md's own epic note says Marketplace sequencing against SLC v1 "is an open product decision,
  not yet made — don't start building this ahead of the civic core loop pilot without an explicit
  call to reprioritize." Three marketplace sub-issues (#63-65) already shipped despite that
  explicit warning. **This is worth flagging directly**: either the reprioritization decision was
  made and TODO.md's epic note needs updating to reflect it, or scope is drifting back toward
  breadth (two unproven surfaces in parallel) exactly when the project's own plan called for
  narrowing to one. Recommend a new issue to force an explicit decision rather than let it stay
  ambiguous — filed below.
- [ ] **54 open issues remain (71 total, 17 closed — all 17 closures are the local-dev epic only)**.
  Zero issues under the Core Commitment System, Problem Management, AI Coordination, Feed,
  Gamification, Security, or Marketplace epics are closed on GitHub, even though TODO.md's
  checkboxes say much of Core Commitment System / Feed / Gamification / Security is functionally
  done. This is the same bookkeeping gap noted in Current Status above — recommend a housekeeping
  pass closing finished issues so `gh issue list` reflects reality; not filing a new issue for this
  (it's a five-minute manual cleanup, not a scoped task).

### GTM / pilot artifacts

- [ ] **No tracking of the "5-10 real local problems" validation step called for in CLAUDE.md's
  "Next Steps" (spec Section 10) exists anywhere** — confirmed via `find` for `pilot` (zero
  results outside architecture diagrams unrelated to this topic) and TODO.md item 14 itself
  ("not started, not an engineering task"). This is the same gap as the Cold Start item above;
  addressed by the single new GTM-seeding issue filed below rather than duplicated.

---

## Issues filed

New label created: `business` (`#5319E7`) — "Monetization, GTM, legal, and business viability."

1. **New issue — Legal review and ToS/liability disclaimer before Actor role and Marketplace RFP
   flow are used by real users.** References CLAUDE.md Critical Open Issue #4. Labels: `business`,
   `security`.
2. **New issue — Track GTM/pilot seeding plan as real issues (5-10 real local problems + landing
   copy) instead of an untracked TODO.md wishlist.** References CLAUDE.md Critical Open Issue #1
   and #5, and TODO.md's "Marketing & Launch" section. Labels: `business`.
3. **New issue — Solution Marketplace supply-side (Solution listing) cold-start plan.** Distinct
   from #73 (demand-side abuse) and #66-69 (matching engine assumes supply exists). Labels:
   `business`.
4. **New issue — Force an explicit decision on Marketplace-vs-SLC-v1 sequencing**, since TODO.md's
   own epic-62 note calls this an open decision but 3 sub-issues already shipped. Labels:
   `business`.

Gaps already covered by existing issues (no duplicates filed): free-tier-abuse-via-multiple-orgs
→ **#73**; billing paywall/quota gate → **#71**; matching engine and supply/demand dependent on it
→ **#66, #67, #68, #69, #72**; 90-day hard-lock early-exit product decision → CLAUDE.md Critical
Open Issue #2 (not a GitHub issue by design — it's explicitly framed as an undecided product
question, not a build task).
