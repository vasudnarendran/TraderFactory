from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from trader_factory.core.paths import ensure_dir, generated_root
from trader_factory.probes.specs import PROBE_LIBRARY, ProbeSpec, probe_spec_names


@dataclass(slots=True)
class ProbeWorkspaceResult:
    probe_name: str
    spec_name: str
    baseline_bot: Path
    output_dir: Path
    readme_path: Path
    config_path: Path
    submission_probe_path: Path
    notes_path: Path


def _default_output_dir(probe_name: str) -> Path:
    return generated_root() / "probes" / probe_name


def _sample_events(spec: ProbeSpec, *, product: str, context: str | None) -> list[dict[str, object]]:
    if spec.name == "boundary":
        return [
            {
                "et": "bd_change",
                "ts": 67800,
                "chg": ["buy_passive_qty"],
                "p": product,
                "bg": 0.23,
                "sg": 0.0,
                "buy_quote_base": 4987,
                "buy_quote_shadow": 4987,
                "sell_quote_base": 4998,
                "sell_quote_shadow": 4998,
                "buy_passive_base": 9,
                "buy_passive_shadow": 8,
                "sell_passive_base": 8,
                "sell_passive_shadow": 8,
            },
            {
                "et": "bd_summary",
                "ts": 199900,
                "active_ticks": 1532,
                "changed_ticks": 1522,
                "max_buy_guard": 0.31,
                "max_sell_guard": 0.28,
                "change_counts": {"buy_passive_qty": 812, "sell_passive_qty": 710},
            },
        ]
    if spec.name == "passive_ladder":
        return [
            {
                "et": "lp_fill",
                "ts": 54700,
                "fill_ts": 54800,
                "p": product,
                "arm": "buy_d0",
                "side": "BUY",
                "price": 4989,
                "qty": 1,
                "age_steps": 1,
            },
            {
                "et": "lp_summary",
                "ts": 199900,
                "stats": {
                    "buy_d0": {"posted_count": 20, "posted_qty": 20, "filled_count": 5, "filled_qty": 5},
                    "buy_d1": {"posted_count": 20, "posted_qty": 20, "filled_count": 1, "filled_qty": 1},
                },
            },
        ]
    probe_context = context or "range_buy"
    return [
        {
            "et": "am_fill",
            "ts": 59300,
            "fill_ts": 59300,
            "p": product,
            "context": probe_context,
            "side": "BUY",
            "price": 4984,
            "qty": 1,
            "visible_edge": -2.5,
            "fair_edge": 1.53,
            "take_margin": 0.41,
        },
        {
            "et": "am_summary",
            "ts": 199900,
            "stats": {
                probe_context: {
                    "available_count": 3,
                    "submitted_count": 3,
                    "submitted_qty": 3,
                    "filled_count": 3,
                    "filled_qty": 3,
                }
            },
        },
    ]


def _render_readme(
    probe_name: str,
    spec: ProbeSpec,
    baseline_bot: Path,
    *,
    product: str,
    context: str | None,
) -> str:
    lines = [
        f"# {probe_name}",
        "",
        f"- Probe type: `{spec.name}`",
        f"- Probe mode: `{spec.mode}`",
        f"- Baseline bot: `{baseline_bot}`",
        f"- Product: `{product}`",
        f"- Analyzer: `{spec.analyzer_cli}`",
        "",
        "## Purpose",
        "",
        spec.purpose,
        "",
        "## Baseline Relationship",
        "",
        spec.baseline_relationship,
        "",
        "## Questions",
        "",
    ]
    for item in spec.questions_answered:
        lines.append(f"- {item}")

    lines += ["", "## Workspace Checklist", ""]
    for item in spec.workspace_sections:
        lines.append(f"- {item}")

    lines += ["", "## Standard Lifecycle", ""]
    for item in spec.lifecycle_events:
        lines.append(f"- `{item}`")

    if context:
        lines += ["", "## Context", "", f"- Requested context: `{context}`"]

    lines += [
        "",
        "## Notes",
        "",
        "- Keep the official interpretation clean. Do not mix multiple probe hypotheses in one bot unless that is the explicit goal.",
        "- If the probe discovers a usable edge, switch to development mode and implement the production change separately.",
        "",
    ]
    return "\n".join(lines)


def _render_submission_probe(spec: ProbeSpec, baseline_bot: Path, *, product: str, context: str | None) -> str:
    sample_events = _sample_events(spec, product=product, context=context)
    events_literal = json.dumps(sample_events, indent=4)
    context_note = f"# Target context: {context}\n" if context else ""
    return f'''from __future__ import annotations

import json


def make_event(*, probe_id, probe_kind, event, product, ts, et=None, **fields):
    payload = {{
        "probe_id": probe_id,
        "probe_kind": probe_kind,
        "event": event,
        "product": product,
        "p": product,
        "ts": ts,
    }}
    if et is not None:
        payload["et"] = et
    payload.update(fields)
    return payload


def emit_diag(events):
    print("DIAG " + json.dumps({{"events": events}}, separators=(",", ":"), sort_keys=True))


class Trader:
    """
    Probe scaffold for `{spec.title}`.

    Start from baseline bot:
    {baseline_bot}

    This scaffold is intentionally not a finished submission.
    Copy the production logic you want to instrument, then emit events that follow the
    `{spec.event_prefix}` schema so the TraderFactory analyzers can parse them.
    """

    def run(self, state):
        {context_note}# Replace this placeholder with instrumented logic based on the baseline bot.
        # Emit only when the probe condition actually matters.
        sample_events = {events_literal}
        # Recommended standard envelope keys:
        # probe_id, probe_kind, event, product, ts
        # plus backward-compatible short keys like et/p where needed by analyzers.
        emit_diag(sample_events)
        return {{}}, 0, state.traderData
'''


def _render_notes(spec: ProbeSpec) -> str:
    return "\n".join(
        [
            "# Notes",
            "",
            "Capture discoveries here as you run the probe.",
            "",
            "Questions this probe should answer:",
            *[f"- {item}" for item in spec.questions_answered],
            "",
            "After each official run, record:",
            "- submission id",
            "- whether the probe was dormant or live",
            "- key metrics from the analyzer",
            "- whether this implies a development-mode follow-up",
            "",
        ]
    )


def scaffold_probe_workspace(
    spec_name: str,
    baseline_bot: str | Path,
    *,
    probe_name: str | None = None,
    output_dir: str | Path | None = None,
    product: str = "TOMATOES",
    context: str | None = None,
) -> ProbeWorkspaceResult:
    if spec_name not in PROBE_LIBRARY:
        raise ValueError(f"Unknown probe spec: {spec_name}. Known specs: {', '.join(probe_spec_names())}")

    spec = PROBE_LIBRARY[spec_name]
    baseline = Path(baseline_bot).expanduser().resolve()
    name = probe_name or f"{baseline.stem}_{spec.name}_probe"
    workspace = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir(name)
    ensure_dir(workspace)

    readme_path = workspace / "README.md"
    config_path = workspace / "probe.json"
    submission_probe_path = workspace / "submission_probe.py"
    notes_path = workspace / "notes.md"

    config_payload = {
        "probe_name": name,
        "spec": spec.name,
        "mode": spec.mode,
        "baseline_bot": str(baseline),
        "product": product,
        "context": context,
        "analyzer_cli": spec.analyzer_cli,
        "event_prefix": spec.event_prefix,
        "core_events": list(spec.core_events),
        "lifecycle_events": list(spec.lifecycle_events),
        "required_event_fields": list(spec.required_event_fields),
    }

    readme_path.write_text(_render_readme(name, spec, baseline, product=product, context=context) + "\n")
    config_path.write_text(json.dumps(config_payload, indent=2) + "\n")
    submission_probe_path.write_text(_render_submission_probe(spec, baseline, product=product, context=context))
    notes_path.write_text(_render_notes(spec) + "\n")

    return ProbeWorkspaceResult(
        probe_name=name,
        spec_name=spec.name,
        baseline_bot=baseline,
        output_dir=workspace,
        readme_path=readme_path,
        config_path=config_path,
        submission_probe_path=submission_probe_path,
        notes_path=notes_path,
    )
