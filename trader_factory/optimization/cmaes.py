from __future__ import annotations

import json
import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from trader_factory.core.paths import ensure_dir, generated_root, trader_factory_root
from trader_factory.simulation.deterministic import run_deterministic


def _resolve_existing_path(raw: str | Path, *, base: Path) -> Path:
    path = Path(raw).expanduser()
    candidates = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend(
            [
                base / path,
                trader_factory_root() / path,
                trader_factory_root().parent / path,
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _resolve_output_path(raw: str | Path, *, base: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def _format_number(value: float) -> str:
    rounded = round(float(value), 10)
    if math.isfinite(rounded) and rounded.is_integer():
        return f"{int(rounded)}.0"
    return repr(rounded)


@dataclass(slots=True, frozen=True)
class ParameterLocation:
    type: str
    container: str | None = None
    key: str | None = None
    class_name: str | None = None


@dataclass(slots=True, frozen=True)
class TunableParameter:
    name: str
    lower: float
    upper: float
    location: ParameterLocation


@dataclass(slots=True, frozen=True)
class SearchConfig:
    max_iter: int
    population: int
    parents: int
    sigma0: float
    seed: int
    timeout_seconds: float


@dataclass(slots=True, frozen=True)
class PenaltyConfig:
    regression: float
    imbalance: float
    drift: float


@dataclass(slots=True, frozen=True)
class CmaesConfig:
    name: str
    config_path: Path
    source_bot: Path
    parameters: tuple[TunableParameter, ...]
    baselines: dict[int, float]
    search: SearchConfig
    penalties: PenaltyConfig
    output_prefix: str
    output_dir: Path | None = None
    data_root: Path | None = None
    default_dict_block: str | None = None

    @property
    def days(self) -> tuple[int, ...]:
        return tuple(sorted(self.baselines))

    @classmethod
    def from_json(cls, config_path: str | Path) -> "CmaesConfig":
        path = Path(config_path).expanduser().resolve()
        payload = json.loads(path.read_text())
        base = path.parent
        default_dict_block = payload.get("default_dict_block")

        parameters = []
        for item in payload["parameters"]:
            location_payload = item.get("location")
            if location_payload is None:
                if not default_dict_block:
                    raise ValueError(
                        f"Parameter {item['name']} omitted location and config has no default_dict_block"
                    )
                location = ParameterLocation(
                    type="dict_block",
                    container=default_dict_block,
                    key=item.get("key", item["name"]),
                )
            else:
                location = ParameterLocation(
                    type=location_payload["type"],
                    container=location_payload.get("container"),
                    key=location_payload.get("key", item["name"]),
                    class_name=location_payload.get("class_name"),
                )
            parameters.append(
                TunableParameter(
                    name=item["name"],
                    lower=float(item["lower"]),
                    upper=float(item["upper"]),
                    location=location,
                )
            )

        search_payload = payload.get("search", {})
        penalty_payload = payload.get("penalties", {})
        baselines = {int(day): float(score) for day, score in payload["baselines"].items()}

        return cls(
            name=payload.get("name", path.stem),
            config_path=path,
            source_bot=_resolve_existing_path(payload["source_bot"], base=base),
            parameters=tuple(parameters),
            baselines=baselines,
            search=SearchConfig(
                max_iter=int(search_payload.get("max_iter", 5)),
                population=int(search_payload.get("population", 6)),
                parents=int(search_payload.get("parents", 3)),
                sigma0=float(search_payload.get("sigma0", 0.08)),
                seed=int(search_payload.get("seed", 0)),
                timeout_seconds=float(search_payload.get("timeout_seconds", 120.0)),
            ),
            penalties=PenaltyConfig(
                regression=float(penalty_payload.get("regression", 0.0)),
                imbalance=float(penalty_payload.get("imbalance", 0.0)),
                drift=float(penalty_payload.get("drift", 0.0)),
            ),
            output_prefix=payload.get("output_prefix", path.stem),
            output_dir=_resolve_output_path(payload["output_dir"], base=base)
            if payload.get("output_dir")
            else None,
            data_root=_resolve_existing_path(payload["data_root"], base=base)
            if payload.get("data_root")
            else None,
            default_dict_block=default_dict_block,
        )


@dataclass(slots=True)
class CmaesOptimizationResult:
    config_path: Path
    source_bot: Path
    output_dir: Path
    best_bot_path: Path
    json_path: Path
    report_path: Path
    best_params: dict[str, float]
    baseline_scores: dict[int, float]
    best_scores: dict[int, float]
    best_average: float
    best_objective: float
    total_evaluations: int


def _dict_block_bounds(source: str, container: str) -> tuple[int, int, str]:
    marker = re.search(rf"{re.escape(container)}\s*=\s*\{{", source)
    if marker is None:
        raise ValueError(f"Could not find dict block {container}")

    start = marker.start()
    brace_start = source.find("{", marker.start())
    if brace_start == -1:
        raise ValueError(f"Could not find opening brace for {container}")

    depth = 0
    end = brace_start
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    return start, end, source[start:end]


def _replace_dict_value(source: str, location: ParameterLocation, value: float) -> str:
    if not location.container or not location.key:
        raise ValueError("dict_block locations require container and key")
    start, end, block = _dict_block_bounds(source, location.container)
    pattern = rf'("{re.escape(location.key)}":\s*)([^,\n]+)'
    replacement = rf"\g<1>{_format_number(value)}"
    updated, count = re.subn(pattern, replacement, block, count=1)
    if count != 1:
        raise ValueError(f"Could not replace {location.container}.{location.key}")
    return source[:start] + updated + source[end:]


def _replace_class_constant(source: str, location: ParameterLocation, value: float) -> str:
    if not location.class_name or not location.key:
        raise ValueError("class_constant locations require class_name and key")
    pattern = (
        rf"(^class {re.escape(location.class_name)}:.*?^\s{{4}}{re.escape(location.key)}\s*=\s*)([^\n]+)"
    )
    updated, count = re.subn(
        pattern,
        rf"\g<1>{_format_number(value)}",
        source,
        count=1,
        flags=re.S | re.M,
    )
    if count != 1:
        raise ValueError(f"Could not replace {location.class_name}.{location.key}")
    return updated


def _extract_dict_value(source: str, location: ParameterLocation) -> float:
    if not location.container or not location.key:
        raise ValueError("dict_block locations require container and key")
    _start, _end, block = _dict_block_bounds(source, location.container)
    match = re.search(rf'"{re.escape(location.key)}":\s*([\d.eE+\-]+)', block)
    if match is None:
        raise ValueError(f"Could not read {location.container}.{location.key}")
    return float(match.group(1))


def _extract_class_constant(source: str, location: ParameterLocation) -> float:
    if not location.class_name or not location.key:
        raise ValueError("class_constant locations require class_name and key")
    pattern = rf"^class {re.escape(location.class_name)}:.*?^\s{{4}}{re.escape(location.key)}\s*=\s*([^\n]+)"
    match = re.search(pattern, source, flags=re.S | re.M)
    if match is None:
        raise ValueError(f"Could not read {location.class_name}.{location.key}")
    return float(match.group(1).strip())


def extract_defaults(source: str, parameters: tuple[TunableParameter, ...]) -> dict[str, float]:
    defaults: dict[str, float] = {}
    for parameter in parameters:
        if parameter.location.type == "dict_block":
            defaults[parameter.name] = _extract_dict_value(source, parameter.location)
        elif parameter.location.type == "class_constant":
            defaults[parameter.name] = _extract_class_constant(source, parameter.location)
        else:
            raise ValueError(f"Unsupported location type: {parameter.location.type}")
    return defaults


def inject_params(source: str, config: CmaesConfig, params: dict[str, float]) -> str:
    patched = source
    for parameter in config.parameters:
        value = params[parameter.name]
        if parameter.location.type == "dict_block":
            patched = _replace_dict_value(patched, parameter.location, value)
        elif parameter.location.type == "class_constant":
            patched = _replace_class_constant(patched, parameter.location, value)
        else:
            raise ValueError(f"Unsupported location type: {parameter.location.type}")
    return patched


def _default_output_dir(config: CmaesConfig) -> Path:
    return generated_root() / "optimization" / config.output_prefix


def _normalize(params: dict[str, float], config: CmaesConfig) -> np.ndarray:
    x = np.zeros(len(config.parameters))
    for index, parameter in enumerate(config.parameters):
        x[index] = (params[parameter.name] - parameter.lower) / (parameter.upper - parameter.lower)
    return x


def _denormalize(x: np.ndarray, config: CmaesConfig) -> dict[str, float]:
    params: dict[str, float] = {}
    for index, parameter in enumerate(config.parameters):
        clipped = float(np.clip(x[index], 0.0, 1.0))
        params[parameter.name] = parameter.lower + clipped * (parameter.upper - parameter.lower)
    return params


def _normalized_drift(params: dict[str, float], defaults: dict[str, float], config: CmaesConfig) -> float:
    total = 0.0
    for parameter in config.parameters:
        scale = max(1e-9, parameter.upper - parameter.lower)
        total += ((params[parameter.name] - defaults[parameter.name]) / scale) ** 2
    return total / len(config.parameters)


def _objective_value(
    scores: dict[int, float],
    params: dict[str, float],
    defaults: dict[str, float],
    config: CmaesConfig,
) -> tuple[float, float, float, float, float]:
    ordered_days = config.days
    average = sum(scores[day] for day in ordered_days) / len(ordered_days)
    regression_penalty = config.penalties.regression * sum(
        max(0.0, config.baselines[day] - scores[day]) for day in ordered_days
    )
    deltas = [scores[day] - config.baselines[day] for day in ordered_days]
    imbalance_penalty = config.penalties.imbalance * (max(deltas) - min(deltas) if len(deltas) > 1 else 0.0)
    drift_penalty = config.penalties.drift * _normalized_drift(params, defaults, config)
    objective = average - regression_penalty - imbalance_penalty - drift_penalty
    return objective, average, regression_penalty, imbalance_penalty, drift_penalty


def _run_scores_for_params(
    source_text: str,
    config: CmaesConfig,
    params: dict[str, float],
) -> dict[int, float]:
    with tempfile.TemporaryDirectory(prefix="traderfactory_cmaes_") as temp_dir:
        temp_root = Path(temp_dir)
        bot_path = temp_root / f"{config.source_bot.stem}_candidate.py"
        patched = inject_params(source_text, config, params)
        if not patched.endswith("\n"):
            patched += "\n"
        bot_path.write_text(patched)

        scores: dict[int, float] = {}
        for day in config.days:
            run_dir = temp_root / f"day_{day}"
            result = run_deterministic(
                bot_path,
                day=day,
                output_dir=run_dir,
                timeout_seconds=config.search.timeout_seconds,
                check=True,
            )
            if result.final_total_pnl is None:
                raise RuntimeError(f"Could not parse final total PnL for day {day}")
            scores[day] = result.final_total_pnl
    return scores


def _evaluate_candidate(
    source_text: str,
    config: CmaesConfig,
    defaults: dict[str, float],
    x: np.ndarray,
) -> dict[str, Any]:
    params = _denormalize(x, config)
    scores = _run_scores_for_params(source_text, config, params)
    objective, average, regression_penalty, imbalance_penalty, drift_penalty = _objective_value(
        scores,
        params,
        defaults,
        config,
    )
    return {
        "scores": scores,
        "params": params,
        "objective": objective,
        "average": average,
        "regression_penalty": regression_penalty,
        "imbalance_penalty": imbalance_penalty,
        "drift_penalty": drift_penalty,
    }


def _run_cmaes_loop(
    source_text: str,
    config: CmaesConfig,
    defaults: dict[str, float],
    x0: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any], list[dict[str, Any]], int]:
    rng = np.random.default_rng(config.search.seed)
    n = len(x0)
    lam = config.search.population
    mu = config.search.parents
    if mu > lam:
        raise ValueError("search.parents cannot exceed search.population")

    raw_weights = np.array([np.log((lam + 1) / 2) - np.log(i) for i in range(1, mu + 1)])
    weights = raw_weights / raw_weights.sum()
    mu_eff = 1.0 / np.sum(weights ** 2)

    c_c = (4 + mu_eff / n) / (n + 4 + 2 * mu_eff / n)
    c_sigma = (mu_eff + 2) / (n + mu_eff + 5)
    d_sigma = 1 + c_sigma + 2 * max(0.0, np.sqrt((mu_eff - 1) / (n + 1)) - 1)
    c_1 = 2.0 / ((n + 1.3) ** 2 + mu_eff)
    c_mu = min(1.0 - c_1, 2.0 * (mu_eff - 0.25) / ((n + 2) ** 2 + mu_eff))
    chi_n = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n**2))

    mean = x0.copy()
    covariance = np.eye(n)
    sigma = config.search.sigma0
    p_c = np.zeros(n)
    p_s = np.zeros(n)

    eval_count = 0
    best_x = np.clip(mean, 0.0, 1.0)
    best_eval = _evaluate_candidate(source_text, config, defaults, best_x)
    eval_count += 1
    best_objective = best_eval["objective"]
    history: list[dict[str, Any]] = []

    for generation in range(1, config.search.max_iter + 1):
        try:
            chol = np.linalg.cholesky(covariance)
        except np.linalg.LinAlgError:
            covariance += 1e-8 * np.eye(n)
            chol = np.linalg.cholesky(covariance)

        z = rng.standard_normal((lam, n))
        y = (chol @ z.T).T
        x = mean + sigma * y
        x_eval = np.clip(x, 0.0, 1.0)

        evaluations = [_evaluate_candidate(source_text, config, defaults, x_eval[index]) for index in range(lam)]
        eval_count += lam
        fitness = np.array([-item["objective"] for item in evaluations])
        order = np.argsort(fitness)
        elite = order[:mu]

        generation_best = evaluations[order[0]]
        if generation_best["objective"] > best_objective:
            best_objective = generation_best["objective"]
            best_x = x_eval[order[0]].copy()
            best_eval = generation_best

        mean_old = mean.copy()
        mean = np.sum(weights[:, None] * x[elite], axis=0)

        y_best = (x[elite] - mean_old) / sigma
        y_w = np.sum(weights[:, None] * y_best, axis=0)
        c_inv_half_y_w = np.linalg.solve(chol.T, y_w)

        p_s = (1 - c_sigma) * p_s + np.sqrt(c_sigma * (2 - c_sigma) * mu_eff) * c_inv_half_y_w
        sigma = float(np.clip(sigma * np.exp((c_sigma / d_sigma) * (np.linalg.norm(p_s) / chi_n - 1)), 1e-4, 1.0))

        expected_ps_norm = np.sqrt(1 - (1 - c_sigma) ** (2 * generation))
        h_sigma = 1 if (np.linalg.norm(p_s) / expected_ps_norm) < (1.4 + 2.0 / (n + 1)) * chi_n else 0
        p_c = (1 - c_c) * p_c + h_sigma * np.sqrt(c_c * (2 - c_c) * mu_eff) * y_w

        delta_h = (1 - h_sigma) * c_c * (2 - c_c)
        rank1 = np.outer(p_c, p_c)
        rank_mu = sum(weights[index] * np.outer(y_best[index], y_best[index]) for index in range(mu))
        covariance = (1 - c_1 - c_mu) * covariance + c_1 * (rank1 + delta_h * covariance) + c_mu * rank_mu
        covariance = (covariance + covariance.T) / 2.0

        history.append(
            {
                "generation": generation,
                "sigma": sigma,
                "generation_best_objective": generation_best["objective"],
                "generation_best_average": generation_best["average"],
                "global_best_objective": best_objective,
                "global_best_average": best_eval["average"],
            }
        )

    return best_x, best_eval, history, eval_count


def _write_best_bot(
    source_text: str,
    config: CmaesConfig,
    params: dict[str, float],
    output_dir: Path,
) -> Path:
    bot_dir = ensure_dir(output_dir / "bots")
    target = bot_dir / f"{config.source_bot.stem}_best.py"
    patched = inject_params(source_text, config, params)
    if not patched.endswith("\n"):
        patched += "\n"
    target.write_text(patched)
    return target


def _write_outputs(
    config: CmaesConfig,
    defaults: dict[str, float],
    baseline_scores: dict[int, float],
    best_eval: dict[str, Any],
    history: list[dict[str, Any]],
    eval_count: int,
    output_dir: Path,
    best_bot_path: Path,
) -> tuple[Path, Path]:
    ensure_dir(output_dir)
    json_path = output_dir / f"{config.output_prefix}_best.json"
    report_path = output_dir / f"{config.output_prefix}_report.md"

    payload = {
        "config_name": config.name,
        "config_path": str(config.config_path),
        "source_bot": str(config.source_bot),
        "best_bot": str(best_bot_path),
        "parameters": best_eval["params"],
        "baseline_scores": baseline_scores,
        "best_scores": best_eval["scores"],
        "average": best_eval["average"],
        "objective": best_eval["objective"],
        "regression_penalty": best_eval["regression_penalty"],
        "imbalance_penalty": best_eval["imbalance_penalty"],
        "drift_penalty": best_eval["drift_penalty"],
        "search": {
            "max_iter": config.search.max_iter,
            "population": config.search.population,
            "parents": config.search.parents,
            "sigma0": config.search.sigma0,
            "seed": config.search.seed,
            "timeout_seconds": config.search.timeout_seconds,
        },
        "penalties": {
            "regression": config.penalties.regression,
            "imbalance": config.penalties.imbalance,
            "drift": config.penalties.drift,
        },
        "total_evaluations": eval_count,
        "history": history,
    }
    json_path.write_text(json.dumps(payload, indent=2))

    lines = [
        f"# {config.name} CMA-ES Report",
        "",
        f"- Config: `{config.config_path}`",
        f"- Source bot: `{config.source_bot}`",
        f"- Best bot: `{best_bot_path}`",
        f"- Total evaluations: `{eval_count}`",
        "",
        "## Baseline Replay",
        "",
    ]
    for day in config.days:
        lines.append(f"- Day {day}: `{baseline_scores[day]:.4f}`")
    lines += [
        "",
        "## Best Candidate",
        "",
        f"- Objective: `{best_eval['objective']:.4f}`",
        f"- Average score: `{best_eval['average']:.4f}`",
        f"- Regression penalty: `{best_eval['regression_penalty']:.4f}`",
        f"- Imbalance penalty: `{best_eval['imbalance_penalty']:.4f}`",
        f"- Drift penalty: `{best_eval['drift_penalty']:.4f}`",
        "",
    ]
    for day in config.days:
        lines.append(f"- Day {day}: `{best_eval['scores'][day]:.4f}`")
    lines += [
        "",
        "## Parameter Changes",
        "",
        "| Parameter | Default | Best | Delta % |",
        "| --- | ---: | ---: | ---: |",
    ]
    for parameter in config.parameters:
        default = defaults[parameter.name]
        best = best_eval["params"][parameter.name]
        delta_pct = ((best - default) / default * 100.0) if abs(default) > 1e-9 else 0.0
        lines.append(f"| {parameter.name} | {default:.6f} | {best:.6f} | {delta_pct:+.2f}% |")

    lines += [
        "",
        "## Generation History",
        "",
        "| Gen | Gen Obj | Gen Avg | Best Obj | Best Avg | Sigma |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in history:
        lines.append(
            f"| {record['generation']} | {record['generation_best_objective']:.4f} | "
            f"{record['generation_best_average']:.4f} | {record['global_best_objective']:.4f} | "
            f"{record['global_best_average']:.4f} | {record['sigma']:.6f} |"
        )

    report_path.write_text("\n".join(lines) + "\n")
    return json_path, report_path


def run_cmaes(
    config_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_iter: int | None = None,
    population: int | None = None,
    parents: int | None = None,
    sigma0: float | None = None,
    seed: int | None = None,
) -> CmaesOptimizationResult:
    config = CmaesConfig.from_json(config_path)
    if max_iter is not None or population is not None or parents is not None or sigma0 is not None or seed is not None:
        config = CmaesConfig(
            name=config.name,
            config_path=config.config_path,
            source_bot=config.source_bot,
            parameters=config.parameters,
            baselines=config.baselines,
            search=SearchConfig(
                max_iter=max_iter if max_iter is not None else config.search.max_iter,
                population=population if population is not None else config.search.population,
                parents=parents if parents is not None else config.search.parents,
                sigma0=sigma0 if sigma0 is not None else config.search.sigma0,
                seed=seed if seed is not None else config.search.seed,
                timeout_seconds=config.search.timeout_seconds,
            ),
            penalties=config.penalties,
            output_prefix=config.output_prefix,
            output_dir=config.output_dir,
            data_root=config.data_root,
            default_dict_block=config.default_dict_block,
        )

    final_output_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else config.output_dir or _default_output_dir(config)
    )
    ensure_dir(final_output_dir)

    source_text = config.source_bot.read_text()
    defaults = extract_defaults(source_text, config.parameters)
    baseline_scores = _run_scores_for_params(source_text, config, defaults)
    x0 = _normalize(defaults, config)
    _best_x, best_eval, history, eval_count = _run_cmaes_loop(source_text, config, defaults, x0)
    best_bot_path = _write_best_bot(source_text, config, best_eval["params"], final_output_dir)
    json_path, report_path = _write_outputs(
        config,
        defaults,
        baseline_scores,
        best_eval,
        history,
        eval_count,
        final_output_dir,
        best_bot_path,
    )

    return CmaesOptimizationResult(
        config_path=config.config_path,
        source_bot=config.source_bot,
        output_dir=final_output_dir,
        best_bot_path=best_bot_path,
        json_path=json_path,
        report_path=report_path,
        best_params=best_eval["params"],
        baseline_scores=baseline_scores,
        best_scores=best_eval["scores"],
        best_average=best_eval["average"],
        best_objective=best_eval["objective"],
        total_evaluations=eval_count,
    )
