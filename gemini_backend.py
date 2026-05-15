#!/usr/bin/env python3
"""
GEMINI Pattern Scanner - Complete Backend
30 Pattern-based scanners (A: Volume, B: Price, C: Indicator)
Uses yfinance for NSE/BSE data + pandas for analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

# ── PATTERN DATA (from uploaded HTML) ───────────────────────────
PATTERNS = {
    'A': [  # VOLUME
        {"name": "Richard Wyckoff", "pattern": "Wyckoff VSA", "desc": "Volume confirms price। Accumulation / Distribution zones।"},
        {"name": "Mark Minervini", "pattern": "SEPA", "desc": "Volume surge on momentum breakout। US Champion strategy।"},
        {"name": "William O'Neil", "pattern": "CAN SLIM", "desc": "Volume 50% above avg on up-days।"},
        {"name": "Richard Arms", "pattern": "TRIN / Arms Index", "desc": "Market breadth + volume breadth।"},
        {"name": "Joe Granville", "pattern": "OBV", "desc": "On-Balance Volume। Volume precedes price।"},
        {"name": "David Weis", "pattern": "Weis Wave", "desc": "Cumulative volume per price wave।"},
        {"name": "Tom Williams", "pattern": "VSA", "desc": "Volume Spread Analysis। Smart Money tracking।"},
        {"name": "Buff Dormeier", "pattern": "VWRS", "desc": "Volume-Weighted Relative Strength।"},
        {"name": "Don Worden", "pattern": "OBV-2", "desc": "Threshold-filtered On-Balance Volume।"},
        {"name": "Gavin Holmes", "pattern": "Modern VSA", "desc": "No Supply / No Demand detection।"},
    ],
    'B': [  # PRICE
        {"name": "Jesse Livermore", "pattern": "Pivot Points", "desc": "Pivotal price levels। Trend following।"},
        {"name": "Charles Dow", "pattern": "Dow Theory", "desc": "Higher Highs/Lows = Uptrend।"},
        {"name": "Ralph Elliott", "pattern": "Elliott Wave", "desc": "5-wave impulse + 3-wave correction।"},
        {"name": "W.D. Gann", "pattern": "Gann Levels", "desc": "25%, 38.2%, 50%, 61.8%, 75% retracements।"},
        {"name": "John Bollinger", "pattern": "Bollinger Bands", "desc": "2σ bands around 20-day MA।"},
        {"name": "J. Welles Wilder", "pattern": "RSI-14", "desc": "Relative Strength Index। Overbought/Oversold।"},
        {"name": "George Lane", "pattern": "Stochastic", "desc": "%K %D। Momentum oscillator।"},
        {"name": "Gerald Appel", "pattern": "MACD", "desc": "12/26/9 crossover। Trend + momentum।"},
        {"name": "Stan Weinstein", "pattern": "Stage Analysis", "desc": "4 stages of price cycle।"},
        {"name": "Charles Le Beau", "pattern": "ATR Stop", "desc": "3×ATR trailing stop loss।"},
    ],
    'C': [  # INDICATOR
        {"name": "PCR", "pattern": "Put-Call Ratio", "desc": "Options market sentiment। >1 Bullish।"},
        {"name": "Momentum", "pattern": "Rate of Change (ROC)", "desc": "10-day + 20-day momentum।"},
        {"name": "News Flow", "pattern": "Price-implied news sentiment", "desc": "5-day change proxy।"},
        {"name": "OI Analysis", "pattern": "Open Interest proxy", "desc": "Volume trend vs 20-day avg।"},
        {"name": "FII / DII", "pattern": "Gap analysis", "desc": "Institutional buying/selling proxy।"},
        {"name": "Order Book", "pattern": "Bid-Ask spread ratio", "desc": "Liquidity detection।"},
        {"name": "India VIX", "pattern": "Fear Index", "desc": "<15 Calm, >20 Panic।"},
        {"name": "Market Breadth", "pattern": "Advance-Decline ratio", "desc": "Up-days vs Down-days।"},
        {"name": "Gamma Flip", "pattern": "ATR-based gamma zone", "desc": "Options dealer hedge point।"},
        {"name": "Sector Rotation", "pattern": "5d vs 20d return", "desc": "Risk-on / Risk-off signal।"},
    ]
}

# ── DATA FETCH ────────────────────────────────────────────────────
def get_data(symbol, period="60d", interval="1d"):
    """Fetch NSE/BSE data via yfinance. Auto-adds .NS suffix."""
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol + '.NS'
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# ── A GROUP: VOLUME SCANNERS ─────────────────────────────────────
def scan_wyckoff_vsa(df):
    """Richard Wyckoff - Volume confirms price"""
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    vol_now = df['Volume'].iloc[-1]
    price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]

    if vol_now > vol_avg * 1.5 and price_change > 0:
        return {"signal": "BULL - Accumulation", "volume_ratio": round(vol_now/vol_avg, 2), "price_change": round(price_change, 2)}
    elif vol_now > vol_avg * 1.5 and price_change < 0:
        return {"signal": "BEAR - Distribution", "volume_ratio": round(vol_now/vol_avg, 2), "price_change": round(price_change, 2)}
    return {"signal": "NEUTRAL", "volume_ratio": round(vol_now/vol_avg, 2)}

def scan_sepa(df):
    """Mark Minervini - Volume surge on momentum breakout"""
    vol_avg = df['Volume'].rolling(50).mean().iloc[-1]
    vol_now = df['Volume'].iloc[-1]
    high_20 = df['High'].rolling(20).max().iloc[-1]
    close = df['Close'].iloc[-1]

    breakout = close > high_20 * 0.98
    vol_surge = vol_now > vol_avg * 1.5

    if breakout and vol_surge:
        return {"signal": "BULL - SEPA Breakout", "vol_surge": round(vol_now/vol_avg, 2), "near_20d_high": round(close/high_20, 3)}
    return {"signal": "NEUTRAL", "vol_surge": round(vol_now/vol_avg, 2)}

def scan_can_slim(df):
    """William O'Neil - Volume 50% above avg on up-days"""
    vol_avg = df['Volume'].rolling(50).mean().iloc[-1]
    vol_now = df['Volume'].iloc[-1]
    price_up = df['Close'].iloc[-1] > df['Close'].iloc[-2]

    if price_up and vol_now > vol_avg * 1.5:
        return {"signal": "BULL - CAN SLIM Volume", "vol_vs_avg": round(vol_now/vol_avg, 2)}
    return {"signal": "NEUTRAL", "vol_vs_avg": round(vol_now/vol_avg, 2)}

def scan_arms_index(df):
    """Richard Arms - TRIN / Market breadth"""
    # Simulated breadth using price advances/declines proxy
    returns = df['Close'].pct_change().dropna()
    up_days = (returns > 0).sum()
    down_days = (returns < 0).sum()
    vol_up = df[returns > 0]['Volume'].sum() if up_days > 0 else 1
    vol_down = df[returns < 0]['Volume'].sum() if down_days > 0 else 1

    trin = (down_days / up_days) / (vol_down / vol_up) if up_days > 0 and vol_down > 0 else 1

    if trin < 0.8:
        return {"signal": "BULL - Strong Breadth", "trin": round(trin, 2)}
    elif trin > 1.2:
        return {"signal": "BEAR - Weak Breadth", "trin": round(trin, 2)}
    return {"signal": "NEUTRAL", "trin": round(trin, 2)}

def scan_obv(df):
    """Joe Granville - On-Balance Volume"""
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])

    obv_series = pd.Series(obv, index=df.index)
    obv_sma = obv_series.rolling(20).mean().iloc[-1]
    obv_now = obv_series.iloc[-1]

    if obv_now > obv_sma * 1.05:
        return {"signal": "BULL - OBV Rising", "obv": int(obv_now), "obv_sma20": int(obv_sma)}
    elif obv_now < obv_sma * 0.95:
        return {"signal": "BEAR - OBV Falling", "obv": int(obv_now), "obv_sma20": int(obv_sma)}
    return {"signal": "NEUTRAL", "obv": int(obv_now)}

def scan_weis_wave(df):
    """David Weis - Cumulative volume per price wave"""
    # Simplified: detect waves by pivot points
    highs = df['High'].rolling(5).max()
    lows = df['Low'].rolling(5).min()

    if highs.iloc[-1] == df['High'].iloc[-1]:
        wave_vol = df['Volume'].iloc[-5:].sum()
        return {"signal": "WAVE PEAK - Volume", "wave_volume": int(wave_vol), "direction": "UP"}
    elif lows.iloc[-1] == df['Low'].iloc[-1]:
        wave_vol = df['Volume'].iloc[-5:].sum()
        return {"signal": "WAVE TROUGH - Volume", "wave_volume": int(wave_vol), "direction": "DOWN"}
    return {"signal": "NEUTRAL", "wave_volume": int(df['Volume'].iloc[-5:].sum())}

def scan_vsa(df):
    """Tom Williams - Volume Spread Analysis"""
    spread = df['High'].iloc[-1] - df['Low'].iloc[-1]
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    vol_now = df['Volume'].iloc[-1]
    close_loc = (df['Close'].iloc[-1] - df['Low'].iloc[-1]) / spread if spread > 0 else 0.5

    if vol_now < vol_avg * 0.7 and close_loc > 0.6:
        return {"signal": "BULL - No Supply", "spread_pct": round(close_loc*100, 1), "vol_ratio": round(vol_now/vol_avg, 2)}
    elif vol_now < vol_avg * 0.7 and close_loc < 0.4:
        return {"signal": "BEAR - No Demand", "spread_pct": round(close_loc*100, 1), "vol_ratio": round(vol_now/vol_avg, 2)}
    return {"signal": "NEUTRAL", "vol_ratio": round(vol_now/vol_avg, 2)}

def scan_vwrs(df):
    """Buff Dormeier - Volume-Weighted Relative Strength"""
    vw_price = (df['Close'] * df['Volume']).rolling(14).sum() / df['Volume'].rolling(14).sum()
    vw_price_prev = vw_price.iloc[-2]
    vw_price_now = vw_price.iloc[-1]

    if vw_price_now > vw_price_prev * 1.02:
        return {"signal": "BULL - VWRS Strong", "vw_price": round(vw_price_now, 2)}
    elif vw_price_now < vw_price_prev * 0.98:
        return {"signal": "BEAR - VWRS Weak", "vw_price": round(vw_price_now, 2)}
    return {"signal": "NEUTRAL", "vw_price": round(vw_price_now, 2)}

def scan_obv2(df):
    """Don Worden - Threshold-filtered OBV"""
    obv = [0]
    threshold = df['Volume'].rolling(20).mean().iloc[-1] * 0.5
    for i in range(1, len(df)):
        if df['Volume'].iloc[i] > threshold:
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            else:
                obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])

    obv_now = obv[-1]
    obv_trend = "UP" if obv[-1] > obv[-5] else "DOWN"
    return {"signal": f"{'BULL' if obv_trend=='UP' else 'BEAR'} - OBV2", "obv": int(obv_now), "trend": obv_trend}

def scan_modern_vsa(df):
    """Gavin Holmes - Modern VSA"""
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    vol_now = df['Volume'].iloc[-1]
    body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
    range_ = df['High'].iloc[-1] - df['Low'].iloc[-1]

    if vol_now > vol_avg * 2 and body > range_ * 0.6:
        return {"signal": "BULL - High Volume Wide Spread", "vol_ratio": round(vol_now/vol_avg, 2)}
    elif vol_now < vol_avg * 0.5 and body < range_ * 0.3:
        return {"signal": "BEAR - Low Volume Narrow Spread", "vol_ratio": round(vol_now/vol_avg, 2)}
    return {"signal": "NEUTRAL", "vol_ratio": round(vol_now/vol_avg, 2)}

# ── B GROUP: PRICE SCANNERS ──────────────────────────────────────
def scan_pivot_points(df):
    """Jesse Livermore - Pivot Points"""
    high = df['High'].iloc[-2]
    low = df['Low'].iloc[-2]
    close = df['Close'].iloc[-2]
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high

    curr = df['Close'].iloc[-1]
    if curr > r1:
        return {"signal": "BULL - Above R1", "pivot": round(pivot, 2), "r1": round(r1, 2), "s1": round(s1, 2)}
    elif curr < s1:
        return {"signal": "BEAR - Below S1", "pivot": round(pivot, 2), "r1": round(r1, 2), "s1": round(s1, 2)}
    return {"signal": "NEUTRAL", "pivot": round(pivot, 2)}

def scan_dow_theory(df):
    """Charles Dow - Higher Highs/Lows"""
    highs = df['High'].rolling(20).max()
    lows = df['Low'].rolling(20).min()

    hh = df['High'].iloc[-1] >= highs.iloc[-2] * 0.99
    hl = df['Low'].iloc[-1] >= lows.iloc[-2] * 0.99

    if hh and hl:
        return {"signal": "BULL - Higher Highs & Lows", "trend": "UPTREND"}
    elif not hh and not hl:
        return {"signal": "BEAR - Lower Highs & Lows", "trend": "DOWNTREND"}
    return {"signal": "NEUTRAL", "trend": "SIDEWAYS"}

def scan_elliott_wave(df):
    """Ralph Elliott - Elliott Wave"""
    # Simplified: detect 5-wave pattern using RSI divergence
    rsi = compute_rsi(df['Close'], 14)
    price_high = df['High'].rolling(20).max().iloc[-1] == df['High'].iloc[-1]
    rsi_high = rsi.rolling(20).max().iloc[-1]

    if price_high and rsi.iloc[-1] < rsi_high * 0.95:
        return {"signal": "BEAR - Wave 5 Divergence", "rsi": round(rsi.iloc[-1], 1)}
    elif df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1] * 1.05:
        return {"signal": "BULL - Wave 3 Impulse", "rsi": round(rsi.iloc[-1], 1)}
    return {"signal": "NEUTRAL", "rsi": round(rsi.iloc[-1], 1)}

def scan_gann_levels(df):
    """W.D. Gann - Retracement Levels"""
    high = df['High'].rolling(60).max().iloc[-1]
    low = df['Low'].rolling(60).min().iloc[-1]
    range_ = high - low
    curr = df['Close'].iloc[-1]

    levels = {
        '25%': low + range_ * 0.25,
        '38.2%': low + range_ * 0.382,
        '50%': low + range_ * 0.5,
        '61.8%': low + range_ * 0.618,
        '75%': low + range_ * 0.75
    }

    nearest = min(levels.items(), key=lambda x: abs(x[1] - curr))
    if curr > levels['61.8%']:
        return {"signal": "BULL - Above 61.8%", "nearest_level": nearest[0], "distance": round(abs(nearest[1]-curr), 2)}
    elif curr < levels['38.2%']:
        return {"signal": "BEAR - Below 38.2%", "nearest_level": nearest[0], "distance": round(abs(nearest[1]-curr), 2)}
    return {"signal": "NEUTRAL", "nearest_level": nearest[0]}

def scan_bollinger(df):
    """John Bollinger - Bollinger Bands"""
    sma = df['Close'].rolling(20).mean().iloc[-1]
    std = df['Close'].rolling(20).std().iloc[-1]
    upper = sma + 2 * std
    lower = sma - 2 * std
    curr = df['Close'].iloc[-1]

    if curr > upper:
        return {"signal": "BEAR - Above Upper Band", "bb_upper": round(upper, 2), "bb_lower": round(lower, 2), "sma20": round(sma, 2)}
    elif curr < lower:
        return {"signal": "BULL - Below Lower Band", "bb_upper": round(upper, 2), "bb_lower": round(lower, 2), "sma20": round(sma, 2)}
    return {"signal": "NEUTRAL", "bb_position": round((curr-lower)/(upper-lower)*100, 1)}

def scan_rsi(df):
    """J. Welles Wilder - RSI-14"""
    rsi = compute_rsi(df['Close'], 14).iloc[-1]
    if rsi > 70:
        return {"signal": "BEAR - Overbought", "rsi": round(rsi, 1)}
    elif rsi < 30:
        return {"signal": "BULL - Oversold", "rsi": round(rsi, 1)}
    return {"signal": "NEUTRAL", "rsi": round(rsi, 1)}

def scan_stochastic(df):
    """George Lane - Stochastic"""
    low14 = df['Low'].rolling(14).min().iloc[-1]
    high14 = df['High'].rolling(14).max().iloc[-1]
    k = 100 * (df['Close'].iloc[-1] - low14) / (high14 - low14) if high14 != low14 else 50

    if k > 80:
        return {"signal": "BEAR - Overbought", "%K": round(k, 1)}
    elif k < 20:
        return {"signal": "BULL - Oversold", "%K": round(k, 1)}
    return {"signal": "NEUTRAL", "%K": round(k, 1)}

def scan_macd(df):
    """Gerald Appel - MACD"""
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()

    if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
        return {"signal": "BULL - MACD Crossover", "macd": round(macd.iloc[-1], 3), "signal": round(signal.iloc[-1], 3)}
    elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
        return {"signal": "BEAR - MACD Crossunder", "macd": round(macd.iloc[-1], 3), "signal": round(signal.iloc[-1], 3)}
    return {"signal": "NEUTRAL", "macd": round(macd.iloc[-1], 3)}

def scan_stage_analysis(df):
    """Stan Weinstein - Stage Analysis"""
    sma30 = df['Close'].rolling(30).mean().iloc[-1]
    sma50 = df['Close'].rolling(50).mean().iloc[-1]
    curr = df['Close'].iloc[-1]

    if curr > sma30 > sma50 and df['Close'].iloc[-5] < df['Close'].iloc[-1]:
        return {"signal": "BULL - Stage 2 Advancing", "sma30": round(sma30, 2), "sma50": round(sma50, 2)}
    elif curr < sma30 < sma50 and df['Close'].iloc[-5] > df['Close'].iloc[-1]:
        return {"signal": "BEAR - Stage 4 Declining", "sma30": round(sma30, 2), "sma50": round(sma50, 2)}
    elif curr > sma50 and curr < sma30:
        return {"signal": "NEUTRAL - Stage 3 Topping", "sma30": round(sma30, 2)}
    return {"signal": "NEUTRAL - Stage 1 Basing", "sma50": round(sma50, 2)}

def scan_atr_stop(df):
    """Charles Le Beau - ATR Trailing Stop"""
    tr1 = df['High'].iloc[-1] - df['Low'].iloc[-1]
    tr2 = abs(df['High'].iloc[-1] - df['Close'].iloc[-2])
    tr3 = abs(df['Low'].iloc[-1] - df['Close'].iloc[-2])
    tr = max(tr1, tr2, tr3)
    atr = df['TR'].rolling(14).mean().iloc[-1] if 'TR' in df.columns else tr

    stop_long = df['Close'].iloc[-1] - 3 * atr
    stop_short = df['Close'].iloc[-1] + 3 * atr

    return {"signal": "INFO", "atr_stop_long": round(stop_long, 2), "atr_stop_short": round(stop_short, 2), "atr": round(atr, 2)}

# ── C GROUP: INDICATOR SCANNERS ──────────────────────────────────
def scan_pcr(df):
    """PCR - Put-Call Ratio (simulated via price action)"""
    returns = df['Close'].pct_change().dropna()
    volatility = returns.rolling(20).std().iloc[-1]

    if volatility > returns.rolling(60).std().iloc[-1] * 1.5:
        return {"signal": "BULL - High Fear (>1 PCR proxy)", "volatility": round(volatility*100, 2)}
    elif volatility < returns.rolling(60).std().iloc[-1] * 0.5:
        return {"signal": "BEAR - Low Fear (<1 PCR proxy)", "volatility": round(volatility*100, 2)}
    return {"signal": "NEUTRAL", "volatility": round(volatility*100, 2)}

def scan_momentum(df):
    """Momentum - Rate of Change"""
    roc10 = (df['Close'].iloc[-1] - df['Close'].iloc[-11]) / df['Close'].iloc[-11] * 100
    roc20 = (df['Close'].iloc[-1] - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100

    if roc10 > 5 and roc20 > 10:
        return {"signal": "BULL - Strong Momentum", "roc10": round(roc10, 2), "roc20": round(roc20, 2)}
    elif roc10 < -5 and roc20 < -10:
        return {"signal": "BEAR - Weak Momentum", "roc10": round(roc10, 2), "roc20": round(roc20, 2)}
    return {"signal": "NEUTRAL", "roc10": round(roc10, 2)}

def scan_news_flow(df):
    """News Flow - Price-implied sentiment"""
    change_5d = (df['Close'].iloc[-1] - df['Close'].iloc[-6]) / df['Close'].iloc[-6] * 100
    vol_spike = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 2

    if change_5d > 5 and vol_spike:
        return {"signal": "BULL - Positive News Flow", "5d_change": round(change_5d, 2)}
    elif change_5d < -5 and vol_spike:
        return {"signal": "BEAR - Negative News Flow", "5d_change": round(change_5d, 2)}
    return {"signal": "NEUTRAL", "5d_change": round(change_5d, 2)}

def scan_oi_analysis(df):
    """OI Analysis - Open Interest proxy"""
    vol_trend = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]
    price_trend = df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1]

    if vol_trend and price_trend:
        return {"signal": "BULL - OI Building (Long)", "vol_vs_20d": round(df['Volume'].iloc[-1]/df['Volume'].rolling(20).mean().iloc[-1], 2)}
    elif vol_trend and not price_trend:
        return {"signal": "BEAR - OI Building (Short)", "vol_vs_20d": round(df['Volume'].iloc[-1]/df['Volume'].rolling(20).mean().iloc[-1], 2)}
    return {"signal": "NEUTRAL", "vol_vs_20d": round(df['Volume'].iloc[-1]/df['Volume'].rolling(20).mean().iloc[-1], 2)}

def scan_fii_dii(df):
    """FII/DII - Gap analysis"""
    gap = df['Open'].iloc[-1] - df['Close'].iloc[-2]
    gap_pct = gap / df['Close'].iloc[-2] * 100

    if gap_pct > 1:
        return {"signal": "BULL - Gap Up (Institutional Buy)", "gap_pct": round(gap_pct, 2)}
    elif gap_pct < -1:
        return {"signal": "BEAR - Gap Down (Institutional Sell)", "gap_pct": round(gap_pct, 2)}
    return {"signal": "NEUTRAL", "gap_pct": round(gap_pct, 2)}

def scan_order_book(df):
    """Order Book - Bid-Ask spread proxy"""
    spread = (df['High'].iloc[-1] - df['Low'].iloc[-1]) / df['Close'].iloc[-1] * 100

    if spread < 0.5:
        return {"signal": "BULL - Tight Spread (High Liquidity)", "spread_pct": round(spread, 2)}
    elif spread > 2:
        return {"signal": "BEAR - Wide Spread (Low Liquidity)", "spread_pct": round(spread, 2)}
    return {"signal": "NEUTRAL", "spread_pct": round(spread, 2)}

def scan_india_vix(df):
    """India VIX - Fear Index proxy via volatility"""
    returns = df['Close'].pct_change().dropna()
    vix_proxy = returns.rolling(20).std().iloc[-1] * np.sqrt(252) * 100

    if vix_proxy < 15:
        return {"signal": "BULL - Low Fear (<15)", "vix_proxy": round(vix_proxy, 1)}
    elif vix_proxy > 20:
        return {"signal": "BEAR - High Fear (>20)", "vix_proxy": round(vix_proxy, 1)}
    return {"signal": "NEUTRAL", "vix_proxy": round(vix_proxy, 1)}

def scan_market_breadth(df):
    """Market Breadth - Advance-Decline proxy"""
    up_days = (df['Close'].pct_change() > 0).rolling(20).sum().iloc[-1]
    down_days = (df['Close'].pct_change() < 0).rolling(20).sum().iloc[-1]

    if up_days > down_days * 1.5:
        return {"signal": "BULL - Broad Rally", "up_days": int(up_days), "down_days": int(down_days)}
    elif down_days > up_days * 1.5:
        return {"signal": "BEAR - Broad Decline", "up_days": int(up_days), "down_days": int(down_days)}
    return {"signal": "NEUTRAL", "up_days": int(up_days), "down_days": int(down_days)}

def scan_gamma_flip(df):
    """Gamma Flip - ATR-based gamma zone"""
    atr = compute_atr(df, 14).iloc[-1]
    curr = df['Close'].iloc[-1]
    gamma_zone = df['Close'].rolling(20).mean().iloc[-1]

    if curr > gamma_zone + atr:
        return {"signal": "BULL - Above Gamma Flip", "gamma_zone": round(gamma_zone, 2), "atr": round(atr, 2)}
    elif curr < gamma_zone - atr:
        return {"signal": "BEAR - Below Gamma Flip", "gamma_zone": round(gamma_zone, 2), "atr": round(atr, 2)}
    return {"signal": "NEUTRAL", "gamma_zone": round(gamma_zone, 2)}

def scan_sector_rotation(df):
    """Sector Rotation - 5d vs 20d return"""
    ret5 = (df['Close'].iloc[-1] - df['Close'].iloc[-6]) / df['Close'].iloc[-6] * 100
    ret20 = (df['Close'].iloc[-1] - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100

    if ret5 > ret20 and ret5 > 0:
        return {"signal": "BULL - Risk-On (Momentum)", "5d_ret": round(ret5, 2), "20d_ret": round(ret20, 2)}
    elif ret5 < ret20 and ret5 < 0:
        return {"signal": "BEAR - Risk-Off (Defensive)", "5d_ret": round(ret5, 2), "20d_ret": round(ret20, 2)}
    return {"signal": "NEUTRAL", "5d_ret": round(ret5, 2)}

# ── HELPERS ──────────────────────────────────────────────────────
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_atr(df, period=14):
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift())
    tr3 = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ── SCANNER MAP ──────────────────────────────────────────────────
SCANNERS = {
    'A': [scan_wyckoff_vsa, scan_sepa, scan_can_slim, scan_arms_index, scan_obv,
          scan_weis_wave, scan_vsa, scan_vwrs, scan_obv2, scan_modern_vsa],
    'B': [scan_pivot_points, scan_dow_theory, scan_elliott_wave, scan_gann_levels,
          scan_bollinger, scan_rsi, scan_stochastic, scan_macd, scan_stage_analysis, scan_atr_stop],
    'C': [scan_pcr, scan_momentum, scan_news_flow, scan_oi_analysis, scan_fii_dii,
          scan_order_book, scan_india_vix, scan_market_breadth, scan_gamma_flip, scan_sector_rotation]
}

# ── MAIN API ─────────────────────────────────────────────────────
@app.route('/analyze')
def analyze():
    symbol = request.args.get('symbol', '').upper()
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    df = get_data(symbol)
    if df is None or len(df) < 30:
        return jsonify({"error": f"Insufficient data for {symbol}"}), 404

    results = {"symbol": symbol, "last_price": round(df['Close'].iloc[-1], 2)}

    for group in ['A', 'B', 'C']:
        results[group] = []
        for i, scanner in enumerate(SCANNERS[group]):
            try:
                res = scanner(df)
                res['legend'] = PATTERNS[group][i]['name']
                res['pattern'] = PATTERNS[group][i]['pattern']
                results[group].append(res)
            except Exception as e:
                results[group].append({"signal": "ERROR", "error": str(e), 
                                       "legend": PATTERNS[group][i]['name'],
                                       "pattern": PATTERNS[group][i]['pattern']})

    return jsonify(results)

@app.route('/patterns')
def get_patterns():
    """Return all 30 patterns as pandas-ready JSON"""
    df = pd.DataFrame([
        {"Rank": i+1, "Group": f"{g}·{'VOLUME' if g=='A' else 'PRICE' if g=='B' else 'INDICATOR'}", 
         "Name": p['name'], "Pattern": p['pattern'], "Description": p['desc']}
        for g in ['A', 'B', 'C'] for i, p in enumerate(PATTERNS[g])
    ])
    return jsonify(df.to_dict('records'))

@app.route('/')
def health():
    return jsonify({"status": "GEMINI Pattern Scanner Active", "patterns": 30, "version": "1.0"})

if __name__ == '__main__':
    print("=" * 50)
    print("GEMINI Pattern Scanner")
    print("30 Pattern-based scanners | Flask API")
    print("Run: python gemini_backend.py")
    print("Test: http://localhost:5000/analyze?symbol=RELIANCE")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
