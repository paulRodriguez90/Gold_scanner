# Gold Scanner — V0.1.2

V0.1.2 keeps the real BLS/Fed data connections from V0.1 and fixes a GitHub Actions compatibility issue with the BLS `.ics` calendar endpoint.

## What changed

- BLS `.ics` calendar is attempted first.
- If BLS returns an HTTP/network error (including `403 Forbidden` from automated runners), the scanner uses an official 2026 fallback schedule for the key releases relevant to gold:
  - Employment Situation / NFP
  - CPI
  - PPI
  - JOLTS
- The BLS Public Data API v1 remains the source for the latest observations.
- The scanner still does **not** calculate market bias yet. V0.1.2 is only a reliable real-data connection layer.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m gold_scanner.main
```

## GitHub Actions

The workflow runs every 15 minutes and can also be launched manually with **Run workflow**.

A successful run should finish with:

```text
CURRENT GOLD SCORE: 0.0
STATE: INDECISION
V0.1 STATUS: DATA CONNECTIONS OK; BIAS ENGINE NOT ACTIVE.
```


## V0.1.2
- Fixed BLS Public Data API single-series request: v1 requires the series ID in the URL for GET requests.
- Added a regression test for the BLS request format.
