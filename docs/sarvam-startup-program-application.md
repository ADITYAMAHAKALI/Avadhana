# Sarvam AI Startup Program — Application Plan

Plan for applying to https://www.sarvam.ai/startup-program. The application
form itself is behind bot-protection I can't fetch programmatically — this
doc is prep so filling it out in your browser is a 10-minute copy/paste job
instead of a blank-page problem, not a substitute for actually opening the
page yourself.

## 1. What the program actually offers (confirmed via press coverage, not the page itself)

- 6–12 months of API credits, sized to startup stage / projected usage.
- Access to Speech-to-Text, Text-to-Speech, Translation, Chat Completion, and Document Intelligence APIs, 22 Indian languages + English.
- Priority engineering support from Sarvam's team.
- Co-branded case studies / launch amplification once you ship something using it.
- **Condition you're implicitly agreeing to if accepted:** "Powered by SarvamAI" branding somewhere in-product.
- Selection is described as merit-based on stage, projected API usage, and technical requirements — and explicitly calls out that startups **already using Sarvam APIs** can apply for *additional* credits + priority support, which is the bucket Avadhana falls into (see below).

Sources: [Sarvam AI Startup Program](https://www.sarvam.ai/startup-program) (page itself, blocked for automated fetch — open it directly), [BusinessToday coverage](https://www.businesstoday.in/technology/news/story/sarvam-launches-startup-programme-offering-ai-credits-tools-to-boost-indias-developer-ecosystem-519295-2026-03-05), [Business Standard coverage](https://www.business-standard.com/companies/start-ups/sarvam-ai-launches-startup-programme-to-back-ai-builders-in-india-details-126030501111_1.html), [startupsamadhan.com summary](https://startupsamadhan.com/sarvam-ai-startup-programme-india-free-credits/).

**I could not verify the actual form fields, deadlines, or a hard eligibility checklist (e.g. whether pre-incorporation solo builders are accepted) — the live page is the only source of truth for that. Open it yourself and paste back anything that doesn't match what's drafted below; I'll adjust.**

## 2. Why Avadhana is a credible applicant, not a cold pitch

Don't undersell this in the application — you have working code, not a slide deck:

- **Real integration already built and closed out**: GitHub issue #19 ("SARVAM AI client integration") is closed. `services/ai-coordinator-worker/impl/sarvam_client.py` is a working `HttpSarvamClient` against `sarvam-105b` (chat completions), with `SARVAM_USE_MOCK`-gated local/CI mocking (`services/sarvam-mock/`) so you were never burning API cost just to develop against it.
- **A specific, non-generic use case**: per `CLAUDE.md`'s "AI Coordination Architecture," Sarvam powers three concrete jobs — discussion summarization, checklist generation from unstructured discussion, and off-topic/scope-drift detection — for civic problem-solving groups (RTI filings, local organizing, community coordination). This is exactly the "vernacular content / regional coordination" shape the program's stated target sectors call out.
- **Currently mocked, not because it doesn't work, but because it's pre-launch**: `SARVAM_USE_MOCK=true` today is a deliberate cost-control decision for the pre-launch SLC v1 pilot (see `docs/vps-deployment.md`), not a sign the integration is unfinished. This is a good thing to say explicitly — it shows engineering discipline, not incompleteness.
- **Public, working repo**: https://github.com/ADITYAMAHAKALI/Avadhana — link it. A reviewer can see real commits, a real test suite (257 backend tests, 26 worker tests passing as of this doc), and a real product spec (`CLAUDE.md`), not just an idea.
- **A credible near-term usage story**: once AI Coordination is un-deferred (issues #20-27 — real summarize/checklist/off-topic prompts, currently placeholder), the intended invocation cadence is a scheduled job every 3–6 hours per active problem (already documented in `CLAUDE.md`), not per-request — a predictable, low, boundable usage pattern that's easy for Sarvam to size credits against.

## 3. Before you open the form

- [ ] Have the repo URL ready: `https://github.com/ADITYAMAHAKALI/Avadhana`
- [ ] Have a live URL ready if you want to show the product itself, not just code — your Render-deployed frontend once `docs/free-tier-deployment.md` is live, or the ngrok tunnel from earlier if that's still the fastest thing you can point to today.
- [ ] Decide how you want to describe yourself: the form likely asks for a company name. You said Avadhana isn't incorporated yet — plan to apply as an individual builder/project, not a registered entity (see draft answers below for exact wording). If the form *requires* a registered company/DPIIT number to submit at all, that's a hard blocker only the page itself will reveal — check this first before spending time on the rest of the form.
- [ ] Have a one-line and a three-line description ready (drafted below) so you're not composing them live in a form field.

## 4. Draft answers for likely form fields

Treat these as a starting draft to paste and adjust once you see the real field labels/character limits, not final copy.

**Company / project name:**
> Avadhana

**One-liner:**
> A commitment-first civic platform where users can actively work on at most 3 problems at a time, locked in for 90 days — depth over breadth, for real-world problem-solving instead of engagement-driven social media.

**What stage are you at:**
> Pre-launch, solo-built. Core commitment mechanic (3-slot system, 90-day lock, commitment-gated voice) and the Solution Marketplace are implemented and tested; AI Coordination layer is integrated against Sarvam but the specific summarization/checklist/off-topic-detection prompts are the next build phase before the SLC v1 pilot (5-10 real local problems) launches.

**How are you using / planning to use Sarvam:**
> Chat Completion (`sarvam-105b`) for three specific jobs on each civic problem's discussion thread, triggered on a schedule (every 3-6 hours per active problem, not per-request): (1) summarizing discussion + progress for committed members, (2) generating a markdown task checklist from unstructured discussion, (3) detecting off-topic/scope-drift contributions to keep discussion focused — core to the product's anti-dilution thesis. The client integration (issue #19) is already built and tested against a local mock; we're applying for credits to move from mocked to live calls as we un-defer the real prompt engineering.

**Why Sarvam specifically (vs. OpenAI/Anthropic/etc.):**
> Cost efficiency for a solo-dev bootstrap, and native multilingual support (22 Indian languages) matches Avadhana's target users — local civic problems in India are frequently discussed in a mix of English and regional languages, and a global-first LLM provider's Indian-language handling is a worse fit than a provider built for this specifically.

**Expected usage volume (if asked for a number):**
> Bounded by design, not open-ended: usage scales with (number of active civic problems) × (1 invocation per problem every 3-6 hours), not with user traffic or request volume — a small, predictable, easy-to-forecast pattern even as user count grows, since only committed members' problems get scheduled invocations at all (not every problem on the platform).

**Links to include:**
- Repo: `https://github.com/ADITYAMAHAKALI/Avadhana`
- Live demo (once deployed per `docs/free-tier-deployment.md`): fill in once you have the Render URL.

## 5. After you apply

- No further action from me until you hear back — this is a human review process on Sarvam's side, not something to automate or follow up on programmatically.
- If accepted: you'll get real credits/a key. At that point, come back and I'll wire `SARVAM_API_KEY` into the deployment (both the Render `backend-api`/`sarvam-mock` env — actually just `ai-coordinator-worker`'s GitHub Actions secrets, since `backend-api` doesn't call Sarvam at all, see `docs/free-tier-deployment.md` section 3d) and flip `SARVAM_USE_MOCK=false`, plus prioritize actually building the real summarize/checklist/off-topic jobs (issues #20-27) so the credits get used on real functionality, not just `ping_job`.
- Remember the "Powered by SarvamAI" branding condition — that's a small UI change (footer or about-page credit) worth doing once accepted, not before you know you're in.
