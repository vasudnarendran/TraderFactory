from trader_factory.core.datamodel import Trade
from trader_factory.strategies.participant import participant_flow_signal


def test_participant_flow_signal_tracks_weighted_buyer_and_seller_activity() -> None:
    trades = [
        Trade(symbol="TEST", price=100, quantity=5, buyer="Olivia", seller="Maker", timestamp=100),
        Trade(symbol="TEST", price=101, quantity=3, buyer="Maker", seller="Mia", timestamp=200),
    ]

    signal = participant_flow_signal(
        trades,
        ["Olivia", "Mia"],
        participant_weights={"Olivia": 2.0},
    )

    assert signal.matched_trades == 2
    assert signal.matched_volume == 8
    assert round(signal.signed_score, 6) == 7.0
    assert round(signal.weighted_volume, 6) == 13.0
    assert round(signal.normalized_bias, 6) == round(7.0 / 13.0, 6)
    assert signal.last_trade_timestamp == 200


def test_participant_flow_signal_returns_zero_without_matching_participants() -> None:
    trades = [
        Trade(symbol="TEST", price=100, quantity=5, buyer="Maker", seller="Other", timestamp=100),
    ]

    signal = participant_flow_signal(trades, ["Olivia"])

    assert signal.matched_trades == 0
    assert signal.matched_volume == 0
    assert signal.normalized_bias == 0.0
    assert signal.last_trade_timestamp is None
