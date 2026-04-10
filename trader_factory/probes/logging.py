from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _normalize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def compact_json(payload: Any) -> str:
    return json.dumps(_normalize(payload), separators=(",", ":"), sort_keys=True)


def make_event(
    *,
    probe_id: str,
    probe_kind: str,
    event: str,
    product: str,
    ts: int,
    et: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "probe_id": probe_id,
        "probe_kind": probe_kind,
        "event": event,
        "product": product,
        "p": product,
        "ts": ts,
    }
    if et is not None:
        payload["et"] = et
    payload.update(fields)
    return payload


def render_diag_line(events: list[dict[str, Any]] | tuple[dict[str, Any], ...], *, meta: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {"events": [_normalize(event) for event in events]}
    if meta:
        payload["meta"] = _normalize(meta)
    return "DIAG " + compact_json(payload)


def emit_diag(events: list[dict[str, Any]] | tuple[dict[str, Any], ...], *, meta: dict[str, Any] | None = None) -> str:
    line = render_diag_line(events, meta=meta)
    print(line)
    return line
