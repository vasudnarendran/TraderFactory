from __future__ import annotations

import argparse
import json
from pathlib import Path

from trader_factory.core.specs import CompetitionSpec
from trader_factory.core.validation import render_validation_markdown, validate_competition_spec
from trader_factory.diagnostics import (
    run_aggressive_markout_report,
    run_boundary_probe_report,
    run_official_trade_quality,
    run_passive_ladder_report,
)
from trader_factory.generation import render_markdown_plan, scaffold_trader_project
from trader_factory.generation.spec_templates import available_spec_templates, render_spec_template
from trader_factory.official import (
    run_imc_prosperity_submission,
    run_imc_prosperity_workflow,
)
from trader_factory.optimization import run_cmaes
from trader_factory.probes import PROBE_LIBRARY, scaffold_probe_workspace
from trader_factory.viewer import run_viewer_server
from trader_factory.workflows import (
    baseline_policy_path,
    describe_imc_baseline_policy,
    describe_imc_gate_policy,
    gate_policy_path,
    load_imc_baseline_policy,
    load_imc_gate_policy,
    run_imc_develop_cycle,
    set_imc_baseline_policy,
    set_imc_gate_policy,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TraderFactory unified CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Render a round plan from a competition spec.")
    plan.add_argument("spec", type=Path, help="Path to a JSON competition spec.")
    plan.add_argument("--output", type=Path, default=None, help="Optional markdown output path.")

    validate = subparsers.add_parser("validate-spec", help="Validate a competition spec and surface missing structural inputs.")
    validate.add_argument("spec", type=Path, help="Path to a JSON competition spec.")
    validate.add_argument("--output", type=Path, default=None, help="Optional markdown output path.")
    validate.add_argument("--json-output", type=Path, default=None, help="Optional JSON output path.")

    spec_template = subparsers.add_parser("spec-template", help="Render a built-in round intake spec template.")
    spec_template.add_argument("template", choices=[template.name for template in available_spec_templates()], help="Named intake template profile.")
    spec_template.add_argument("--competition-name", default="NewCompetition", help="Competition name to place in the template.")
    spec_template.add_argument("--round-name", default="round_1", help="Round name to place in the template.")
    spec_template.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")

    deterministic = subparsers.add_parser("deterministic", help="Run TraderFactory deterministic replay.")
    deterministic.add_argument("bot", type=Path, help="Path to the trader Python file.")
    deterministic.add_argument("--day", type=int, default=-1, help="Day to replay.")
    deterministic.add_argument("--output", type=Path, default=None, help="Optional output directory.")
    deterministic.add_argument("--data-root", type=Path, default=None, help="Optional replay data directory override.")
    deterministic.add_argument("--dataset-tag", default=None, help="Optional replay dataset tag override.")

    monte = subparsers.add_parser("monte-carlo", help="Run TraderFactory headless Monte Carlo robustness.")
    monte.add_argument("bot", type=Path, help="Path to the trader Python file.")
    monte.add_argument("--compare-bot", type=Path, default=None, help="Optional comparison trader Python file.")
    monte.add_argument("--output-dir", type=Path, default=None, help="Optional output directory.")
    monte.add_argument("--data-root", type=Path, default=None, help="Optional replay data directory override.")
    monte.add_argument("--dataset-tag", default=None, help="Optional replay dataset tag override.")
    monte.add_argument("--days", type=int, nargs="*", default=[-1, -2], help="Replay days to include.")
    monte.add_argument("--samples-per-family", type=int, default=4, help="Monte Carlo samples per family.")
    monte.add_argument("--families", nargs="*", default=None, help="Optional family subset.")
    monte.add_argument("--seed", type=int, default=52, help="Random seed.")
    monte.add_argument("--quick", action="store_true", help="Run quick preset.")
    monte.add_argument("--heavy", action="store_true", help="Run heavy preset.")

    otq = subparsers.add_parser("official-trade-quality", help="Run the official trade quality analyzer.")
    otq.add_argument("log_path", type=Path, help="Primary official .log file.")
    otq.add_argument("--baseline", type=Path, default=None, help="Optional baseline official .log file.")
    otq.add_argument("--primary-json", type=Path, default=None, help="Optional primary official .json file.")
    otq.add_argument("--baseline-json", type=Path, default=None, help="Optional baseline official .json file.")
    otq.add_argument("--output-dir", type=Path, default=None, help="Optional TraderFactory output directory.")
    otq.add_argument("--prefix", default="", help="Optional output prefix.")

    boundary = subparsers.add_parser("boundary-probe", help="Run the boundary probe analyzer.")
    boundary.add_argument("log_path", type=Path, help="Official .log file.")
    boundary.add_argument("--output-dir", type=Path, default=None, help="Optional TraderFactory output directory.")

    ladder = subparsers.add_parser("passive-ladder", help="Run the passive ladder analyzer.")
    ladder.add_argument("log_path", type=Path, help="Official .log file.")
    ladder.add_argument("--json-path", type=Path, default=None, help="Optional official .json file.")
    ladder.add_argument("--output-dir", type=Path, default=None, help="Optional TraderFactory output directory.")

    aggressive = subparsers.add_parser("aggressive-markout", help="Run the aggressive markout analyzer.")
    aggressive.add_argument("log_path", type=Path, help="Official .log file.")
    aggressive.add_argument("--json-path", type=Path, default=None, help="Optional official .json file.")
    aggressive.add_argument("--output-dir", type=Path, default=None, help="Optional TraderFactory output directory.")

    cmaes = subparsers.add_parser("cmaes", help="Run config-driven CMA-ES optimization.")
    cmaes.add_argument("config", type=Path, help="Path to the optimization JSON config.")
    cmaes.add_argument("--output-dir", type=Path, default=None, help="Optional output directory override.")
    cmaes.add_argument("--max-iter", type=int, default=None, help="Optional max-iteration override.")
    cmaes.add_argument("--population", type=int, default=None, help="Optional population override.")
    cmaes.add_argument("--parents", type=int, default=None, help="Optional parent-count override.")
    cmaes.add_argument("--sigma0", type=float, default=None, help="Optional initial sigma override.")
    cmaes.add_argument("--seed", type=int, default=None, help="Optional random-seed override.")

    probe = subparsers.add_parser("probe-scaffold", help="Scaffold a research probe workspace from a baseline bot.")
    probe.add_argument("kind", choices=sorted(PROBE_LIBRARY), help="Probe kind to scaffold.")
    probe.add_argument("baseline_bot", type=Path, help="Baseline bot file the probe is built around.")
    probe.add_argument("--name", default=None, help="Optional probe workspace name.")
    probe.add_argument("--output-dir", type=Path, default=None, help="Optional workspace directory override.")
    probe.add_argument("--product", default="PRIMARY_PRODUCT", help="Primary product symbol for the probe.")
    probe.add_argument("--context", default=None, help="Optional probe context label, mainly for aggressive probes.")

    scaffold = subparsers.add_parser("scaffold-project", help="Generate a baseline trader project from a competition spec.")
    scaffold.add_argument("spec", type=Path, help="Path to the competition spec JSON.")
    scaffold.add_argument("--output-dir", type=Path, default=None, help="Optional target project directory.")
    scaffold.add_argument("--name", default=None, help="Optional project name override.")

    viewer = subparsers.add_parser("viewer", help="Run the TraderFactory Monte Carlo viewer.")
    viewer.add_argument(
        "--results-dir",
        type=Path,
        action="append",
        dest="results_dirs",
        default=None,
        help="Optional result directory root to scan recursively. Can be passed multiple times.",
    )
    viewer.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    viewer.add_argument("--port", type=int, default=8012, help="Port to bind.")

    official = subparsers.add_parser("official-submit-imc", help="Submit a bot to IMC Prosperity and collect the result zip.")
    official.add_argument("bot", type=Path, help="Path to the trader Python file to submit.")
    official.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")
    official.add_argument("--output-dir", type=Path, default=None, help="Optional output directory.")
    official.add_argument("--chrome-app", default="Google Chrome", help="macOS application name for Chrome.")
    official.add_argument("--chrome-profile-dir", default="Default", help="Chrome profile directory, default Default.")
    official.add_argument("--game-url", default="https://prosperity.imc.com/game", help="Prosperity landing page.")
    official.add_argument(
        "--api-root",
        default="https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod",
        help="Prosperity API root discovered from the HAR.",
    )
    official.add_argument("--poll-seconds", type=float, default=15.0, help="Polling interval while the run is simulating.")
    official.add_argument("--timeout-seconds", type=float, default=900.0, help="Maximum time to wait for the run.")
    official.add_argument("--baseline-log", type=Path, default=None, help="Optional baseline official .log for automatic comparison.")
    official.add_argument("--baseline-json", type=Path, default=None, help="Optional baseline official .json for automatic comparison.")
    official.add_argument("--skip-analysis", action="store_true", help="Skip automatic official trade-quality analysis.")

    official_cycle = subparsers.add_parser(
        "official-cycle-imc",
        help="Queue-aware IMC Prosperity submission workflow with automatic baseline snapshot.",
    )
    official_cycle.add_argument("bot", type=Path, help="Path to the trader Python file to submit.")
    official_cycle.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")
    official_cycle.add_argument("--output-dir", type=Path, default=None, help="Optional output directory.")
    official_cycle.add_argument("--chrome-app", default="Google Chrome", help="macOS application name for Chrome.")
    official_cycle.add_argument("--chrome-profile-dir", default="Default", help="Chrome profile directory, default Default.")
    official_cycle.add_argument("--game-url", default="https://prosperity.imc.com/game", help="Prosperity landing page.")
    official_cycle.add_argument(
        "--api-root",
        default="https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod",
        help="Prosperity API root discovered from the HAR.",
    )
    official_cycle.add_argument("--poll-seconds", type=float, default=15.0, help="Polling interval while the new run is simulating.")
    official_cycle.add_argument("--timeout-seconds", type=float, default=900.0, help="Maximum time to wait for the new run.")
    official_cycle.add_argument(
        "--queue-poll-seconds",
        type=float,
        default=20.0,
        help="Polling interval while waiting for the team submission slot to clear.",
    )
    official_cycle.add_argument(
        "--queue-timeout-seconds",
        type=float,
        default=1800.0,
        help="Maximum time to wait for the team submission slot.",
    )
    official_cycle.add_argument(
        "--baseline-log",
        type=Path,
        default=None,
        help="Optional explicit baseline official .log. If omitted, the current active submission is downloaded automatically.",
    )
    official_cycle.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
        help="Optional explicit baseline official .json. If omitted, the current active submission is downloaded automatically.",
    )
    official_cycle.add_argument("--skip-analysis", action="store_true", help="Skip automatic official trade-quality analysis.")

    develop_cycle = subparsers.add_parser(
        "develop-cycle-imc",
        help="Development-mode pipeline: local gate first, official submission second.",
    )
    develop_cycle.add_argument("bot", type=Path, help="Candidate trader Python file.")
    develop_cycle.add_argument("--compare-bot", type=Path, default=None, help="Optional local baseline trader for deterministic and Monte Carlo comparison.")
    develop_cycle.add_argument("--output-dir", type=Path, default=None, help="Optional output directory.")
    develop_cycle.add_argument("--data-root", type=Path, default=None, help="Optional replay data directory override.")
    develop_cycle.add_argument("--dataset-tag", default=None, help="Optional replay dataset tag override.")
    develop_cycle.add_argument("--deterministic-days", type=int, nargs="*", default=[-1, -2], help="Days for local deterministic gating.")
    develop_cycle.add_argument("--skip-deterministic", action="store_true", help="Skip deterministic gating.")
    develop_cycle.add_argument("--skip-monte-carlo", action="store_true", help="Skip Monte Carlo gating.")
    develop_cycle.add_argument(
        "--deterministic-min-total-delta",
        type=float,
        default=None,
        help="Minimum candidate minus baseline deterministic total delta required to pass.",
    )
    develop_cycle.add_argument(
        "--mc-families",
        nargs="*",
        default=None,
        help="Optional Monte Carlo family subset. Defaults to quick plausible families.",
    )
    develop_cycle.add_argument("--mc-samples-per-family", type=int, default=2, help="Monte Carlo samples per family.")
    develop_cycle.add_argument("--mc-seed", type=int, default=52, help="Monte Carlo random seed.")
    develop_cycle.add_argument("--mc-min-mean-delta", type=float, default=None, help="Minimum overall Monte Carlo mean delta vs local baseline.")
    develop_cycle.add_argument("--mc-min-p10-delta", type=float, default=None, help="Optional minimum overall Monte Carlo p10 delta vs local baseline.")
    develop_cycle.add_argument(
        "--mc-min-plausible-mean-delta",
        type=float,
        default=None,
        help="Minimum plausible-profile Monte Carlo mean delta vs local baseline.",
    )
    develop_cycle.add_argument(
        "--mc-min-plausible-p10-delta",
        type=float,
        default=None,
        help="Optional minimum plausible-profile Monte Carlo p10 delta vs local baseline.",
    )
    develop_cycle.add_argument("--force-submit", action="store_true", help="Submit officially even if local gates fail.")
    develop_cycle.add_argument("--dry-run", action="store_true", help="Run the local gates and summary only, without using an official submission slot.")
    develop_cycle.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")
    develop_cycle.add_argument("--chrome-app", default="Google Chrome", help="macOS application name for Chrome.")
    develop_cycle.add_argument("--chrome-profile-dir", default="Default", help="Chrome profile directory, default Default.")
    develop_cycle.add_argument("--game-url", default="https://prosperity.imc.com/game", help="Prosperity landing page.")
    develop_cycle.add_argument(
        "--api-root",
        default="https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod",
        help="Prosperity API root discovered from the HAR.",
    )
    develop_cycle.add_argument("--poll-seconds", type=float, default=15.0, help="Polling interval while the official run is simulating.")
    develop_cycle.add_argument("--timeout-seconds", type=float, default=900.0, help="Maximum time to wait for the official run.")
    develop_cycle.add_argument("--queue-poll-seconds", type=float, default=20.0, help="Polling interval while waiting for the team submission slot.")
    develop_cycle.add_argument("--queue-timeout-seconds", type=float, default=1800.0, help="Maximum time to wait for the team submission slot.")
    develop_cycle.add_argument("--baseline-log", type=Path, default=None, help="Optional explicit official baseline .log for the official comparison.")
    develop_cycle.add_argument("--baseline-json", type=Path, default=None, help="Optional explicit official baseline .json for the official comparison.")
    develop_cycle.add_argument("--skip-analysis", action="store_true", help="Skip automatic official trade-quality analysis after official submission.")

    baseline_show = subparsers.add_parser("baseline-imc-show", help="Show the persisted IMC baseline policy for a round.")
    baseline_show.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")

    baseline_set = subparsers.add_parser("baseline-imc-set", help="Persist the IMC baseline policy for a round.")
    baseline_set.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")
    baseline_set.add_argument("--compare-bot", type=Path, default=None, help="Local baseline trader to use for development gating.")
    baseline_set.add_argument("--official-baseline-log", type=Path, default=None, help="Optional official baseline .log to pin.")
    baseline_set.add_argument("--official-baseline-json", type=Path, default=None, help="Optional official baseline .json to pin.")
    baseline_set.add_argument("--notes", default="", help="Optional note for the baseline policy.")

    gate_show = subparsers.add_parser("gate-imc-show", help="Show the persisted IMC gate policy for a round.")
    gate_show.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")

    gate_set = subparsers.add_parser("gate-imc-set", help="Persist the IMC gate policy for a round.")
    gate_set.add_argument("--round-id", type=int, default=1, help="Prosperity round id, default 1.")
    gate_set.add_argument("--require-deterministic", dest="require_deterministic", action="store_true", default=None, help="Require deterministic gating.")
    gate_set.add_argument("--no-require-deterministic", dest="require_deterministic", action="store_false", help="Disable deterministic gating in the policy.")
    gate_set.add_argument("--require-monte-carlo", dest="require_monte_carlo", action="store_true", default=None, help="Require Monte Carlo gating.")
    gate_set.add_argument("--no-require-monte-carlo", dest="require_monte_carlo", action="store_false", help="Disable Monte Carlo gating in the policy.")
    gate_set.add_argument("--deterministic-min-total-delta", type=float, default=None, help="Minimum deterministic total delta.")
    gate_set.add_argument("--mc-min-mean-delta", type=float, default=None, help="Minimum Monte Carlo mean delta.")
    gate_set.add_argument("--mc-min-p10-delta", type=float, default=None, help="Minimum Monte Carlo p10 delta.")
    gate_set.add_argument("--mc-min-plausible-mean-delta", type=float, default=None, help="Minimum plausible-profile Monte Carlo mean delta.")
    gate_set.add_argument("--mc-min-plausible-p10-delta", type=float, default=None, help="Minimum plausible-profile Monte Carlo p10 delta.")
    gate_set.add_argument("--notes", default="", help="Optional note for the gate policy.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "plan":
        spec = CompetitionSpec.from_json(args.spec)
        plan = render_markdown_plan(spec)
        if args.output is None:
            print(plan)
        else:
            args.output.write_text(plan)
            print(f"Wrote plan to {args.output}")
        return

    if args.command == "validate-spec":
        spec = CompetitionSpec.from_json(args.spec)
        report = validate_competition_spec(spec)
        rendered = render_validation_markdown(report)
        if args.output is None:
            print(rendered)
        else:
            args.output.write_text(rendered + "\n")
            print(f"Wrote validation report to {args.output}")
        if args.json_output is not None:
            args.json_output.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
            print(f"Wrote validation JSON to {args.json_output}")
        return

    if args.command == "spec-template":
        payload = render_spec_template(
            args.template,
            competition_name=args.competition_name,
            round_name=args.round_name,
        )
        rendered = json.dumps(payload, indent=2) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.write_text(rendered)
            print(f"Wrote spec template to {args.output}")
        return

    if args.command == "deterministic":
        from trader_factory.simulation import run_deterministic

        result = run_deterministic(
            args.bot,
            day=args.day,
            output_dir=args.output,
            data_root=args.data_root,
            dataset_tag=args.dataset_tag,
        )
        print(f"Output dir: {result.output_dir}")
        print(f"Summary: {result.summary_path}")
        print(f"Final total PnL: {result.final_total_pnl}")
        return

    if args.command == "gate-imc-show":
        policy = load_imc_gate_policy(args.round_id)
        print(describe_imc_gate_policy(policy))
        if policy is not None:
            print(f"\nPolicy path: {gate_policy_path(args.round_id)}")
        return

    if args.command == "gate-imc-set":
        policy, path = set_imc_gate_policy(
            round_id=args.round_id,
            require_deterministic=args.require_deterministic,
            require_monte_carlo=args.require_monte_carlo,
            deterministic_min_total_delta=args.deterministic_min_total_delta,
            mc_min_mean_delta=args.mc_min_mean_delta,
            mc_min_p10_delta=args.mc_min_p10_delta,
            mc_min_plausible_mean_delta=args.mc_min_plausible_mean_delta,
            mc_min_plausible_p10_delta=args.mc_min_plausible_p10_delta,
            notes=args.notes,
        )
        print(describe_imc_gate_policy(policy))
        print(f"\nSaved to: {path}")
        return

    if args.command == "monte-carlo":
        from trader_factory.simulation import run_monte_carlo

        result = run_monte_carlo(
            args.bot,
            compare_bot_path=args.compare_bot,
            output_dir=args.output_dir,
            data_root=args.data_root,
            dataset_tag=args.dataset_tag,
            days=tuple(args.days),
            samples_per_family=args.samples_per_family,
            families=args.families,
            seed=args.seed,
            quick=args.quick,
            heavy=args.heavy,
        )
        print(f"Output dir: {result.output_dir}")
        print(f"JSON: {result.report_json_path}")
        print(f"Report: {result.report_markdown_path}")
        print(f"Mean total PnL: {result.mean_total_pnl}")
        print(f"Std total PnL: {result.std_total_pnl}")
        print(f"Median total PnL: {result.median_total_pnl}")
        return

    if args.command == "official-trade-quality":
        result = run_official_trade_quality(
            args.log_path,
            baseline_log=args.baseline,
            primary_json=args.primary_json,
            baseline_json=args.baseline_json,
            output_dir=args.output_dir,
            output_prefix=args.prefix,
        )
        print(f"Output dir: {result.output_dir}")
        if result.summary_path:
            print(f"Summary: {result.summary_path}")
        return

    if args.command == "boundary-probe":
        result = run_boundary_probe_report(args.log_path, output_dir=args.output_dir)
        print(f"Output dir: {result.output_dir}")
        print(f"Summary: {result.summary_path}")
        return

    if args.command == "passive-ladder":
        result = run_passive_ladder_report(args.log_path, json_path=args.json_path, output_dir=args.output_dir)
        print(f"Output dir: {result.output_dir}")
        print(f"Summary: {result.summary_path}")
        return

    if args.command == "aggressive-markout":
        result = run_aggressive_markout_report(args.log_path, json_path=args.json_path, output_dir=args.output_dir)
        print(f"Output dir: {result.output_dir}")
        print(f"Summary: {result.summary_path}")
        return

    if args.command == "cmaes":
        result = run_cmaes(
            args.config,
            output_dir=args.output_dir,
            max_iter=args.max_iter,
            population=args.population,
            parents=args.parents,
            sigma0=args.sigma0,
            seed=args.seed,
        )
        print(f"Output dir: {result.output_dir}")
        print(f"Best bot: {result.best_bot_path}")
        print(f"JSON: {result.json_path}")
        print(f"Report: {result.report_path}")
        print(f"Best objective: {result.best_objective}")
        print(f"Best average: {result.best_average}")
        return

    if args.command == "probe-scaffold":
        result = scaffold_probe_workspace(
            args.kind,
            args.baseline_bot,
            probe_name=args.name,
            output_dir=args.output_dir,
            product=args.product,
            context=args.context,
        )
        print(f"Workspace: {result.output_dir}")
        print(f"README: {result.readme_path}")
        print(f"Config: {result.config_path}")
        print(f"Submission scaffold: {result.submission_probe_path}")
        print(f"Notes: {result.notes_path}")
        return

    if args.command == "scaffold-project":
        result = scaffold_trader_project(
            args.spec,
            output_dir=args.output_dir,
            project_name=args.name,
        )
        print(f"Project dir: {result.output_dir}")
        print(f"README: {result.readme_path}")
        print(f"Spec copy: {result.spec_copy_path}")
        print(f"Plan: {result.plan_path}")
        print(f"Trader: {result.trader_path}")
        print(f"Params: {result.params_path}")
        print(f"Notes: {result.notes_path}")
        print(f"Experiments: {result.experiments_dir}")
        print(f"Research: {result.research_dir}")
        return

    if args.command == "viewer":
        run_viewer_server(results_dirs=args.results_dirs, host=args.host, port=args.port)
        return

    if args.command == "official-submit-imc":
        result = run_imc_prosperity_submission(
            args.bot,
            round_id=args.round_id,
            output_dir=args.output_dir,
            chrome_app=args.chrome_app,
            chrome_profile_dir=args.chrome_profile_dir,
            game_url=args.game_url,
            api_root=args.api_root,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
            run_analysis=not args.skip_analysis,
            baseline_log=args.baseline_log,
            baseline_json=args.baseline_json,
        )
        print(f"Output dir: {result.output_dir}")
        print(f"Submission id: {result.submission_id}")
        print(f"Round id: {result.round_id}")
        print(f"Auth mode: {result.auth_mode}")
        print(f"ZIP: {result.zip_path}")
        if result.python_path:
            print(f"Bot copy: {result.python_path}")
        if result.json_path:
            print(f"JSON: {result.json_path}")
        if result.log_path:
            print(f"LOG: {result.log_path}")
        if result.analysis_result and result.analysis_result.summary_path:
            print(f"Analysis summary: {result.analysis_result.summary_path}")
        return

    if args.command == "official-cycle-imc":
        result = run_imc_prosperity_workflow(
            args.bot,
            round_id=args.round_id,
            output_dir=args.output_dir,
            chrome_app=args.chrome_app,
            chrome_profile_dir=args.chrome_profile_dir,
            game_url=args.game_url,
            api_root=args.api_root,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
            queue_poll_seconds=args.queue_poll_seconds,
            queue_timeout_seconds=args.queue_timeout_seconds,
            run_analysis=not args.skip_analysis,
            baseline_log=args.baseline_log,
            baseline_json=args.baseline_json,
        )
        print(f"Submission dir: {result.run_result.output_dir}")
        print(f"Submission id: {result.run_result.submission_id}")
        print(f"Queue wait seconds: {result.queue_wait_seconds}")
        if result.baseline_submission is not None:
            print(f"Baseline submission id: {result.baseline_submission.id}")
        if result.latest_active_submission is not None:
            print(f"Current active submission id: {result.latest_active_submission.id}")
        print(f"Counts for team: {result.counts_for_team}")
        if result.superseded_by_submission_id is not None:
            print(f"Superseded by submission id: {result.superseded_by_submission_id}")
        if result.comparison_profit_delta is not None:
            print(f"Profit delta vs baseline: {result.comparison_profit_delta}")
        print(f"Summary: {result.summary_path}")
        print(f"Workflow metadata: {result.metadata_path}")
        return

    if args.command == "develop-cycle-imc":
        result = run_imc_develop_cycle(
            args.bot,
            compare_bot_path=args.compare_bot,
            output_dir=args.output_dir,
            data_root=args.data_root,
            dataset_tag=args.dataset_tag,
            deterministic_days=args.deterministic_days,
            skip_deterministic=args.skip_deterministic,
            skip_monte_carlo=args.skip_monte_carlo,
            deterministic_min_total_delta=args.deterministic_min_total_delta,
            mc_families=args.mc_families,
            mc_samples_per_family=args.mc_samples_per_family,
            mc_seed=args.mc_seed,
            mc_min_mean_delta=args.mc_min_mean_delta,
            mc_min_p10_delta=args.mc_min_p10_delta,
            mc_min_plausible_mean_delta=args.mc_min_plausible_mean_delta,
            mc_min_plausible_p10_delta=args.mc_min_plausible_p10_delta,
            force_submit=args.force_submit,
            dry_run=args.dry_run,
            round_id=args.round_id,
            chrome_app=args.chrome_app,
            chrome_profile_dir=args.chrome_profile_dir,
            game_url=args.game_url,
            api_root=args.api_root,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
            queue_poll_seconds=args.queue_poll_seconds,
            queue_timeout_seconds=args.queue_timeout_seconds,
            skip_analysis=args.skip_analysis,
            baseline_log=args.baseline_log,
            baseline_json=args.baseline_json,
        )
        print(f"Output dir: {result.output_dir}")
        print(f"Local gates passed: {result.local_passed}")
        print(f"Submitted officially: {result.submitted_officially}")
        if result.deterministic.total_delta is not None:
            print(f"Deterministic total delta: {result.deterministic.total_delta}")
        if result.monte_carlo.mean_delta is not None:
            print(f"Monte Carlo mean delta: {result.monte_carlo.mean_delta}")
        if result.monte_carlo.plausible_mean_delta is not None:
            print(f"Monte Carlo plausible mean delta: {result.monte_carlo.plausible_mean_delta}")
        if result.official_result is not None:
            print(f"Official submission id: {result.official_result.run_result.submission_id}")
            print(f"Counts for team: {result.official_result.counts_for_team}")
        print(f"Summary: {result.summary_path}")
        print(f"Metadata: {result.metadata_path}")
        return

    if args.command == "baseline-imc-show":
        policy = load_imc_baseline_policy(args.round_id)
        print(describe_imc_baseline_policy(policy))
        if policy is not None:
            print(f"policy_path: {baseline_policy_path(args.round_id)}")
        return

    if args.command == "baseline-imc-set":
        policy, path = set_imc_baseline_policy(
            round_id=args.round_id,
            compare_bot_path=args.compare_bot,
            official_baseline_log=args.official_baseline_log,
            official_baseline_json=args.official_baseline_json,
            notes=args.notes,
        )
        print("Saved IMC baseline policy:")
        print(describe_imc_baseline_policy(policy))
        print(f"policy_path: {path}")
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
