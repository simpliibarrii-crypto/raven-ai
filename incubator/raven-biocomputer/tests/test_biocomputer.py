from raven_biocomputer import BioComputer, BiologyPolicy, ToolRegistry


def test_sequence_stats(tmp_path):
    receipt = BioComputer(tmp_path).execute(
        task="Calculate sequence properties",
        tool="sequence_stats",
        payload={"sequence": "ACGTNN"},
        run_id="test-run",
    )
    assert receipt["status"] == "completed"
    assert receipt["result"]["gc_fraction"] == 0.5
    assert receipt["integrations"]["jspace_envelope"]["workspace"] == "raven-biocomputer"


def test_sensitive_work_is_held_for_review():
    decision = BiologyPolicy().evaluate(
        "Diagnose this patient-specific case",
        "sequence_stats",
        {"sequence": "ACGT"},
    )
    assert not decision.allowed
    assert decision.requires_human_review


def test_overlapping_motif():
    result = ToolRegistry().run(
        "find_motif",
        {"sequence": "ATATAT", "motif": "ATA"},
    )
    assert result["positions_zero_based"] == [0, 2]
