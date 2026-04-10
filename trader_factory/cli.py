from __future__ import annotations

import argparse
from pathlib import Path

from trader_factory.core.specs import CompetitionSpec
from trader_factory.diagnostics import (
    run_aggressive_markout_report,
    run_boundary_probe_report,
    run_official_trade_quality,
    run_passive_ladder_report,
)
from trader_factory.generation.bootstrap import render_markdown_plan
from trader_factory.optimization import run_cmaes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TraderFactory unified CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Render a round plan from a competition spec.")
    plan.add_argument("spec", type=Path, help="Path to a JSON competition spec.")
    plan.add_argument("--output", type=Path, default=None, help="Optional markdown output path.")

    deterministic = subparsers.add_parser("deterministic", help="Run TraderFactory deterministic replay.")
    deterministic.add_argument("bot", type=Path, help="Path to the trader Python file.")
    deterministic.add_argument("--day", type=int, default=-1, help="Day to replay.")
    deterministic.add_argument("--output", type=Path, default=None, help="Optional output directory.")

    monte = subparsers.add_parser("monte-carlo", help="Run TraderFactory headless Monte Carlo robustness.")
    monte.add_argument("bot", type=Path, help="Path to the trader Python file.")
    monte.add_argument("--compare-bot", type=Path, default=None, help="Optional comparison trader Python file.")
    monte.add_argument("--output-dir", type=Path, default=None, help="Optional output directory.")
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

    if args.command == "deterministic":
        from trader_factory.simulation import run_deterministic

        result = run_deterministic(args.bot, day=args.day, output_dir=args.output)
        print(f"Output dir: {result.output_dir}")
        print(f"Summary: {result.summary_path}")
        print(f"Final total PnL: {result.final_total_pnl}")
        return

    if args.command == "monte-carlo":
        from trader_factory.simulation import run_monte_carlo

        result = run_monte_carlo(
            args.bot,
            compare_bot_path=args.compare_bot,
            output_dir=args.output_dir,
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

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
