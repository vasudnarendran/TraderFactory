from trader_factory.workflows.gates import ImcGatePolicy, evaluate_imc_gate_policy, resolve_imc_gate_policy


def test_resolve_imc_gate_policy_prefers_explicit_values() -> None:
    base = ImcGatePolicy(
        round_id=7,
        deterministic_min_total_delta=5.0,
        mc_min_mean_delta=2.0,
        notes="baseline",
    )
    resolved = resolve_imc_gate_policy(
        round_id=7,
        base_policy=base,
        deterministic_min_total_delta=8.0,
        mc_min_p10_delta=1.5,
    )
    assert resolved.round_id == 7
    assert resolved.deterministic_min_total_delta == 8.0
    assert resolved.mc_min_mean_delta == 2.0
    assert resolved.mc_min_p10_delta == 1.5
    assert resolved.notes == "baseline"


def test_evaluate_imc_gate_policy_reports_threshold_failures() -> None:
    policy = ImcGatePolicy(
        round_id=1,
        deterministic_min_total_delta=1.0,
        mc_min_mean_delta=0.5,
        mc_min_plausible_mean_delta=0.25,
    )
    evaluation = evaluate_imc_gate_policy(
        policy=policy,
        deterministic_ran=True,
        deterministic_total_delta=0.5,
        monte_carlo_ran=True,
        mc_mean_delta=0.4,
        mc_p10_delta=None,
        mc_plausible_mean_delta=0.3,
        mc_plausible_p10_delta=None,
    )
    assert evaluation.passed is False
    failed_names = {check.name for check in evaluation.checks if not check.passed}
    assert "deterministic_total_delta" in failed_names
    assert "mc_mean_delta" in failed_names
    assert "mc_plausible_mean_delta" not in failed_names


def test_evaluate_imc_gate_policy_can_pass_with_disabled_monte_carlo() -> None:
    policy = ImcGatePolicy(
        round_id=1,
        require_deterministic=True,
        require_monte_carlo=False,
        deterministic_min_total_delta=0.0,
    )
    evaluation = evaluate_imc_gate_policy(
        policy=policy,
        deterministic_ran=True,
        deterministic_total_delta=1.0,
        monte_carlo_ran=False,
        mc_mean_delta=None,
        mc_p10_delta=None,
        mc_plausible_mean_delta=None,
        mc_plausible_p10_delta=None,
    )
    assert evaluation.passed is True
