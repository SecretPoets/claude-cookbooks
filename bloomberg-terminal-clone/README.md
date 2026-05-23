# TERM-AI :: a Bloomberg-style terminal clone, powered by Claude

A web app styled like a Bloomberg terminal — black background, amber text,
multi-panel grid, scrolling ticker strip, command bar — with a built-in AI
analyst pane that talks to Claude.

This is a cookbook demo. **All market data is mock data, hard-coded in
`backend/mock_data.py`.** Nothing here is investment advice and nothing
queries a real exchange.

## What it demonstrates

The chat pane on the right is a single endpoint that shows four Claude API
features end-to-end:

| Feature             | Where it lives                                                  |
| ------------------- | --------------------------------------------------------------- |
| **Tool use**        | Claude calls `get_quote` / `get_history` / `get_news` / `market_overview` against the mock-data layer. |
| **Streaming**       | Tokens are pushed to the browser as Server-Sent Events as they're generated. |
| **Extended thinking** | Toggle the **EXT. THINKING** checkbox in the chat header to enable a thinking budget; thinking tokens stream into a separate panel. |
| **Prompt caching**  | The long system prompt is sent with `cache_control: ephemeral`. The usage strip under the chat reports `cache read` tokens after the first turn. |

The agentic loop lives in `backend/claude_client.py::stream_chat` — it runs
the tool-call → tool-result loop until Claude stops asking for tools, then
emits a `done` SSE frame.

## Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ TERM-AI   CMD> [ ticker / NEWS / CHAT … ]              LIVE 14:22 UTC│
├──────────────────────────────────────────────────────────────────────┤
│ ◀ IDX:SPX 5970 ▲ … FX:EURUSD 1.0521 … COMM:CL 71.22 … CRY:BTC 97k …  │
├──────────────┬───────────────────────────────────┬───────────────────┤
│  WATCHLIST   │        QUOTE + CHART              │     NEWS WIRE     │
│  AAPL  ▲     │  AAPL  234.18  ▲ 2.26 (+0.97%)    │  08:42 NVDA  …    │
│  MSFT  ▲     │  OPEN 232.40   MKT 3.54T          │  08:30 AAPL  …    │
│  NVDA  ▲     │  [ candle chart ]                 │  08:15 TSLA  …    │
│  TSLA  ▼     │                                   ├───────────────────┤
│  GOOGL ▲     │                                   │  TERM-AI ANALYST  │
│  ...         │                                   │  > question…      │
└──────────────┴───────────────────────────────────┴───────────────────┘
```

- Click any row in the **WATCHLIST** to load that ticker.
- Click a **news headline** to expand the body.
- Type a ticker (`AAPL`), `NEWS`, `NEWS TSLA`, `CHAT <question>`, or `HELP`
  into the top command bar.
- `F1` help · `F2` jump to chat · `F3` show top news.

## Running locally

You need Python 3.11+ and an `ANTHROPIC_API_KEY`.

```bash
cd bloomberg-terminal-clone
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Either set the env var directly...
export ANTHROPIC_API_KEY=sk-ant-...
# ...or copy the cookbook's .env into this directory:
#   cp ../.env .

python run.py
```

Open <http://127.0.0.1:8000>.

The dashboard works fully without the API key (mock data is local); only
the chat panel needs the key.

## File map

```
bloomberg-terminal-clone/
├── README.md
├── requirements.txt
├── run.py                    # launcher (loads .env, starts uvicorn)
├── backend/
│   ├── __init__.py
│   ├── main.py               # FastAPI app + SSE chat endpoint
│   ├── claude_client.py      # tools, streaming, thinking, caching
│   └── mock_data.py          # tickers / indices / FX / commodities / news
└── frontend/
    ├── index.html            # multi-panel terminal layout
    ├── style.css             # black + amber CRT styling
    └── app.js                # vanilla JS, SSE parser, canvas chart
```

## Things to try in the chat

- `Quick read on NVDA: price action, latest news, and a BUY/HOLD/SELL call.`
- `Compare AAPL and MSFT on valuation and recent news.`
- `What's moving the market today? Use market_overview and the top news.`
- `Screen my watchlist for tickers down today; suggest one to watch.`
- Toggle **EXT. THINKING** and ask a multi-step question; you'll see the
  thinking stream above the answer.

After the first turn, watch the usage strip under the chat — you should
see `cache read` tokens grow on subsequent turns, confirming the system
prompt is being served from cache.
