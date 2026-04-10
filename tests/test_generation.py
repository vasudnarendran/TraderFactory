from pathlib import Path

from trader_factory.generation import scaffold_trader_project


def test_scaffold_trader_project_creates_expected_files(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_1",
  "products": [
    {
      "symbol": "ALPHA",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "anchored",
      "execution_style": "mostly_passive",
      "mechanics": ["anchored", "static_anchor"]
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="alpha_project")

    assert result.output_dir.exists()
    assert result.trader_path.exists()
    assert result.params_path.exists()
    assert result.plan_path.exists()
    assert "class AlphaTrader" in result.trader_path.read_text()
    assert "PRODUCT_LIMITS" in result.params_path.read_text()
