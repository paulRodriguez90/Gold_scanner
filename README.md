# Gold Scanner

## V0.2 — DXY + US10Y + real yields + XAUUSD

This version connects the four market drivers that most directly help contextualize gold:

- **DXY** — ICE US Dollar Index via Yahoo Finance market data.
- **US10Y** — 10-year U.S. Treasury nominal yield via FRED series `DGS10`.
- **10Y real yield** — 10-year inflation-indexed Treasury yield via FRED series `DFII10`.
- **XAUUSD** — spot gold via Yahoo Finance, with a Stooq quote fallback.

The scanner compares 1-day and 5-day movement and converts it into a preliminary factor score from -100 to +100. For gold, rising DXY, nominal yields and real yields are treated as bearish pressure; rising XAUUSD is treated as bullish confirmation.

**Important:** this is still a market-driver layer, not a complete trading signal. Fed, inflation, employment, China/PBoC, geopolitics, news surprise and reaction analysis will be integrated next.

## Run locally

```bash
pip install -r requirements.txt
python -m pytest -q
python -m gold_scanner.main
```

## GitHub Actions

The existing scheduled/manual workflow runs tests and then the scanner.
