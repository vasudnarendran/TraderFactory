from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


def _participant_key(value: Any) -> str:
    return str(value or "").strip().casefold()


@dataclass(frozen=True)
class ParticipantFlowSignal:
    matched_trades: int
    matched_volume: int
    signed_score: float
    weighted_volume: float
    normalized_bias: float
    last_trade_timestamp: int | None


def participant_flow_signal(
    trades: Iterable[Any],
    tracked_participants: Sequence[str],
    *,
    participant_weights: Mapping[str, float] | None = None,
) -> ParticipantFlowSignal:
    tracked_keys = {_participant_key(participant) for participant in tracked_participants if _participant_key(participant)}
    if not tracked_keys:
        return ParticipantFlowSignal(
            matched_trades=0,
            matched_volume=0,
            signed_score=0.0,
            weighted_volume=0.0,
            normalized_bias=0.0,
            last_trade_timestamp=None,
        )

    raw_weights = participant_weights or {}
    normalized_weights = {
        _participant_key(participant): float(weight)
        for participant, weight in raw_weights.items()
        if _participant_key(participant)
    }

    matched_trades = 0
    matched_volume = 0
    signed_score = 0.0
    weighted_volume = 0.0
    last_trade_timestamp: int | None = None

    for trade in trades:
        quantity = abs(int(getattr(trade, "quantity", 0) or 0))
        if quantity <= 0:
            continue

        buyer_key = _participant_key(getattr(trade, "buyer", None))
        seller_key = _participant_key(getattr(trade, "seller", None))
        buyer_weight = float(normalized_weights.get(buyer_key, 1.0)) if buyer_key in tracked_keys else 0.0
        seller_weight = float(normalized_weights.get(seller_key, 1.0)) if seller_key in tracked_keys else 0.0
        if buyer_weight == 0.0 and seller_weight == 0.0:
            continue

        matched_trades += 1
        matched_volume += quantity
        signed_score += quantity * buyer_weight
        signed_score -= quantity * seller_weight
        weighted_volume += quantity * abs(buyer_weight)
        weighted_volume += quantity * abs(seller_weight)

        timestamp = getattr(trade, "timestamp", None)
        if timestamp is not None:
            timestamp = int(timestamp)
            last_trade_timestamp = timestamp if last_trade_timestamp is None else max(last_trade_timestamp, timestamp)

    normalized_bias = 0.0 if weighted_volume <= 0.0 else signed_score / weighted_volume
    return ParticipantFlowSignal(
        matched_trades=matched_trades,
        matched_volume=matched_volume,
        signed_score=signed_score,
        weighted_volume=weighted_volume,
        normalized_bias=normalized_bias,
        last_trade_timestamp=last_trade_timestamp,
    )
