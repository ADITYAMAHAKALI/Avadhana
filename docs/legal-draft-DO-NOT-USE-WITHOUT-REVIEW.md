# ⚠️ UNREVIEWED DRAFT — DO NOT USE WITHOUT REAL LEGAL REVIEW ⚠️

> **THIS IS NOT A TERMS OF SERVICE. THIS IS NOT A PRIVACY POLICY. THIS IS NOT
> LEGAL ADVICE. NO LAWYER HAS READ THIS DOCUMENT.**
>
> This file is scaffolding written by an engineer (with AI assistance) to
> mark where real legal language needs to go before Avadhana's **Actor
> role** or **Marketplace RFP posting** are exposed to real users taking
> real-world action (RTI filings, organizing, legal proceedings, procurement
> relationships involving real money). It exists so a real lawyer, reviewing
> this platform's actual liability exposure in its actual operating
> jurisdiction, has a concrete starting draft to correct rather than a blank
> page — not so the platform can skip that review.
>
> **Do not deploy this text to production. Do not link this document as an
> actual ToS/Privacy Policy in any user-facing flow implying it is legally
> binding or reviewed. Do not remove this banner when the file is edited —
> if the content below is ever replaced with real reviewed copy, replace
> this banner and rename the file at the same time, so an unreviewed
> placeholder can never be mistaken for the real thing.**
>
> Tracked under GitHub issue [#78](https://github.com/ADITYAMAHAKALI/Avadhana/issues/78)
> ("Legal review + ToS needed before Actor role / Marketplace RFP go live"),
> itself under epic **#55 Security & Moderation Safety**. See also CLAUDE.md
> "Critical Open Issues" #4 (legal liability) and "Known Unknowns" #2 (legal
> disclaimers) — this document is the first concrete artifact against those
> two open items, not a resolution of them.

---

## 1. What Avadhana is (and isn't)

Avadhana is a **coordination platform** — software that helps people commit
to civic/social problems, organize discussion, track tasks, and (in the
Marketplace) connect buyers posting RFPs with vendors publishing Solutions.

Avadhana is:

- A tool for structuring commitment, discussion, and task tracking around a
  problem a group of users has chosen to work on together.
- A directory/matching layer connecting Marketplace buyers and solution
  providers.

Avadhana is **not**:

- A party to any real-world action a user takes as part of an "Actor" role
  commitment (see Section 2).
- A broker, agent, guarantor, or party to any procurement relationship
  formed via the Marketplace (see Section 3).
- A law firm, legal service provider, or source of legal advice of any
  kind, in any jurisdiction.
- An insurer or guarantor of outcomes — for civic problems or Marketplace
  matches alike.

## 2. Actor role — RTI filings, organizing, legal action

Users who commit to a problem may choose the **Actor** role
(`services/backend-api/app/models/commitment.py`, `CommitmentRole.ACTOR`),
optionally with a specialization (e.g. `Legal`, `Field organizing`).

**Placeholder disclaimer language (needs real legal drafting):**

> Actions taken by a user in the Actor role — including but not limited to
> filing Right to Information (RTI) requests, organizing in-person or
> online activity, meeting with officials, or initiating or participating
> in legal action — are the user's own actions, undertaken in their
> personal capacity. Avadhana:
>
> - does not review, approve, supervise, or take responsibility for the
>   content, legality, or consequences of any Actor's real-world actions;
> - provides no legal backing, representation, indemnification, or
>   guarantee of any outcome;
> - is not a party to any RTI filing, legal proceeding, or organizing
>   activity a user undertakes, even when that activity was coordinated
>   using tasks, checklists, or discussion hosted on Avadhana.
>
> Users choosing the Actor role, particularly with the `Legal` specialization,
> are strongly encouraged to seek independent legal counsel appropriate to
> their jurisdiction before taking action.

This section directly addresses CLAUDE.md's Critical Open Issue #4 ("Legal
liability: Real-world actions ... raise jurisdiction-specific legal
questions. This needs specialist legal review before the Actor role is
enabled publicly") and Known Unknown #2 ("Legal disclaimers: RTI filings and
legal cases organized through Actors need appropriate disclaimers and legal
review before going public"). **Neither issue is resolved by this
document** — real jurisdiction-specific review is still required before the
Actor role is presented to real users outside of internal testing/beta with
informed participants.

## 3. Marketplace — RFPs, Solutions, and matching

The Marketplace (`services/backend-api/app/models/marketplace/`) matches
Organizations posting RFPs against a repository of Solutions using a
ranking engine, per CLAUDE.md's "Solution Marketplace Architecture."

**Placeholder disclaimer language (needs real legal drafting):**

> Avadhana's Marketplace matching engine produces a ranked shortlist of
> candidate Solution providers for a posted RFP. Avadhana:
>
> - is not a broker, agent, guarantor, or party to any procurement,
>   contracting, or commercial relationship formed between an RFP-posting
>   Organization and any matched Solution provider;
> - does not vet, verify, endorse, or guarantee the accuracy of any
>   Solution listing, RFP requirement, or match score;
> - takes no responsibility for the outcome, performance, or terms of any
>   engagement the parties enter into directly with each other.
>
> The `resolution_mode: community` promotion path (an RFP promoted into a
> civic Problem) is a bridge into the ordinary civic commitment mechanic —
> once promoted, standard Avadhana civic rules (3-slot system, 90-day lock,
> commitment-gated voice) apply to that Problem like any other, and this
> Marketplace disclaimer no longer governs the promoted Problem's discussion
> — the general platform disclaimer in Section 1 does.

## 4. Account & data handling (describes the system as built, not aspirational)

This section is limited to what is actually true of the system today, to
avoid making claims a real privacy policy would later have to walk back:

- **Authentication**: Avadhana uses JWT-based authentication
  (`services/backend-api/app/core/security.py`,
  `services/backend-api/app/routers/auth.py`). No third-party
  identity/social login is currently integrated.
- **Primary data store**: User, Problem, Commitment, and Marketplace data
  is stored in Postgres. A job queue (Redis-backed) is used for
  asynchronous AI coordination and Marketplace-matching jobs — see
  CLAUDE.md "Local Development Environment" and "Solution Marketplace
  Architecture" > "Service boundaries."
- **Third-party data sharing — AI providers only, by design**: the
  architecture routes problem discussion content to **SARVAM AI** for
  summarization, checklist generation, and off-topic detection (CLAUDE.md
  "Model Stack & Inference"), and routes Marketplace RFP/Solution text to
  a **second, separate embeddings provider** for the semantic-similarity
  signals used in match ranking (CLAUDE.md "Embeddings provider") — the
  specific provider is an implementation detail documented in code/config,
  not named here to avoid this document going stale if it changes. As of
  this writing, the real summarization/checklist/off-topic-detection calls
  and the embeddings calls are wired into the codebase but not yet invoked
  from any live user-triggered flow (SARVAM's only active call today is a
  connectivity ping; the embeddings client has no router/job calling it
  yet) — so today's actual outbound data flow is effectively nil, but this
  document describes the intended architecture, not a promise that it
  stays that way. Outside of these two AI integrations, Avadhana does not
  share user or problem data with third parties: no payment processor,
  email/SMS provider, or third-party analytics/tracking service is
  integrated anywhere in the codebase as of this writing.
- **No payment processing yet**: `BillingEvent` records track free-quota
  usage/billable-status only; no card/bank data is collected or processed
  by Avadhana today (CLAUDE.md "Monetization" — "actual payment processing
  ... is explicitly out of scope for the first pass").
- This section does **not** constitute a complete privacy policy (it
  omits, for example, data retention periods, user rights/deletion
  requests, cookie/tracking behavior, and jurisdiction-specific
  requirements like GDPR/DPDP compliance) — a real privacy policy still
  needs to be drafted and reviewed.

## 5. Status of this document

- **Not reviewed by a lawyer.** Written by the (solo) engineering side of
  the project as a structural placeholder.
- **Not a liability shield.** Presenting this text to users does not, by
  itself, create an enforceable disclaimer, waiver, or limitation of
  liability — that requires real legal drafting appropriate to Avadhana's
  operating jurisdiction(s).
- **Must be reviewed and replaced before**: the Actor role or Marketplace
  RFP posting are made available to real users outside of internal
  testing/informed beta participants (per issue #78's scope).
- Until reviewed, treat every sentence above as a draft placeholder subject
  to change, not a commitment about how Avadhana will actually behave
  legally.
