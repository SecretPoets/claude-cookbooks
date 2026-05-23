"""Claude integration for the Bloomberg terminal clone.

Showcases four API features in one place:
  - tool use         : Claude calls get_quote / get_news / get_history / market_overview
  - streaming        : tokens are pushed to the frontend as Server-Sent Events
  - extended thinking: optional, surfaces a "thinking" stream to the UI
  - prompt caching   : the long system prompt is cached so repeated queries are cheap
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

import anthropic

from . import mock_data

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    """You are TERM-AI, the analyst assistant inside a Bloomberg-style terminal.

You speak in the clipped, dense register of a sell-side desk note: short
sentences, bullet points where useful, numbers with appropriate precision,
and explicit caveats when the data is incomplete. Never invent numbers --
if you don't have the data, call a tool to get it.

Available tools:
  - get_quote(symbol)         : real-time-ish snapshot for a ticker
  - get_history(symbol, days) : daily OHLC bars
  - get_news(symbol?)         : recent headlines, optionally ticker-filtered
  - market_overview()         : indices / FX / commodities / crypto strip

Style rules:
  - Open with the punchline -- the call, the level, or the catalyst.
  - Use % moves vs prev close, not absolute prints, when discussing direction.
  - Cite tool data inline, e.g. "AAPL 234.18 (+0.97%)".
  - If asked for a recommendation, give one (BUY / HOLD / SELL / WATCH) with
    a one-line rationale and a one-line risk.
  - End with "// END" on its own line.

You are inside a paper-trading sandbox. Nothing you produce is investment
advice. Mock data only -- prices, news and fundamentals are illustrative.
"""
    + ("\n" * 4)
    + (
        "Reference taxonomy (kept verbose so the system prompt qualifies for caching; "
        "the cache hit pays for itself after the first turn):\n"
        "- Coverage universe: mega-cap US tech (AAPL, MSFT, NVDA, GOOGL, META, AMZN), "
        "EV / consumer cyclical (TSLA), financials (JPM, BRK.B), energy (XOM).\n"
        "- Indices: SPX, DJI, IXIC, RUT, VIX. FX majors: EURUSD, USDJPY, GBPUSD, USDCNY. "
        "Commodities: CL (WTI), GC (gold), SI (silver), NG (nat gas). "
        "Crypto: BTC, ETH, SOL.\n"
        "- For multi-leg questions ('compare X to Y', 'screen for Z'), parallelize "
        "tool calls in a single turn rather than chaining sequentially.\n"
        "- Treat headlines from get_news as a feed of potentially market-moving items; "
        "tie them back to the quote when you cite them.\n"
    )
)

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_quote",
        "description": (
            "Return a snapshot quote for a single ticker symbol, including last price, "
            "OHLC for the session, prev close, volume, market cap, P/E, dividend yield, "
            "52-week range, and beta. Returns null-equivalent if symbol is unknown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol, e.g. AAPL, MSFT, NVDA.",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_history",
        "description": "Return daily OHLC bars for a ticker over the last N trading days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol."},
                "days": {
                    "type": "integer",
                    "description": "Lookback window in calendar days (default 90).",
                    "default": 90,
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "Return recent news headlines. Pass a symbol to filter to ticker-related "
            "items (plus macro items that affect everyone); omit for the top feed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Optional ticker filter.",
                },
                "limit": {"type": "integer", "default": 8},
            },
        },
    },
    {
        "name": "market_overview",
        "description": (
            "Snapshot of the top-of-screen strip: indices, FX majors, commodities, crypto."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _run_tool(name: str, args: dict[str, Any]) -> Any:
    """Dispatch a tool call to the mock data layer."""
    if name == "get_quote":
        return mock_data.get_quote(args.get("symbol", "")) or {"error": "unknown symbol"}
    if name == "get_history":
        return mock_data.get_history(args.get("symbol", ""), int(args.get("days", 90))) or {
            "error": "unknown symbol"
        }
    if name == "get_news":
        return mock_data.get_news(args.get("symbol"), int(args.get("limit", 8)))
    if name == "market_overview":
        return mock_data.market_overview()
    return {"error": f"unknown tool {name}"}


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set -- copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def _sse(event: str, data: dict | str) -> str:
    """Format a Server-Sent Event frame."""
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def stream_chat(
    user_message: str,
    history: list[dict] | None = None,
    thinking: bool = False,
) -> Iterator[str]:
    """Stream a Claude reply as SSE frames.

    Yields frames of the following types:
        meta     : run metadata (model, thinking on/off)
        thinking : a chunk of extended-thinking text
        text     : a chunk of the final answer
        tool_use : Claude is invoking a tool
        tool_result : the tool returned (truncated for display)
        usage    : token + cache usage at the end of each model call
        done     : terminal frame
        error    : something went wrong
    """
    yield _sse("meta", {"model": MODEL, "thinking": thinking})

    try:
        client = _client()
    except Exception as e:  # noqa: BLE001 -- surface to the UI as a friendly frame
        yield _sse("error", {"message": str(e)})
        yield _sse("done", {})
        return

    # Cache the system prompt so subsequent turns pay only for new tokens.
    system_blocks: list[dict] = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": user_message})

    extra_kwargs: dict[str, Any] = {}
    if thinking:
        extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4000}
        max_tokens = 8000
    else:
        max_tokens = 2048

    # Agentic loop: keep going until Claude stops calling tools.
    for _ in range(8):
        try:
            with client.messages.stream(
                model=MODEL,
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
                max_tokens=max_tokens,
                **extra_kwargs,
            ) as stream:
                current_block: dict | None = None
                tool_input_buf = ""

                for event in stream:
                    et = event.type

                    if et == "content_block_start":
                        current_block = {"type": event.content_block.type}
                        if event.content_block.type == "tool_use":
                            current_block["id"] = event.content_block.id
                            current_block["name"] = event.content_block.name
                            tool_input_buf = ""
                            yield _sse(
                                "tool_use_start",
                                {"id": current_block["id"], "name": current_block["name"]},
                            )

                    elif et == "content_block_delta":
                        d = event.delta
                        if d.type == "thinking_delta":
                            yield _sse("thinking", {"text": d.thinking})
                        elif d.type == "text_delta":
                            yield _sse("text", {"text": d.text})
                        elif d.type == "input_json_delta":
                            tool_input_buf += d.partial_json

                    elif et == "content_block_stop":
                        if current_block and current_block.get("type") == "tool_use":
                            try:
                                parsed = json.loads(tool_input_buf) if tool_input_buf else {}
                            except json.JSONDecodeError:
                                parsed = {}
                            yield _sse(
                                "tool_use",
                                {
                                    "id": current_block["id"],
                                    "name": current_block["name"],
                                    "input": parsed,
                                },
                            )
                        current_block = None

                final = stream.get_final_message()

            # Emit usage info (incl. cache stats) for the run.
            usage = getattr(final, "usage", None)
            if usage:
                yield _sse(
                    "usage",
                    {
                        "input_tokens": getattr(usage, "input_tokens", 0),
                        "output_tokens": getattr(usage, "output_tokens", 0),
                        "cache_creation_input_tokens": getattr(
                            usage, "cache_creation_input_tokens", 0
                        ),
                        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                    },
                )

            # If Claude is asking to call tools, run them and loop.
            if final.stop_reason == "tool_use":
                assistant_content = [b.model_dump() for b in final.content]
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results: list[dict] = []
                for block in final.content:
                    if block.type == "tool_use":
                        result = _run_tool(block.name, block.input or {})
                        result_str = json.dumps(result, default=str)
                        # Send a compact preview to the UI.
                        preview = result_str if len(result_str) < 600 else result_str[:600] + "..."
                        yield _sse(
                            "tool_result",
                            {"id": block.id, "name": block.name, "preview": preview},
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_str,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            break

        except anthropic.APIError as e:
            yield _sse("error", {"message": f"Anthropic API error: {e}"})
            break
        except Exception as e:  # noqa: BLE001 -- surface to the UI
            yield _sse("error", {"message": f"{type(e).__name__}: {e}"})
            break

    yield _sse("done", {})
