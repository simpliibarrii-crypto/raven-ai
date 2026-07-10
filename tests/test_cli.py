"""CLI contract tests for Raven AI."""

from __future__ import annotations

import json

from runtime import __version__
from runtime.cli import main


def test_version_command(capsys) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_doctor_emits_machine_readable_report(capsys) -> None:
    exit_code = main(["doctor"])
    report = json.loads(capsys.readouterr().out)

    assert report["version"] == __version__
    assert "runtime.evidence_graph" in report["checks"]
    assert exit_code in (0, 1)


def test_help_without_command(capsys) -> None:
    assert main([]) == 0
    assert "Raven AI" in capsys.readouterr().out
