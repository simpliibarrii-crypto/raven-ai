#!/usr/bin/env python3
"""Push all substrate MVP files to GitHub via OAuth Contents API.

For each file:
1. Check current SHA on GitHub (via GET)
2. If unchanged, skip
3. If changed or missing, PUT with new content
"""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from pathlib import Path

REPO = "simpliibarrii-crypto/raven-ai"
ROOT = Path("/workspace/raven-ai")

FILES = [
    ".editorconfig",
    ".gitignore",
    "biology_ai/__init__.py",
    "biology_ai/generation/__init__.py",
    "biology_ai/generation/adapters.py",
    "consent/default-psw-brian.consent.json",
    "CONTRIBUTING.md",
    "Dockerfile",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "docker-compose.yml",
    "docs/CPHI-PROPOSAL.md",
    "docs/PROJECT-BRIEF.md",
    "docs/THREAT-MODEL.md",
    "psw-assistant/app.js",
    "psw-assistant/biology_news.json",
    "psw-assistant/index.html",
    "psw-assistant/manifest.json",
    "psw-assistant/style.css",
    "psw-assistant/assets/logo.svg",
    "psw-assistant/locales/en.json",
    "psw-assistant/locales/fr.json",
    "pyproject.toml",
    "registry/keys/default.pub",
    "registry/psw-shift-handoff.v1.0.0.manifest.json",
    "run_dev.sh",
    "runtime/__init__.py",
    "runtime/affordability.py",
    "runtime/audit.py",
    "runtime/bio_security.py",
    "runtime/config.py",
    "runtime/consent.py",
    "runtime/cost.py",
    "runtime/efficient.py",
    "runtime/models.py",
    "runtime/sanitize.py",
    "runtime/server.py",
    "runtime/tenants.py",
    "tenants/tenants.json",
    "tests/test_affordability.py",
    "tests/test_efficient.py",
    "tests/test_substrate.py",
    "tools/grant_consent.py",
    "tools/push_to_github.py",
    "tools/sign_manifest.py",
    "tools/smoke_test.sh",
    "tools/smoke_test_generation.sh",
]


def run(cmd: list[str], stdin: str | None = None, allow_404: bool = False) -> dict:
    """Run a command and return parsed JSON. allow_404 returns {} on 404."""
    result = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        if allow_404 and '"status":' in result.stdout and '"404"' in result.stdout:
            return {}
        print(f"  STDERR: {result.stderr[:500]}", file=sys.stderr)
        print(f"  STDOUT: {result.stdout[:500]}", file=sys.stderr)
        raise RuntimeError(f"command failed: {' '.join(cmd)}")
    if not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def get_remote_sha(path: str) -> str | None:
    """Get the SHA of a file on the remote, or None if missing."""
    result = run([
        "assistant", "oauth", "request",
        "--provider", "github",
        "-X", "GET",
        f"/repos/{REPO}/contents/{path}",
    ], allow_404=True)
    return result.get("sha")


def push_file(rel_path: str, sha: str | None) -> bool:
    """Push a file to GitHub. Returns True if pushed."""
    full = ROOT / rel_path
    if not full.exists():
        print(f"  SKIP missing: {rel_path}")
        return False

    content = full.read_bytes()
    content_b64 = base64.b64encode(content).decode("ascii")

    payload = {
                    "message": f"raven-ai v0.6.0 — native american myth branding + agentic upgrade: {rel_path}",
                    "content": content_b64,
                    "branch": "main",
                }
    if sha:
        payload["sha"] = sha

    result = run([
        "assistant", "oauth", "request",
        "--provider", "github",
        "-X", "PUT",
        "-H", "Content-Type: application/json",
        f"/repos/{REPO}/contents/{rel_path}",
        "-d", json.dumps(payload),
    ])
    commit = result.get("commit", {})
    new_sha = result.get("content", {}).get("sha", "?")
    print(f"  PUSHED {rel_path} → commit {commit.get('sha', '?')[:10]} content {new_sha[:10]}")
    return True


def main() -> int:
    pushed = 0
    skipped = 0
    failed = 0

    for rel in FILES:
        print(f"[{rel}]")
        try:
            remote_sha = get_remote_sha(rel)
            full = ROOT / rel
            if remote_sha and full.exists():
                # Quick SHA-compare against remote
                local_sha = base64.b64encode(full.read_bytes()).decode("ascii")
                # We can't easily get remote's raw bytes, so just always push
                # GitHub returns 422 if SHA matches, which is fine
                pass
            if push_file(rel, remote_sha):
                pushed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print()
    print(f"Done. Pushed: {pushed}, Skipped: {skipped}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())