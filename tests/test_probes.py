from pathlib import Path

from trader_factory.probes import PROBE_LIBRARY, make_event, render_diag_line, scaffold_probe_workspace


def test_probe_library_contains_expected_specs() -> None:
    assert {"boundary", "passive_ladder", "aggressive_markout"} <= set(PROBE_LIBRARY)


def test_diag_line_starts_with_prefix() -> None:
    line = render_diag_line([make_event(probe_id="p1", probe_kind="boundary", event="changed", product="TOMATOES", ts=100, et="bd_change")])
    assert line.startswith("DIAG ")
    assert '"et":"bd_change"' in line
    assert '"probe_kind":"boundary"' in line


def test_scaffold_probe_workspace_creates_expected_files(tmp_path: Path) -> None:
    baseline = tmp_path / "BaselineBot.py"
    baseline.write_text("class Trader:\n    pass\n")

    result = scaffold_probe_workspace(
        "aggressive_markout",
        baseline,
        probe_name="sample_probe",
        output_dir=tmp_path / "probe_workspace",
        context="range_buy",
    )

    assert result.output_dir.exists()
    assert result.readme_path.exists()
    assert result.config_path.exists()
    assert result.submission_probe_path.exists()
    assert result.notes_path.exists()
    assert "range_buy" in result.readme_path.read_text()
    assert "emit_diag" in result.submission_probe_path.read_text()
