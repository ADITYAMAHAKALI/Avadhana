# Avadhana — Landing Page Copy (Draft)

Status: **draft, not yet placed on a live route**. Written to satisfy the first
item in issue #81's suggested scope ("Landing page copy explaining the 3-slot
/ 90-day-lock / commitment-gated-voice constraints before signup"). This is
copy, not a build — wiring it into an actual public route (`services/web` has
no marketing/landing route today, only `/login` and `/signup`) is a separate,
small follow-up decision: does the landing page live inside the same React
app, or as a static page served ahead of the app shell? Not decided here.

Tone target: CLAUDE.md's "friction is the feature" framing (Section 9, risk
5 — "Growth tension") — lead with the constraints, don't apologize for them.
Aimed at people frustrated with performative online activism, per the
Change.org contrast in spec Section 3.1.

---

## Hero

**अवधान — Avadhana**
**Time is the one currency you can never earn back.**

Every other platform wants your attention split across a hundred things.
Avadhana wants it on three. That's not a limitation — it's the whole point.

[ Sign up ] [ How it works ]

---

## The pitch (above the fold, before any sign-up form)

You've signed a dozen petitions. Followed a dozen causes. How many of them
actually resolved?

Avadhana is built on a bet: **breadth produces spectators, and depth
produces outcomes.** So instead of an infinite feed of causes to half-care
about, we force a choice.

- **Three focus slots. Ever.** You can be actively working on at most three
  problems at a time. Want a fourth? Finish, resolve, or formally abandon
  one first. No exceptions.
- **A 90-day lock, no early exit.** Once you commit a slot to a problem, it's
  locked for a minimum of 90 days — not a deadline to finish, just the
  earliest point you're allowed to step back. This isn't a bug we haven't
  fixed. It's the mechanism that stops the platform from becoming another
  place people drop in, feel good, and drop out.
- **Only committed members have a voice.** If you haven't spent a slot on a
  problem, you can read it, share it, and recruit others to it — but you
  don't get to comment, vote, or steer it. Voice is earned by commitment,
  not by showing up in a comment section.

If that sounds restrictive, it is. That's the pitch, not the fine print.

---

## Why this, not another platform

Change.org and its peers optimize for one thing: getting as many people to
click as possible. A petition with a hundred thousand signatures and zero
resolutions still counts as a win by that metric.

Avadhana optimizes for the opposite: **fewer people, doing more, on fewer
things.** A problem with three committed people who actually filed the RTI,
organized the meeting, and followed up until it resolved is worth more than
ten thousand people who clicked once.

We're not trying to be everywhere. We're trying to work.

---

## What committing actually looks like

1. **Find a problem** — search by topic, location, or scale. No algorithmic
   feed decides what you see; you look for what you want to work on.
2. **Pick a role** — Thinker (research, strategy, framing), Actor (on-ground
   execution — filing RTIs, organizing, meeting officials), or Backer
   (funding). No role requires the others.
3. **Commit a slot** — and see exactly what that means before you confirm:
   the 90-day lock, what happens if you abandon early (it's recorded on your
   profile, permanently), which of your three slots this is.
4. **Do the work, or help others do it** — post updates, coordinate tasks,
   track progress against the problem's actual resolution, not against an
   engagement metric.

---

## What abandoning costs you

We won't pretend there's no cost to committing. Sometimes a problem stalls.
Sometimes you're wrong about what you signed up for. You can still walk
away — but it shows on your public record as an abandoned commitment, not a
quietly deleted history. Reputation on Avadhana moves on follow-through, not
on how much you posted.

That's the trade we're asking you to make: less flexibility, more
accountability. If that's not what you're looking for, we're probably not
the platform for you — and that's fine.

---

## Closing CTA

Three slots. Ninety days. Real accountability.

**[ Choose deliberately. Sign up. ]**

---

## Notes for whoever picks this up next

- Every hard-coded number above (3 slots, 90 days) matches the current
  backend enforcement (`FocusSlot` / `Commitment` models,
  `services/backend-api/app/services/commitment_service.py`,
  `checkpoint_service.py`) — if either constraint ever changes, this copy
  needs to change with it, not just the code.
- "Only committed members have a voice" phrasing intentionally echoes the
  existing in-app tooltip/error copy (`app/services/commitment_gate.py`,
  `ProblemPage.tsx`'s lock-icon explanation) — new users should recognize
  the same language once they're inside the app, not encounter a different
  vocabulary at the door.
- Deliberately does **not** mention the Solution Marketplace (B2B/B2G) — this
  copy is for the civic-platform audience per issue #81's scope. The
  Marketplace, being a genuinely different audience (enterprise/government
  buyers, not individual civic organizers), likely needs its own separate
  landing copy/page entirely — flagging that as a distinct follow-up, not
  attempting it here.
- Per CLAUDE.md Critical Open Issue #4 / issue #78: nothing above should
  imply legal backing for Actor-role actions (RTI filings, organizing, legal
  action). Re-check this copy against whatever real legal review eventually
  produces for #78 before either goes live — they need to agree with each
  other.
