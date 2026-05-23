"""Mock financial data for the Bloomberg terminal clone.

Self-contained sample data so the demo runs offline without any market data API.
Numbers are illustrative, not real prices.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

TICKERS: dict[str, dict] = {
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "last": 234.18,
        "open": 232.40,
        "high": 235.90,
        "low": 231.55,
        "prev_close": 231.92,
        "volume": 48_920_311,
        "market_cap": 3_540_000_000_000,
        "pe": 36.4,
        "div_yield": 0.43,
        "eps": 6.43,
        "beta": 1.21,
        "wk52_high": 246.10,
        "wk52_low": 164.07,
    },
    "MSFT": {
        "name": "Microsoft Corp.",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "last": 432.12,
        "open": 429.80,
        "high": 433.55,
        "low": 428.10,
        "prev_close": 430.55,
        "volume": 21_330_004,
        "market_cap": 3_210_000_000_000,
        "pe": 37.2,
        "div_yield": 0.71,
        "eps": 11.62,
        "beta": 0.93,
        "wk52_high": 468.35,
        "wk52_low": 309.45,
    },
    "NVDA": {
        "name": "NVIDIA Corp.",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "last": 138.42,
        "open": 136.10,
        "high": 139.88,
        "low": 135.42,
        "prev_close": 135.61,
        "volume": 245_810_223,
        "market_cap": 3_400_000_000_000,
        "pe": 64.1,
        "div_yield": 0.03,
        "eps": 2.16,
        "beta": 1.71,
        "wk52_high": 152.89,
        "wk52_low": 39.23,
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "sector": "Consumer Cyclical",
        "exchange": "NASDAQ",
        "last": 248.91,
        "open": 252.30,
        "high": 253.40,
        "low": 246.10,
        "prev_close": 251.44,
        "volume": 88_220_551,
        "market_cap": 794_000_000_000,
        "pe": 71.3,
        "div_yield": 0.00,
        "eps": 3.49,
        "beta": 2.31,
        "wk52_high": 299.29,
        "wk52_low": 138.80,
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Communication Services",
        "exchange": "NASDAQ",
        "last": 178.55,
        "open": 177.80,
        "high": 179.20,
        "low": 176.55,
        "prev_close": 177.10,
        "volume": 18_330_511,
        "market_cap": 2_180_000_000_000,
        "pe": 24.1,
        "div_yield": 0.45,
        "eps": 7.41,
        "beta": 1.05,
        "wk52_high": 193.31,
        "wk52_low": 130.66,
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "sector": "Consumer Cyclical",
        "exchange": "NASDAQ",
        "last": 207.44,
        "open": 205.10,
        "high": 208.55,
        "low": 204.90,
        "prev_close": 204.88,
        "volume": 35_991_002,
        "market_cap": 2_180_000_000_000,
        "pe": 45.7,
        "div_yield": 0.00,
        "eps": 4.54,
        "beta": 1.16,
        "wk52_high": 215.90,
        "wk52_low": 142.81,
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "sector": "Communication Services",
        "exchange": "NASDAQ",
        "last": 612.30,
        "open": 608.00,
        "high": 614.20,
        "low": 606.55,
        "prev_close": 609.41,
        "volume": 12_440_998,
        "market_cap": 1_550_000_000_000,
        "pe": 28.4,
        "div_yield": 0.34,
        "eps": 21.55,
        "beta": 1.22,
        "wk52_high": 638.40,
        "wk52_low": 379.25,
    },
    "JPM": {
        "name": "JPMorgan Chase & Co.",
        "sector": "Financial Services",
        "exchange": "NYSE",
        "last": 248.10,
        "open": 246.55,
        "high": 249.30,
        "low": 245.80,
        "prev_close": 246.22,
        "volume": 8_113_007,
        "market_cap": 700_000_000_000,
        "pe": 13.1,
        "div_yield": 2.01,
        "eps": 18.94,
        "beta": 1.08,
        "wk52_high": 254.31,
        "wk52_low": 169.32,
    },
    "BRK.B": {
        "name": "Berkshire Hathaway Inc.",
        "sector": "Financial Services",
        "exchange": "NYSE",
        "last": 478.90,
        "open": 477.10,
        "high": 480.50,
        "low": 476.30,
        "prev_close": 476.45,
        "volume": 3_220_115,
        "market_cap": 1_032_000_000_000,
        "pe": 9.8,
        "div_yield": 0.00,
        "eps": 48.86,
        "beta": 0.88,
        "wk52_high": 491.67,
        "wk52_low": 354.08,
    },
    "XOM": {
        "name": "Exxon Mobil Corp.",
        "sector": "Energy",
        "exchange": "NYSE",
        "last": 117.55,
        "open": 118.10,
        "high": 118.80,
        "low": 116.90,
        "prev_close": 118.04,
        "volume": 14_220_881,
        "market_cap": 510_000_000_000,
        "pe": 13.9,
        "div_yield": 3.32,
        "eps": 8.46,
        "beta": 0.91,
        "wk52_high": 126.34,
        "wk52_low": 95.77,
    },
}

INDICES: dict[str, dict] = {
    "SPX": {"name": "S&P 500", "last": 5970.84, "chg": 12.44, "chg_pct": 0.21},
    "DJI": {"name": "Dow Jones Industrial", "last": 43990.10, "chg": -55.21, "chg_pct": -0.13},
    "IXIC": {"name": "NASDAQ Composite", "last": 19384.55, "chg": 88.32, "chg_pct": 0.46},
    "VIX": {"name": "CBOE Volatility Index", "last": 14.92, "chg": -0.31, "chg_pct": -2.04},
    "RUT": {"name": "Russell 2000", "last": 2412.71, "chg": 4.10, "chg_pct": 0.17},
}

FX: dict[str, dict] = {
    "EURUSD": {"name": "Euro / US Dollar", "last": 1.0521, "chg": 0.0012, "chg_pct": 0.11},
    "USDJPY": {"name": "US Dollar / Yen", "last": 154.32, "chg": -0.41, "chg_pct": -0.27},
    "GBPUSD": {"name": "Pound / US Dollar", "last": 1.2588, "chg": 0.0034, "chg_pct": 0.27},
    "USDCNY": {"name": "US Dollar / Yuan", "last": 7.2410, "chg": 0.0021, "chg_pct": 0.03},
}

COMMODITIES: dict[str, dict] = {
    "CL": {"name": "Crude Oil WTI", "last": 71.22, "chg": 0.84, "chg_pct": 1.19, "unit": "USD/bbl"},
    "GC": {"name": "Gold", "last": 2698.40, "chg": -3.10, "chg_pct": -0.11, "unit": "USD/oz"},
    "SI": {"name": "Silver", "last": 31.55, "chg": 0.21, "chg_pct": 0.67, "unit": "USD/oz"},
    "NG": {"name": "Natural Gas", "last": 3.41, "chg": 0.08, "chg_pct": 2.40, "unit": "USD/MMBtu"},
}

CRYPTO: dict[str, dict] = {
    "BTC": {"name": "Bitcoin", "last": 97_230.10, "chg": 1245.50, "chg_pct": 1.30},
    "ETH": {"name": "Ethereum", "last": 3411.85, "chg": -22.10, "chg_pct": -0.64},
    "SOL": {"name": "Solana", "last": 241.55, "chg": 5.32, "chg_pct": 2.25},
}

NEWS: list[dict] = [
    {
        "id": "N0001",
        "time": "08:42",
        "ticker": "NVDA",
        "headline": "NVIDIA tops estimates as data center revenue climbs 94% YoY",
        "source": "MarketWire",
        "body": (
            "NVIDIA Corporation reported quarterly revenue of $35.1B, up 94% YoY, driven by "
            "continued Hopper and Blackwell demand from hyperscale customers. Gross margin held "
            "above 75%. Management guided next quarter revenue to $37.5B +/- 2%, modestly above "
            "consensus, but cautioned that Blackwell supply constraints could persist into Q2."
        ),
    },
    {
        "id": "N0002",
        "time": "08:30",
        "ticker": "AAPL",
        "headline": "Apple reportedly accelerates AI server build-out, eyes custom silicon",
        "source": "Bloomberg",
        "body": (
            "Apple is said to be expanding its private cloud compute infrastructure with custom "
            "M-series-derived server chips, according to people familiar with the matter. The "
            "effort is aimed at supporting Apple Intelligence features at scale while keeping "
            "user data on-device or within Apple-controlled servers."
        ),
    },
    {
        "id": "N0003",
        "time": "08:15",
        "ticker": "TSLA",
        "headline": "Tesla cuts FSD subscription price by 30% in push for adoption",
        "source": "Reuters",
        "body": (
            "Tesla lowered its Full Self-Driving subscription to $69/month from $99 in the US. "
            "The move follows a slower-than-expected ramp in take rate and comes ahead of the "
            "Cybercab production timeline reaffirmed by CEO Elon Musk last week."
        ),
    },
    {
        "id": "N0004",
        "time": "07:58",
        "ticker": "JPM",
        "headline": "JPMorgan raises FY net interest income guidance amid resilient consumer",
        "source": "WSJ",
        "body": (
            "JPMorgan Chase increased its full-year net interest income outlook to ~$92B, citing "
            "stronger-than-expected card balances and benign credit costs. CFO Jeremy Barnum said "
            "the consumer remains on solid footing despite cumulative inflation pressure."
        ),
    },
    {
        "id": "N0005",
        "time": "07:45",
        "ticker": "XOM",
        "headline": "Exxon advances Guyana FID, eyes 1.3M bpd from Stabroek by 2027",
        "source": "Energy Intel",
        "body": (
            "Exxon Mobil approved a sixth development project offshore Guyana, advancing its "
            "target of 1.3 million barrels per day of gross capacity in the Stabroek block by "
            "2027. Breakeven for the project sits below $35/bbl, the company said."
        ),
    },
    {
        "id": "N0006",
        "time": "07:30",
        "ticker": "MSFT",
        "headline": "Microsoft expands Azure AI capacity with new Wisconsin datacenter",
        "source": "MarketWire",
        "body": (
            "Microsoft broke ground on a $3.3B AI-focused datacenter campus in Mount Pleasant, "
            "Wisconsin, intended to host frontier model training and inference workloads. The "
            "site will draw on a mix of grid power and on-site generation."
        ),
    },
    {
        "id": "N0007",
        "time": "07:10",
        "ticker": None,
        "headline": "Fed minutes signal patience on cuts as services inflation lingers",
        "source": "Bloomberg",
        "body": (
            "Minutes from the latest FOMC meeting show policymakers leaning toward a slower pace "
            "of rate reductions, with several participants flagging persistent services inflation "
            "and a tight labor market. Markets now price ~35% odds of a cut at the next meeting."
        ),
    },
    {
        "id": "N0008",
        "time": "06:55",
        "ticker": "BTC",
        "headline": "Bitcoin tops $97K as ETF flows hit fresh weekly record",
        "source": "CoinDesk",
        "body": (
            "Bitcoin briefly touched $97,400 in early trading after spot ETF inflows reached a "
            "record $3.1B for the week. Analysts cite year-end allocator flows and improving "
            "regulatory tone as supportive of further upside."
        ),
    },
]


def _ohlc_series(start: float, days: int, seed: int) -> list[dict]:
    """Generate a deterministic daily OHLC series ending today."""
    rng = random.Random(seed)
    today = datetime.now(UTC).date()
    prices: list[dict] = []
    price = start
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        drift = rng.uniform(-0.018, 0.020)
        op = price
        cl = max(0.5, op * (1 + drift))
        hi = max(op, cl) * (1 + rng.uniform(0.0, 0.012))
        lo = min(op, cl) * (1 - rng.uniform(0.0, 0.012))
        vol = int(rng.uniform(0.6, 1.6) * 25_000_000)
        prices.append(
            {
                "date": d.isoformat(),
                "open": round(op, 2),
                "high": round(hi, 2),
                "low": round(lo, 2),
                "close": round(cl, 2),
                "volume": vol,
            }
        )
        price = cl
    return prices


def get_quote(ticker: str) -> dict | None:
    """Return a snapshot quote for a ticker symbol."""
    t = ticker.upper().strip()
    if t in TICKERS:
        q = dict(TICKERS[t])
        q["symbol"] = t
        q["change"] = round(q["last"] - q["prev_close"], 2)
        q["change_pct"] = round((q["last"] - q["prev_close"]) / q["prev_close"] * 100, 2)
        return q
    return None


def get_history(ticker: str, days: int = 90) -> list[dict] | None:
    """Return a deterministic OHLC series for the ticker."""
    t = ticker.upper().strip()
    if t not in TICKERS:
        return None
    start = TICKERS[t]["last"] * 0.85
    seed = sum(ord(c) for c in t) * 31 + days
    return _ohlc_series(start, days, seed)


def get_news(ticker: str | None = None, limit: int = 10) -> list[dict]:
    """Return recent news, optionally filtered by ticker."""
    if ticker:
        t = ticker.upper().strip()
        items = [n for n in NEWS if n.get("ticker") == t or (n.get("ticker") is None)]
    else:
        items = list(NEWS)
    return items[:limit]


def market_overview() -> dict:
    """Snapshot of indices, FX, commodities, and crypto for the top strip."""
    return {
        "indices": [{"symbol": k, **v} for k, v in INDICES.items()],
        "fx": [{"symbol": k, **v} for k, v in FX.items()],
        "commodities": [{"symbol": k, **v} for k, v in COMMODITIES.items()],
        "crypto": [{"symbol": k, **v} for k, v in CRYPTO.items()],
    }


def watchlist_snapshot(symbols: list[str]) -> list[dict]:
    """Return quote summaries for a list of symbols, skipping unknowns."""
    out = []
    for s in symbols:
        q = get_quote(s)
        if q is not None:
            out.append(
                {
                    "symbol": q["symbol"],
                    "name": q["name"],
                    "last": q["last"],
                    "change": q["change"],
                    "change_pct": q["change_pct"],
                    "volume": q["volume"],
                }
            )
    return out


def jitter_overview(overview: dict, seed: int | None = None) -> dict:
    """Apply tiny random jitter so the dashboard feels live between polls."""
    rng = random.Random(seed)
    for bucket in ("indices", "fx", "commodities", "crypto"):
        for row in overview[bucket]:
            base = row["last"]
            delta = base * rng.uniform(-0.0015, 0.0015)
            row["last"] = round(base + delta, 4 if bucket == "fx" else 2)
            row["chg"] = round(row["chg"] + delta, 4 if bucket == "fx" else 2)
            row["chg_pct"] = round(row["chg_pct"] + rng.uniform(-0.05, 0.05), 2)
    return overview
