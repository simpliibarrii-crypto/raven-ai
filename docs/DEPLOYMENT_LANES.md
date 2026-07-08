# Raven Deployment Lanes

Updated: 2026-07-08

Raven uses two deployment lanes for different jobs.

## Replit: prototype lane

Use Replit when Raven needs a fast visual prototype, demo experiment, or early user-feedback surface.

Current discovered Replit app:

- Raven Evidence Graph
- Purpose: rapid visual demonstration of Raven claim/source tracing and evidence export.

Rules:

- Replit is for speed, exploration, and feedback.
- Replit demos must clearly state what is real and what is experimental.
- Stable logic should move back into GitHub.
- Public polished surfaces should graduate to Vercel when appropriate.

## Vercel: polished public deployment lane

Use Vercel when Raven needs a polished public web surface, preview deployment, production deployment, runtime logs, and release-grade public links.

Discovered Vercel team:

- bclermo

Discovered Vercel projects:

- hermes-edge
- homeforai-trading
- public
- home-for-ai-ui
- home-for-ai

Recommended Raven path:

1. Keep core runtime and docs in GitHub.
2. Use the existing Replit Raven Evidence Graph app for prototype feedback.
3. Create or assign a Vercel web surface for Raven public docs/demo if no existing Vercel project is the right fit.
4. Link Vercel deployments to GitHub commits and Linear issues.
5. Attach runtime logs, preview links, and production URLs to release receipts.

## Promotion checklist

A Replit demo graduates to Vercel only when:

- the demo works without placeholder content,
- source logic is represented in GitHub,
- public claims are evidence-linked,
- install or replay steps are documented,
- runtime limitations are written plainly,
- Linear issue and GitHub branch are linked.

## Deployment receipt schema

```json
{
  "schema": "raven.deployment_receipt.v1",
  "surface": "raven-evidence-graph",
  "lane": "replit-prototype | vercel-preview | vercel-production",
  "github_commit": "",
  "linear_issue": "",
  "url": "",
  "runtime_checks": [],
  "known_limitations": [],
  "public_claims": [],
  "evidence_trace": "raven.evidence_graph.v1"
}
```
