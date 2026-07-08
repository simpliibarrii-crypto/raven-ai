# Connector Deployment Workflow

Updated: 2026-07-08

This document defines how Raven AI uses connected tools without turning the workflow into chaos.

## Golden Rule

GitHub is the source of truth. Linear is the execution spine. Replit is the prototype lane. Vercel is the polished web deployment lane. Google Drive is the research and asset vault. FeedClaw/X is the distribution lane.

## Roles

### GitHub

Use GitHub for code, documentation, pull requests, release packets, source-linked examples, CI, and review history.

### Linear

Use Linear for initiatives, projects, milestones, issues, release accountability, and weekly status updates.

### Replit

Use Replit for fast prototypes, clickable demos, early UI experiments, and quick public proof-of-concept loops. Replit demos should not become the source of truth. When a Replit demo proves useful, export the lesson back into GitHub and decide whether it deserves a Vercel production lane.

### Vercel

Use Vercel for polished public web demos, landing pages, documentation portals, and stable preview deployments. Vercel should receive only work that has a release packet and a clear repo source.

### Google Drive

Use Drive for research notes, scientific paper drafts, launch copy, release receipts, screenshots, and planning assets.

### FeedClaw/X

Use FeedClaw for X distribution only after the public claim is supported by a visible artifact, release note, demo, or limitation statement.

## Promotion Path

1. Idea enters Drive or Linear.
2. GitHub issue defines scope.
3. Replit prototype proves the interaction.
4. GitHub stores the implementation and docs.
5. Linear milestone tracks readiness.
6. Vercel hosts the polished web demo.
7. FeedClaw publishes the launch update.
8. Metrics return to Linear and Drive.

## Replit Gate

A Replit app is useful when it answers one question clearly:

- Can a user understand the demo in under 30 seconds?
- Does it avoid unsupported claims?
- Does it point back to Raven AI?
- Is it free of placeholder IDs and confusing branding?
- Does it generate a useful artifact, trace, or visual proof?

## Vercel Gate

A Vercel deployment is ready when:

- the source repo is known,
- the build path is documented,
- the public route is stable,
- runtime errors are checked,
- the demo is mobile-friendly,
- the release packet explains limits,
- the X post points to the right artifact.

## Linear Gate

A Linear issue is ready when it has:

- a clear owner,
- a target milestone,
- a proof artifact,
- a publish/block/review state,
- a link to GitHub, Drive, Replit, or Vercel.

## Current Deployment Inventory

### Replit

Detected demo lane:

- Raven Evidence Graph

Status: prototype lane. It should be reviewed before being treated as the polished Raven public demo.

### Vercel

Detected team: bclermo.

Detected projects:

- hermes-edge
- homeforai-trading
- public
- home-for-ai-ui
- home-for-ai

Status: Vercel has active project inventory, but no Raven AI production web project was confirmed in the current scan. Raven should either add a dedicated Raven project or route the demo through a known public project after source-of-truth review.

## Immediate Actions

1. Create Linear issues for GitHub release packet, Replit demo review, Vercel public demo lane, Drive research pack, and X launch.
2. Keep Raven claims sober until benchmarks and replay artifacts exist.
3. Use Replit for fast demo iteration.
4. Use Vercel only for polished public deployment.
5. Use Linear as the dashboard of all work.
