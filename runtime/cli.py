"""Command-line interface for Raven AI.

The CLI intentionally keeps imports light so `raven --help`, `raven version`,
and `raven doctor` work before optional runtime services are started.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Sequence

from runtime import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raven",
        description="Raven AI local-first scientific agent runtime",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Print the installed Raven AI version")
    subparsers.add_parser("doctor", help="Check core runtime modules and report readiness")

    serve = subparsers.add_parser("serve", help="Start the Raven FastAPI runtime")
    serve.add_argument("--host", default="127.0.0.1", help="Bind address")
    serve.add_argument("--port", type=int, default=8000, help="Bind port")
    serve.add_argument("--reload", action="store_true", help="Enable development reload")
    serve.add_argument("--log-level", default="info", help="Uvicorn log level")

    return parser


def _doctor() -> int:
    checks: dict[str, dict[str, str | bool]] = {}
    modules = (
        "runtime.evidence_graph",
        "runtime.token_economy",
        "runtime.scientific_agent_gates",
        "runtime.server",
    )
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            checks[module_name] = {"ok": True, "detail": "imported"}
        except Exception as exc:  # pragma: no cover - exact import errors vary by extras
            checks[module_name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}

    healthy = all(bool(result["ok"]) for result in checks.values())
    print(json.dumps({"version": __version__, "healthy": healthy, "checks": checks}, indent=2))
    return 0 if healthy else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command in (None, "version"):
        if args.command is None:
            parser.print_help()
        else:
            print(__version__)
        return 0

    if args.command == "doctor":
        return _doctor()

    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover
            parser.error("Serving requires the runtime dependencies: pip install -e .")
            raise AssertionError("unreachable") from exc

        uvicorn.run(
            "runtime.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
