from __future__ import annotations

import csv
import io
import json
import math
import random
import statistics
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import trader_factory.simulation.internal_backtest as ib
from trader_factory.core.paths import ensure_dir, generated_root


@dataclass(frozen=True)
class ScenarioFamily:
    name: str
    description: str
    path_mode: str
    block_steps_min: int
    block_steps_max: int
    passive_fill_prob_range: tuple[float, float]
    passive_qty_scale_range: tuple[float, float]
    aggressive_slip_prob_range: tuple[float, float]
    aggressive_slip_ticks_range: tuple[int, int]


@dataclass(frozen=True)
class DayScenario:
    family: str
    sample_index: int
    day: int
    path_mode: str
    block_steps: int
    passive_fill_prob: float
    passive_qty_scale: float
    aggressive_slip_prob: float
    aggressive_slip_ticks: int

    @property
    def sample_id(self) -> str:
        return f"{self.family}_{self.sample_index:03d}"


@dataclass
class ReplayDay:
    day: int
    ordered_timestamps: list[int]
    snapshots_by_timestamp: dict[int, dict[str, Any]]
    trades_by_timestamp_product: dict[tuple[int, str], list[Any]]
    plain_observations_by_timestamp: dict[int, dict[str, int | float]]
    conversion_observations_by_timestamp: dict[int, dict[str, dict[str, float]]]
    step_interval: int
    source_timestamps: list[int]


@dataclass
class DayResult:
    bot: str
    family: str
    sample_id: str
    day: int
    total_pnl: float
    total_fills: int
    final_positions: dict[str, int]
    product_pnl: dict[str, float]
    block_steps: int
    passive_fill_prob: float
    passive_qty_scale: float
    aggressive_slip_prob: float
    aggressive_slip_ticks: int
    path_mode: str


@dataclass(slots=True)
class MonteCarloRunResult:
    primary_bot_path: Path
    compare_bot_path: Path | None
    output_dir: Path
    report_json_path: Path
    report_markdown_path: Path
    day_results_csv_path: Path
    sample_totals_csv_path: Path
    config: dict[str, Any]
    baseline: dict[str, Any]
    monte_carlo: dict[str, Any]
    comparison: dict[str, Any] | None
    mean_total_pnl: float | None
    std_total_pnl: float | None
    median_total_pnl: float | None
    p05_total_pnl: float | None
    p95_total_pnl: float | None


FAMILY_LIBRARY: dict[str, ScenarioFamily] = {
    "original_noise": ScenarioFamily(
        name="original_noise",
        description="Original historical path with very mild execution-noise perturbations.",
        path_mode="original",
        block_steps_min=0,
        block_steps_max=0,
        passive_fill_prob_range=(0.94, 1.00),
        passive_qty_scale_range=(0.96, 1.00),
        aggressive_slip_prob_range=(0.00, 0.03),
        aggressive_slip_ticks_range=(1, 1),
    ),
    "bootstrap_path": ScenarioFamily(
        name="bootstrap_path",
        description="Block-bootstrap of the historical path with no fill perturbation.",
        path_mode="bootstrap",
        block_steps_min=160,
        block_steps_max=520,
        passive_fill_prob_range=(1.00, 1.00),
        passive_qty_scale_range=(1.00, 1.00),
        aggressive_slip_prob_range=(0.00, 0.00),
        aggressive_slip_ticks_range=(1, 1),
    ),
    "bootstrap_balanced": ScenarioFamily(
        name="bootstrap_balanced",
        description="Block-bootstrap with calibrated mild-to-moderate execution degradation.",
        path_mode="bootstrap",
        block_steps_min=140,
        block_steps_max=420,
        passive_fill_prob_range=(0.84, 0.97),
        passive_qty_scale_range=(0.86, 0.97),
        aggressive_slip_prob_range=(0.01, 0.08),
        aggressive_slip_ticks_range=(1, 1),
    ),
    "bootstrap_stress": ScenarioFamily(
        name="bootstrap_stress",
        description="Block-bootstrap with stressed execution assumptions.",
        path_mode="bootstrap",
        block_steps_min=80,
        block_steps_max=240,
        passive_fill_prob_range=(0.68, 0.88),
        passive_qty_scale_range=(0.68, 0.85),
        aggressive_slip_prob_range=(0.05, 0.18),
        aggressive_slip_ticks_range=(1, 2),
    ),
}

PROFILE_LIBRARY: dict[str, list[str]] = {
    "plausible": ["original_noise", "bootstrap_path", "bootstrap_balanced"],
    "stress": ["bootstrap_stress"],
    "all": list(FAMILY_LIBRARY.keys()),
}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(0.0, min(1.0, pct)) * (len(ordered) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summarize_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "p05": 0.0,
            "p10": 0.0,
            "p25": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "max": 0.0,
            "cvar10": 0.0,
        }
    ordered = sorted(float(value) for value in values)
    p10 = _percentile(ordered, 0.10)
    tail = [value for value in ordered if value <= p10]
    return {
        "count": len(ordered),
        "mean": round(statistics.fmean(ordered), 4),
        "std": round(statistics.pstdev(ordered) if len(ordered) > 1 else 0.0, 4),
        "min": round(ordered[0], 4),
        "p05": round(_percentile(ordered, 0.05), 4),
        "p10": round(p10, 4),
        "p25": round(_percentile(ordered, 0.25), 4),
        "median": round(_percentile(ordered, 0.50), 4),
        "p75": round(_percentile(ordered, 0.75), 4),
        "p90": round(_percentile(ordered, 0.90), 4),
        "p95": round(_percentile(ordered, 0.95), 4),
        "max": round(ordered[-1], 4),
        "cvar10": round(statistics.fmean(tail), 4),
    }


def _default_output_dir(primary_bot: Path, compare_bot: Path | None) -> Path:
    stem = primary_bot.stem if compare_bot is None else f"{primary_bot.stem}_vs_{compare_bot.stem}"
    return ensure_dir(generated_root() / "runs" / "monte_carlo" / stem)


def _build_original_day(
    day: int,
    prices_by_key: dict[tuple[int, int], dict[str, Any]],
    market_trades_by_day: dict[int, dict[tuple[int, str], list[Any]]],
    plain_observations_by_key: dict[tuple[int, int], dict[str, int | float]],
    conversion_observations_by_key: dict[tuple[int, int], dict[str, dict[str, float]]],
    ordered_keys: list[tuple[int, int]],
) -> ReplayDay:
    ordered_timestamps = [timestamp for price_day, timestamp in ordered_keys if price_day == day]
    if not ordered_timestamps:
        raise ValueError(f"No timestamps found for day {day}")

    step_interval = 100
    if len(ordered_timestamps) > 1:
        diffs = [ordered_timestamps[index] - ordered_timestamps[index - 1] for index in range(1, len(ordered_timestamps))]
        positive_diffs = [diff for diff in diffs if diff > 0]
        if positive_diffs:
            step_interval = int(statistics.median(positive_diffs))

    snapshots_by_timestamp = {timestamp: prices_by_key[(day, timestamp)] for timestamp in ordered_timestamps}
    trades_by_timestamp_product = {
        (timestamp, product): list(trades)
        for (timestamp, product), trades in market_trades_by_day.get(day, {}).items()
    }
    plain_observations_by_timestamp = {
        timestamp: dict(plain_observations_by_key[(day, timestamp)])
        for timestamp in ordered_timestamps
        if (day, timestamp) in plain_observations_by_key
    }
    conversion_observations_by_timestamp = {
        timestamp: {product: dict(values) for product, values in conversion_observations_by_key[(day, timestamp)].items()}
        for timestamp in ordered_timestamps
        if (day, timestamp) in conversion_observations_by_key
    }

    return ReplayDay(
        day=day,
        ordered_timestamps=ordered_timestamps,
        snapshots_by_timestamp=snapshots_by_timestamp,
        trades_by_timestamp_product=trades_by_timestamp_product,
        plain_observations_by_timestamp=plain_observations_by_timestamp,
        conversion_observations_by_timestamp=conversion_observations_by_timestamp,
        step_interval=step_interval,
        source_timestamps=ordered_timestamps,
    )


def _clone_trade(trade: Any, new_timestamp: int, trade_class: Any) -> Any:
    return trade_class(
        symbol=trade.symbol,
        price=trade.price,
        quantity=trade.quantity,
        buyer=trade.buyer,
        seller=trade.seller,
        timestamp=new_timestamp,
    )


def _bootstrap_day(base_day: ReplayDay, rng: random.Random, block_steps: int, trade_class: Any) -> ReplayDay:
    original_timestamps = list(base_day.ordered_timestamps)
    target_steps = len(original_timestamps)
    if target_steps == 0:
        raise ValueError("Cannot bootstrap an empty day")

    block_steps = max(1, min(block_steps, target_steps))
    new_timestamps: list[int] = []
    snapshots_by_timestamp: dict[int, dict[str, Any]] = {}
    trades_by_timestamp_product: dict[tuple[int, str], list[Any]] = {}
    plain_observations_by_timestamp: dict[int, dict[str, int | float]] = {}
    conversion_observations_by_timestamp: dict[int, dict[str, dict[str, float]]] = {}

    while len(new_timestamps) < target_steps:
        remaining = target_steps - len(new_timestamps)
        current_block = min(block_steps, remaining)
        start_max = max(0, len(original_timestamps) - current_block)
        start_index = rng.randint(0, start_max)
        selected_block = original_timestamps[start_index : start_index + current_block]

        for original_timestamp in selected_block:
            new_timestamp = len(new_timestamps) * base_day.step_interval
            new_timestamps.append(new_timestamp)

            product_snapshots: dict[str, Any] = {}
            for product, snapshot in base_day.snapshots_by_timestamp[original_timestamp].items():
                product_snapshots[product] = ib.Snapshot(
                    day=base_day.day,
                    timestamp=new_timestamp,
                    abs_timestamp=(base_day.day * 1_000_000) + new_timestamp,
                    product=product,
                    bid_levels=list(snapshot.bid_levels),
                    ask_levels=list(snapshot.ask_levels),
                    mid_price=snapshot.mid_price,
                )
            snapshots_by_timestamp[new_timestamp] = product_snapshots

            for product in product_snapshots:
                trades = base_day.trades_by_timestamp_product.get((original_timestamp, product), [])
                if trades:
                    trades_by_timestamp_product[(new_timestamp, product)] = [
                        _clone_trade(trade, new_timestamp, trade_class) for trade in trades
                    ]
            plain_observations = base_day.plain_observations_by_timestamp.get(original_timestamp)
            if plain_observations:
                plain_observations_by_timestamp[new_timestamp] = dict(plain_observations)
            conversion_observations = base_day.conversion_observations_by_timestamp.get(original_timestamp)
            if conversion_observations:
                conversion_observations_by_timestamp[new_timestamp] = {
                    product: dict(values) for product, values in conversion_observations.items()
                }

    return ReplayDay(
        day=base_day.day,
        ordered_timestamps=new_timestamps,
        snapshots_by_timestamp=snapshots_by_timestamp,
        trades_by_timestamp_product=trades_by_timestamp_product,
        plain_observations_by_timestamp=plain_observations_by_timestamp,
        conversion_observations_by_timestamp=conversion_observations_by_timestamp,
        step_interval=base_day.step_interval,
        source_timestamps=original_timestamps,
    )


def _scenario_rng(seed: int, family: str, sample_index: int, day: int) -> random.Random:
    return random.Random(f"{seed}:{family}:{sample_index}:{day}")


def _sample_day_scenario(family: ScenarioFamily, sample_index: int, day: int, seed: int) -> DayScenario:
    rng = _scenario_rng(seed, family.name, sample_index, day)
    block_steps = 0
    if family.path_mode == "bootstrap":
        block_steps = rng.randint(family.block_steps_min, family.block_steps_max)
    return DayScenario(
        family=family.name,
        sample_index=sample_index,
        day=day,
        path_mode=family.path_mode,
        block_steps=block_steps,
        passive_fill_prob=rng.uniform(*family.passive_fill_prob_range),
        passive_qty_scale=rng.uniform(*family.passive_qty_scale_range),
        aggressive_slip_prob=rng.uniform(*family.aggressive_slip_prob_range),
        aggressive_slip_ticks=rng.randint(*family.aggressive_slip_ticks_range),
    )


def _stochastic_round(value: float, rng: random.Random) -> int:
    if value <= 0:
        return 0
    whole = int(math.floor(value))
    remainder = value - whole
    if rng.random() < remainder:
        whole += 1
    return whole


def _execute_crossing_order_with_noise(order: Any, snapshot: Any, side: str, day_scenario: DayScenario, rng: random.Random) -> tuple[list[Any], int]:
    fills, remaining = ib.execute_crossing_order(order, snapshot, side)
    adjusted_fills: list[Any] = []
    for fill in fills:
        fill_price = fill.price
        fill_type = fill.fill_type
        if day_scenario.aggressive_slip_prob > 0 and rng.random() < day_scenario.aggressive_slip_prob:
            slip_ticks = max(0, int(day_scenario.aggressive_slip_ticks))
            fill_price = fill_price + slip_ticks if fill.side == "BUY" else fill_price - slip_ticks
            fill_type = "aggressive_cross_mc_slip"
        adjusted_fills.append(
            ib.Fill(
                day=fill.day,
                timestamp=fill.timestamp,
                abs_timestamp=fill.abs_timestamp,
                product=fill.product,
                side=fill.side,
                price=fill_price,
                quantity=fill.quantity,
                fill_type=fill_type,
                source_order_price=fill.source_order_price,
            )
        )
    return adjusted_fills, remaining


def _try_fill_pending_order_with_noise(
    order: Any,
    snapshot: Any,
    market_trades: list[Any],
    day_scenario: DayScenario,
    rng: random.Random,
) -> list[Any]:
    base_fillable = min(order.quantity, ib.pending_fill_quantity(order, snapshot, market_trades))
    if base_fillable <= 0:
        return []
    if rng.random() > day_scenario.passive_fill_prob:
        return []
    scaled_quantity = _stochastic_round(base_fillable * day_scenario.passive_qty_scale, rng)
    fillable_quantity = min(order.quantity, scaled_quantity)
    if fillable_quantity <= 0:
        return []
    return [
        ib.Fill(
            day=snapshot.day,
            timestamp=snapshot.timestamp,
            abs_timestamp=snapshot.abs_timestamp,
            product=order.product,
            side=order.side,
            price=order.price,
            quantity=fillable_quantity,
            fill_type="passive_resting_fill_mc",
            source_order_price=order.price,
        )
    ]


def _run_replay_day(
    bot_path: Path,
    replay_day: ReplayDay,
    day_scenario: DayScenario,
    datamodel: tuple[Any, Any, Any, Any, Any, Any, Any],
    listings: dict[str, Any],
    seed: int,
) -> DayResult:
    (
        _ListingClass,
        ObservationClass,
        ConversionObservationClass,
        OrderClass,
        OrderDepthClass,
        TradeClass,
        TradingStateClass,
    ) = datamodel
    trader = ib.load_trader(bot_path)
    products = sorted(listings.keys())

    position = {product: 0 for product in products}
    cash = {product: 0.0 for product in products}
    pending_orders: dict[str, list[Any]] = {product: [] for product in products}
    last_own_trades = ib.build_empty_own_trades(products)
    trader_data = ""
    total_fills = 0
    event_rng = random.Random(f"run:{seed}:{bot_path}:{day_scenario.sample_id}:{day_scenario.day}")

    for timestamp in replay_day.ordered_timestamps:
        snapshots = replay_day.snapshots_by_timestamp[timestamp]
        fills_between_steps: list[Any] = []

        for product in products:
            snapshot = snapshots[product]
            market_trades = replay_day.trades_by_timestamp_product.get((timestamp, product), [])
            for pending in pending_orders[product]:
                new_fills = _try_fill_pending_order_with_noise(
                    pending,
                    snapshot,
                    market_trades,
                    day_scenario,
                    event_rng,
                )
                if new_fills:
                    fills_between_steps.extend(new_fills)
            pending_orders[product] = []

        if fills_between_steps:
            total_fills += len(fills_between_steps)
            last_own_trades = ib.apply_fills(fills_between_steps, cash, position, TradeClass)

        order_depths = {
            product: ib.snapshot_to_order_depth(snapshots[product], OrderDepthClass) for product in products
        }
        market_trades = ib.build_market_trades(products, replay_day.trades_by_timestamp_product, timestamp)
        observations = ib.build_observations(
            ObservationClass,
            ConversionObservationClass,
            replay_day.plain_observations_by_timestamp.get(timestamp, {}),
            replay_day.conversion_observations_by_timestamp.get(timestamp, {}),
        )

        state = TradingStateClass(
            traderData=trader_data,
            timestamp=timestamp,
            listings=listings,
            order_depths=order_depths,
            own_trades=last_own_trades,
            market_trades=market_trades,
            position=dict(position),
            observations=observations,
        )

        with redirect_stdout(io.StringIO()):
            orders_by_product, _conversions, trader_data = trader.run(state)

        step_fills: list[Any] = []
        for product, orders in orders_by_product.items():
            snapshot = snapshots[product]
            for order in orders:
                if not isinstance(order, OrderClass) or order.quantity == 0:
                    continue
                side = "BUY" if order.quantity > 0 else "SELL"
                aggressive_fills, remaining_qty = _execute_crossing_order_with_noise(
                    order,
                    snapshot,
                    side,
                    day_scenario,
                    event_rng,
                )
                step_fills.extend(aggressive_fills)

                if remaining_qty > 0:
                    resting_price = int(order.price)
                    best_bid = snapshot.bid_levels[0][0]
                    best_ask = snapshot.ask_levels[0][0]
                    is_resting = (side == "BUY" and resting_price < best_ask) or (side == "SELL" and resting_price > best_bid)
                    if is_resting:
                        pending_orders[product].append(
                            ib.PendingOrder(
                                product=product,
                                side=side,
                                price=resting_price,
                                quantity=remaining_qty,
                                day=replay_day.day,
                                timestamp=timestamp,
                            )
                        )

        if step_fills:
            total_fills += len(step_fills)
            last_own_trades = ib.apply_fills(step_fills, cash, position, TradeClass)
        else:
            last_own_trades = ib.build_empty_own_trades(products)

    final_timestamp = replay_day.ordered_timestamps[-1]
    final_snapshots = replay_day.snapshots_by_timestamp[final_timestamp]
    product_pnl: dict[str, float] = {}
    total_pnl = 0.0
    for product in products:
        mid_price = final_snapshots[product].mid_price
        pnl = cash[product] + position[product] * mid_price
        product_pnl[product] = pnl
        total_pnl += pnl

    return DayResult(
        bot=bot_path.stem,
        family=day_scenario.family,
        sample_id=day_scenario.sample_id,
        day=day_scenario.day,
        total_pnl=round(total_pnl, 4),
        total_fills=total_fills,
        final_positions=dict(position),
        product_pnl={product: round(pnl, 4) for product, pnl in product_pnl.items()},
        block_steps=day_scenario.block_steps,
        passive_fill_prob=round(day_scenario.passive_fill_prob, 6),
        passive_qty_scale=round(day_scenario.passive_qty_scale, 6),
        aggressive_slip_prob=round(day_scenario.aggressive_slip_prob, 6),
        aggressive_slip_ticks=day_scenario.aggressive_slip_ticks,
        path_mode=day_scenario.path_mode,
    )


def _flatten_day_result(result: DayResult) -> dict[str, Any]:
    row: dict[str, Any] = {
        "bot": result.bot,
        "family": result.family,
        "sample_id": result.sample_id,
        "day": result.day,
        "total_pnl": result.total_pnl,
        "total_fills": result.total_fills,
        "path_mode": result.path_mode,
        "block_steps": result.block_steps,
        "passive_fill_prob": result.passive_fill_prob,
        "passive_qty_scale": result.passive_qty_scale,
        "aggressive_slip_prob": result.aggressive_slip_prob,
        "aggressive_slip_ticks": result.aggressive_slip_ticks,
    }
    for product, pnl in sorted(result.product_pnl.items()):
        row[f"{product}_pnl"] = pnl
    for product, position in sorted(result.final_positions.items()):
        row[f"{product}_position"] = position
    return row


def _aggregate_samples(day_results: list[DayResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in day_results:
        key = (result.bot, result.family, result.sample_id)
        if key not in grouped:
            grouped[key] = {
                "bot": result.bot,
                "family": result.family,
                "sample_id": result.sample_id,
                "total_pnl": 0.0,
                "total_fills": 0,
                "days": {},
                "path_mode": result.path_mode,
                "block_steps": [],
                "passive_fill_prob": [],
                "passive_qty_scale": [],
                "aggressive_slip_prob": [],
                "aggressive_slip_ticks": [],
            }
        entry = grouped[key]
        entry["total_pnl"] += result.total_pnl
        entry["total_fills"] += result.total_fills
        entry["days"][str(result.day)] = result.total_pnl
        entry["block_steps"].append(result.block_steps)
        entry["passive_fill_prob"].append(result.passive_fill_prob)
        entry["passive_qty_scale"].append(result.passive_qty_scale)
        entry["aggressive_slip_prob"].append(result.aggressive_slip_prob)
        entry["aggressive_slip_ticks"].append(result.aggressive_slip_ticks)

    rows: list[dict[str, Any]] = []
    for _, entry in sorted(grouped.items()):
        row = {
            "bot": entry["bot"],
            "family": entry["family"],
            "sample_id": entry["sample_id"],
            "total_pnl": round(entry["total_pnl"], 4),
            "total_fills": entry["total_fills"],
            "path_mode": entry["path_mode"],
            "avg_block_steps": round(statistics.fmean(entry["block_steps"]), 4),
            "avg_passive_fill_prob": round(statistics.fmean(entry["passive_fill_prob"]), 6),
            "avg_passive_qty_scale": round(statistics.fmean(entry["passive_qty_scale"]), 6),
            "avg_aggressive_slip_prob": round(statistics.fmean(entry["aggressive_slip_prob"]), 6),
            "avg_aggressive_slip_ticks": round(statistics.fmean(entry["aggressive_slip_ticks"]), 6),
        }
        for day_key, pnl in sorted(entry["days"].items()):
            row[f"day_{day_key}_pnl"] = round(pnl, 4)
        rows.append(row)
    return rows


def _summarize_profiles(sample_rows: list[dict[str, Any]], bot_name: str) -> dict[str, dict[str, float]]:
    bot_rows = [row for row in sample_rows if row["bot"] == bot_name]
    return {
        profile_name: _summarize_distribution([row["total_pnl"] for row in bot_rows if row["family"] in families])
        for profile_name, families in PROFILE_LIBRARY.items()
    }


def _compare_samples(sample_rows: list[dict[str, Any]], primary_bot: str, compare_bot: str) -> dict[str, Any]:
    primary_by_key = {(row["family"], row["sample_id"]): row["total_pnl"] for row in sample_rows if row["bot"] == primary_bot}
    compare_by_key = {(row["family"], row["sample_id"]): row["total_pnl"] for row in sample_rows if row["bot"] == compare_bot}
    shared_keys = sorted(set(primary_by_key) & set(compare_by_key))
    deltas = [primary_by_key[key] - compare_by_key[key] for key in shared_keys]
    family_breakdown: dict[str, dict[str, float]] = {}
    for family in sorted({key[0] for key in shared_keys}):
        family_deltas = [primary_by_key[key] - compare_by_key[key] for key in shared_keys if key[0] == family]
        family_breakdown[family] = {
            "samples": len(family_deltas),
            "mean_delta": round(statistics.fmean(family_deltas), 4) if family_deltas else 0.0,
            "win_rate": round(sum(delta > 0 for delta in family_deltas) / len(family_deltas), 4) if family_deltas else 0.0,
            "p10_delta": round(_percentile(family_deltas, 0.10), 4) if family_deltas else 0.0,
        }
    return {
        "primary_bot": primary_bot,
        "compare_bot": compare_bot,
        "shared_samples": len(shared_keys),
        "summary": {
            "mean_delta": round(statistics.fmean(deltas), 4) if deltas else 0.0,
            "median_delta": round(_percentile(deltas, 0.50), 4) if deltas else 0.0,
            "p10_delta": round(_percentile(deltas, 0.10), 4) if deltas else 0.0,
            "win_rate": round(sum(delta > 0 for delta in deltas) / len(deltas), 4) if deltas else 0.0,
        },
        "by_family": family_breakdown,
    }


def _compare_profiles(sample_rows: list[dict[str, Any]], primary_bot: str, compare_bot: str) -> dict[str, dict[str, float]]:
    primary_rows = {(row["family"], row["sample_id"]): row["total_pnl"] for row in sample_rows if row["bot"] == primary_bot}
    compare_rows = {(row["family"], row["sample_id"]): row["total_pnl"] for row in sample_rows if row["bot"] == compare_bot}
    profile_breakdown: dict[str, dict[str, float]] = {}
    for profile_name, families in PROFILE_LIBRARY.items():
        shared_keys = sorted(key for key in set(primary_rows) & set(compare_rows) if key[0] in families)
        deltas = [primary_rows[key] - compare_rows[key] for key in shared_keys]
        profile_breakdown[profile_name] = {
            "samples": len(deltas),
            "mean_delta": round(statistics.fmean(deltas), 4) if deltas else 0.0,
            "median_delta": round(_percentile(deltas, 0.50), 4) if deltas else 0.0,
            "p10_delta": round(_percentile(deltas, 0.10), 4) if deltas else 0.0,
            "win_rate": round(sum(delta > 0 for delta in deltas) / len(deltas), 4) if deltas else 0.0,
        }
    return profile_breakdown


def _build_markdown_report(
    output_name: str,
    bot_paths: list[Path],
    families: list[ScenarioFamily],
    baseline_summary: dict[str, Any],
    monte_carlo_summary: dict[str, Any],
    comparison: dict[str, Any] | None,
) -> str:
    lines = [
        "# Monte Carlo Robustness Report",
        "",
        f"- Output name: `{output_name}`",
        f"- Bots: {', '.join(path.name for path in bot_paths)}",
        "",
        "## Families",
        "",
    ]
    for family in families:
        lines.append(f"- `{family.name}`: {family.description}")
    lines += ["", "## Baseline Replay", ""]
    for bot_name, summary in sorted(baseline_summary.items()):
        lines.append(f"### {bot_name}")
        lines.append("")
        lines.append(f"- Combined total PnL: `{summary['combined_total_pnl']:.4f}`")
        for day_key, day_total in sorted(summary["per_day"].items()):
            lines.append(f"- Day {day_key}: `{day_total:.4f}`")
        lines.append("")

    lines += ["## Monte Carlo Summary", ""]
    for bot_name, summary in sorted(monte_carlo_summary.items()):
        overall = summary["overall"]
        lines.append(f"### {bot_name}")
        lines.append("")
        lines.append(
            f"- Overall samples: `{overall['count']}` | mean `{overall['mean']}` | "
            f"p10 `{overall['p10']}` | cvar10 `{overall['cvar10']}` | std `{overall['std']}`"
        )
        for profile_name, profile_summary in sorted(summary["profiles"].items()):
            lines.append(
                f"- Profile `{profile_name}`: count `{profile_summary['count']}`, mean `{profile_summary['mean']}`, "
                f"p10 `{profile_summary['p10']}`, cvar10 `{profile_summary['cvar10']}`"
            )
        for family_name, family_summary in sorted(summary["by_family"].items()):
            lines.append(
                f"- `{family_name}`: count `{family_summary['count']}`, mean `{family_summary['mean']}`, "
                f"p10 `{family_summary['p10']}`, cvar10 `{family_summary['cvar10']}`"
            )
        lines.append("")

    if comparison is not None:
        lines += [
            "## Comparison",
            "",
            f"- Primary: `{comparison['primary_bot']}`",
            f"- Compare: `{comparison['compare_bot']}`",
            f"- Shared samples: `{comparison['shared_samples']}`",
            f"- Mean delta: `{comparison['summary']['mean_delta']}`",
            f"- Median delta: `{comparison['summary']['median_delta']}`",
            f"- P10 delta: `{comparison['summary']['p10_delta']}`",
            f"- Win rate: `{comparison['summary']['win_rate']}`",
            "",
        ]
        for family_name, family_summary in sorted(comparison["by_family"].items()):
            lines.append(
                f"- `{family_name}`: mean delta `{family_summary['mean_delta']}`, "
                f"p10 delta `{family_summary['p10_delta']}`, win rate `{family_summary['win_rate']}`"
            )
        lines.append("")
        for profile_name, profile_summary in sorted(comparison["by_profile"].items()):
            lines.append(
                f"- Profile `{profile_name}`: mean delta `{profile_summary['mean_delta']}`, "
                f"p10 delta `{profile_summary['p10_delta']}`, win rate `{profile_summary['win_rate']}`"
            )
        lines.append("")
    return "\n".join(lines)


def run_monte_carlo(
    trader_path: str | Path,
    *,
    compare_bot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    data_root: str | Path | None = None,
    dataset_tag: str | None = None,
    days: tuple[int, ...] | list[int] = (-1, -2),
    samples_per_family: int = 4,
    families: list[str] | tuple[str, ...] | None = None,
    seed: int = 52,
    quick: bool = False,
    heavy: bool = False,
    check: bool = True,
) -> MonteCarloRunResult:
    del check  # local engine raises directly
    primary_bot = ib.resolve_bot_path(str(trader_path))
    compare_bot = ib.resolve_bot_path(str(compare_bot_path)) if compare_bot_path else None

    if quick:
        if families is None:
            families = PROFILE_LIBRARY["plausible"]
        if samples_per_family == 4:
            samples_per_family = 2
    elif heavy:
        if families is None:
            families = PROFILE_LIBRARY["all"]
        if samples_per_family == 4:
            samples_per_family = 8

    selected_family_names = list(families) if families is not None else PROFILE_LIBRARY["all"]
    selected_families = [FAMILY_LIBRARY[name] for name in selected_family_names]
    output_root = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir(primary_bot, compare_bot)
    ensure_dir(output_root)

    (
        ListingClass,
        ObservationClass,
        ConversionObservationClass,
        OrderClass,
        OrderDepthClass,
        TradeClass,
        TradingStateClass,
    ) = ib.ensure_imports(primary_bot)
    datamodel = (
        ListingClass,
        ObservationClass,
        ConversionObservationClass,
        OrderClass,
        OrderDepthClass,
        TradeClass,
        TradingStateClass,
    )
    resolved_data_root = ib.resolve_data_dir(data_root)
    resolved_dataset_tag = ib.resolve_dataset_tag(resolved_data_root, dataset_tag)
    (
        prices_by_key,
        market_trades_by_day,
        plain_observations_by_key,
        conversion_observations_by_key,
        listings,
        ordered_keys,
    ) = ib.load_market(
        ListingClass,
        TradeClass,
        resolved_data_root,
        resolved_dataset_tag,
        day_filter=None,
    )
    ordered_days = tuple(days)
    original_days = {
        day: _build_original_day(
            day,
            prices_by_key,
            market_trades_by_day,
            plain_observations_by_key,
            conversion_observations_by_key,
            ordered_keys,
        )
        for day in ordered_days
    }

    bot_paths = [primary_bot] + ([compare_bot] if compare_bot is not None else [])
    baseline_summary: dict[str, Any] = {}
    baseline_day_results: list[DayResult] = []
    for bot_path in bot_paths:
        per_day: dict[int, float] = {}
        combined_total = 0.0
        for day in ordered_days:
            baseline_scenario = DayScenario(
                family="baseline",
                sample_index=0,
                day=day,
                path_mode="original",
                block_steps=0,
                passive_fill_prob=1.0,
                passive_qty_scale=1.0,
                aggressive_slip_prob=0.0,
                aggressive_slip_ticks=1,
            )
            result = _run_replay_day(bot_path, original_days[day], baseline_scenario, datamodel, listings, seed)
            baseline_day_results.append(result)
            per_day[day] = result.total_pnl
            combined_total += result.total_pnl
        baseline_summary[bot_path.stem] = {
            "per_day": {str(day): round(total, 4) for day, total in per_day.items()},
            "combined_total_pnl": round(combined_total, 4),
        }

    sampled_scenarios: list[DayScenario] = []
    for family in selected_families:
        for sample_index in range(1, samples_per_family + 1):
            for day in ordered_days:
                sampled_scenarios.append(_sample_day_scenario(family, sample_index, day, seed))

    replay_days: dict[tuple[str, int, str], ReplayDay] = {}
    for day_scenario in sampled_scenarios:
        base_day = original_days[day_scenario.day]
        path_rng = _scenario_rng(seed + 10_000, day_scenario.family, day_scenario.sample_index, day_scenario.day)
        if day_scenario.path_mode == "bootstrap":
            replay_days[(day_scenario.sample_id, day_scenario.day, day_scenario.family)] = _bootstrap_day(
                base_day,
                path_rng,
                day_scenario.block_steps,
                TradeClass,
            )
        else:
            replay_days[(day_scenario.sample_id, day_scenario.day, day_scenario.family)] = base_day

    monte_carlo_day_results: list[DayResult] = []
    for bot_path in bot_paths:
        for day_scenario in sampled_scenarios:
            replay_day = replay_days[(day_scenario.sample_id, day_scenario.day, day_scenario.family)]
            monte_carlo_day_results.append(
                _run_replay_day(bot_path, replay_day, day_scenario, datamodel, listings, seed)
            )

    sample_rows = _aggregate_samples(monte_carlo_day_results)
    monte_carlo_summary: dict[str, Any] = {}
    for bot_path in bot_paths:
        bot_rows = [row for row in sample_rows if row["bot"] == bot_path.stem]
        overall_values = [row["total_pnl"] for row in bot_rows]
        family_values = {
            family.name: [row["total_pnl"] for row in bot_rows if row["family"] == family.name]
            for family in selected_families
        }
        monte_carlo_summary[bot_path.stem] = {
            "overall": _summarize_distribution(overall_values),
            "profiles": _summarize_profiles(sample_rows, bot_path.stem),
            "by_family": {
                family_name: _summarize_distribution(values)
                for family_name, values in family_values.items()
            },
        }

    comparison = None
    if compare_bot is not None:
        comparison = _compare_samples(sample_rows, primary_bot.stem, compare_bot.stem)
        comparison["by_profile"] = _compare_profiles(sample_rows, primary_bot.stem, compare_bot.stem)

    output_name = output_root.name
    report_json = {
        "config": {
            "seed": seed,
            "days": list(ordered_days),
            "samples_per_family": samples_per_family,
            "families": [asdict(family) for family in selected_families],
            "bots": [str(path) for path in bot_paths],
        },
        "baseline": baseline_summary,
        "monte_carlo": monte_carlo_summary,
        "comparison": comparison,
    }

    report_json_path = output_root / "report.json"
    report_markdown_path = output_root / "report.md"
    day_results_csv_path = output_root / "day_results.csv"
    sample_totals_csv_path = output_root / "sample_totals.csv"

    report_json_path.write_text(json.dumps(report_json, indent=2))
    _write_csv(day_results_csv_path, [_flatten_day_result(result) for result in monte_carlo_day_results])
    _write_csv(sample_totals_csv_path, sample_rows)
    report_markdown_path.write_text(
        _build_markdown_report(
            output_name,
            bot_paths,
            selected_families,
            baseline_summary,
            monte_carlo_summary,
            comparison,
        )
        + "\n"
    )

    overall = monte_carlo_summary[primary_bot.stem]["overall"]
    return MonteCarloRunResult(
        primary_bot_path=primary_bot,
        compare_bot_path=compare_bot,
        output_dir=output_root,
        report_json_path=report_json_path,
        report_markdown_path=report_markdown_path,
        day_results_csv_path=day_results_csv_path,
        sample_totals_csv_path=sample_totals_csv_path,
        config=report_json["config"],
        baseline=baseline_summary,
        monte_carlo=monte_carlo_summary,
        comparison=comparison,
        mean_total_pnl=overall["mean"],
        std_total_pnl=overall["std"],
        median_total_pnl=overall["median"],
        p05_total_pnl=overall["p05"],
        p95_total_pnl=overall["p95"],
    )
