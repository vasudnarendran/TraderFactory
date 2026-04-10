from __future__ import annotations

import json
import urllib.parse
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trader_factory.core.paths import ensure_dir
from trader_factory.diagnostics import run_official_trade_quality
from trader_factory.official.imc_prosperity import (
    DEFAULT_API_ROOT,
    DEFAULT_CHROME_APP,
    DEFAULT_GAME_URL,
    DEFAULT_ORIGIN,
    DEFAULT_REFERER,
    DEFAULT_CHROME_PROFILE_DIR,
    ImcProsperityRunResult,
    ImcSubmissionRecord,
    OfficialAutomationError,
    _default_output_dir,
    _download_url,
    _extract_zip,
    _fetch_zip_url,
    _find_working_headers,
    _first_suffix,
    _list_submissions,
    _normalize_submission,
    _open_or_focus_prosperity_tab,
    _poll_submission,
    _read_session_bundle,
    _upload_submission,
)


DEFAULT_QUEUE_POLL_SECONDS = 20.0
DEFAULT_QUEUE_TIMEOUT_SECONDS = 1800.0
BUSY_STATUSES = {
    "PENDING",
    "QUEUED",
    "UPLOADING",
    "SIMULATING",
    "RUNNING",
    "PROCESSING",
    "STARTED",
}
@dataclass(slots=True)
class ImcQueueSnapshot:
    timestamp_unix: float
    busy: bool
    busy_ids: list[int]
    statuses: list[dict[str, Any]]


@dataclass(slots=True)
class ImcProsperityWorkflowResult:
    run_result: ImcProsperityRunResult
    summary_path: Path
    metadata_path: Path
    queue_wait_seconds: float
    queue_snapshots: list[ImcQueueSnapshot]
    baseline_submission: ImcSubmissionRecord | None = None
    baseline_dir: Path | None = None
    baseline_log_path: Path | None = None
    baseline_json_path: Path | None = None
    baseline_download_error: str | None = None
    latest_active_submission: ImcSubmissionRecord | None = None
    counts_for_team: bool = False
    superseded_by_submission_id: int | None = None
    comparison_profit_delta: float | None = None


def _is_busy_status(status: str) -> bool:
    return status.upper() in BUSY_STATUSES


def _normalize_records(items: list[dict[str, Any]]) -> list[ImcSubmissionRecord]:
    return [_normalize_submission(item) for item in items]


def _select_active_submission(records: list[ImcSubmissionRecord], *, exclude_id: int | None = None) -> ImcSubmissionRecord | None:
    active = [record for record in records if record.active and record.id != exclude_id]
    if active:
        return active[0]
    finished = [record for record in records if record.status.upper() == "FINISHED" and record.id != exclude_id]
    if finished:
        return finished[0]
    return None


def _queue_snapshot(records: list[ImcSubmissionRecord]) -> ImcQueueSnapshot:
    busy_ids = [record.id for record in records if _is_busy_status(record.status)]
    statuses = [
        {
            "id": record.id,
            "status": record.status,
            "active": record.active,
            "filename": record.filename,
            "submitted_at": record.submitted_at,
            "submitted_by": record.submitted_by,
        }
        for record in records[:10]
    ]
    return ImcQueueSnapshot(
        timestamp_unix=time.time(),
        busy=bool(busy_ids),
        busy_ids=busy_ids,
        statuses=statuses,
    )


def _wait_for_queue_clear(
    *,
    api_root: str,
    round_id: int,
    headers: dict[str, str],
    queue_poll_seconds: float,
    queue_timeout_seconds: float,
) -> tuple[list[ImcSubmissionRecord], float, list[ImcQueueSnapshot]]:
    deadline = time.monotonic() + queue_timeout_seconds
    start = time.monotonic()
    snapshots: list[ImcQueueSnapshot] = []
    while True:
        records = _normalize_records(_list_submissions(api_root=api_root, round_id=round_id, headers=headers))
        snapshot = _queue_snapshot(records)
        snapshots.append(snapshot)
        if not snapshot.busy:
            return records, time.monotonic() - start, snapshots
        if time.monotonic() > deadline:
            raise OfficialAutomationError(
                "Timed out waiting for the official submission queue to clear. "
                f"Busy submission ids: {snapshot.busy_ids}"
            )
        time.sleep(queue_poll_seconds)


def _download_existing_submission(
    record: ImcSubmissionRecord,
    *,
    output_dir: Path,
    api_root: str,
    headers: dict[str, str],
) -> tuple[Path, list[Path], Path | None, Path | None, Path | None]:
    target_dir = ensure_dir(output_dir)
    zip_url = _fetch_zip_url(record.id, api_root=api_root, headers=headers)
    download_name = Path(record.filename).with_suffix(".zip").name or f"{record.id}.zip"
    zip_path = _download_url(zip_url, target_dir / download_name)
    extracted = _extract_zip(zip_path, target_dir)
    return (
        zip_path,
        extracted,
        _first_suffix(extracted, ".log"),
        _first_suffix(extracted, ".json"),
        _first_suffix(extracted, ".py"),
    )


def _read_profit(json_path: Path | None) -> float | None:
    if json_path is None or not json_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text())
    except json.JSONDecodeError:
        return None
    profit = payload.get("profit")
    if isinstance(profit, (int, float)):
        return float(profit)
    return None


def _write_summary(
    result: ImcProsperityRunResult,
    *,
    summary_path: Path,
    queue_wait_seconds: float,
    queue_snapshots: list[ImcQueueSnapshot],
    baseline_submission: ImcSubmissionRecord | None,
    baseline_log_path: Path | None,
    baseline_json_path: Path | None,
    baseline_download_error: str | None,
    latest_active_submission: ImcSubmissionRecord | None,
    comparison_profit_delta: float | None,
) -> Path:
    current_profit = _read_profit(result.json_path)
    baseline_profit = _read_profit(baseline_json_path)
    lines = [
        "# IMC Prosperity Workflow Summary",
        "",
        "## Submission",
        f"- Submitted bot: `{result.python_path or 'unknown'}`",
        f"- Official submission id: `{result.submission_id}`",
        f"- Output dir: `{result.output_dir}`",
        f"- Auth mode: `{result.auth_mode}`",
        f"- Status history: `{', '.join(result.status_history)}`",
        "",
        "## Queue Handling",
        f"- Queue wait seconds: `{round(queue_wait_seconds, 2)}`",
        f"- Queue snapshots recorded: `{len(queue_snapshots)}`",
    ]
    if any(snapshot.busy for snapshot in queue_snapshots):
        waited_for = sorted({busy_id for snapshot in queue_snapshots for busy_id in snapshot.busy_ids})
        lines.append(f"- Waited for busy submission ids: `{waited_for}`")
    else:
        lines.append("- Queue was clear immediately.")
    lines.extend(["", "## Baseline"])
    if baseline_submission is None:
        lines.append("- No baseline submission was detected before upload.")
    else:
        lines.extend(
            [
                f"- Baseline submission id: `{baseline_submission.id}`",
                f"- Baseline filename: `{baseline_submission.filename}`",
                f"- Baseline submitted by: `{baseline_submission.submitted_by or 'unknown'}`",
                f"- Baseline status: `{baseline_submission.status}`",
                f"- Baseline log: `{baseline_log_path or 'not downloaded'}`",
                f"- Baseline json: `{baseline_json_path or 'not downloaded'}`",
            ]
        )
        if baseline_download_error is not None:
            lines.append(f"- Baseline download warning: `{baseline_download_error}`")
    lines.extend(["", "## Result"])
    lines.append(f"- Current profit: `{current_profit}`")
    if baseline_profit is not None:
        lines.append(f"- Baseline profit: `{baseline_profit}`")
    if comparison_profit_delta is not None:
        lines.append(f"- Profit delta vs baseline: `{comparison_profit_delta}`")
    if result.analysis_result and result.analysis_result.summary_path:
        lines.append(f"- Official analysis: `{result.analysis_result.summary_path}`")
    else:
        lines.append("- Official analysis: skipped")
    lines.extend(["", "## Counting Status"])
    if latest_active_submission is None:
        lines.append("- Could not determine the current active submission after completion.")
    else:
        lines.append(f"- Current active submission id: `{latest_active_submission.id}`")
        lines.append(f"- Current active filename: `{latest_active_submission.filename}`")
        if latest_active_submission.id == result.submission_id:
            lines.append("- This submission is currently the one that counts.")
        else:
            lines.append(
                f"- This submission does not currently count. Active submission `{latest_active_submission.id}` superseded it."
            )
    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n")
    return summary_path


def run_imc_prosperity_workflow(
    bot_path: str | Path,
    *,
    round_id: int = 1,
    output_dir: str | Path | None = None,
    chrome_app: str = DEFAULT_CHROME_APP,
    chrome_profile_dir: str = DEFAULT_CHROME_PROFILE_DIR,
    game_url: str = DEFAULT_GAME_URL,
    api_root: str = DEFAULT_API_ROOT,
    poll_seconds: float = 15.0,
    timeout_seconds: float = 900.0,
    queue_poll_seconds: float = DEFAULT_QUEUE_POLL_SECONDS,
    queue_timeout_seconds: float = DEFAULT_QUEUE_TIMEOUT_SECONDS,
    run_analysis: bool = True,
    baseline_log: str | Path | None = None,
    baseline_json: str | Path | None = None,
) -> ImcProsperityWorkflowResult:
    bot = Path(bot_path).expanduser().resolve()
    if not bot.exists():
        raise FileNotFoundError(f"Bot file does not exist: {bot}")
    if not chrome_profile_dir:
        raise OfficialAutomationError("chrome_profile_dir must not be empty.")

    _open_or_focus_prosperity_tab(game_url=game_url, chrome_app=chrome_app)
    time.sleep(2.0)
    session = _read_session_bundle(chrome_app=chrome_app)
    auth_mode, working_headers, _ = _find_working_headers(
        session,
        api_root=api_root,
        round_id=round_id,
        origin=DEFAULT_ORIGIN,
        referer=DEFAULT_REFERER,
    )

    queue_records, queue_wait_seconds, queue_snapshots = _wait_for_queue_clear(
        api_root=api_root,
        round_id=round_id,
        headers=working_headers,
        queue_poll_seconds=queue_poll_seconds,
        queue_timeout_seconds=queue_timeout_seconds,
    )
    baseline_submission = _select_active_submission(queue_records)

    initial_upload = _upload_submission(bot, api_root=api_root, headers=working_headers)
    submission_id = int(initial_upload["id"])
    resolved_output_dir = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir(submission_id)
    ensure_dir(resolved_output_dir)

    auto_baseline_log: Path | None = Path(baseline_log).expanduser().resolve() if baseline_log else None
    auto_baseline_json: Path | None = Path(baseline_json).expanduser().resolve() if baseline_json else None
    baseline_dir: Path | None = None
    baseline_download_error: str | None = None
    if baseline_submission is not None and (auto_baseline_log is None or auto_baseline_json is None):
        try:
            baseline_dir = ensure_dir(resolved_output_dir / f"baseline_{baseline_submission.id}")
            _, _, downloaded_log, downloaded_json, _ = _download_existing_submission(
                baseline_submission,
                output_dir=baseline_dir,
                api_root=api_root,
                headers=working_headers,
            )
            if auto_baseline_log is None:
                auto_baseline_log = downloaded_log
            if auto_baseline_json is None:
                auto_baseline_json = downloaded_json
        except Exception as exc:  # pragma: no cover - defensive workflow fallback
            baseline_download_error = str(exc)

    record, history = _poll_submission(
        submission_id,
        api_root=api_root,
        round_id=round_id,
        headers=working_headers,
        poll_seconds=poll_seconds,
        timeout_seconds=timeout_seconds,
    )
    zip_url = _fetch_zip_url(submission_id, api_root=api_root, headers=working_headers)
    download_name = Path(urllib.parse.urlparse(zip_url).path).name or f"{submission_id}.zip"
    zip_path = _download_url(zip_url, resolved_output_dir / download_name)
    extracted = _extract_zip(zip_path, resolved_output_dir)
    log_path = _first_suffix(extracted, ".log")
    json_path = _first_suffix(extracted, ".json")
    python_path = _first_suffix(extracted, ".py")
    analysis_result = None
    if run_analysis and log_path is not None:
        analysis_result = run_official_trade_quality(
            log_path,
            baseline_log=auto_baseline_log,
            primary_json=json_path,
            baseline_json=auto_baseline_json,
            output_dir=resolved_output_dir / "analysis",
        )
    run_result = ImcProsperityRunResult(
        submission_id=submission_id,
        round_id=round_id,
        output_dir=resolved_output_dir,
        zip_path=zip_path,
        extracted_files=extracted,
        log_path=log_path,
        json_path=json_path,
        python_path=python_path,
        download_url=zip_url,
        session_page_url=session.page_url,
        auth_mode=auth_mode,
        status_history=history,
        analysis_result=analysis_result,
    )
    (resolved_output_dir / "metadata.json").write_text(
        json.dumps(
            {
                "submission_id": submission_id,
                "round_id": round_id,
                "api_root": api_root,
                "game_url": game_url,
                "auth_mode": auth_mode,
                "status_history": history,
                "submission_record": asdict(record),
                "download_url": zip_url,
                "session_page_url": session.page_url,
                "chrome_app": chrome_app,
                "chrome_profile_dir": chrome_profile_dir,
                "bot_path": str(bot),
            },
            indent=2,
        )
    )

    latest_active_submission: ImcSubmissionRecord | None
    try:
        final_records = _normalize_records(_list_submissions(api_root=api_root, round_id=round_id, headers=working_headers))
        latest_active_submission = _select_active_submission(final_records)
    except Exception:  # pragma: no cover - preserve finished run even if the post-run listing fails
        latest_active_submission = None
    current_profit = _read_profit(run_result.json_path)
    baseline_profit = _read_profit(auto_baseline_json)
    comparison_profit_delta = None
    if current_profit is not None and baseline_profit is not None:
        comparison_profit_delta = current_profit - baseline_profit

    summary_path = _write_summary(
        run_result,
        summary_path=resolved_output_dir / "workflow_summary.md",
        queue_wait_seconds=queue_wait_seconds,
        queue_snapshots=queue_snapshots,
        baseline_submission=baseline_submission,
        baseline_log_path=auto_baseline_log,
        baseline_json_path=auto_baseline_json,
        baseline_download_error=baseline_download_error,
        latest_active_submission=latest_active_submission,
        comparison_profit_delta=comparison_profit_delta,
    )
    metadata_path = resolved_output_dir / "workflow_metadata.json"
    metadata = {
        "bot_path": str(bot),
        "queue_wait_seconds": queue_wait_seconds,
        "queue_snapshots": [asdict(snapshot) for snapshot in queue_snapshots],
        "baseline_submission": asdict(baseline_submission) if baseline_submission else None,
        "baseline_log_path": str(auto_baseline_log) if auto_baseline_log else None,
        "baseline_json_path": str(auto_baseline_json) if auto_baseline_json else None,
        "baseline_download_error": baseline_download_error,
        "latest_active_submission": asdict(latest_active_submission) if latest_active_submission else None,
        "counts_for_team": bool(latest_active_submission and latest_active_submission.id == run_result.submission_id),
        "superseded_by_submission_id": (
            latest_active_submission.id
            if latest_active_submission is not None and latest_active_submission.id != run_result.submission_id
            else None
        ),
        "comparison_profit_delta": comparison_profit_delta,
        "run_result": {
            "submission_id": run_result.submission_id,
            "output_dir": str(run_result.output_dir),
            "zip_path": str(run_result.zip_path),
            "log_path": str(run_result.log_path) if run_result.log_path else None,
            "json_path": str(run_result.json_path) if run_result.json_path else None,
            "python_path": str(run_result.python_path) if run_result.python_path else None,
            "auth_mode": run_result.auth_mode,
            "status_history": run_result.status_history,
            "analysis_summary": (
                str(run_result.analysis_result.summary_path)
                if run_result.analysis_result and run_result.analysis_result.summary_path
                else None
            ),
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))
    return ImcProsperityWorkflowResult(
        run_result=run_result,
        summary_path=summary_path,
        metadata_path=metadata_path,
        queue_wait_seconds=queue_wait_seconds,
        queue_snapshots=queue_snapshots,
        baseline_submission=baseline_submission,
        baseline_dir=baseline_dir,
        baseline_log_path=auto_baseline_log,
        baseline_json_path=auto_baseline_json,
        baseline_download_error=baseline_download_error,
        latest_active_submission=latest_active_submission,
        counts_for_team=bool(latest_active_submission and latest_active_submission.id == run_result.submission_id),
        superseded_by_submission_id=(
            latest_active_submission.id
            if latest_active_submission is not None and latest_active_submission.id != run_result.submission_id
            else None
        ),
        comparison_profit_delta=comparison_profit_delta,
    )
