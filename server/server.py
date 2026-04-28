"""
============================================================
RAKSHA BACKEND  -  AWS Ubuntu Server  (i-0c62cef0694a8c956)
File: server.py    |    Port: 8080 (REST) + 8081 (WS)
============================================================
Ye backend aapke 10 brokers se connect hoga aur 9 scanners
chala kar HTML frontend ko live data + scores bhejega.

Install:
    sudo apt install python3-pip
    pip3 install fastapi uvicorn websockets httpx pandas \
                 numpy ta-lib kiteconnect upstox-python-sdk

Run:
    uvicorn server:app --host 0.0.0.0 --port 8080
    python3 ws_server.py   # alag terminal mein
============================================================
"""

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import asyncio, time, os, json

app = FastAPI(title="Raksha Pipeline")

# Frontend GitHub Pages se call karega, CORS open rakhna padega
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # production mein apna domain dalna
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- BROKER ADAPTERS ----------
# Har broker ka ek adapter, same interface follow karega
class BrokerBase:
    def login(self, creds):     raise NotImplementedError
    def quote(self, symbols):   raise NotImplementedError
    def history(self, symbol, interval, days): raise NotImplementedError

class ZerodhaAdapter(BrokerBase):
    def __init__(self):
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=os.getenv("KITE_KEY", ""))
    def login(self, creds):
        self.kite.set_access_token(creds["access_token"])
        return {"ok": True}
    def quote(self, symbols):
        return self.kite.quote(symbols)
    def history(self, symbol, interval, days):
        from datetime import datetime, timedelta
        to_d = datetime.now()
        from_d = to_d - timedelta(days=days)
        return self.kite.historical_data(symbol, from_d, to_d, interval)

# Aise hi UpstoxAdapter, AngelAdapter ... 10 banaane hain
ADAPTERS = {
    "zerodha": ZerodhaAdapter,
    # "upstox":  UpstoxAdapter,
    # "angel":   AngelAdapter,
    # ... etc
}

def get_adapter(broker_name: str):
    cls = ADAPTERS.get(broker_name)
    if not cls:
        raise HTTPException(400, f"Broker {broker_name} not configured")
    return cls()


# ---------- SCANNER ENGINE ----------
# Har scanner ek function. Score 0-100 return karta hai.
# Yahan main 1-2 sample diya hu, baaki same pattern follow.

import numpy as np, pandas as pd

def scanner_morning_bell(df: pd.DataFrame) -> dict:
    """Nifty100 stocks > 500 rs filter, gap-up + volume surge"""
    if df.empty or df['close'].iloc[-1] < 500:
        return {"score": 0, "reason": "below 500"}
    gap = (df['open'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
    score = min(100, max(0, (gap * 10) + (vol_ratio * 20)))
    return {"score": round(score), "gap_pct": round(gap, 2), "vol_ratio": round(vol_ratio, 2)}

def scanner_mahakal(df: pd.DataFrame) -> dict:
    """8 price-action tools combined"""
    if len(df) < 50:
        return {"score": 0}
    # Simplified - aap apni JS class ka logic yahan port karoge
    rsi = compute_rsi(df['close'], 14).iloc[-1]
    ema_cross = df['close'].ewm(span=9).mean().iloc[-1] > df['close'].ewm(span=21).mean().iloc[-1]
    macd_pos = compute_macd(df['close']).iloc[-1] > 0
    above_vwap = df['close'].iloc[-1] > vwap(df).iloc[-1]
    score = (
        (30 if 50 < rsi < 70 else 10) +
        (25 if ema_cross else 0) +
        (25 if macd_pos else 0) +
        (20 if above_vwap else 0)
    )
    return {"score": score, "rsi": round(rsi, 1)}

def scanner_bherve(df):       return {"score": 0}   # 7 indicator groups
def scanner_index_power(df):  return {"score": 0}
def scanner_trishul_news(df): return {"score": 0}   # NEWS api integrate karna - SELL bug yahin fix karoge
def scanner_sudarshan(df):    return {"score": 0}
def scanner_brahmastra(df):   return {"score": 0}
def scanner_expiry_scalper(df): return {"score": 0}

SCANNER_REGISTRY = {
    "morning_bell":   scanner_morning_bell,
    "mahakal":        scanner_mahakal,
    "bherve":         scanner_bherve,
    "index_power":    scanner_index_power,
    "trishul_news":   scanner_trishul_news,
    "sudarshan":      scanner_sudarshan,
    "brahmastra":     scanner_brahmastra,
    "expiry_scalper": scanner_expiry_scalper,
}


# ---------- INDICATOR HELPERS ----------
def compute_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    dn = -delta.clip(upper=0).rolling(period).mean()
    return 100 - (100 / (1 + up / dn))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_f = series.ewm(span=fast).mean()
    ema_s = series.ewm(span=slow).mean()
    macd  = ema_f - ema_s
    return macd - macd.ewm(span=signal).mean()   # histogram

def vwap(df):
    tp = (df['high'] + df['low'] + df['close']) / 3
    return (tp * df['volume']).cumsum() / df['volume'].cumsum()


# ---------- API ENDPOINTS ----------
@app.post("/auth/login")
async def login(payload: dict):
    broker = payload.get("broker")
    adapter = get_adapter(broker)
    result = adapter.login(payload.get("credentials", {}))
    return {"token": result.get("access_token", "demo"), "broker": broker}

@app.get("/quotes")
async def quotes(symbols: str, authorization: Optional[str] = Header(None)):
    syms = symbols.split(",")
    adapter = get_adapter("zerodha")        # default; production mein session se le
    return adapter.quote(syms)

@app.get("/scanner/{name}")
async def run_scanner(name: str, symbol: str):
    fn = SCANNER_REGISTRY.get(name)
    if not fn:
        raise HTTPException(404, f"Scanner {name} not found")
    adapter = get_adapter("zerodha")
    df = pd.DataFrame(adapter.history(symbol, "5minute", 5))
    return fn(df)

@app.get("/health")
async def health():
    return {"ok": True, "ts": int(time.time())}


# ---------- WEBSOCKET (alag file ws_server.py) ----------
"""
import asyncio, websockets, json
from kiteconnect import KiteTicker

async def handler(ws, path):
    # parse token from query
    token = path.split("token=")[-1]
    kt = KiteTicker(api_key=os.getenv("KITE_KEY"), access_token=token)

    def on_ticks(ws_kt, ticks):
        for t in ticks:
            asyncio.run(ws.send(json.dumps({
                "symbol": t["instrument_token"],
                "ltp": t["last_price"],
                "ch": t.get("change", 0),
                "vol": t.get("volume", 0),
                "ts": int(time.time())
            })))

    kt.on_ticks = on_ticks
    kt.connect(threaded=True)
    async for msg in ws:
        data = json.loads(msg)
        if "subscribe" in data:
            kt.subscribe(data["subscribe"])

start_server = websockets.serve(handler, "0.0.0.0", 8081)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
"""
