# Raven AI Production Line

Updated: 2026-07-08
Owner: Barry Clerjuste
Status: Draft production operating system

## Mission

Raven AI is the flagship local-first scientific AI platform for biology, clinical workflows, agent orchestration, evidence provenance, and token-efficient reasoning.

The production line turns Raven from a repository into a repeatable machine:

1. Research signal enters.
2. Evidence Graph traces claims to sources.
3. Token Economy plans cheap draft, cache, narrow retrieval, selective verification, and escalation.
4. Scientific Agent Gates decide whether an output is publishable, review-only, or blocked.
5. GitHub stores the source-of-truth implementation.
6. Google Drive stores papers, launch assets, and release receipts.
7. FeedClaw/X distributes truthful updates.
8. Metrics return to the next cycle.

## Operating Principles

### Evidence before charisma

No public claim ships unless it can point to sources, evidence labels, artifacts, and review status.

### Reproducibility before spectacle

A scientific-agent run is not production-ready unless it includes code artifacts, output artifacts, metrics, a replay command, and an environment fingerprint.

### Cost discipline before brute force

Expensive model calls must justify themselves. Raven should prefer cache, local lanes, narrow retrieval, and selective verification before escalation.

### Privacy before reach

PHI, clinical notes, private files, credentials, and unpublished strategy stay local or inside approved deployment boundaries.

### Distribution follows proof

Marketing must describe what Raven can currently prove, not what it hopes to become.

## Production Stages

| Stage | Purpose | Primary connector | Output |
|---|---|---|---|
| Intake | Capture ideas, papers, datasets, repo issues, user requirements | Google Drive, GitHub | Work item or research brief |
| Evidence | Convert inputs into sources, claims, confidence, risk, trace IDs | Raven Evidence Graph | `raven.evidence_graph.v1` JSON |
| Planning | Route work by cost, privacy, confidence, and tool needs | Raven Token Economy | Token plan and route decision |
| Execution | Run code, adapters, analyses, and demos | GitHub, local runtime, deployment connector | Artifacts and logs |
| Gatekeeping | Check evidence, reproducibility, PHI, benchmark, and public-claim safety | Scientific Agent Gates | Publish/block/review report |
| Packaging | Create README updates, papers, demos, assets, release notes | GitHub, Google Drive | Release bundle |
| Distribution | Publish X posts, community posts, newsletters, demo links | FeedClaw, future community tools | Public launch record |
| Measurement | Track stars, forks, installs, demos, replies, citations, PRs | GitHub, analytics connectors | Weekly metrics receipt |

## Minimum Release Packet

A Raven release is not ready unless it has:

- README update or release note.
- Working install/test instructions.
- Evidence Graph example or exported trace.
- Token Economy note when model routing or cost claims are involved.
- Scientific Gate report if scientific/clinical claims are present.
- Demo script or screenshot path.
- X post draft.
- Metrics receipt placeholder.
- Clear limitations.

## Connector Roles

### Core production

- GitHub: source of truth, branches, PRs, release docs, issues, CI review.
- Google Drive: research vault, paper drafts, distribution calendar, investor/community materials.
- FeedClaw/X: public micro-distribution and launch log.

### Specialized stations

- Elicit/SciSpace/Consensus: literature discovery and paper tables.
- GitHub/Linear/Asana/ClickUp: backlog and engineering execution.
- Vercel/Netlify/Replit/AppDeploy/Lovable: deployment experiments.
- Canva/Gamma/SlidesGPT/Adobe Express: public-facing visuals and decks.
- Ahrefs/GSC Wizard/vidIQ/LinkedIn/Common Room/Clay: audience research and growth when connected.
- Gmail/Google Calendar/Contacts: outreach and scheduling when explicitly requested.

## Truthful Public Positioning

Use this one-line positioning until benchmarks prove more:

> Raven AI is local-first infrastructure for evidence-linked scientific and clinical AI workflows: claims, sources, token routing, reproducibility gates, and reviewable outputs.

Avoid:

- Autonomous cure/discovery claims.
- State-of-the-art claims without held-out evaluation.
- Medical-device claims.
- Benchmark claims without reproducible artifacts.
- Crypto-token confusion around Token Economy.

## Weekly Operating Rhythm

Monday: review issues, paper signals, and metrics.
Tuesday: build one small adapter or demo improvement.
Wednesday: run tests, gates, and docs.
Thursday: package release notes, paper updates, and visual assets.
Friday: publish one truthful distribution update.
Weekend: community replies, cleanup, backlog grooming.

## Real Research Signals to Track

- DSpark, 2026: confidence-scheduled speculative decoding and adaptive verification. Claimed 60 to 85 percent per-user generation speedup in DeepSeek-V4 serving under reported conditions.
- PaperBench, 2025: full research replication remains hard for AI agents; benchmark includes 8,316 gradable subtasks across 20 ICML 2024 papers.
- ScienceAgentBench, 2025/2026 signal family: scientific agents need executable, isolated tasks, output artifacts, and evaluation.
- AI Agents That Matter, 2024: agent evaluation must account for cost, accuracy, reproducibility, and resistance to benchmark overfitting.

## Next Build Items

1. Add a release packet template to `/templates`.
2. Add a machine-readable production manifest schema.
3. Add example release receipt for the Evidence Graph demo.
4. Add a GitHub Action that checks docs for forbidden claims.
5. Add a benchmark receipt schema for Hermes Edge local token savings.
