# Clean Demo Video

Raven Evidence Graph has a clean, watermark-free product demo video for social launch and project previews.

- X post: https://x.com/i/web/status/2074684335639187945
- Project: https://github.com/simpliibarrii-crypto/raven-ai
- Contract: `raven.evidence_graph.v1`

## What This Video Shows

The demo introduces Raven Evidence Graph as a local-first provenance layer for scientific AI:

1. Add evidence sources.
2. Link claims to sources.
3. Generate answer traces with confidence and risk.
4. Move the same trace packet across Raven AI, OpenClinical AI, Home for AI, and Hermes Edge.

## Why It Is Clean

The video is generated from code in `scripts/render_clean_demo_video.py` instead of an avatar or template exporter. It contains no Replit marks, no HeyGen marks, no React Flow attribution, no stock footage watermark, and no generator branding.

## Regenerate Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install pillow
python scripts/render_clean_demo_video.py
```

The script writes `outputs/raven-evidence-graph-clean-demo.mp4`. It requires `ffmpeg` to be installed on the system path.

## Publishing Notes

Use the code-generated MP4 for launch posts and demos. If a hosted video platform adds its own branding, regenerate from this script and upload through a clean export path instead of covering or cropping a watermark.
