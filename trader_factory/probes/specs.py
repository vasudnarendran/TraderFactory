from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProbeSpec:
    name: str
    title: str
    mode: str
    analyzer_cli: str
    event_prefix: str
    purpose: str
    baseline_relationship: str
    questions_answered: tuple[str, ...]
    core_events: tuple[str, ...]
    lifecycle_events: tuple[str, ...]
    required_event_fields: tuple[str, ...]
    workspace_sections: tuple[str, ...]


PROBE_LIBRARY: dict[str, ProbeSpec] = {
    "boundary": ProbeSpec(
        name="boundary",
        title="Decision-Boundary Probe",
        mode="shadow",
        analyzer_cli="python3 -m trader_factory.cli boundary-probe <official_log>",
        event_prefix="bd_",
        purpose="Check whether a shadow overlay actually changes discrete decisions on the official path.",
        baseline_relationship="Keep the production baseline trading behavior identical and run the overlay in shadow.",
        questions_answered=(
            "Is the candidate overlay dormant or live officially?",
            "Does it change quote price, passive size, taker size, or take/no-take?",
            "How often do changes occur and on which side?",
        ),
        core_events=("bd_guard", "bd_change", "bd_summary"),
        lifecycle_events=("candidate", "changed", "summary"),
        required_event_fields=(
            "et",
            "probe_id",
            "probe_kind",
            "event",
            "product",
            "ts",
            "chg",
            "bg",
            "sg",
            "buy_quote_base",
            "buy_quote_shadow",
            "sell_quote_base",
            "sell_quote_shadow",
        ),
        workspace_sections=(
            "baseline bot and hypothesis",
            "shadow overlay definition",
            "discrete decision fields",
            "official submission plan",
        ),
    ),
    "passive_ladder": ProbeSpec(
        name="passive_ladder",
        title="Passive Distance Ladder Probe",
        mode="replacement",
        analyzer_cli="python3 -m trader_factory.cli passive-ladder <official_log> --json-path <official_json>",
        event_prefix="lp_",
        purpose="Measure official passive-fill behavior by distance from the touch.",
        baseline_relationship="Usually run as a dedicated lightweight probe bot rather than on top of the production strategy.",
        questions_answered=(
            "Do tiny passive orders at d0/d1/d2 actually fill officially?",
            "How does fill latency vary by distance?",
            "Are deeper passive prices rewarded on visible edge and markout?",
        ),
        core_events=("lp_post", "lp_fill", "lp_summary"),
        lifecycle_events=("submitted", "filled", "expired", "summary"),
        required_event_fields=(
            "et",
            "probe_id",
            "probe_kind",
            "event",
            "product",
            "ts",
            "arm",
            "side",
            "price",
            "qty",
            "fill_ts",
            "age_steps",
        ),
        workspace_sections=(
            "ladder arm definition",
            "inventory cap and safety rules",
            "markout horizons",
            "official submission plan",
        ),
    ),
    "aggressive_markout": ProbeSpec(
        name="aggressive_markout",
        title="Aggressive Markout Probe",
        mode="overlay",
        analyzer_cli="python3 -m trader_factory.cli aggressive-markout <official_log> --json-path <official_json>",
        event_prefix="am_",
        purpose="Tag specific aggressive-taker contexts and measure short-horizon markout quality officially.",
        baseline_relationship="Prefer baseline-identical tagging or a single-context probe so the official path stays interpretable.",
        questions_answered=(
            "Which taker contexts are actually profitable despite negative visible edge?",
            "Which contexts never appear on the official baseline path?",
            "Should a discovered context move into development mode?",
        ),
        core_events=("am_candidate", "am_fill", "am_summary"),
        lifecycle_events=("candidate", "submitted", "filled", "summary"),
        required_event_fields=(
            "et",
            "probe_id",
            "probe_kind",
            "event",
            "product",
            "ts",
            "context",
            "side",
            "price",
            "qty",
            "fair_edge",
            "visible_edge",
            "take_margin",
        ),
        workspace_sections=(
            "context definition",
            "sampling rule",
            "baseline invariance",
            "official submission plan",
        ),
    ),
}


def probe_spec_names() -> tuple[str, ...]:
    return tuple(sorted(PROBE_LIBRARY))
