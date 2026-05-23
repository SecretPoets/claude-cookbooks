"""FastAPI backend for the Bloomberg terminal clone.

Serves the static frontend, exposes mock-data REST endpoints, and proxies a
streaming Claude chat endpoint over Server-Sent Events.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import claude_client, mock_data

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="TERM-AI: Bloomberg Terminal Clone")


@app.get("/api/overview")
def overview(jitter: bool = True) -> dict:
    """Top-of-screen ticker strip: indices, FX, commodities, crypto."""
    data = mock_data.market_overview()
    if jitter:
        data = mock_data.jitter_overview(data)
    return data


@app.get("/api/quote/{symbol}")
def quote(symbol: str) -> dict:
    q = mock_data.get_quote(symbol)
    if q is None:
        raise HTTPException(status_code=404, detail=f"unknown symbol: {symbol}")
    return q


@app.get("/api/history/{symbol}")
def history(symbol: str, days: int = 90) -> dict:
    h = mock_data.get_history(symbol, days)
    if h is None:
        raise HTTPException(status_code=404, detail=f"unknown symbol: {symbol}")
    return {"symbol": symbol.upper(), "bars": h}


@app.get("/api/news")
def news(symbol: str | None = None, limit: int = Query(10, ge=1, le=50)) -> dict:
    return {"items": mock_data.get_news(symbol, limit)}


@app.get("/api/watchlist")
def watchlist(symbols: str = "AAPL,MSFT,NVDA,TSLA,GOOGL,AMZN,META,JPM") -> dict:
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    return {"items": mock_data.watchlist_snapshot(syms)}


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    thinking: bool = False


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    """Stream a Claude reply as Server-Sent Events."""

    def event_stream():
        yield from claude_client.stream_chat(
            user_message=req.message,
            history=req.history,
            thinking=req.thinking,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --- Static frontend --------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "tickers": len(mock_data.TICKERS)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)


# Silence unused import warning when run as a script
_ = json
