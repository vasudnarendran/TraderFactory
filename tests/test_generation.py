import ast
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
    assert result.spec_validation_path.exists()
    assert result.spec_validation_json_path.exists()
    assert result.experiments_dir.exists()
    assert result.research_dir.exists()
    assert result.round_start_checklist_path.exists()
    assert result.structural_design_brief_path.exists()
    assert result.gate_policy_template_path.exists()
    assert "class AlphaTrader" in result.trader_path.read_text()
    assert "PRODUCT_LIMITS" in result.params_path.read_text()
    assert "DEFAULT_ALPHA_PARAMS" in result.trader_path.read_text()
    assert '"fallback_mode": "normal"' in result.params_path.read_text()
    assert "Spec Validation" in result.spec_validation_path.read_text()
    assert "Preferred archetype" in result.plan_path.read_text()
    assert "spec_validation.md" in result.readme_path.read_text()
    assert (result.experiments_dir / "README.md").exists()
    assert (result.research_dir / "README.md").exists()
    assert (result.experiments_dir / "cmaes_template_alpha.json").exists()
    ast.parse(result.trader_path.read_text())
    ast.parse(result.params_path.read_text())


def test_scaffold_trader_project_surfaces_unknown_mechanics(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_2",
  "products": [
    {
      "symbol": "BETA",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "mixed",
      "execution_style": "mixed",
      "mechanics": ["microstructure_alpha", "trend", "unknown_execution"],
      "unknown_mechanics": ["Passive queue behavior is only partially known."]
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="beta_project")

    params_text = result.params_path.read_text()
    checklist_text = result.round_start_checklist_path.read_text()
    research_text = (result.research_dir / "probe_targets.md").read_text()

    assert '"fallback_mode": "research_overlay"' in params_text
    assert '"unknown_mechanics": ["Passive queue behavior is only partially known."]' in params_text
    assert "Research triggers: boundary, aggressive_markout, passive_ladder" in checklist_text
    assert "probe-scaffold boundary" in research_text


def test_scaffold_trader_project_generates_runnable_conversion_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_3",
  "products": [
    {
      "symbol": "GAMMA",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "unknown",
      "execution_style": "mixed",
      "mechanics": ["conversion", "transport"],
      "conversion_rule": {
        "ratio": 2.0,
        "fee": 1.5,
        "delay_steps": 3,
        "lot_size": 5
      }
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="gamma_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()
    gate_text = result.gate_policy_template_path.read_text()

    assert "class GammaTrader" in trader_text
    assert "def conversion_reference(self, state: TradingState):" in trader_text
    assert 'conversion_rule = self.metadata.get("conversion_rule") or {}' in trader_text
    assert "def build_conversions(self, state: TradingState) -> int:" in trader_text
    assert '"generated_archetype": "conversion_mm"' in params_text
    assert '"conversion_rule": {"custom_fields": {}, "delay_steps": 3, "fee": 1.5, "lot_size": 5, "price_observation_key": "", "ratio": 2.0, "source_product": "", "target_product": ""}' in params_text
    assert "Adjust thresholds after the first trustworthy baseline run." in gate_text


def test_scaffold_trader_project_generates_runnable_derivative_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_3b",
  "products": [
    {
      "symbol": "CALL_100",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "derivative",
      "execution_style": "mixed",
      "mechanics": ["option", "expiry"],
      "derivative_contract": {
        "underlying": "SPOT",
        "strike": 100.0,
        "option_kind": "call",
        "time_to_expiry_years": 0.25,
        "volatility": 0.2
      }
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="call_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()

    assert "from trader_factory.strategies.derivative import black_scholes_option_reference" in trader_text
    assert "class Call100Trader" in trader_text
    assert "def derivative_reference(self, state: TradingState):" in trader_text
    assert 'derivative_contract = self.metadata.get("derivative_contract") or {}' in trader_text
    assert '"generated_archetype": "derivative_mm"' in params_text
    assert '"derivative_contract": {"carry_rate": null, "contract_size": null, "custom_fields": {}, "expiry_style": "", "option_kind": "call", "risk_free_rate": null, "settlement_formula": "", "strike": 100.0, "time_to_expiry_years": 0.25, "underlying": "SPOT", "volatility": 0.2}' in params_text


def test_scaffold_trader_project_generates_runnable_basket_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_3c",
  "products": [
    {
      "symbol": "ETF",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "linked",
      "execution_style": "mixed",
      "mechanics": ["basket", "pair_linked"],
      "basket_definition": {
        "components": [
          {"symbol": "A", "weight": 2.0},
          {"symbol": "B", "weight": -1.0}
        ],
        "divisor": 1.0,
        "fair_offset": 3.0
      }
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="basket_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()

    assert "from trader_factory.strategies.basket import basket_reference_fair" in trader_text
    assert "class EtfTrader" in trader_text
    assert "def basket_reference(self, state: TradingState, own_mid: float) -> float | None:" in trader_text
    assert 'basket_definition = self.metadata.get("basket_definition") or {}' in trader_text
    assert '"generated_archetype": "basket_mm"' in params_text
    assert '"basket_definition": {"components": [{"offset": 0.0, "symbol": "A", "weight": 2.0}, {"offset": 0.0, "symbol": "B", "weight": -1.0}], "custom_fields": {}, "divisor": 1.0, "fair_offset": 3.0}' in params_text


def test_scaffold_trader_project_generates_runnable_spread_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_4",
  "relationships": [
    {
      "left": "DELTA",
      "right": "SIGMA",
      "relationship": "spread",
      "hedge_ratio": 1.5
    }
  ],
  "products": [
    {
      "symbol": "DELTA",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "linked",
      "execution_style": "mixed",
      "mechanics": ["pair_linked", "spread_relationship"]
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="delta_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()

    assert "from trader_factory.strategies.spread import linked_reference_fair" in trader_text
    assert "class DeltaTrader" in trader_text
    assert "def reference_fair(self, state: TradingState, own_mid: float) -> float | None:" in trader_text
    assert '"generated_archetype": "spread_mm"' in params_text
    assert '"relationship_details": [{"counterpart": "SIGMA", "description": "", "hedge_ratio": 1.5, "relationship": "spread", "tags": []}]' in params_text


def test_scaffold_trader_project_generates_runnable_participant_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_5",
  "products": [
    {
      "symbol": "EPSILON",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "mixed",
      "execution_style": "mixed",
      "mechanics": ["named_participant", "flow_following"],
      "participant_rule": {
        "tracked_participants": ["Olivia", "Mia"],
        "follow_mode": "fade",
        "participant_weights": {"Olivia": 2.0}
      }
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="epsilon_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()

    assert "from trader_factory.strategies.participant import participant_flow_signal" in trader_text
    assert "class EpsilonTrader" in trader_text
    assert "def participant_signal(self, state: TradingState):" in trader_text
    assert '"generated_archetype": "participant_mm"' in params_text
    assert '"participant_rule": {"custom_fields": {}, "follow_mode": "fade", "participant_weights": {"Olivia": 2.0}, "signal_horizon": null, "tracked_participants": ["Olivia", "Mia"]}' in params_text


def test_scaffold_trader_project_generates_runnable_signal_sleeve(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_6",
  "products": [
    {
      "symbol": "ZETA",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "mixed",
      "execution_style": "mixed",
      "mechanics": ["external_signal"],
      "signal_rule": {
        "source_key": "WEATHER_SIGNAL",
        "latency_hint": "one_step"
      },
      "observation_channels": [
        {
          "key": "WEATHER_SIGNAL",
          "kind": "plain",
          "role": "signal",
          "description": "External weather feed"
        }
      ]
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="zeta_project")

    trader_text = result.trader_path.read_text()
    params_text = result.params_path.read_text()

    assert "from trader_factory.strategies.signal import signal_reference_fair" in trader_text
    assert "class ZetaTrader" in trader_text
    assert "def signal_key(self) -> str:" in trader_text
    assert "def signal_reference(self, state: TradingState, best_bid: int, best_ask: int):" in trader_text
    assert 'signal_rule = self.metadata.get("signal_rule") or {}' in trader_text
    assert '"generated_archetype": "signal_mm"' in params_text
    assert '"observation_channels": [{"custom_fields": {}, "description": "External weather feed", "fields": [], "key": "WEATHER_SIGNAL", "kind": "plain", "latency_hint": "", "open_questions": [], "role": "signal", "source_product": "", "tags": [], "units": ""}]' in params_text
    assert '"signal_rule": {"custom_fields": {}, "interpretation_mode": "", "latency_hint": "one_step", "source_key": "WEATHER_SIGNAL", "staleness_limit": null}' in params_text


def test_scaffold_trader_project_preserves_structured_auction_rule_metadata(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_7",
  "products": [
    {
      "symbol": "AUC",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "auction",
      "execution_style": "mixed",
      "mechanics": ["auction"],
      "auction_rule": {
        "schedule": "open_and_close",
        "clearing_rule": "uniform_price",
        "prep_window": 10,
        "visibility": ["imbalance", "indicative_price"]
      }
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="auction_project")

    params_text = result.params_path.read_text()
    trader_text = result.trader_path.read_text()

    assert '"generated_archetype": "auction_stub"' in params_text
    assert '"auction_rule": {"clearing_rule": "uniform_price", "custom_fields": {}, "prep_window": 10, "schedule": "open_and_close", "submission_window": null, "visibility": ["imbalance", "indicative_price"]}' in params_text
    assert "class AucTrader" in trader_text


def test_scaffold_trader_project_writes_validation_findings_for_incomplete_specs(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        """
{
  "name": "TestComp",
  "round_name": "round_validation",
  "products": [
    {
      "symbol": "CALL_100",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "derivative",
      "execution_style": "mixed",
      "mechanics": ["option", "expiry"],
      "derivative_contract": {
        "underlying": "SPOT",
        "strike": 100.0,
        "option_kind": "call"
      }
    },
    {
      "symbol": "SPOT",
      "position_limit": 20,
      "tick_size": 1.0,
      "price_regime": "anchored",
      "execution_style": "mixed",
      "mechanics": ["anchored"]
    }
  ]
}
""".strip()
    )

    result = scaffold_trader_project(spec_path, output_dir=tmp_path / "project", project_name="validation_project")

    validation_text = result.spec_validation_path.read_text()
    validation_json = result.spec_validation_json_path.read_text()

    assert "CALL_100" in validation_text
    assert "missing time to expiry" in validation_text
    assert "missing volatility" in validation_text
    assert '"status": "blocked"' in validation_json
