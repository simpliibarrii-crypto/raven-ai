# Raven Trust Runtime: Evidence-Linked, Token-Aware, Reproducible Infrastructure for Scientific AI Agents

Barry Clerjuste
Raven AI
Draft: 2026-07-08

## Abstract

Scientific AI agents should not be marketed as magic notebooks or autonomous discovery engines. They should be treated as auditable workflow systems whose outputs can be traced, replayed, reviewed, and costed. Raven Trust Runtime is the operating model behind Raven AI: a local-first scientific AI platform combining Evidence Graphs, Token Economy planning, and Scientific Agent Gates. The goal is to make biology, clinical, lab, and research workflows cheaper to run, easier to inspect, and safer to review without making unsupported claims about medical use, benchmark superiority, or autonomous scientific discovery.

## 1. Motivation

Recent agent research points in two directions at once. Inference systems are getting faster and more adaptive, while scientific-agent benchmarks show that full research replication remains difficult. Raven AI is designed for the gap between those facts: not a claim that agents can replace scientists, but a runtime that helps humans inspect what agents did.

DSpark, published in July 2026, introduces confidence-scheduled speculative decoding with semi-autoregressive generation. It reports 60 to 85 percent per-user generation speedups in DeepSeek-V4 serving at matched throughput levels under live-traffic deployment conditions. Raven does not depend on DeepSeek or DSpark directly, but adopts the broader product lesson: cheap drafting and adaptive verification should be planned explicitly rather than hidden inside black-box generation.

PaperBench evaluates AI agents on replication of 20 ICML 2024 papers using 8,316 gradable subtasks. The benchmark reports that the best tested agent scored 21.0 percent on average and that tested models did not outperform the recruited ML PhD baseline in the evaluated setting. Raven treats this as a warning against vague automation claims and a reason to decompose scientific work into gated, reviewable stages.

AI Agents That Matter argues that agent evaluation should jointly consider accuracy, cost, reproducibility, and benchmark overfitting resistance. Raven adopts that lesson directly: public outputs should explain not only what answer was produced, but what it cost, what evidence supports it, and whether it can be replayed.

## 2. Raven Trust Runtime

Raven Trust Runtime has three core contracts.

### 2.1 Evidence Graph

Evidence Graph stores sources, claims, confidence, risk, and answer traces. Its purpose is to let Raven outputs answer a simple question: why should anyone trust this?

Minimum evidence fields:

- source ID
- source title
- source kind
- claim ID
- claim text
- evidence label
- confidence
- risk
- trace ID

### 2.2 Token Economy

Token Economy plans how Raven spends compute and model context. It prefers cache, local lanes, narrow retrieval, cheap drafts, confidence thresholds, selective verification, and escalation only when needed.

Minimum Token Economy fields:

- draft lane
- context budget
- cache strategy
- estimated saved context tokens
- confidence floor
- verification spans
- escalation rule

### 2.3 Scientific Agent Gates

Scientific Agent Gates determine whether an output is publishable, review-only, or blocked. Gates cover evidence, reproducibility, token metadata, privacy, and public-claim safety.

Minimum gate fields:

- evidence decision
- code artifacts
- output artifacts
- metrics
- replay command
- environment fingerprint
- PHI routing decision
- human review status

## 3. System Workflow

A Raven scientific workflow follows eight stages:

1. Intake: collect paper, dataset, question, protocol, or repo issue.
2. Evidence: convert input into sources, claims, and trace IDs.
3. Planning: choose model/tool route under Token Economy rules.
4. Execution: run code, analysis, adapters, or demo.
5. Gatekeeping: evaluate publishability and safety.
6. Packaging: create report, release packet, and artifacts.
7. Distribution: publish only claims that passed gates.
8. Measurement: capture metrics and feed them into the next cycle.

## 4. Application Surfaces

- Raven Bio: genomics, transcriptomics, proteomics, structural biology, wet-lab planning.
- Raven Clinical: evidence workflows, calculators, terminology, PHI-aware routing.
- Raven LabOps: protocol execution, sample tracking, instrument coordination, audit logs.
- Raven Research: literature review, citation verification, hypotheses, reproducible reports.

## 5. Production and Deployment Lanes

### GitHub

GitHub is the source of truth. All production docs, runtime contracts, schemas, code, tests, release packets, and PR discussions live there first.

### Linear

Linear is the execution spine. It tracks milestones, issues, due dates, risk, and release accountability.

### Replit

Replit is the prototype lane. Raven can use it for quick demo experiments, but not for secrets, PHI, production databases, irreversible actions, or source-of-truth decisions. A Replit prototype must export its result back to GitHub or Google Drive before distribution.

### Vercel

Vercel is the polished deployment lane. Approved public demos can ship there after claim review, release-packet completion, and environment-boundary checks. GitHub remains the source of truth; Vercel is the public surface.

### Google Drive

Google Drive is the research and asset vault for paper drafts, strategy docs, launch calendars, and metric receipts.

### FeedClaw / X

FeedClaw and X are distribution channels. They should publish only short, truthful updates that are supported by repository artifacts and release packets.

## 6. Safety Boundaries

Raven should block:

- unsupported biomedical claims,
- fake benchmark claims,
- medical-device claims,
- autonomous-discovery claims without human review,
- state-of-the-art claims without held-out evaluation,
- PHI-bearing traces routed through unapproved remote lanes,
- token-saving claims without cost or route metadata.

## 7. Research Contributions

Raven Trust Runtime contributes a practical operating pattern:

1. Evidence-linked claims instead of free-floating answers.
2. Token-aware routing instead of hidden compute spend.
3. Reproducibility gates instead of screenshot demos.
4. Privacy-aware routing instead of accidental data leakage.
5. Distribution discipline instead of hype-first marketing.

## 8. Evaluation Plan

Raven should be evaluated in stages:

- Unit tests for Evidence Graph and Token Economy contracts.
- Synthetic release packets with known supported, contradicted, and insufficient-evidence claims.
- Replayable workflow tasks with code/output artifacts and environment fingerprints.
- Cost and latency receipts for local-small, local-large, and remote model lanes.
- Human review of claims before any scientific or clinical public release.

## 9. Limitations

This paper is a position and operating-system draft. It does not claim clinical validity, state-of-the-art benchmark performance, autonomous discovery, or medical-device readiness. Raven still needs broader adapters, external review, real benchmark receipts, and hardened deployment paths before stronger claims are justified.

## 10. References

- Cheng et al. DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation. arXiv:2607.05147, 2026.
- Starace et al. PaperBench: Evaluating AI's Ability to Replicate AI Research. arXiv:2504.01848, 2025.
- Kapoor et al. AI Agents That Matter. arXiv:2407.01502, 2024.
