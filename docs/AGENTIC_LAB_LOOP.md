# Raven Agentic Lab Loop

Raven's agentic lab loop is a restrained implementation pattern for closed-loop scientific work. It is inspired by the goal of collapsing the distance between research, data generation, testing, and model improvement, while keeping every public claim tied to receipts, evidence traces, and safety gates.

## Source inspiration

Capable describes the target operating pattern as:

- rapid in-house data generation feeding ever-improving ML models;
- humans leveraging AI progress to become more capable themselves;
- same-day synthesis-to-testing iterations for therapeutics;
- collapsing the loop between research, synthesis, and testing.

Raven does not claim to perform wet-lab synthesis or therapeutic validation. This repository implements the software-side contract for auditable agentic science: hypothesis capture, connector receipts, evidence traces, metrics, verification, and publication gates.

## Loop contract

1. Capture a falsifiable question and hypothesis.
2. Assign narrow subagents to intake, hypothesis, planning, execution, evidence, verification, safety, metrics, deployment, paper writing, distribution, and red-team review.
3. Record each connector interaction as a `ConnectorReceipt`.
4. Convert receipts into Evidence Graph compatible sources.
5. Convert claims into `ScientificClaimCheck` records.
6. Require code artifacts, output artifacts, metrics, replay commands, and environment fingerprints for executable work.
7. Run `evaluate_scientific_run` before anything is treated as publishable.
8. Keep claims modest when Replit, Vercel, Hugging Face, or other surfaces are read-only, paused, missing traces, or not yet deployed.

## Connector diagnostic receipts from the first implementation pass

| Surface | Status | Receipt |
| --- | --- | --- |
| GitHub | pass | Repository access, branch creation, code fetch, code creation, and PR-capable actions are available. |
| Linear | pass | The Raven AI Production Line project exists with milestones for Evidence Graph, Token Economy, Scientific Gates, Vercel deployment, Replit demo loop, and distribution. |
| Vercel | warn | Team and project listing works. Runtime error scans for `home-for-ai` and `home-for-ai-ui` returned no recent errors, but there are no deployments or Agent Run traces for the checked projects. |
| Replit | blocked | App listing works, but agent inspection returned `phase: paused` with an empty response for `home-for-ai` and `Raven Evidence Graph`. Treat Replit as blocked until the app is opened or the Replit agent session is resumed. |
| Hugging Face | read-only | Repo details for `bclermo/raven-ai` and `bclermo/openclinical-ai` are readable. No write/update operation was exposed by the available Hugging Face connector. |
| X | blocked | The X post URL did not expose readable content through the available browser text fetch. Treat it as directional user intent only unless the post text is pasted or accessed through another source. |
| MCP registry | pass | The registry is queryable. It shows Replit-related MCP servers and exposes timeout-related configuration for the Replit SSH server, but that is not the same as the ChatGPT Replit app connector. |

## Why Replit is timing out or pausing

The observed failure is not a universal MCP outage. It is a Replit-specific paused response pattern:

- `list_apps` succeeds, so account-level Replit access exists.
- `ask_question` returns `phase: paused` and an empty response, so the Replit agent is not completing inspection.
- The safest interpretation is paused app-agent execution, unresolved app state, or a Replit-side session/permission boundary, not missing global ChatGPT permission.

If using a local Replit SSH MCP server outside ChatGPT, increase the documented request timeout variable and verify SSH/SFTP access. Inside this ChatGPT connector, the only practical next step is to resume/open the app in Replit or use `update_app_using_prompt` for a specific natural-language app change.

## Safety boundaries

Raven must not claim autonomous discovery, therapeutic validation, medical-device readiness, PHI-safe production deployment, or same-day wet-lab synthesis unless those claims are backed by independent test receipts, expert review, and appropriate governance.

## Replay

```bash
pytest -q tests/test_lab_loop.py tests/test_scientific_agent_gates.py
```

## Public claim wording

Safe: Raven now includes a software contract for auditable agentic lab-loop records.

Unsafe without more evidence: Raven performs autonomous therapeutic discovery or validated same-day synthesis-to-testing cycles.
