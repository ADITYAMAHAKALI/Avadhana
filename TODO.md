# Avadhana — Build Checklist

Mirrors the GitHub issue backlog (`ADITYAMAHAKALI/Avadhana`, epics `#3` `#10` `#18` `#28` `#35` `#39` `#55`) so progress can be tracked here or on GitHub. Check items off in either place — GitHub is the source of truth for status; this file is for a quick local read.

**Immediate focus**: get every service running locally on Kubernetes via Podman before any cloud/VPS work. Start with the Local Kubernetes Dev Environment section below.

## [Local Kubernetes Dev Environment (Podman)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/39) — start here

- [ ] [Install & configure Podman for local Kubernetes](https://github.com/ADITYAMAHAKALI/Avadhana/issues/40)
- [ ] [Set up local k8s cluster + kubectl context](https://github.com/ADITYAMAHAKALI/Avadhana/issues/41)
- [ ] [Containerize Backend API service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/42)
- [ ] [Containerize AI Coordinator Worker service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/43)
- [ ] [Containerize Moderation service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/44)
- [ ] [K8s manifests: PostgreSQL (local dev)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/45)
- [ ] [K8s manifests: Redis (local dev)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/46)
- [ ] [K8s manifests: Backend API](https://github.com/ADITYAMAHAKALI/Avadhana/issues/47)
- [ ] [K8s manifests: AI Coordinator Worker](https://github.com/ADITYAMAHAKALI/Avadhana/issues/48)
- [ ] [Local Ingress / routing](https://github.com/ADITYAMAHAKALI/Avadhana/issues/49)
- [ ] [Local secrets management](https://github.com/ADITYAMAHAKALI/Avadhana/issues/50)
- [ ] [Local SARVAM AI mock/stub](https://github.com/ADITYAMAHAKALI/Avadhana/issues/51)
- [ ] [One-command dev bring-up (Makefile / script)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/52)
- [ ] [CI: build & validate container images + manifests](https://github.com/ADITYAMAHAKALI/Avadhana/issues/53)
- [ ] [Document local dev setup](https://github.com/ADITYAMAHAKALI/Avadhana/issues/54)

## [Core Commitment System](https://github.com/ADITYAMAHAKALI/Avadhana/issues/3)

User, focus slots, commitments, 90-day lock.

- [ ] [Design User schema](https://github.com/ADITYAMAHAKALI/Avadhana/issues/4)
- [ ] [Implement FocusSlot model + 3-slot enforcement](https://github.com/ADITYAMAHAKALI/Avadhana/issues/5)
- [ ] [Implement Commitment creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/6)
- [ ] [Implement 90-day checkpoint job + UI flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/7)
- [ ] [Implement commitment-gated authorization middleware](https://github.com/ADITYAMAHAKALI/Avadhana/issues/8)
- [ ] [CommitmentCheckpoint audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/9)

## [Problem Management & Hierarchy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/10)

Problems, tiers, search, split/merge.

- [ ] [Problem schema + creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/11)
- [ ] [Tier classification rubric (S–D)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/12)
- [ ] [Problem search & discovery](https://github.com/ADITYAMAHAKALI/Avadhana/issues/13)
- [ ] [Tier reclassification governance flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/14)
- [ ] [Problem split mechanic](https://github.com/ADITYAMAHAKALI/Avadhana/issues/15)
- [ ] [Problem merge mechanic + conflict detection](https://github.com/ADITYAMAHAKALI/Avadhana/issues/16)
- [ ] [ProblemRelationship audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/17)

## [AI Coordination Layer (SARVAM AI)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/18)

Summarization, checklist generation, off-topic detection, moderation.

- [ ] [SARVAM AI client integration](https://github.com/ADITYAMAHAKALI/Avadhana/issues/19)
- [ ] [AI agent invocation trigger](https://github.com/ADITYAMAHAKALI/Avadhana/issues/20)
- [ ] [Summarization generation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/21)
- [ ] [Markdown checklist generation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/22)
- [ ] [Off-topic detection + confidence scoring](https://github.com/ADITYAMAHAKALI/Avadhana/issues/23)
- [ ] [Auto-block + human review queue](https://github.com/ADITYAMAHAKALI/Avadhana/issues/24)
- [ ] [Appeal workflow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/25)
- [ ] [Moderation calibration feedback loop](https://github.com/ADITYAMAHAKALI/Avadhana/issues/26)
- [ ] [AIInvocation audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/27)

## [Problem-Specific Feed & Interactions](https://github.com/ADITYAMAHAKALI/Avadhana/issues/28)

- [ ] [Feed core: post / comment / like](https://github.com/ADITYAMAHAKALI/Avadhana/issues/29)
- [ ] [Share (open, non-gated)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/30)
- [ ] [Polls](https://github.com/ADITYAMAHAKALI/Avadhana/issues/31)
- [ ] [Task board: create / pick up / handover tasks](https://github.com/ADITYAMAHAKALI/Avadhana/issues/32)
- [ ] [Asset uploads](https://github.com/ADITYAMAHAKALI/Avadhana/issues/33)
- [ ] [Donation flow (Backer)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/34) — ⚠️ open design question: slot-gated or open to non-committed supporters? Decide before building.

## [Gamification & Reputation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/35)

Rewards follow-through, not activity — do not build a second engagement-farming loop.

- [ ] [Badge schema + award rules](https://github.com/ADITYAMAHAKALI/Avadhana/issues/36)
- [ ] [Reputation score computation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/37)
- [ ] [Profile page](https://github.com/ADITYAMAHAKALI/Avadhana/issues/38)

## [Security & Moderation Safety](https://github.com/ADITYAMAHAKALI/Avadhana/issues/55)

- [ ] [API key & secrets management policy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/56)
- [ ] [Immutable audit logging for moderation actions](https://github.com/ADITYAMAHAKALI/Avadhana/issues/57)
- [ ] [Appeal fraud throttling](https://github.com/ADITYAMAHAKALI/Avadhana/issues/58)
- [ ] [Human override for moderators](https://github.com/ADITYAMAHAKALI/Avadhana/issues/59)
