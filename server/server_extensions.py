"""
============================================================
RAKSHA BACKEND - WATCHDOG + TRACKER EXTENSIONS
File: server_extensions.py  (server.py mein merge karna hai)
============================================================
Ye 3 endpoints add karo apne mukhya server.py mein:
  /auth/refresh   -> token rotation
  /eval           -> signal accuracy evaluation (high/low check)
  /scanner_health -> kis scanner ki kya halat hai
============================================================
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from server import app, get_adapter

from fastapi import HTTPException, Header
from typing import Optional
import time
import pandas as pd

# ---------- TOKEN REFRESH ----------
@app.post("/auth/refresh")
async def refresh_token(authorization: Optional[str] = Header(None)):
    """
    Pre-emptive token refresh. 7 hour ke baad watchdog ye call karta hai
    taki user ko phir se login na karna pade.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    old_token = authorization.replace("Bearer ", "")

    # Broker-specific refresh logic. Zerodha example:
    # Zerodha ka token daily expire hota hai, refresh nahi hota - relogin chahiye
    # Upstox/Angel mein refresh_token flow hai
    try:
        # Yahan apne broker SDK ka refresh call karo
        # Demo:
        new_token = old_token   # production: actual refresh
        return {"token": new_token, "expiresIn": 8 * 3600}
    except Exception as e:
        raise HTTPException(401, f"Refresh failed: {e}")


# ---------- SIGNAL EVALUATION (sahi/galat check) ----------
@app.get("/eval")
async def eval_signal(
    symbol: str,
    from_: int,        # query as ?from=
    to: int,
    entry: float,
    target: float,
    sl: float,
    authorization: Optional[str] = Header(None)
):
    """
    Signal log hone ke baad ye check karta hai actual price action mein
    target hit hua ya SL laga - intraday OHLC se.

    Returns:
      hitTarget    : kya target price chhua candle high ne
      hitSL        : kya SL price chhua candle low ne
      hitSLBefore  : SL pehle laga ya target pehle hit hua
      exitPrice    : eval window end pe price
      maxFavorable : best price in window (for trailing analysis)
      maxAdverse   : worst price in window
    """
    adapter = get_adapter("zerodha")        # production: from session
    from_dt = pd.Timestamp(from_/1000, unit='s', tz='Asia/Kolkata')
    to_dt   = pd.Timestamp(to/1000, unit='s', tz='Asia/Kolkata')

    # 1-min candles le aao window ke andar
    try:
        bars = adapter.history(symbol, "minute",
                               days=int((to - from_) / 86400000) + 1)
        df = pd.DataFrame(bars)
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= from_dt) & (df['date'] <= to_dt)
        df = df[mask].reset_index(drop=True)
    except Exception as e:
        raise HTTPException(500, f"History fetch fail: {e}")

    if df.empty:
        raise HTTPException(404, "No data in window")

    # Sequential walk - kaun pehle hit hua dekho
    hit_target = False
    hit_sl = False
    hit_sl_before = False
    target_idx = None
    sl_idx = None

    for i, row in df.iterrows():
        if not hit_target and row['high'] >= target:
            hit_target = True
            target_idx = i
        if not hit_sl and row['low'] <= sl:
            hit_sl = True
            sl_idx = i
        if hit_target and hit_sl:
            break

    # Order check
    if hit_target and hit_sl and sl_idx is not None and target_idx is not None:
        hit_sl_before = sl_idx < target_idx

    return {
        "hitTarget":     hit_target,
        "hitSL":         hit_sl,
        "hitSLBefore":   hit_sl_before,
        "exitPrice":     float(df['close'].iloc[-1]),
        "maxFavorable":  float(df['high'].max()),
        "maxAdverse":    float(df['low'].min()),
        "barsChecked":   len(df)
    }


# ---------- SCANNER HEALTH (server-side) ----------
# Backend bhi track karta hai ki kaun sa scanner kitna time leta hai
SCANNER_HEALTH = {}

@app.get("/scanner_health")
async def scanner_health():
    """Watchdog ko ye batata hai server-side se kaun sa scanner heavy hai"""
    return SCANNER_HEALTH

# server.py ke run_scanner endpoint ko wrap karo:
"""
@app.get("/scanner/{name}")
async def run_scanner(name: str, symbol: str):
    fn = SCANNER_REGISTRY.get(name)
    if not fn: raise HTTPException(404, f"Scanner {name} not found")
    t0 = time.time()
    try:
        adapter = get_adapter("zerodha")
        df = pd.DataFrame(adapter.history(symbol, "5minute", 5))
        result = fn(df)
        elapsed = (time.time() - t0) * 1000
        h = SCANNER_HEALTH.setdefault(name, {"calls": 0, "errors": 0, "avgMs": 0})
        h["calls"] += 1
        h["avgMs"] = round((h["avgMs"] * 0.7) + (elapsed * 0.3), 1)
        h["lastOk"] = int(time.time())
        return result
    except Exception as e:
        h = SCANNER_HEALTH.setdefault(name, {"calls": 0, "errors": 0, "avgMs": 0})
        h["errors"] += 1
        h["lastError"] = str(e)
        raise HTTPException(500, str(e))
"""

# ---------- PERSISTENCE (optional - signals SQLite mein save karne ke liye) ----------
"""
import sqlite3
DB = sqlite3.connect("/home/ubuntu/raksha.db", check_same_thread=False)
DB.execute('''
  CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    scanner TEXT, symbol TEXT, score REAL, type TEXT,
    entry REAL, target REAL, sl REAL,
    ts INTEGER, eval_at INTEGER,
    outcome TEXT, exit_price REAL, pnl_pct REAL
  )
''')

@app.post("/signals/log")
async def log_signal_db(signal: dict):
    DB.execute('INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (signal['id'], signal['scanner'], signal['symbol'], signal['score'],
         signal['type'], signal['entry'], signal['target'], signal['sl'],
         signal['ts'], signal.get('evalAt'), signal.get('outcome'),
         signal.get('exitPrice'), signal.get('pnlPct')))
    DB.commit()
    return {"ok": True}

@app.get("/signals/stats")
async def signal_stats():
    rows = DB.execute('''
      SELECT scanner,
        COUNT(*) as total,
        SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
        AVG(pnl_pct) as avg_pnl
      FROM signals WHERE outcome IS NOT NULL
      GROUP BY scanner
    ''').fetchall()
    return [{"scanner": r[0], "total": r[1], "wins": r[2], "losses": r[3], "avgPnl": r[4]} for r in rows]
"""
