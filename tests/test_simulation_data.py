from pathlib import Path
import random

import pytest

from trader_factory.core import datamodel
from trader_factory.simulation.deterministic import run_deterministic
from trader_factory.simulation.internal_backtest import resolve_dataset_tag
from trader_factory.simulation.internal_backtest import build_observations, load_market
from trader_factory.simulation.monte_carlo import _bootstrap_day, _build_original_day


def write_dataset_files(root: Path, tag: str) -> None:
    (root / f"prices_{tag}_day_-1.csv").write_text("header\n")
    (root / f"trades_{tag}_day_-1.csv").write_text("header\n")


def inline_price_row(
    *,
    day: int,
    timestamp: int,
    product: str,
    bid_price: int,
    bid_volume: int,
    ask_price: int,
    ask_volume: int,
    mid_price: float,
    observation_bid: float,
    observation_ask: float,
    transport_fees: float,
    export_tariff: float,
    import_tariff: float,
    sunlight: float,
    humidity: float,
) -> str:
    return ";".join(
        [
            str(day),
            str(timestamp),
            product,
            str(bid_price),
            str(bid_volume),
            "",
            "",
            "",
            "",
            str(ask_price),
            str(ask_volume),
            "",
            "",
            "",
            "",
            str(mid_price),
            "0.0",
            str(observation_bid),
            str(observation_ask),
            str(transport_fees),
            str(export_tariff),
            str(import_tariff),
            str(sunlight),
            str(humidity),
        ]
    )


def plain_price_row(
    *,
    day: int,
    timestamp: int,
    product: str,
    bid_price: int,
    bid_volume: int,
    ask_price: int,
    ask_volume: int,
    mid_price: float,
) -> str:
    return ";".join(
        [
            str(day),
            str(timestamp),
            product,
            str(bid_price),
            str(bid_volume),
            "",
            "",
            "",
            "",
            str(ask_price),
            str(ask_volume),
            "",
            "",
            "",
            "",
            str(mid_price),
            "0.0",
        ]
    )


def plain_signal_price_row(
    *,
    day: int,
    timestamp: int,
    product: str,
    bid_price: int,
    bid_volume: int,
    ask_price: int,
    ask_volume: int,
    mid_price: float,
    observation_value: float,
) -> str:
    return plain_price_row(
        day=day,
        timestamp=timestamp,
        product=product,
        bid_price=bid_price,
        bid_volume=bid_volume,
        ask_price=ask_price,
        ask_volume=ask_volume,
        mid_price=mid_price,
    ) + ";" + str(observation_value)


def test_resolve_dataset_tag_single_dataset(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    assert resolve_dataset_tag(tmp_path) == "round_0"


def test_resolve_dataset_tag_multiple_datasets_requires_explicit_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    write_dataset_files(tmp_path, "round_1")

    with pytest.raises(ValueError):
        resolve_dataset_tag(tmp_path)


def test_resolve_dataset_tag_accepts_explicit_valid_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    write_dataset_files(tmp_path, "round_1")

    assert resolve_dataset_tag(tmp_path, "round_1") == "round_1"


def test_resolve_dataset_tag_rejects_unknown_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")

    with pytest.raises(FileNotFoundError):
        resolve_dataset_tag(tmp_path, "missing")


def test_load_market_extracts_inline_conversion_observations(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss;observation_bid_price;observation_ask_price;transport_fees;export_tariff;import_tariff;sunlight;humidity",
                inline_price_row(
                    day=0,
                    timestamp=0,
                    product="ORCHIDS",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                    observation_bid=98,
                    observation_ask=102,
                    transport_fees=1.5,
                    export_tariff=0.5,
                    import_tariff=0.25,
                    sunlight=7,
                    humidity=8,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")

    _, _, _, conversion_observations_by_key, _, _ = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )

    orchids = conversion_observations_by_key[(0, 0)]["ORCHIDS"]
    assert orchids["bidPrice"] == 98.0
    assert orchids["askPrice"] == 102.0
    assert orchids["transportFees"] == 1.5


def test_load_market_reads_sidecar_conversion_observations_and_builds_datamodel_objects(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss",
                plain_price_row(
                    day=0,
                    timestamp=0,
                    product="ORCHIDS",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")
    (tmp_path / "observations_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day,timestamp,product,bid_price,ask_price,transport_fees,export_tariff,import_tariff,sunlight,humidity",
                "0,0,ORCHIDS,97,103,2.0,0.75,0.5,11,13",
            ]
        )
        + "\n"
    )

    _, _, _, conversion_observations_by_key, _, _ = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )
    observations = build_observations(
        datamodel.Observation,
        datamodel.ConversionObservation,
        None,
        conversion_observations_by_key[(0, 0)],
    )

    orchids = observations.conversionObservations["ORCHIDS"]
    assert orchids.bidPrice == 97.0
    assert orchids.askPrice == 103.0
    assert orchids.exportTariff == 0.75
    assert orchids.humidity == 13.0


def test_bootstrap_day_preserves_conversion_observations(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss;observation_bid_price;observation_ask_price;transport_fees;export_tariff;import_tariff;sunlight;humidity",
                inline_price_row(
                    day=0,
                    timestamp=0,
                    product="ORCHIDS",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                    observation_bid=98,
                    observation_ask=102,
                    transport_fees=1.5,
                    export_tariff=0.5,
                    import_tariff=0.25,
                    sunlight=7,
                    humidity=8,
                ),
                inline_price_row(
                    day=0,
                    timestamp=100,
                    product="ORCHIDS",
                    bid_price=101,
                    bid_volume=6,
                    ask_price=102,
                    ask_volume=6,
                    mid_price=101.5,
                    observation_bid=99,
                    observation_ask=103,
                    transport_fees=1.6,
                    export_tariff=0.5,
                    import_tariff=0.25,
                    sunlight=7,
                    humidity=8,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")

    prices_by_key, market_trades_by_day, plain_observations_by_key, conversion_observations_by_key, _, ordered_keys = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )
    replay_day = _build_original_day(
        0,
        prices_by_key,
        market_trades_by_day,
        plain_observations_by_key,
        conversion_observations_by_key,
        ordered_keys,
    )
    bootstrapped = _bootstrap_day(replay_day, random.Random(0), 1, datamodel.Trade)

    assert set(bootstrapped.conversion_observations_by_timestamp) == set(bootstrapped.ordered_timestamps)
    for timestamp in bootstrapped.ordered_timestamps:
        assert "ORCHIDS" in bootstrapped.conversion_observations_by_timestamp[timestamp]


def test_load_market_extracts_inline_plain_observations(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss;observation_value",
                plain_signal_price_row(
                    day=0,
                    timestamp=0,
                    product="WEATHERED",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                    observation_value=12.5,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")

    _, _, plain_observations_by_key, _, _, _ = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )

    assert plain_observations_by_key[(0, 0)]["WEATHERED"] == 12.5


def test_load_market_reads_sidecar_plain_observations_and_builds_datamodel_objects(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss",
                plain_price_row(
                    day=0,
                    timestamp=0,
                    product="ORCHIDS",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")
    (tmp_path / "plain_observations_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day,timestamp,observation_key,value",
                "0,0,WEATHER_SIGNAL,17.5",
            ]
        )
        + "\n"
    )

    _, _, plain_observations_by_key, _, _, _ = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )
    observations = build_observations(
        datamodel.Observation,
        datamodel.ConversionObservation,
        plain_observations_by_key[(0, 0)],
        None,
    )

    assert observations.plainValueObservations["WEATHER_SIGNAL"] == 17.5


def test_bootstrap_day_preserves_plain_observations(tmp_path: Path) -> None:
    (tmp_path / "prices_round_1_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss;observation_value",
                plain_signal_price_row(
                    day=0,
                    timestamp=0,
                    product="WEATHERED",
                    bid_price=100,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.5,
                    observation_value=11.0,
                ),
                plain_signal_price_row(
                    day=0,
                    timestamp=100,
                    product="WEATHERED",
                    bid_price=101,
                    bid_volume=6,
                    ask_price=102,
                    ask_volume=6,
                    mid_price=101.5,
                    observation_value=13.0,
                ),
            ]
        )
        + "\n"
    )
    (tmp_path / "trades_round_1_day_0.csv").write_text("timestamp;symbol;price;quantity;buyer;seller\n")

    prices_by_key, market_trades_by_day, plain_observations_by_key, conversion_observations_by_key, _, ordered_keys = load_market(
        datamodel.Listing,
        datamodel.Trade,
        tmp_path,
        "round_1",
        day_filter=0,
    )
    replay_day = _build_original_day(
        0,
        prices_by_key,
        market_trades_by_day,
        plain_observations_by_key,
        conversion_observations_by_key,
        ordered_keys,
    )
    bootstrapped = _bootstrap_day(replay_day, random.Random(0), 1, datamodel.Trade)

    assert set(bootstrapped.plain_observations_by_timestamp) == set(bootstrapped.ordered_timestamps)
    for timestamp in bootstrapped.ordered_timestamps:
        assert "WEATHERED" in bootstrapped.plain_observations_by_timestamp[timestamp]


def test_run_deterministic_records_passive_resting_fills_in_csv_and_summary(tmp_path: Path) -> None:
    bot_path = tmp_path / "passive_bot.py"
    bot_path.write_text(
        """
from __future__ import annotations

try:
    from datamodel import Order
except ModuleNotFoundError:
    from trader_factory.core.datamodel import Order


class Trader:
    def run(self, state):
        return {"ALPHA": [Order("ALPHA", 100, 1)]}, 0, ""
""".strip()
        + "\n"
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "prices_round_test_day_0.csv").write_text(
        "\n".join(
            [
                "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss",
                plain_price_row(
                    day=0,
                    timestamp=0,
                    product="ALPHA",
                    bid_price=99,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.0,
                ),
                plain_price_row(
                    day=0,
                    timestamp=100,
                    product="ALPHA",
                    bid_price=99,
                    bid_volume=5,
                    ask_price=101,
                    ask_volume=5,
                    mid_price=100.0,
                ),
            ]
        )
        + "\n"
    )
    (data_dir / "trades_round_test_day_0.csv").write_text(
        "\n".join(
            [
                "timestamp;symbol;price;quantity;buyer;seller",
                "100;ALPHA;100;1;;",
            ]
        )
        + "\n"
    )

    result = run_deterministic(
        bot_path,
        day=0,
        output_dir=tmp_path / "out",
        data_root=data_dir,
        dataset_tag="round_test",
    )

    fills_lines = result.fills_path.read_text().strip().splitlines()
    summary = result.summary_path.read_text()
    step_rows = result.step_log_path.read_text().strip().splitlines()

    assert len(fills_lines) == 2
    assert "passive_resting_fill" in fills_lines[1]
    assert "Total fills: 1" in summary
    assert "Passive fills: 1" in summary
    assert "Aggressive fills: 0" in summary
    assert step_rows[-1].split(",")[4] == "1"
