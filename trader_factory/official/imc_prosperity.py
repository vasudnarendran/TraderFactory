from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from trader_factory.core.paths import ensure_dir, generated_root
from trader_factory.diagnostics import DiagnosticRunResult, run_official_trade_quality


DEFAULT_GAME_URL = "https://prosperity.imc.com/game"
DEFAULT_API_ROOT = "https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod"
DEFAULT_ORIGIN = "https://prosperity.imc.com"
DEFAULT_REFERER = "https://prosperity.imc.com/"
DEFAULT_CHROME_APP = "Google Chrome"
DEFAULT_CHROME_PROFILE_DIR = "Default"


@dataclass(slots=True)
class ProsperitySessionBundle:
    page_url: str
    cookie_string: str
    cookies: dict[str, str]
    local_storage: dict[str, str]
    access_token: str | None
    id_token: str | None
    refresh_token: str | None
    last_auth_user: str | None


@dataclass(slots=True)
class ImcSubmissionRecord:
    id: int
    round_id: int
    status: str
    filename: str
    active: bool
    submitted_at: str
    submitted_by: str
    simulation_identifier: str | None


@dataclass(slots=True)
class ImcProsperityRunResult:
    submission_id: int
    round_id: int
    output_dir: Path
    zip_path: Path
    extracted_files: list[Path]
    log_path: Path | None
    json_path: Path | None
    python_path: Path | None
    download_url: str
    session_page_url: str
    auth_mode: str
    status_history: list[str] = field(default_factory=list)
    analysis_result: DiagnosticRunResult | None = None


class OfficialAutomationError(RuntimeError):
    """Raised when official automation cannot proceed."""


def _default_output_dir(submission_id: int) -> Path:
    return ensure_dir(generated_root() / "official_runs" / "imc_prosperity" / str(submission_id))


def _run_subprocess(command: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip()
        stdout = process.stdout.strip()
        message = stderr or stdout or f"Command failed: {' '.join(command)}"
        raise OfficialAutomationError(message)
    return process


def _run_osascript(script: str) -> str:
    try:
        process = _run_subprocess(["osascript"], input_text=script, check=True)
    except OfficialAutomationError as exc:
        message = str(exc)
        if "Executing JavaScript through AppleScript is turned off" in message:
            raise OfficialAutomationError(
                "Chrome is blocking JavaScript from Apple Events. In Chrome, enable "
                "View > Developer > Allow JavaScript from Apple Events, then rerun the command."
            ) from exc
        raise
    return process.stdout.strip()


def _open_or_focus_prosperity_tab(*, game_url: str, chrome_app: str) -> None:
    script = f'''
tell application "{chrome_app}"
    activate
    set found to false
    repeat with w in windows
        repeat with i from 1 to (count of tabs of w)
            set t to tab i of w
            if URL of t starts with "https://prosperity.imc.com/" then
                set active tab index of w to i
                set index of w to 1
                set found to true
                exit repeat
            end if
        end repeat
        if found then exit repeat
    end repeat
    if not found then
        if (count of windows) = 0 then
            set newWindow to make new window
            set URL of active tab of newWindow to "{game_url}"
        else
            set newTab to make new tab at end of tabs of front window
            set URL of newTab to "{game_url}"
            set active tab index of front window to (count of tabs of front window)
        end if
    end if
end tell
'''
    _run_osascript(script)


def _execute_js_in_prosperity_tab(js_source: str, *, chrome_app: str) -> str:
    encoded = base64.b64encode(js_source.encode("utf-8")).decode("ascii")
    script = f'''
tell application "{chrome_app}"
    repeat 80 times
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t starts with "https://prosperity.imc.com/" then
                    return (execute t javascript "eval(atob('{encoded}'))")
                end if
            end repeat
        end repeat
        delay 0.25
    end repeat
end tell
error "Could not find a prosperity.imc.com tab in Google Chrome."
'''
    return _run_osascript(script)


def _session_bundle_js() -> str:
    return r"""
(() => {
  function readStorage(storage) {
    const out = {};
    try {
      for (let i = 0; i < storage.length; i += 1) {
        const key = storage.key(i);
        out[key] = storage.getItem(key);
      }
    } catch (err) {
      out.__error__ = String(err);
    }
    return out;
  }

  const cookieString = document.cookie || "";
  const cookies = {};
  for (const part of cookieString.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const idx = trimmed.indexOf("=");
    const key = idx >= 0 ? trimmed.slice(0, idx) : trimmed;
    const value = idx >= 0 ? trimmed.slice(idx + 1) : "";
    cookies[key] = value;
  }

  function findToken(suffix) {
    const cookieKey = Object.keys(cookies).find((key) => key.endsWith(suffix));
    if (cookieKey) return cookies[cookieKey];
    const storage = readStorage(window.localStorage);
    const storageKey = Object.keys(storage).find((key) => key.endsWith(suffix));
    return storageKey ? storage[storageKey] : null;
  }

  const localStorageDump = readStorage(window.localStorage);

  return JSON.stringify({
    pageUrl: window.location.href,
    cookieString,
    cookies,
    localStorage: localStorageDump,
    accessToken: findToken(".accessToken"),
    idToken: findToken(".idToken"),
    refreshToken: findToken(".refreshToken"),
    lastAuthUser: findToken(".LastAuthUser"),
  });
})()
"""


def _read_session_bundle(*, chrome_app: str) -> ProsperitySessionBundle:
    raw = _execute_js_in_prosperity_tab(_session_bundle_js(), chrome_app=chrome_app)
    data = json.loads(raw)
    return ProsperitySessionBundle(
        page_url=str(data.get("pageUrl", "")),
        cookie_string=str(data.get("cookieString", "")),
        cookies={str(key): str(value) for key, value in dict(data.get("cookies", {})).items()},
        local_storage={str(key): str(value) for key, value in dict(data.get("localStorage", {})).items()},
        access_token=data.get("accessToken"),
        id_token=data.get("idToken"),
        refresh_token=data.get("refreshToken"),
        last_auth_user=data.get("lastAuthUser"),
    )


def _multipart_body(file_path: Path) -> tuple[bytes, str]:
    boundary = f"----TraderFactoryBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode("utf-8")
    )
    body.extend(b"Content-Type: text/x-python-script\r\n\r\n")
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary


def _base_headers(*, origin: str, referer: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Origin": origin,
        "Referer": referer,
        "User-Agent": f"TraderFactory/{sys.version_info.major}.{sys.version_info.minor}",
    }


def _candidate_auth_headers(
    session: ProsperitySessionBundle,
    *,
    origin: str,
    referer: str,
) -> list[tuple[str, dict[str, str]]]:
    base = _base_headers(origin=origin, referer=referer)
    candidates: list[tuple[str, dict[str, str]]] = []
    cookie_variants = [session.cookie_string] if session.cookie_string else [None]
    token_variants: list[tuple[str, str | None]] = [
        ("none", None),
        ("id_token_raw", session.id_token),
        ("id_token_bearer", f"Bearer {session.id_token}" if session.id_token else None),
        ("access_token_raw", session.access_token),
        ("access_token_bearer", f"Bearer {session.access_token}" if session.access_token else None),
    ]
    seen: set[tuple[tuple[str, str], ...]] = set()
    for cookie in cookie_variants:
        for label, auth_value in token_variants:
            headers = dict(base)
            parts: list[str] = []
            if cookie:
                headers["Cookie"] = cookie
                parts.append("cookie")
            if auth_value:
                headers["Authorization"] = auth_value
                parts.append(label)
            mode = "+".join(parts) if parts else "anonymous"
            key = tuple(sorted(headers.items()))
            if key in seen:
                continue
            seen.add(key)
            candidates.append((mode, headers))
    return candidates


def _http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    data: bytes | None = None,
    timeout: float = 60.0,
) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return response.status, payload, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        return exc.code, payload, dict(exc.headers.items())


def _parse_json_response(status: int, payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise OfficialAutomationError(f"Expected JSON response, got HTTP {status}: {payload[:500]}") from exc
    return data


def _find_working_headers(
    session: ProsperitySessionBundle,
    *,
    api_root: str,
    round_id: int,
    origin: str,
    referer: str,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    url = f"{api_root}/submissions/algo/{round_id}?page=1&pageSize=50"
    last_error: str | None = None
    for mode, headers in _candidate_auth_headers(session, origin=origin, referer=referer):
        status, payload, _ = _http_request("GET", url, headers=headers)
        if 200 <= status < 300:
            parsed = _parse_json_response(status, payload)
            if parsed.get("success"):
                return mode, headers, parsed
        last_error = f"{mode}: HTTP {status} {payload[:400]}"
    raise OfficialAutomationError(
        "Could not authenticate against the Prosperity API using the logged-in Chrome session. "
        f"Last response: {last_error or 'none'}"
    )


def _list_submissions(
    *,
    api_root: str,
    round_id: int,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    status, payload, _ = _http_request(
        "GET",
        f"{api_root}/submissions/algo/{round_id}?page=1&pageSize=50",
        headers=headers,
    )
    parsed = _parse_json_response(status, payload)
    if not parsed.get("success"):
        raise OfficialAutomationError(f"Submission list request failed: HTTP {status} {payload[:400]}")
    return list(parsed.get("data", {}).get("items", []))


def _upload_submission(
    bot_path: Path,
    *,
    api_root: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    body, boundary = _multipart_body(bot_path)
    upload_headers = dict(headers)
    upload_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    status, payload, _ = _http_request(
        "POST",
        f"{api_root}/submission/algo",
        headers=upload_headers,
        data=body,
    )
    parsed = _parse_json_response(status, payload)
    if status != 201 or not parsed.get("success"):
        raise OfficialAutomationError(f"Upload failed: HTTP {status} {payload[:500]}")
    return dict(parsed.get("data", {}))


def _normalize_submission(item: dict[str, Any]) -> ImcSubmissionRecord:
    submitter = item.get("submittedBy") or {}
    full_name = " ".join(str(x) for x in [submitter.get("firstName"), submitter.get("lastName")] if x).strip()
    return ImcSubmissionRecord(
        id=int(item["id"]),
        round_id=int(item["roundId"]),
        status=str(item.get("status", "")),
        filename=str(item.get("filename", "")),
        active=bool(item.get("active", False)),
        submitted_at=str(item.get("submittedAt", "")),
        submitted_by=full_name,
        simulation_identifier=item.get("simulationApplicationAlgoSubmissionIdentifier"),
    )


def _poll_submission(
    submission_id: int,
    *,
    api_root: str,
    round_id: int,
    headers: dict[str, str],
    poll_seconds: float,
    timeout_seconds: float,
) -> tuple[ImcSubmissionRecord, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    history: list[str] = []
    while time.monotonic() <= deadline:
        items = _list_submissions(api_root=api_root, round_id=round_id, headers=headers)
        match = next((item for item in items if int(item.get("id", -1)) == submission_id), None)
        if match is None:
            raise OfficialAutomationError(f"Submission {submission_id} disappeared from the listing response.")
        record = _normalize_submission(match)
        if not history or history[-1] != record.status:
            history.append(record.status)
        if record.status == "FINISHED":
            return record, history
        if record.status in {"FAILED", "ERROR", "CANCELLED"}:
            raise OfficialAutomationError(f"Submission {submission_id} ended with status {record.status}")
        time.sleep(poll_seconds)
    raise OfficialAutomationError(
        f"Timed out waiting for submission {submission_id} to finish after {timeout_seconds:.0f} seconds"
    )


def _fetch_zip_url(
    submission_id: int,
    *,
    api_root: str,
    headers: dict[str, str],
) -> str:
    status, payload, _ = _http_request(
        "GET",
        f"{api_root}/submissions/algo/{submission_id}/zip",
        headers=headers,
    )
    parsed = _parse_json_response(status, payload)
    if not parsed.get("success"):
        raise OfficialAutomationError(f"ZIP URL request failed: HTTP {status} {payload[:400]}")
    url = parsed.get("data", {}).get("url")
    if not url:
        raise OfficialAutomationError("ZIP URL response did not contain a download URL.")
    return str(url)


def _download_url(url: str, target_path: Path) -> Path:
    ensure_dir(target_path.parent)
    request = urllib.request.Request(url, headers={"User-Agent": "TraderFactory"})
    with urllib.request.urlopen(request, timeout=120.0) as response, target_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return target_path


def _extract_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(output_dir)
        for name in archive.namelist():
            extracted.append((output_dir / name).resolve())
    return extracted


def _first_suffix(paths: list[Path], suffix: str) -> Path | None:
    for path in paths:
        if path.suffix == suffix:
            return path
    return None


def run_imc_prosperity_submission(
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
    run_analysis: bool = True,
    baseline_log: str | Path | None = None,
    baseline_json: str | Path | None = None,
) -> ImcProsperityRunResult:
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

    submission = _upload_submission(bot, api_root=api_root, headers=working_headers)
    submission_id = int(submission["id"])
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
    out = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir(submission_id)
    ensure_dir(out)
    zip_path = _download_url(zip_url, out / download_name)
    extracted = _extract_zip(zip_path, out)
    log_path = _first_suffix(extracted, ".log")
    json_path = _first_suffix(extracted, ".json")
    python_path = _first_suffix(extracted, ".py")

    metadata = {
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
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2))

    analysis_result: DiagnosticRunResult | None = None
    if run_analysis and log_path is not None:
        analysis_result = run_official_trade_quality(
            log_path,
            baseline_log=baseline_log,
            primary_json=json_path,
            baseline_json=baseline_json,
            output_dir=out / "analysis",
        )

    return ImcProsperityRunResult(
        submission_id=submission_id,
        round_id=round_id,
        output_dir=out,
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
