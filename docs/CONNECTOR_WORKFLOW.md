# Raven AI Connector Workflow

Updated: 2026-07-08

This document organizes connected tools into a practical Raven AI production workflow. Each connector must improve evidence quality, reduce production friction, improve distribution, or create measurable feedback.

## Command Center Model

| Layer | Job | Connectors |
|---|---|---|
| Source of truth | Code, docs, releases, issues, reproducibility | GitHub |
| Product planning | Roadmap, backlog, milestones, weekly execution | Linear |
| Research vault | Papers, datasets, strategy, drafts, release receipts | Google Drive |
| Prototype lane | Rapid demos and experimental product surfaces | Replit |
| Production deployment lane | Polished web deployments, previews, logs, runtime checks | Vercel |
| Scientific intelligence | Literature discovery, paper synthesis, claim checking | Elicit, SciSpace, Consensus, Exa, Tavily |
| Distribution | X posts, email, decks, visuals, community assets | FeedClaw, Canva, Gamma, Adobe Express, Google Slides |
| Growth and feedback | SEO, community research, prospects, analytics, outreach | Ahrefs, GSC Wizard, LinkedIn, Clay, Common Room, Gmail |

## Default Workflow

### 1. Intake

Inputs can be papers, repo issues, user notes, datasets, workflow observations, or demo requests.

- Store raw notes in Google Drive.
- Convert actionable engineering work into Linear issues.
- Link each Linear issue to the related GitHub branch, PR, or repo file.
- Convert public-growth work into a distribution card.
- Convert research ideas into a paper brief.

### 2. Evidence conversion

Every meaningful statement becomes a source-linked claim:

```json
{
  "schema": "raven.evidence_graph.v1",
  "claim": "Scientific agent outputs should include replay commands before public claims.",
  "sources": ["paperbench", "scienceagentbench"],
  "risk": "medium",
  "confidence": 0.78
}
```

### 3. Token Economy planning

Each expensive run should include:

- draft lane,
- context budget,
- estimated saved context tokens,
- confidence floor,
- verification spans,
- escalation criteria.

### 4. Engineering execution

- GitHub owns source code and reviewable docs.
- Linear owns the execution plan, priorities, milestones, and weekly status.
- Replit is used for fast demos, UI prototypes, pitchable experiments, and early feedback.
- Vercel is used for production-grade web deployment, preview links, logs, runtime checks, and polished public surfaces.

### 5. Scientific gate

A run is publishable only after review:

- evidence labels are present,
- reproducibility artifacts exist,
- metrics are included,
- privacy route is clear,
- public claims are restrained.

### 6. Packaging

Every release packet should include:

- GitHub branch or PR,
- Linear issue/project links,
- README or docs update,
- paper or research note if relevant,
- demo link from Replit or preview/production link from Vercel,
- X post,
- release receipt,
- metrics target.

### 7. Distribution

Publishing order:

1. GitHub PR or release note.
2. Drive paper/research doc.
3. Vercel production or preview link if the release includes a web surface.
4. Replit demo link if the release includes an experimental demo.
5. X post.
6. Community post.
7. Newsletter or outreach when a target list exists.

## Connector Use Rules

### GitHub

Use GitHub for code and source-of-truth docs. Branch before writing. Pull request before merge. Avoid direct main changes unless the change is tiny and low-risk.

### Linear

Use Linear for the production backlog, release milestones, owner assignments, and weekly status updates. Every important Raven workstream should have a Linear issue or project.

Recommended Linear project structure:

- Project: Raven AI Production Line
- Milestone 1: Evidence Graph public demo
- Milestone 2: Token Economy adapters
- Milestone 3: Scientific Gates release packet
- Milestone 4: Vercel public deployment
- Milestone 5: Replit rapid demo loop
- Milestone 6: Distribution and community system

### Google Drive

Use Drive for strategy documents, scientific papers, release receipts, screenshots, and community copy. Drive is the boardroom, GitHub is the engine room.

### Replit

Use Replit for rapid prototypes, visual demos, and exploratory product surfaces. Replit should not become the final source of truth unless the code is later moved into GitHub.

### Vercel

Use Vercel for polished web deployments, preview deployments, production logs, runtime error checks, and public demo surfaces. A Vercel release should point back to the matching GitHub commit and Linear issue.

### FeedClaw/X

Use X for truthful public claims. Do not post benchmark or autonomous-discovery claims unless a release receipt supports them.

### Deployment connectors

Use Vercel as the primary polished deployment lane. Use Replit as the prototype lane. Use Netlify, AppDeploy, or Lovable only when they match the product surface better than Vercel/Replit.

### Design connectors

Use Canva, Gamma, SlidesGPT, Adobe Express, or Google Slides to package the story after technical proof exists.

### Research connectors

Use Elicit, SciSpace, Consensus, Exa, and Tavily for literature discovery and citation triage. Their outputs must still flow through Evidence Graph and Scientific Gates.

## Fame System

Fame is not a connector action. It is a compounding loop:

1. Ship credible proof weekly.
2. Explain the proof simply.
3. Publish the artifact publicly.
4. Invite builders to reproduce it.
5. Reply to serious feedback.
6. Turn objections into Linear issues.
7. Turn issues into GitHub releases.
8. Turn releases into papers and demos.

## Distribution Cadence

- 3 X posts per week.
- 1 GitHub release note per week.
- 1 Linear status update per week.
- 1 technical thread per week.
- 1 paper/research update every two weeks.
- 1 Replit/Vercel demo update per month.
- 1 community outreach batch per week.

## Metrics

Track:

- GitHub stars, forks, issues, PRs, releases.
- Linear issue completion and milestone progress.
- Vercel deployment health and runtime errors.
- Replit demo feedback.
- X impressions, replies, bookmarks, profile visits.
- Paper reads/downloads.
- Community replies.
- Contributor interest.

## Stop Conditions

Do not publish if:

- the claim cannot be traced,
- the run cannot be replayed,
- private-data status is unclear,
- benchmark data is missing,
- the output implies readiness beyond the evidence,
- the marketing language outruns the artifact.
