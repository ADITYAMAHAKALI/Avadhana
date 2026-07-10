# Usability / Product-Usefulness Audit — 2026-07-10

Scope: `services/web` (React + TS + Vite frontend), `services/backend-api` (error copy,
validation, marketplace routers), `TODO.md`, `CLAUDE.md`. Code-read audit — the frontend
was not run; component/route code was read directly (dev server start was judged
unnecessary given how directly the mock-data ports expose exact UI states).

This audit respects the platform's anti-mainstream thesis (3-slot cap, 90-day no-early-exit
lock, commitment-gated voice). Findings below flag **missing explanation, dead ends, and
unwired UI**, not the friction itself — friction that CLAUDE.md calls for (hard blocks, no
early exit, gated voice) is treated as correct and is *not* flagged as a bug anywhere in
this report.

---

## Current Status

### What's actually built and usable

- **Auth + onboarding messaging** (`LoginPage.tsx`, `SignupPage.tsx`): Both screens carry a
  brand panel that states the three core constraints in plain language before the user ever
  signs up ("At most 3 focus slots, ever," "A 90-day minimum commitment lock — not a
  deadline to finish, just the earliest checkpoint," "Only committed members get a voice").
  Signup also has fine print: "abandoning a commitment before its 90-day minimum is recorded
  on your profile." This is a real, working first-exposure explanation — not a silent trap.

- **Commit flow** (`CommitModal.tsx`): Two-step modal. Step 1 is role selection
  (Thinker/Actor/Backer) with plain-language descriptions and Actor specializations. Step 2
  is an explicit confirmation screen with a 90-day ring visual, restates which slot this is
  ("Slot: 3 of 3 — your last" when applicable), an explicit "Abandoning before the minimum
  counts against your record" warning, and a required acknowledgment checkbox ("I understand
  I cannot free this slot for 90 days") before the commit button is even reachable. This is
  a genuinely good confirmation step — the opposite of a silent trap.

- **90-day checkpoint flow** (`CheckpointModal.tsx`, wired from `DashboardPage.tsx`): Full
  resolve/continue/abandon flow, two-step (choose outcome → confirm with optional note), each
  option has a plain-language consequence line, and the abandon option gets an extra red
  warning ("This cannot be undone and will show as an abandoned commitment on your public
  profile"). `DashboardPage` surfaces a checkpoint banner computed from `dayInCycle >=
  cycleLengthDays` and disables the "Review" button with an explanatory `title` tooltip
  before it's actually due. Backend (`commitments.py`, `LOCK_ACTIVE` error with
  `daysRemaining`) re-validates server-side regardless of frontend timing — good
  defense-in-depth, and the modal surfaces the server's own `daysRemaining` on a race.

- **Commitment-gated voice, with explanation** (`ProblemPage.tsx`): Non-committed users see
  a lock icon + "Only committed members can post here. Commit a slot to join the discussion"
  in place of the composer, and a per-comment-thread "Commit a slot to comment" link instead
  of a composer. The like button is disabled with a `title="Only committed members can like
  posts here."` tooltip on hover. This directly satisfies CLAUDE.md's "explain why on
  hover/UX" requirement — it is implemented, not just specified. Backend
  (`commitment_gate.py`) also encodes the exact same explanatory sentence server-side, so the
  UI copy and the API's 403 `NOT_COMMITTED` message agree.

- **4th-commitment block, with explanation**: `FocusSlotsWidget.tsx` narrates state ("All
  three slots are spent. No fourth slot exists.") persistently in the sidebar, not just at
  the moment of failure. `CommitModal`'s error path surfaces the backend's own
  `SLOT_LIMIT_EXCEEDED` message verbatim (`commitments.py` returns `used` count in the 409
  body). This is a hard block with a clear, persistent, pre-emptive explanation — exactly
  what CLAUDE.md asks for ("an error message, not soft discouragement").

- **Discovery** (`DiscoverPage.tsx`): Real, debounced (250ms) search bar plus tier chips
  (S/A/B/C/D) and free-text location/category filters, wired to `GET /problems?q=&tier=&loc
  ation=&category=`. Page header explicitly frames this as "Deliberate discovery — no
  algorithm." Empty state exists ("No problems match these filters yet. Try widening your
  search, or propose one.") rather than a blank screen. This is a real, usable answer to the
  cold-start/discovery risk CLAUDE.md flags — not a stub.

- **Problem creation & tier picker** (`NewProblemPage.tsx`): Full tier rubric (hours +
  funding ranges per tier, matching CLAUDE.md's rubric table) is surfaced inline as
  selectable cards with tooltips and a detail panel under the grid, plus a hint that
  reclassification is available later. Fine print clarifies proposing a problem doesn't spend
  a slot, only committing does — this is an important and correctly-drawn distinction that a
  first-time user could otherwise get wrong.

- **Profile / accountability record** (`ProfilePage.tsx`): Shows currently committed
  problems (x/3), commitment history with resolved/continued/abandoned status pills
  (abandoned entries are visually distinguished — red dot, red status), and a follow-through
  rate ("2 of 3 cycles resolved or continued... 1 abandonment on record"). This matches
  CLAUDE.md's requirement that abandonment be a visible, non-neutral signal.

### What's missing, unwired, or confusing

- **The AI coordination / moderation / appeal UI is entirely mock-data with no backend
  behind it, and the buttons in it don't do anything.** `CoordinatorPage.tsx` renders a
  review queue with "Uphold block," "Allow," "Deny appeal," "Reverse block" buttons — none
  of them have an `onClick`. It's read from `MockModerationPort.ts` reading static fixtures;
  there is no `ModerationPort` implementation backed by real data
  (`services/web/src/data/real/` has no moderation API file), and a repo-wide grep of
  `services/backend-api/app` found **zero** appeal-related endpoints — the entire AI
  Coordination epic (#18) is correctly deferred post-v1 per `TODO.md`, but the frontend
  already ships a page that *looks* fully functional (stat cards, a queue, action buttons)
  while doing nothing. A user who finds this page has no way to know it's non-functional.

- **The AI-generated checklist on `ProblemPage.tsx` is presented as live but is 100% static
  mock content** — same for the "SARVAM Coordinator · summary" card ("Testing at 3 borewells
  confirms nitrate above safe limits...") and the "✦ Invoke coordinator" button (no
  handler). CLAUDE.md requires checklists to read as "suggestions, not commands" — the
  current UI doesn't even reach the point of being a suggestion; it's inert copy with no
  edit affordance, no "regenerate," no per-item claim/dismiss action.

- **The Coordinator/moderation page and Problem Graph page are effectively unreachable in a
  real deployment.** `Sidebar.tsx` hardcodes three nav links to a single fixture problem id
  (`/problems/p-groundwater`, `/graph/p-groundwater`, `/coordinator/p-groundwater`) that only
  resolves against mock fixture data — against the real backend (`isUsingRealData`) these
  links 404 or show "Problem not found." `ProblemPage.tsx` (the real per-problem hub) has no
  link to that problem's own Graph or Coordinator page — the "✦ Invoke coordinator" button
  doesn't navigate anywhere. There is no way to reach a specific problem's graph/coordinator
  view via normal navigation once real data is wired up.

- **Badges on the Profile page are hardcoded static markup, not real data**, even though the
  page fetches everything else (`currentUserPort.getCurrentUser/getCommittedProblems/
  getCommitmentHistory`) from real ports. `ProfilePage.tsx` lines ~142-160 render 4 fixed
  badge divs ("First commitment," "Cycle completed," "Resolved a B-tier," a locked "Resolve
  an S-tier") for every user regardless of their actual history. This is consistent with
  `TODO.md` marking badge schema (#36) as post-v1/not built — but the UI currently
  misrepresents every user as having earned the same 3 badges, which actively works against
  the platform's own "accountability record, not vanity page" principle from CLAUDE.md.

- **Marketplace has real backend (Organizations, RFPs — `app/routers/marketplace/`,
  `app/models/marketplace/`, migration `c11f09a3a44d`, integration tests) but zero frontend
  surface.** No Marketplace tab, no RFP posting form, no Solution browsing/publishing UI, no
  match-results/explainability UI anywhere in `services/web/src`. This is expected per
  `TODO.md` (issue #72 "Web frontend: Marketplace tab" is open, unstarted, and epic #62 is
  explicitly "designed, not yet sequenced") — flagged here for completeness, not as a
  surprise finding, and not filed as a new issue since #69/#72 already cover it.

- **Accessibility is minimal.** Zero `alt` attributes and zero `<img>` tags exist (icons are
  emoji/inline SVG, which sidesteps missing-alt-text specifically), but only 3 total
  `aria-*`/`role=` usages exist across the entire `services/web/src` tree. Icon-only buttons
  (e.g., "✦ Invoke coordinator," like-button heart, search "⌕") have no `aria-label`;
  interactive `<div>`s used for role cards, tier cards, and action cards
  (`CommitModal`, `CheckpointModal`, `NewProblemPage`) use `onClick` on non-button elements
  without a `role="button"`/`tabIndex`/keyboard handler, so they are likely not
  keyboard-operable or screen-reader-announced as interactive. Given this app gates core
  functionality (committing, checkpointing) behind exactly these modal card interactions,
  this is a real usability barrier for keyboard/screen-reader users on the platform's most
  consequential actions.

- **Minor: hardcoded date/data leakage in `CommitModal.tsx`.** The Step 2 confirmation card
  shows "Minimum lock until: **6 Oct 2026**" as a literal hardcoded string regardless of
  which problem or what today's date is — this isn't computed from `Date.now() + 90 days`.
  Low severity (cosmetic/incorrect-but-not-blocking) but worth noting since it sits directly
  inside the most important confirmation screen in the app.

- **`ProblemPage.tsx` has other static/non-functional decorations that could mislead a
  user into thinking features exist**: "Assets · 4" tab (asset upload is post-v1, issue
  #33 — the tab shows a count with no content behind it), "Members · N" tab (not wired to
  an actual roster view), a hardcoded avatar stack (`RM`/`AS`/`DK`/`PN` + "+4") that doesn't
  reflect the actual committed members returned by the API, and a `(dispute tier)` link with
  no handler (tier reclassification is post-v1, issue #14). Each is individually minor, but
  collectively the problem workspace currently presents several controls that look
  interactive but are decorative.

---

## Gaps

- [ ] **Coordinator/moderation page has fully non-functional action buttons ("Uphold block," "Allow," "Deny appeal," "Reverse block") with no `onClick` handlers, and no backend appeal endpoints exist at all.** Severity: Medium — this is expected given AI Coordination (#18) is correctly deferred post-v1, but the *page itself* is reachable and looks complete, which could mislead an early pilot moderator (the solo dev, per CLAUDE.md) into thinking it works. Recommend either gating the route behind a "coming soon" state or at minimum disabling the buttons with a tooltip until #23-#26 land. Not filing as a new issue — covered by the AI Coordination epic #18 and its children (#24 auto-block/review queue, #25 appeal workflow); the "make the frontend match reality" nuance is small enough to fold into whichever of those lands the real endpoints.

- [ ] **`Sidebar.tsx` hardcodes navigation to a single fixture problem id (`p-groundwater`) for Problem workspace, Problem graph, and Coordinator & moderation links — broken/meaningless against real backend data.** Severity: Medium-High for navigation usability once the app runs against real data (which it already can, per `VITE_API_BASE_URL`) — these three nav items will 404 or dead-end for any real user. There's also no link from a real problem's `ProblemPage` to its own Graph or Coordinator page. **Filed as new issue** (see below) — didn't find an existing issue specifically calling out this navigation gap; closest is #60 (Web Frontend epic, still open) but it doesn't mention this specific dead-link defect.

- [ ] **AI-generated checklist and coordinator summary on `ProblemPage.tsx` are static mock copy presented as if live, with no edit/regenerate/dismiss affordance — doesn't yet satisfy CLAUDE.md's "checklists are suggestions, not commands" requirement (there's nothing to check-suggest yet).** Severity: Low right now (expected, AI coordination is post-v1) but worth tracking as an explicit UX requirement for whenever #21/#22 (summarization, checklist generation) are built, so the eventual UI doesn't ship as a read-only fait accompli. Covered by existing issues #21 (Summarization generation) and #22 (Markdown checklist generation) — not filing new, but recommend the "editable suggestion, not command" requirement be called out explicitly when picking those up, since neither issue title currently signals it.

- [ ] **Profile page shows 4 hardcoded badges for every user regardless of actual history, contradicting the "accountability record, not vanity page" principle in CLAUDE.md.** Severity: Medium — badges are supposed to mean something (a badge for resolving an S-tier problem should mean much more than a D-tier one, per CLAUDE.md), but right now every user's profile displays the identical badge set including "Resolved a B-tier," which is actively false for most/all real users. This is worse than showing no badges at all. Covered by existing issue #36 (Badge schema + award rules, post-v1) — not filing new, but flagging that the *current* placeholder state is actively misleading (recommend removing the hardcoded badge markup or clearly marking it as a design preview until #36 ships real data, rather than leaving it live and indistinguishable from real badges).

- [ ] **Minimal accessibility coverage: only 3 `aria-*`/`role=` attributes in the entire frontend; interactive role/tier/action cards are `onClick`-only `<div>`s with no keyboard/screen-reader support; icon-only buttons lack `aria-label`.** Severity: Medium — this affects the platform's most consequential interactions (choosing a role and confirming a 90-day commitment lock in `CommitModal`, choosing resolve/continue/abandon in `CheckpointModal`). No existing issue specifically covers accessibility/a11y anywhere in the 73-issue backlog. **Filed as new issue** (see below).

- [ ] **`ProblemPage.tsx` has several decorative, non-functional controls that could read as broken features**: "Assets · 4" tab and "Members" tab with no destination, a hardcoded avatar stack not reflecting real committed members, a "(dispute tier)" link with no handler, and an "✦ Invoke coordinator" button with no navigation. Severity: Low-Medium — each maps to an already-tracked backlog item (Assets → #33, Members roster → not explicitly tracked but low-stakes, dispute tier → #14, Invoke coordinator → #20/#18) but the *combined effect* on a first-time user is a workspace that looks 80% complete with several silent dead ends. Not filing new issues per-control since each maps to existing backlog items already listed in `TODO.md`; recommend disabling/greying these specific controls (rather than rendering them as if live) as a fast, cheap fix whenever the frontend gets a pass, tracked under the general Web Frontend epic #60.

- [ ] **No dedicated Marketplace frontend exists yet (RFP posting, Solution browsing, match explainability), while the backend (Organizations, RFPs) already has real routers, models, and tests merged.** Severity: N/A as a "gap to fix now" — this is expected, sequenced, and already tracked. Fully covered by existing issues #69 (Matching results UI: ranked shortlist + explainability) and #72 (Web frontend: Marketplace tab); epic #62 explicitly notes sequencing against SLC v1 is still an open product decision. Not filing new.

- [ ] **Hardcoded date "6 Oct 2026" in `CommitModal.tsx`'s lock-confirmation screen instead of a computed `today + 90 days`.** Severity: Low (cosmetic bug, not a UX-design gap) — noted here for completeness since it sits inside the most safety-critical confirmation screen in the app, but likely more appropriate as a quick bug fix than a tracked usability issue. Not filed as a separate GitHub issue; recommend fixing inline next time `CommitModal.tsx` is touched.

---

## GitHub Issues Filed

Checked `gh issue list --repo ADITYAMAHAKALI/Avadhana --state all --limit 200` (73 issues)
before filing anything. Created label `usability` (`#FBCA04`, "UX, onboarding, and product
usefulness") since none existed. Filed 2 new issues for gaps not already covered by an
existing issue; all other gaps above map to existing issues and were cross-referenced
instead of duplicated.
