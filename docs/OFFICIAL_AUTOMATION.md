# Official Automation

`TraderFactory` now includes a first IMC Prosperity automation path for algorithm submissions.

The goal is to remove the manual loop of:

1. upload bot by hand
2. wait for completion
3. download the `.zip`
4. extract `.py`, `.json`, `.log`
5. rerun official diagnostics manually

Instead, the factory can now do that in one command.

## What This Automation Does

The lower-level command:

```bash
python3 -m trader_factory.cli official-submit-imc /path/to/Trader.py
```

does the following:

1. reuses the logged-in Prosperity Chrome profile
2. opens or focuses a `prosperity.imc.com` tab
3. reads the live session bundle from that page
4. uploads the bot to the official tutorial-round algorithm endpoint
5. polls the official submission list until the run is `FINISHED`
6. fetches the official signed ZIP download URL
7. downloads and extracts the ZIP under `generated/official_runs/imc_prosperity/<submission_id>/`
8. optionally runs the official trade-quality analyzer on the downloaded artifacts

The recommended higher-level command is now:

```bash
python3 -m trader_factory.cli official-cycle-imc /path/to/Trader.py
```

That workflow adds the team-aware behavior you asked for:

1. wait until the shared submission queue is available again if a teammate run is still processing
2. snapshot the current active official submission before uploading
3. submit the new bot
4. download the new result bundle
5. automatically download the previous active submission as the baseline if you did not provide one explicitly
6. run the official comparison
7. emit a one-file workflow summary including whether the new run is still the submission that counts

## Current Requirements

This automation is intentionally profile-based, not password-based.

That means the user must already have a working logged-in Chrome profile for Prosperity.

Current assumptions:

- browser: `Google Chrome`
- profile directory: `Default`
- Prosperity game URL: `https://prosperity.imc.com/game`
- API root discovered from the HAR:
  - `https://3dzqiahkw1.execute-api.eu-west-1.amazonaws.com/prod`

## One-Time Chrome Setting

Chrome must allow JavaScript execution from Apple Events.

Enable this once in Chrome:

1. open Chrome
2. open the menu bar item `View`
3. open `Developer`
4. enable `Allow JavaScript from Apple Events`

Without this setting, TraderFactory cannot read the live Prosperity session from the logged-in tab.

## Why This Design Was Chosen

The HAR showed that the official site uses direct API endpoints for:

- listing submissions
- uploading bots
- fetching the ZIP download URL

But the authentication material is tied to the logged-in browser session, not to a simple static API token in the repo.

So the current design is:

- browser-assisted session reuse
- API-driven submission/download once the live session is available

This is much more stable than trying to click the UI for every step.

## Output Layout

A successful run creates a directory like:

```text
generated/official_runs/imc_prosperity/<submission_id>/
```

Typical contents:

- downloaded ZIP
- extracted `.py`
- extracted `.json`
- extracted `.log`
- `metadata.json`
- optional `analysis/` directory from the official trade-quality report

## CLI Options

Useful flags:

```bash
python3 -m trader_factory.cli official-submit-imc /path/to/Trader.py \
  --round-id 1 \
  --baseline-log /path/to/baseline.log \
  --baseline-json /path/to/baseline.json
```

You can also override:

- `--output-dir`
- `--chrome-app`
- `--chrome-profile-dir`
- `--game-url`
- `--api-root`
- `--poll-seconds`
- `--timeout-seconds`
- `--skip-analysis`

For the higher-level workflow:

```bash
python3 -m trader_factory.cli official-cycle-imc /path/to/Trader.py \
  --queue-poll-seconds 20 \
  --queue-timeout-seconds 1800
```

Useful workflow-specific options:

- `--queue-poll-seconds`
- `--queue-timeout-seconds`
- `--baseline-log`
- `--baseline-json`
- `--skip-analysis`

If `--baseline-log` / `--baseline-json` are omitted, TraderFactory will automatically use the current active official submission before your upload as the comparison baseline.

## Current Limitations

- this is currently tailored to the IMC Prosperity site flow discovered from the provided HAR
- it assumes the user has already logged into Prosperity in Chrome
- it does not yet create a dedicated browser profile or manage login itself
- it currently targets the algorithm submission flow, not manual challenge rounds
- there is still a race window between “queue clear” and “upload submitted”; if a teammate uploads in that exact window, Prosperity may still accept whichever submission ends up last

## Next Likely Improvements

- support per-round presets once future Prosperity rounds open
- add a richer post-run pipeline that automatically runs more official analyzers
- add a browser-side fallback request path if direct API auth conventions change
