from __future__ import annotations

import json
from pathlib import Path

from trader_factory.viewer.monte_carlo import collect_results, detailed_payload


def test_collect_results_finds_nested_monte_carlo_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "generated" / "runs" / "monte_carlo" / "v52_vs_v51"
    run_dir.mkdir(parents=True)

    report = {
        "config": {"bots": ["/tmp/Traderv52.py", "/tmp/Traderv51.py"]},
        "baseline": {
            "Traderv52": {"combined_total_pnl": 29884.0, "per_day": {"-1": 15081.0, "-2": 14803.0}},
            "Traderv51": {"combined_total_pnl": 29488.5, "per_day": {"-1": 14868.0, "-2": 14620.5}},
        },
        "monte_carlo": {
            "Traderv52": {
                "overall": {"count": 2, "mean": 29030.0, "std": 0.0},
                "profiles": {"all": {"mean": 29030.0}, "plausible": {"mean": 29100.0}, "stress": {"mean": 28900.0}},
                "by_family": {"original_noise": {"mean": 29030.0}},
            },
            "Traderv51": {
                "overall": {"count": 2, "mean": 28606.0, "std": 0.0},
                "profiles": {"all": {"mean": 28606.0}},
                "by_family": {"original_noise": {"mean": 28606.0}},
            },
        },
        "comparison": {
            "primary_bot": "Traderv52",
            "compare_bot": "Traderv51",
            "shared_samples": 1,
            "summary": {"mean_delta": 424.0, "median_delta": 424.0, "p10_delta": 424.0, "win_rate": 1.0},
        },
    }
    (run_dir / "report.json").write_text(json.dumps(report))
    (run_dir / "sample_totals.csv").write_text("bot,family,sample_id,total_pnl\nTraderv52,original_noise,s1,29030.0\n")
    (run_dir / "day_results.csv").write_text("bot,day,total_pnl\nTraderv52,-1,15081.0\n")

    summaries = collect_results([tmp_path / "generated" / "runs" / "monte_carlo"])
    assert len(summaries) == 1
    assert summaries[0]["kind"] == "mc_report"
    assert summaries[0]["displayName"] == "v52_vs_v51"


def test_detailed_payload_loads_companion_csvs_for_report_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "generated" / "runs" / "monte_carlo" / "v52"
    run_dir.mkdir(parents=True)
    report_path = run_dir / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "config": {"bots": ["/tmp/Traderv52.py"]},
                "baseline": {"Traderv52": {"combined_total_pnl": 29884.0}},
                "monte_carlo": {"Traderv52": {"overall": {"count": 1, "mean": 29030.0}, "profiles": {}, "by_family": {}}},
                "comparison": {},
            }
        )
    )
    (run_dir / "sample_totals.csv").write_text("bot,family,sample_id,total_pnl\nTraderv52,original_noise,s1,29030.0\n")
    (run_dir / "day_results.csv").write_text("bot,day,total_pnl\nTraderv52,-1,15081.0\n")

    payload = detailed_payload([tmp_path / "generated" / "runs" / "monte_carlo"], str(report_path))
    assert payload is not None
    assert payload["kind"] == "mc_report"
    assert len(payload["sampleTotals"]) == 1
    assert len(payload["dayResults"]) == 1
