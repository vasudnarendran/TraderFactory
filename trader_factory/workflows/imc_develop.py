from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trader_factory.core.paths import ensure_dir, generated_root
from trader_factory.official import ImcProsperityWorkflowResult, run_imc_prosperity_workflow
from trader_factory.simulation import run_deterministic, run_monte_carlo
from trader_factory.workflows.baselines import ImcBaselinePolicy, load_imc_baseline_policy
from trader_factory.workflows.gates import ImcGateEvaluation, ImcGatePolicy, evaluate_imc_gate_policy, load_imc_gate_policy, resolve_imc_gate_policy


@dataclass(slots=True)
class DeterministicGateResult:
    ran: bool
    passed: bool
    baseline_bot_path: Path | None
    days: list[int]
    candidate_totals_by_day: dict[int, float | None]
    baseline_totals_by_day: dict[int, float | None]
    total_delta: float | None
    min_required_delta: float | None


@dataclass(slots=True)
class MonteCarloGateResult:
    ran: bool
    passed: bool
    compare_bot_path: Path | None
    report_json_path: Path | None
    report_markdown_path: Path | None
    mean_delta: float | None
    p10_delta: float | None
    plausible_mean_delta: float | None
    plausible_p10_delta: float | None
    min_mean_delta: float | None
    min_p10_delta: float | None
    min_plausible_mean_delta: float | None
    min_plausible_p10_delta: float | None


@dataclass(slots=True)
class ImcDevelopCycleResult:
    output_dir: Path
    summary_path: Path
    metadata_path: Path
    local_passed: bool
    submitted_officially: bool
    baseline_policy: ImcBaselinePolicy | None
    gate_policy: ImcGatePolicy
    gate_evaluation: ImcGateEvaluation
    deterministic: DeterministicGateResult
    monte_carlo: MonteCarloGateResult
    official_result: ImcProsperityWorkflowResult | None


def _default_output_dir(bot_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ensure_dir(generated_root() / "workflows" / "develop_imc" / f"{stamp}_{bot_path.stem}")


def _jsonify(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    return value


def _sum_known(values: dict[int, float | None]) -> float | None:
    numbers = [value for value in values.values() if value is not None]
    if len(numbers) != len(values):
        return None
    return float(sum(numbers))


def _run_deterministic_gate(
    candidate_bot: Path,
    *,
    baseline_bot: Path | None,
    days: list[int],
    output_dir: Path,
    data_root: Path | None,
    dataset_tag: str | None,
    min_required_delta: float | None,
) -> DeterministicGateResult:
    candidate_totals_by_day: dict[int, float | None] = {}
    baseline_totals_by_day: dict[int, float | None] = {}
    for day in days:
        candidate_result = run_deterministic(
            candidate_bot,
            day=day,
            output_dir=output_dir / "candidate" / f"day_{day}",
            data_root=data_root,
            dataset_tag=dataset_tag,
        )
        candidate_totals_by_day[day] = candidate_result.final_total_pnl
        if baseline_bot is not None:
            baseline_result = run_deterministic(
                baseline_bot,
                day=day,
                output_dir=output_dir / "baseline" / f"day_{day}",
                data_root=data_root,
                dataset_tag=dataset_tag,
            )
            baseline_totals_by_day[day] = baseline_result.final_total_pnl
    if baseline_bot is None:
        return DeterministicGateResult(
            ran=True,
            passed=True,
            baseline_bot_path=None,
            days=days,
            candidate_totals_by_day=candidate_totals_by_day,
            baseline_totals_by_day=baseline_totals_by_day,
            total_delta=None,
            min_required_delta=min_required_delta,
        )
    candidate_total = _sum_known(candidate_totals_by_day)
    baseline_total = _sum_known(baseline_totals_by_day)
    total_delta = None
    if candidate_total is not None and baseline_total is not None:
        total_delta = candidate_total - baseline_total
    passed = True
    if min_required_delta is not None:
        passed = total_delta is not None and total_delta >= min_required_delta
    return DeterministicGateResult(
        ran=True,
        passed=passed,
        baseline_bot_path=baseline_bot,
        days=days,
        candidate_totals_by_day=candidate_totals_by_day,
        baseline_totals_by_day=baseline_totals_by_day,
        total_delta=total_delta,
        min_required_delta=min_required_delta,
    )


def _run_monte_carlo_gate(
    candidate_bot: Path,
    *,
    compare_bot: Path | None,
    output_dir: Path,
    data_root: Path | None,
    dataset_tag: str | None,
    days: list[int],
    families: list[str] | None,
    samples_per_family: int,
    seed: int,
    min_mean_delta: float | None,
    min_p10_delta: float | None,
    min_plausible_mean_delta: float | None,
    min_plausible_p10_delta: float | None,
    quick: bool,
) -> MonteCarloGateResult:
    result = run_monte_carlo(
        candidate_bot,
        compare_bot_path=compare_bot,
        output_dir=output_dir,
        data_root=data_root,
        dataset_tag=dataset_tag,
        days=days,
        families=families,
        samples_per_family=samples_per_family,
        seed=seed,
        quick=quick,
    )
    comparison = result.comparison or {}
    summary = comparison.get("summary", {})
    profiles = comparison.get("by_profile", {})
    mean_delta = summary.get("mean_delta")
    p10_delta = summary.get("p10_delta")
    plausible = profiles.get("plausible", {})
    plausible_mean_delta = plausible.get("mean_delta")
    plausible_p10_delta = plausible.get("p10_delta")

    checks: list[bool] = []
    if compare_bot is not None:
        if min_mean_delta is not None:
            checks.append(mean_delta is not None and float(mean_delta) >= min_mean_delta)
        if min_p10_delta is not None:
            checks.append(p10_delta is not None and float(p10_delta) >= min_p10_delta)
        if min_plausible_mean_delta is not None:
            checks.append(plausible_mean_delta is not None and float(plausible_mean_delta) >= min_plausible_mean_delta)
        if min_plausible_p10_delta is not None:
            checks.append(plausible_p10_delta is not None and float(plausible_p10_delta) >= min_plausible_p10_delta)

    return MonteCarloGateResult(
        ran=True,
        passed=all(checks) if checks else True,
        compare_bot_path=compare_bot,
        report_json_path=result.report_json_path,
        report_markdown_path=result.report_markdown_path,
        mean_delta=float(mean_delta) if mean_delta is not None else None,
        p10_delta=float(p10_delta) if p10_delta is not None else None,
        plausible_mean_delta=float(plausible_mean_delta) if plausible_mean_delta is not None else None,
        plausible_p10_delta=float(plausible_p10_delta) if plausible_p10_delta is not None else None,
        min_mean_delta=min_mean_delta,
        min_p10_delta=min_p10_delta,
        min_plausible_mean_delta=min_plausible_mean_delta,
        min_plausible_p10_delta=min_plausible_p10_delta,
    )


def _write_summary(
    output_path: Path,
    *,
    candidate_bot: Path,
    local_passed: bool,
    submitted_officially: bool,
    force_submit: bool,
    dry_run: bool,
    baseline_policy: ImcBaselinePolicy | None,
    gate_policy: ImcGatePolicy,
    gate_evaluation: ImcGateEvaluation,
    deterministic: DeterministicGateResult,
    monte_carlo: MonteCarloGateResult,
    official_result: ImcProsperityWorkflowResult | None,
) -> Path:
    lines = [
        "# IMC Develop Cycle Summary",
        "",
        f"- Candidate bot: `{candidate_bot}`",
        f"- Local gates passed: `{local_passed}`",
        f"- Submitted officially: `{submitted_officially}`",
        f"- Force submit override: `{force_submit}`",
        f"- Dry run: `{dry_run}`",
        "",
        "## Baseline Policy",
        f"- Loaded policy: `{baseline_policy is not None}`",
        f"- Policy compare bot: `{baseline_policy.compare_bot_path if baseline_policy else 'none'}`",
        f"- Policy official baseline log: `{baseline_policy.official_baseline_log if baseline_policy else 'none'}`",
        f"- Policy official baseline json: `{baseline_policy.official_baseline_json if baseline_policy else 'none'}`",
        "",
        "## Gate Policy",
        f"- Round id: `{gate_policy.round_id}`",
        f"- Require deterministic: `{gate_policy.require_deterministic}`",
        f"- Require Monte Carlo: `{gate_policy.require_monte_carlo}`",
        f"- Deterministic min total delta: `{gate_policy.deterministic_min_total_delta}`",
        f"- Monte Carlo min mean delta: `{gate_policy.mc_min_mean_delta}`",
        f"- Monte Carlo min P10 delta: `{gate_policy.mc_min_p10_delta}`",
        f"- Plausible min mean delta: `{gate_policy.mc_min_plausible_mean_delta}`",
        f"- Plausible min P10 delta: `{gate_policy.mc_min_plausible_p10_delta}`",
        f"- Notes: `{gate_policy.notes or ''}`",
        "",
        "## Gate Evaluation",
        f"- Overall passed: `{gate_evaluation.passed}`",
        "",
        "## Deterministic Gate",
        f"- Ran: `{deterministic.ran}`",
        f"- Passed: `{deterministic.passed}`",
        f"- Baseline bot: `{deterministic.baseline_bot_path or 'none'}`",
        f"- Days: `{deterministic.days}`",
    ]
    for day in deterministic.days:
        lines.append(
            f"- Day {day}: candidate `{deterministic.candidate_totals_by_day.get(day)}`"
            f", baseline `{deterministic.baseline_totals_by_day.get(day)}`"
        )
    lines.append(f"- Total delta: `{deterministic.total_delta}`")
    lines.append(f"- Minimum required total delta: `{deterministic.min_required_delta}`")
    lines.extend(["", "## Monte Carlo Gate"])
    lines.extend(
        [
            f"- Ran: `{monte_carlo.ran}`",
            f"- Passed: `{monte_carlo.passed}`",
            f"- Compare bot: `{monte_carlo.compare_bot_path or 'none'}`",
            f"- Mean delta: `{monte_carlo.mean_delta}`",
            f"- P10 delta: `{monte_carlo.p10_delta}`",
            f"- Plausible mean delta: `{monte_carlo.plausible_mean_delta}`",
            f"- Plausible P10 delta: `{monte_carlo.plausible_p10_delta}`",
            f"- Minimum mean delta: `{monte_carlo.min_mean_delta}`",
            f"- Minimum P10 delta: `{monte_carlo.min_p10_delta}`",
            f"- Minimum plausible mean delta: `{monte_carlo.min_plausible_mean_delta}`",
            f"- Minimum plausible P10 delta: `{monte_carlo.min_plausible_p10_delta}`",
            f"- Report: `{monte_carlo.report_markdown_path or 'none'}`",
        ]
    )
    lines.extend(["", "## Gate Checks"])
    for check in gate_evaluation.checks:
        lines.append(
            f"- `{check.name}`: passed `{check.passed}`, actual `{check.actual}`, minimum `{check.min_required}`, reason `{check.reason}`"
        )
    lines.extend(["", "## Official"])
    if official_result is None:
        lines.append("- Official submission was skipped.")
    else:
        lines.extend(
            [
                f"- Submission id: `{official_result.run_result.submission_id}`",
                f"- Output dir: `{official_result.run_result.output_dir}`",
                f"- Queue wait seconds: `{official_result.queue_wait_seconds}`",
                f"- Counts for team: `{official_result.counts_for_team}`",
                f"- Superseded by: `{official_result.superseded_by_submission_id}`",
                f"- Profit delta vs baseline: `{official_result.comparison_profit_delta}`",
                f"- Workflow summary: `{official_result.summary_path}`",
            ]
        )
    lines.append("")
    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def run_imc_develop_cycle(
    bot_path: str | Path,
    *,
    compare_bot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    data_root: str | Path | None = None,
    dataset_tag: str | None = None,
    deterministic_days: list[int] | tuple[int, ...] = (-1, -2),
    skip_deterministic: bool = False,
    skip_monte_carlo: bool = False,
    deterministic_min_total_delta: float | None = None,
    mc_families: list[str] | tuple[str, ...] | None = None,
    mc_samples_per_family: int = 2,
    mc_seed: int = 52,
    mc_min_mean_delta: float | None = None,
    mc_min_p10_delta: float | None = None,
    mc_min_plausible_mean_delta: float | None = None,
    mc_min_plausible_p10_delta: float | None = None,
    force_submit: bool = False,
    dry_run: bool = False,
    round_id: int = 1,
    chrome_app: str = "Google Chrome",
    chrome_profile_dir: str = "Default",
    game_url: str = "https://prosperity.imc.com/game",
    api_root: str = "https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod",
    poll_seconds: float = 15.0,
    timeout_seconds: float = 900.0,
    queue_poll_seconds: float = 20.0,
    queue_timeout_seconds: float = 1800.0,
    skip_analysis: bool = False,
    baseline_log: str | Path | None = None,
    baseline_json: str | Path | None = None,
) -> ImcDevelopCycleResult:
    candidate_bot = Path(bot_path).expanduser().resolve()
    baseline_policy = load_imc_baseline_policy(round_id)
    persisted_gate_policy = load_imc_gate_policy(round_id)
    gate_policy = resolve_imc_gate_policy(
        round_id=round_id,
        base_policy=persisted_gate_policy,
        require_deterministic=(False if skip_deterministic else None),
        require_monte_carlo=(False if skip_monte_carlo else None),
        deterministic_min_total_delta=deterministic_min_total_delta,
        mc_min_mean_delta=mc_min_mean_delta,
        mc_min_p10_delta=mc_min_p10_delta,
        mc_min_plausible_mean_delta=mc_min_plausible_mean_delta,
        mc_min_plausible_p10_delta=mc_min_plausible_p10_delta,
    )
    compare_bot = Path(compare_bot_path).expanduser().resolve() if compare_bot_path else None
    if compare_bot is None and baseline_policy is not None:
        compare_bot = baseline_policy.compare_bot_path
    root = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir(candidate_bot)
    ensure_dir(root)
    resolved_data_root = Path(data_root).expanduser().resolve() if data_root else None
    day_list = [int(day) for day in deterministic_days]
    resolved_baseline_log = Path(baseline_log).expanduser().resolve() if baseline_log else None
    resolved_baseline_json = Path(baseline_json).expanduser().resolve() if baseline_json else None
    if resolved_baseline_log is None and baseline_policy is not None:
        resolved_baseline_log = baseline_policy.official_baseline_log
    if resolved_baseline_json is None and baseline_policy is not None:
        resolved_baseline_json = baseline_policy.official_baseline_json

    deterministic_result = DeterministicGateResult(
        ran=False,
        passed=True,
        baseline_bot_path=compare_bot,
        days=day_list,
        candidate_totals_by_day={},
        baseline_totals_by_day={},
        total_delta=None,
        min_required_delta=gate_policy.deterministic_min_total_delta,
    )
    if not skip_deterministic:
        deterministic_result = _run_deterministic_gate(
            candidate_bot,
            baseline_bot=compare_bot,
            days=day_list,
            output_dir=root / "deterministic",
            data_root=resolved_data_root,
            dataset_tag=dataset_tag,
            min_required_delta=(gate_policy.deterministic_min_total_delta if compare_bot is not None else None),
        )

    monte_carlo_result = MonteCarloGateResult(
        ran=False,
        passed=True,
        compare_bot_path=compare_bot,
        report_json_path=None,
        report_markdown_path=None,
        mean_delta=None,
        p10_delta=None,
        plausible_mean_delta=None,
        plausible_p10_delta=None,
        min_mean_delta=gate_policy.mc_min_mean_delta,
        min_p10_delta=gate_policy.mc_min_p10_delta,
        min_plausible_mean_delta=gate_policy.mc_min_plausible_mean_delta,
        min_plausible_p10_delta=gate_policy.mc_min_plausible_p10_delta,
    )
    if not skip_monte_carlo:
        monte_carlo_result = _run_monte_carlo_gate(
            candidate_bot,
            compare_bot=compare_bot,
            output_dir=root / "monte_carlo",
            data_root=resolved_data_root,
            dataset_tag=dataset_tag,
            days=day_list,
            families=list(mc_families) if mc_families is not None else None,
            samples_per_family=mc_samples_per_family,
            seed=mc_seed,
            min_mean_delta=(gate_policy.mc_min_mean_delta if compare_bot is not None else None),
            min_p10_delta=(gate_policy.mc_min_p10_delta if compare_bot is not None else None),
            min_plausible_mean_delta=(gate_policy.mc_min_plausible_mean_delta if compare_bot is not None else None),
            min_plausible_p10_delta=(gate_policy.mc_min_plausible_p10_delta if compare_bot is not None else None),
            quick=True,
        )

    gate_evaluation = evaluate_imc_gate_policy(
        policy=gate_policy,
        deterministic_ran=deterministic_result.ran,
        deterministic_total_delta=deterministic_result.total_delta,
        monte_carlo_ran=monte_carlo_result.ran,
        mc_mean_delta=monte_carlo_result.mean_delta,
        mc_p10_delta=monte_carlo_result.p10_delta,
        mc_plausible_mean_delta=monte_carlo_result.plausible_mean_delta,
        mc_plausible_p10_delta=monte_carlo_result.plausible_p10_delta,
    )
    local_passed = gate_evaluation.passed
    official_result: ImcProsperityWorkflowResult | None = None
    submitted_officially = False
    if (local_passed or force_submit) and not dry_run:
        official_result = run_imc_prosperity_workflow(
            candidate_bot,
            round_id=round_id,
            output_dir=root / "official",
            chrome_app=chrome_app,
            chrome_profile_dir=chrome_profile_dir,
            game_url=game_url,
            api_root=api_root,
            poll_seconds=poll_seconds,
            timeout_seconds=timeout_seconds,
            queue_poll_seconds=queue_poll_seconds,
            queue_timeout_seconds=queue_timeout_seconds,
            run_analysis=not skip_analysis,
            baseline_log=resolved_baseline_log,
            baseline_json=resolved_baseline_json,
        )
        submitted_officially = True

    summary_path = _write_summary(
        root / "summary.md",
        candidate_bot=candidate_bot,
        local_passed=local_passed,
        submitted_officially=submitted_officially,
        force_submit=force_submit,
        dry_run=dry_run,
        baseline_policy=baseline_policy,
        gate_policy=gate_policy,
        gate_evaluation=gate_evaluation,
        deterministic=deterministic_result,
        monte_carlo=monte_carlo_result,
        official_result=official_result,
    )
    metadata = {
        "candidate_bot": str(candidate_bot),
        "compare_bot": str(compare_bot) if compare_bot else None,
        "baseline_policy": baseline_policy.to_dict() if baseline_policy else None,
        "gate_policy": gate_policy.to_dict(),
        "gate_evaluation": {
            "passed": gate_evaluation.passed,
            "checks": [asdict(check) for check in gate_evaluation.checks],
        },
        "local_passed": local_passed,
        "submitted_officially": submitted_officially,
        "force_submit": force_submit,
        "dry_run": dry_run,
        "deterministic": _jsonify(asdict(deterministic_result)),
        "monte_carlo": _jsonify(asdict(monte_carlo_result)),
        "official_result": {
            "submission_id": official_result.run_result.submission_id,
            "summary_path": str(official_result.summary_path),
            "metadata_path": str(official_result.metadata_path),
            "counts_for_team": official_result.counts_for_team,
            "superseded_by_submission_id": official_result.superseded_by_submission_id,
            "comparison_profit_delta": official_result.comparison_profit_delta,
        }
        if official_result is not None
        else None,
    }
    metadata_path = root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    return ImcDevelopCycleResult(
        output_dir=root,
        summary_path=summary_path,
        metadata_path=metadata_path,
        local_passed=local_passed,
        submitted_officially=submitted_officially,
        baseline_policy=baseline_policy,
        gate_policy=gate_policy,
        gate_evaluation=gate_evaluation,
        deterministic=deterministic_result,
        monte_carlo=monte_carlo_result,
        official_result=official_result,
    )
