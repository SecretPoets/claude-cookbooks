/* =====================================================
   TERM-AI :: Bloomberg-style terminal frontend
   Vanilla JS, no build step. Talks to FastAPI backend.
   ===================================================== */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const WATCHLIST = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "JPM", "BRK.B", "XOM"];
let currentSymbol = "AAPL";
let chatHistory = []; // {role, content} pairs we replay back to the API

/* ---------- Utilities ---------- */

function fmtNum(x, digits = 2) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return Number(x).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtCompact(x) {
  if (x === null || x === undefined) return "—";
  const abs = Math.abs(x);
  if (abs >= 1e12) return (x / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return (x / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return (x / 1e6).toFixed(2) + "M";
  if (abs >= 1e3) return (x / 1e3).toFixed(2) + "K";
  return String(x);
}

function chgClass(x) {
  if (x > 0) return "up";
  if (x < 0) return "down";
  return "flat";
}

function chgArrow(x) {
  if (x > 0) return "▲";
  if (x < 0) return "▼";
  return "·";
}

function escapeHTML(s) {
  return (s ?? "")
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ---------- Clock ---------- */

function tickClock() {
  const d = new Date();
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  const ss = String(d.getUTCSeconds()).padStart(2, "0");
  $("#clock").textContent = `${hh}:${mm}:${ss} UTC`;
}
setInterval(tickClock, 1000);
tickClock();

/* ---------- Ticker strip ---------- */

async function loadOverview() {
  try {
    const r = await fetch("/api/overview");
    const data = await r.json();
    renderTicker(data);
    $("#last-update").textContent = "updated " + new Date().toLocaleTimeString();
  } catch (e) {
    console.error("overview failed", e);
  }
}

function renderTicker(data) {
  const groups = [
    ["IDX", data.indices],
    ["FX", data.fx],
    ["COMM", data.commodities],
    ["CRY", data.crypto],
  ];
  const items = [];
  for (const [label, rows] of groups) {
    for (const r of rows) {
      const cls = chgClass(r.chg);
      const digits = label === "FX" ? 4 : 2;
      items.push(
        `<span class="tk"><b>${label}:${r.symbol}</b> ${fmtNum(r.last, digits)} <span class="${cls}">${chgArrow(r.chg)} ${fmtNum(r.chg, digits)} (${fmtNum(r.chg_pct, 2)}%)</span></span>`
      );
    }
  }
  // Duplicate the list so the scrolling loop is seamless.
  const html = items.join("") + items.join("");
  $("#ticker-track").innerHTML = html;
}

setInterval(loadOverview, 8000);
loadOverview();

/* ---------- Watchlist ---------- */

async function loadWatchlist() {
  try {
    const r = await fetch("/api/watchlist?symbols=" + WATCHLIST.join(","));
    const data = await r.json();
    renderWatchlist(data.items);
    $("#watchlist-meta").textContent = data.items.length + " SYMBOLS";
  } catch (e) {
    console.error("watchlist failed", e);
  }
}

function renderWatchlist(items) {
  const tbody = $("#watchlist-table tbody");
  tbody.innerHTML = items
    .map(
      (it) => `
      <tr data-sym="${it.symbol}" class="${it.symbol === currentSymbol ? "selected" : ""}">
        <td>${it.symbol}</td>
        <td>${escapeHTML(it.name)}</td>
        <td class="num">${fmtNum(it.last)}</td>
        <td class="num ${chgClass(it.change)}">${chgArrow(it.change)} ${fmtNum(it.change)}</td>
        <td class="num ${chgClass(it.change_pct)}">${fmtNum(it.change_pct, 2)}%</td>
        <td class="num">${fmtCompact(it.volume)}</td>
      </tr>`
    )
    .join("");
  for (const row of $$("#watchlist-table tbody tr")) {
    row.addEventListener("click", () => selectSymbol(row.dataset.sym));
  }
}

setInterval(loadWatchlist, 10000);
loadWatchlist();

/* ---------- Quote panel + chart ---------- */

async function selectSymbol(sym) {
  currentSymbol = sym;
  for (const row of $$("#watchlist-table tbody tr")) {
    row.classList.toggle("selected", row.dataset.sym === sym);
  }
  $("#quote-title").textContent = sym;
  await Promise.all([loadQuote(sym), loadHistory(sym), loadNews(sym)]);
}

async function loadQuote(sym) {
  try {
    const r = await fetch("/api/quote/" + encodeURIComponent(sym));
    if (!r.ok) throw new Error("quote " + r.status);
    const q = await r.json();
    $("#quote-symbol").textContent = q.symbol;
    $("#quote-name").textContent = q.name;
    $("#quote-exchange").textContent = q.exchange + " · " + q.sector;
    $("#quote-last").textContent = fmtNum(q.last);
    const chgEl = $("#quote-chg");
    chgEl.className = "hero-chg " + chgClass(q.change);
    chgEl.textContent = `${chgArrow(q.change)} ${fmtNum(q.change)} (${fmtNum(q.change_pct, 2)}%)`;
    $("#q-open").textContent = fmtNum(q.open);
    $("#q-high").textContent = fmtNum(q.high);
    $("#q-low").textContent = fmtNum(q.low);
    $("#q-prev").textContent = fmtNum(q.prev_close);
    $("#q-vol").textContent = fmtCompact(q.volume);
    $("#q-mcap").textContent = fmtCompact(q.market_cap);
    $("#q-pe").textContent = fmtNum(q.pe);
    $("#q-div").textContent = fmtNum(q.div_yield) + "%";
    $("#q-eps").textContent = fmtNum(q.eps);
    $("#q-beta").textContent = fmtNum(q.beta);
    $("#q-52h").textContent = fmtNum(q.wk52_high);
    $("#q-52l").textContent = fmtNum(q.wk52_low);
  } catch (e) {
    console.error("quote failed", e);
  }
}

async function loadHistory(sym) {
  try {
    const r = await fetch("/api/history/" + encodeURIComponent(sym) + "?days=120");
    if (!r.ok) return;
    const data = await r.json();
    renderChart(data.bars);
  } catch (e) {
    console.error("history failed", e);
  }
}

function renderChart(bars) {
  if (!bars || bars.length === 0) return;
  const cv = $("#chart");
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth;
  const h = cv.clientHeight;
  cv.width = w * dpr;
  cv.height = h * dpr;
  const ctx = cv.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const pad = { l: 50, r: 10, t: 10, b: 22 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const closes = bars.map((b) => b.close);
  let mn = Math.min(...bars.map((b) => b.low));
  let mx = Math.max(...bars.map((b) => b.high));
  const range = mx - mn || 1;
  mn -= range * 0.05;
  mx += range * 0.05;

  const xStep = innerW / Math.max(1, bars.length - 1);
  const yScale = (p) => pad.t + innerH - ((p - mn) / (mx - mn)) * innerH;

  // grid
  ctx.strokeStyle = "#181818";
  ctx.lineWidth = 1;
  ctx.font = "10px monospace";
  ctx.fillStyle = "#555";
  const yTicks = 5;
  for (let i = 0; i <= yTicks; i++) {
    const v = mn + ((mx - mn) * i) / yTicks;
    const y = yScale(v);
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(w - pad.r, y);
    ctx.stroke();
    ctx.fillText(v.toFixed(2), 4, y + 3);
  }
  // x-axis date labels
  const xTicks = 5;
  for (let i = 0; i <= xTicks; i++) {
    const idx = Math.round(((bars.length - 1) * i) / xTicks);
    const x = pad.l + xStep * idx;
    ctx.fillText(bars[idx].date.slice(5), x - 14, h - 6);
  }

  // candles
  const candleW = Math.max(2, xStep * 0.6);
  for (let i = 0; i < bars.length; i++) {
    const b = bars[i];
    const x = pad.l + xStep * i;
    const up = b.close >= b.open;
    ctx.strokeStyle = up ? "#20d070" : "#ff4030";
    ctx.fillStyle = up ? "#20d070" : "#ff4030";
    // wick
    ctx.beginPath();
    ctx.moveTo(x, yScale(b.high));
    ctx.lineTo(x, yScale(b.low));
    ctx.stroke();
    // body
    const yo = yScale(b.open);
    const yc = yScale(b.close);
    const top = Math.min(yo, yc);
    const bh = Math.max(1, Math.abs(yc - yo));
    ctx.fillRect(x - candleW / 2, top, candleW, bh);
  }

  // close line overlay
  ctx.strokeStyle = "rgba(240,160,32,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let i = 0; i < bars.length; i++) {
    const x = pad.l + xStep * i;
    const y = yScale(bars[i].close);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  const first = closes[0];
  const last = closes[closes.length - 1];
  const chg = last - first;
  const pct = (chg / first) * 100;
  $("#chart-legend").innerHTML =
    `${bars.length}D · ` +
    `<span class="${chgClass(chg)}">${chgArrow(chg)} ${fmtNum(chg)} (${fmtNum(pct, 2)}%)</span> ` +
    `over window · range ${fmtNum(mn)}–${fmtNum(mx)}`;
}

window.addEventListener("resize", () => loadHistory(currentSymbol));

/* ---------- News ---------- */

async function loadNews(sym) {
  try {
    const url = sym ? `/api/news?symbol=${encodeURIComponent(sym)}&limit=12` : "/api/news?limit=12";
    const r = await fetch(url);
    const data = await r.json();
    renderNews(data.items);
    $("#news-meta").textContent = sym ? sym : "TOP";
  } catch (e) {
    console.error("news failed", e);
  }
}

function renderNews(items) {
  const list = $("#news-list");
  if (items.length === 0) {
    list.innerHTML = '<div class="muted">no headlines</div>';
    return;
  }
  list.innerHTML = items
    .map(
      (n) => `
      <div class="news-item" data-id="${n.id}">
        <div class="news-meta">
          <span>${escapeHTML(n.time)}</span>
          ${n.ticker ? `<span class="nt-ticker">${escapeHTML(n.ticker)}</span>` : ""}
          <span class="nt-src">${escapeHTML(n.source)}</span>
        </div>
        <div class="news-head">${escapeHTML(n.headline)}</div>
        <div class="news-body">${escapeHTML(n.body)}</div>
      </div>`
    )
    .join("");
  for (const el of $$(".news-item")) {
    el.addEventListener("click", () => el.classList.toggle("open"));
  }
}

/* ---------- Command bar ---------- */

const HELP_TEXT = `
COMMANDS
  <TICKER>     load ticker (e.g. AAPL)
  NEWS         show top news
  NEWS <TKR>   filter news to ticker
  HELP         this message
  CHAT <Q>     send a question to TERM-AI

KEYS
  F1 help · F2 jump to chat · F3 news
`;

$("#cmdform").addEventListener("submit", (e) => {
  e.preventDefault();
  const raw = $("#cmdinput").value.trim().toUpperCase();
  $("#cmdinput").value = "";
  if (!raw) return;
  handleCommand(raw);
});

function handleCommand(cmd) {
  if (cmd === "HELP") {
    appendChat("sys", "HELP", HELP_TEXT);
    return;
  }
  if (cmd.startsWith("NEWS")) {
    const parts = cmd.split(/\s+/);
    loadNews(parts[1] || null);
    return;
  }
  if (cmd.startsWith("CHAT ")) {
    sendChat(cmd.slice(5));
    return;
  }
  // Treat as a ticker by default.
  if (WATCHLIST.includes(cmd) || cmd.match(/^[A-Z.]{1,8}$/)) {
    selectSymbol(cmd).catch(() =>
      appendChat("sys", "CMD", `Unknown ticker: ${cmd}. Try one of ${WATCHLIST.join(", ")}.`)
    );
    return;
  }
  appendChat("sys", "CMD", `Unrecognized: ${cmd}. Type HELP.`);
}

// Function-key shortcuts
window.addEventListener("keydown", (e) => {
  if (e.key === "F1") {
    e.preventDefault();
    appendChat("sys", "HELP", HELP_TEXT);
  } else if (e.key === "F2") {
    e.preventDefault();
    $("#chatinput").focus();
  } else if (e.key === "F3") {
    e.preventDefault();
    loadNews(null);
  }
});

/* ---------- Chat panel + Claude streaming ---------- */

function appendChat(kind, role, body) {
  const log = $("#chat-log");
  const div = document.createElement("div");
  div.className = "chat-msg " + kind;
  div.innerHTML = `<div class="role">${escapeHTML(role)}</div><div class="body"></div>`;
  div.querySelector(".body").textContent = body;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div.querySelector(".body");
}

function appendStreaming(kind, role) {
  const log = $("#chat-log");
  const div = document.createElement("div");
  div.className = "chat-msg " + kind;
  div.innerHTML = `<div class="role">${escapeHTML(role)}</div><div class="body"></div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div.querySelector(".body");
}

// Click-to-fill examples in the seed message.
document.addEventListener("click", (e) => {
  const ex = e.target.closest(".example");
  if (ex && ex.dataset.prompt) {
    $("#chatinput").value = ex.dataset.prompt;
    $("#chatinput").focus();
  }
});

$("#chatform").addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = $("#chatinput").value.trim();
  if (!msg) return;
  $("#chatinput").value = "";
  sendChat(msg);
});

async function sendChat(message) {
  const thinking = $("#thinking-toggle").checked;
  appendChat("user", "YOU", message);
  $("#chatsend").disabled = true;

  let assistantSink = null;
  let thinkingSink = null;

  // Track assistant text so we can append it to chatHistory after streaming.
  let assistantText = "";
  let sawText = false;

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: chatHistory,
        thinking,
      }),
    });

    if (!resp.ok || !resp.body) {
      appendChat("sys", "ERR", `HTTP ${resp.status}`);
      return;
    }

    const reader = resp.body.getReader();
    const dec = new TextDecoder("utf-8");
    let buf = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });

      // Parse SSE frames split by blank lines.
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const lines = frame.split("\n");
        let ev = "message";
        let data = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        let parsed = {};
        try {
          parsed = JSON.parse(data || "{}");
        } catch {
          parsed = { raw: data };
        }

        if (ev === "thinking") {
          if (!thinkingSink) thinkingSink = appendStreaming("thinking", "THINKING");
          thinkingSink.textContent += parsed.text || "";
          $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
        } else if (ev === "text") {
          if (!assistantSink) {
            assistantSink = appendStreaming("assistant", "TERM-AI");
            sawText = true;
          }
          assistantSink.textContent += parsed.text || "";
          assistantText += parsed.text || "";
          $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
        } else if (ev === "tool_use") {
          const args = JSON.stringify(parsed.input || {});
          appendChat("tool", "TOOL CALL", `${parsed.name}(${args})`);
        } else if (ev === "tool_result") {
          appendChat("tool", `RESULT [${parsed.name}]`, parsed.preview || "");
        } else if (ev === "usage") {
          const u = parsed;
          $("#usage-strip").textContent =
            `tokens in=${u.input_tokens} out=${u.output_tokens} · ` +
            `cache write=${u.cache_creation_input_tokens} read=${u.cache_read_input_tokens}` +
            (u.cache_read_input_tokens > 0 ? "  ✓ cache hit" : "");
        } else if (ev === "error") {
          appendChat("sys", "ERR", parsed.message || "unknown error");
        } else if (ev === "meta") {
          // No-op for now; could surface model name.
        } else if (ev === "done") {
          // finalize
        }
      }
    }

    if (sawText && assistantText.trim()) {
      chatHistory.push({ role: "user", content: message });
      chatHistory.push({ role: "assistant", content: assistantText });
      // Keep history bounded.
      if (chatHistory.length > 20) {
        chatHistory = chatHistory.slice(-20);
      }
    }
  } catch (err) {
    appendChat("sys", "ERR", String(err));
  } finally {
    $("#chatsend").disabled = false;
    $("#chatinput").focus();
  }
}

/* ---------- Init ---------- */

selectSymbol(currentSymbol);
