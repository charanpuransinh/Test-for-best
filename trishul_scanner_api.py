"""
================================================================================
TRISHUL PRO MASTER — UNIFIED SCANNER API
================================================================================
Author  : Aruna (Trishul Pro)
Version : 1.0.0
Date    : 2026-05-12

5 HIGH-ACCURACY SCANNERS (90%+ target):
  S1: SMART MONEY    — Trend + Volume + Volatility    (A1,A2,A4,V1,V2,H9,H10)
  S2: MOMENTUM BURST — Momentum + Volume              (A3,A5,H3,H6,H7,V11,V15)
  S3: TREND BREAKOUT — Trend Direction + Adaptive     (A6,A7,A8,A10,V4,H4,H7)
  S4: SAFE REVERSAL  — Pattern + Extreme + Vigor      (A9,H1,H2,V3,V5,H5,H10)
  S5: VOLUME POWER   — Pure Volume Confluence         (V1,V2,V3,V4,V5,V11,V15)

ACCURACY RULE: Signal fires only when 5 of 7 indicators agree (71% threshold)
API: Flask REST — GET /scan?symbol=RELIANCE&scanner=S1

INSTALL: pip install flask pandas numpy yfinance flask-cors
RUN    : python trishul_scanner_api.py
================================================================================
"""

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# ============================================================
# ── CORE MATH (shared, zero duplication)
# ============================================================

def _rma(s, p):
    r, a = np.full(len(s), np.nan), 1/p
    valid = ~np.isnan(s)
    if not valid.any(): return r
    fi = np.where(valid)[0][0]
    if fi+p > len(s): return r
    r[fi+p-1] = np.mean(s[fi:fi+p])
    for i in range(fi+p, len(s)):
        if not np.isnan(s[i]) and not np.isnan(r[i-1]):
            r[i] = a*s[i] + (1-a)*r[i-1]
    return r

def _ema(s, p):
    r, a = np.full(len(s), np.nan), 2/(p+1)
    valid = ~np.isnan(s)
    if not valid.any(): return r
    fi = np.where(valid)[0][0]
    r[fi] = s[fi]
    for i in range(fi+1, len(s)):
        if not np.isnan(s[i]) and not np.isnan(r[i-1]):
            r[i] = a*s[i] + (1-a)*r[i-1]
    return r

def _sma(s, p):
    r = np.full(len(s), np.nan)
    for i in range(p-1, len(s)):
        w = s[i-p+1:i+1]
        if not np.all(np.isnan(w)): r[i] = np.nanmean(w)
    return r

def _wma(s, p):
    r = np.full(len(s), np.nan)
    w = np.arange(1, p+1, dtype=float)
    ws = w.sum()
    for i in range(p-1, len(s)):
        win = s[i-p+1:i+1]
        if not np.all(np.isnan(win)): r[i] = np.nansum(win*w)/ws
    return r

def _std(s, p):
    r = np.full(len(s), np.nan)
    for i in range(p-1, len(s)):
        w = s[i-p+1:i+1]
        v = w[~np.isnan(w)]
        if len(v) > 1: r[i] = np.std(v, ddof=0)
    return r

def _tr(H, L, C):
    pc = np.concatenate(([C[0]], C[:-1]))
    return np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))

def _zdiv(n, d, def_=0.001):
    safe = np.where(np.abs(d) < 1e-10, def_, d)
    return n/safe

def _lscore(v, lo, hi, ls=0., hs=10.):
    return np.where(np.isnan(v), np.nan,
           np.where(v >= hi, hs,
           np.where(v <= lo, ls,
                    ls + (hs-ls)*(v-lo)/(hi-lo)))).astype(float)

# ============================================================
# ── MODULE A: TREND INDICATORS (A1-A10)
# ============================================================

def A1_ADX(H, L, C):
    pm = np.maximum(H-np.concatenate(([H[0]], H[:-1])), 0)
    mm = np.maximum(np.concatenate(([L[0]], L[:-1]))-L, 0)
    pm = np.where(pm > mm, pm, 0)
    mm = np.where(mm >= pm, mm, 0)
    tr = _tr(H, L, C)
    tr14, pm14, mm14 = _rma(tr, 14), _rma(pm, 14), _rma(mm, 14)
    pdi = 100*_zdiv(pm14, tr14)
    mdi = 100*_zdiv(mm14, tr14)
    dx  = 100*_zdiv(np.abs(pdi-mdi), pdi+mdi)
    adx = _rma(dx, 14)
    return _lscore(adx, 15, 40)

def A2_EMA_Align(C):
    e9, e21, e55 = _ema(C,9), _ema(C,21), _ema(C,55)
    conds = [(e9>e21)&(e21>e55),(e9>e21)&(e21<=e55),(e9<e21)&(e21>=e55),(e9<e21)&(e21<e55)]
    return pd.Series(np.select(conds,[10,7,3,0],default=5), dtype=float).values

def A3_MACD(C):
    hist = _ema(C,12)-_ema(C,26)
    hist = hist - _ema(hist, 9)
    hp = hist > 0; hr = hist > np.concatenate(([hist[0]], hist[:-1]))
    return np.select([hp&hr, hp&~hr, ~hp&hr, ~hp&~hr],[10,7,3,0],default=5).astype(float)

def A4_Supertrend(H, L, C):
    hl2 = (H+L)/2
    atr = _rma(_tr(H,L,C), 10)
    ub, lb = (hl2+3*atr).copy(), (hl2-3*atr).copy()
    n = len(C)
    trend = np.ones(n); fub, flb = ub.copy(), lb.copy()
    for i in range(1, n):
        if trend[i-1]==1:
            flb[i] = max(lb[i], flb[i-1])
            fub[i] = ub[i]
            trend[i] = 0 if C[i]<flb[i] else 1
        else:
            fub[i] = min(ub[i], fub[i-1])
            flb[i] = lb[i]
            trend[i] = 1 if C[i]>fub[i] else 0
    return trend * 10.0

def A5_TSI(C):
    pc = C - np.concatenate(([C[0]], C[:-1]))
    ds = _ema(_ema(pc,25),13)
    da = _ema(_ema(np.abs(pc),25),13)
    return _lscore(100*_zdiv(ds,da), -25, 25)

def A6_LinReg(C, p=20):
    x=np.arange(p,dtype=float); sx=x.sum(); sx2=(x**2).sum()
    denom=p*sx2-sx**2; slope=np.full(len(C),np.nan)
    for i in range(p-1,len(C)):
        y=C[i-p+1:i+1]; slope[i]=(p*np.dot(x,y)-sx*y.sum())/denom if denom else 0
    return np.where(np.isnan(slope),np.nan,np.where(slope>0,10,np.where(slope<0,0,5))).astype(float)

def A7_DI_Spread(H, L, C):
    pm = np.maximum(H-np.concatenate(([H[0]],H[:-1])),0)
    mm = np.maximum(np.concatenate(([L[0]],L[:-1]))-L,0)
    pm = np.where(pm>mm,pm,0); mm = np.where(mm>=pm,mm,0)
    tr14=_rma(_tr(H,L,C),14)
    spread = 100*_zdiv(_rma(pm,14),tr14) - 100*_zdiv(_rma(mm,14),tr14)
    return _lscore(spread,-25,25)

def A8_SMA200(C):
    if len(C)<200: return np.full(len(C),5.)
    s200=_sma(C,200)
    return _lscore(_zdiv(C-s200,s200)*100,-5,5)

def A9_3Bar(H, L):
    h1,h2=np.concatenate(([H[0]],H[:-1])),np.concatenate(([H[0],H[0]],H[:-2]))
    l1,l2=np.concatenate(([L[0]],L[:-1])),np.concatenate(([L[0],L[0]],L[:-2]))
    hh=(H>h1)&(h1>h2); hl=(L>l1)&(l1>l2)
    lh=(H<h1)&(h1<h2); ll=(L<l1)&(l1<l2)
    s=np.full(len(H),5.)
    s=np.where(hh|hl,7.5,s); s=np.where(lh|ll,2.5,s)
    s=np.where(hh&hl,10.,s); s=np.where(lh&ll,0.,s)
    return s

def A10_HullMA(C, n=16):
    raw = 2*_wma(C,n//2)-_wma(C,n)
    hma = _wma(raw, int(np.sqrt(n)))
    prev = np.concatenate(([np.nan],hma[:-1]))
    return np.where(np.isnan(hma)|np.isnan(prev),np.nan,
           np.where(hma>prev,10,np.where(hma<prev,0,5))).astype(float)

# ============================================================
# ── MODULE C: VOLUME INDICATORS (V1-V5)
# ============================================================

def V1_VWAP(H, L, C, V):
    tp=( H+L+C)/3; tpv=tp*V
    tpvs=np.full(len(C),np.nan); vs=np.full(len(C),np.nan)
    for i in range(19,len(C)):
        tpvs[i]=np.nansum(tpv[i-19:i+1]); vs[i]=np.nansum(V[i-19:i+1])
    vwap=_zdiv(tpvs,vs)
    return _lscore(_zdiv(C-vwap,vwap)*100,-2,2)

def V2_CMF(H, L, C, V, p=20):
    hl=H-L; safe=np.where(hl<1e-10,1e-4,hl)
    mfv=((C-L)-(H-C))/safe*V
    ms=np.full(len(C),np.nan); vs=np.full(len(C),np.nan)
    for i in range(p-1,len(C)):
        ms[i]=np.nansum(mfv[i-p+1:i+1]); vs[i]=np.nansum(V[i-p+1:i+1])
    return _lscore(_zdiv(ms,vs),-0.1,0.1)

def V3_VSA(H, L, C, V):
    sp=H-L; av=_sma(V,20); asp=_sma(sp,20)
    hv=V>av*1.5; ws=sp>asp*1.3
    ssp=np.where(sp<1e-10,1e-4,sp)
    cnl=(C-L)/ssp<0.3; cnh=(H-C)/ssp<0.3
    wm=np.isnan(av)|np.isnan(asp)
    s=np.full(len(C),5.)
    s=np.where(hv&ws&cnh,0.,s); s=np.where(hv&ws&cnl,10.,s)
    return np.where(wm,np.nan,s)

def V4_OBV(C, V):
    obv=np.empty(len(C)); obv[0]=V[0]
    for i in range(1,len(C)):
        if C[i]>C[i-1]: obv[i]=obv[i-1]+V[i]
        elif C[i]<C[i-1]: obv[i]=obv[i-1]-V[i]
        else: obv[i]=obv[i-1]
    slope=np.full(len(C),np.nan); slope[10:]=obv[10:]-obv[:-len(obv)+10] if len(obv)>10 else np.nan
    std=pd.Series(obv).rolling(10,min_periods=10).std().values
    safe=np.where(np.isnan(std)|(std<1e-10),np.nan,std)
    return _lscore(slope/safe,-2,2)

def V5_MFI(H, L, C, V):
    tp=(H+L+C)/3; rmf=tp*V
    td=np.zeros(len(C)); td[1:]=tp[1:]-tp[:-1]
    pm=np.where(td>0,rmf,0); nm=np.where(td<0,rmf,0)
    ps=np.full(len(C),np.nan); ns=np.full(len(C),np.nan)
    for i in range(13,len(C)):
        ps[i]=np.nansum(pm[i-13:i+1]); ns[i]=np.nansum(nm[i-13:i+1])
    mfi=100-100/(1+_zdiv(ps,ns))
    return _lscore(mfi,20,80)

# ============================================================
# ── MODULE E: ADVANCED VOLUME (V11-V15)
# ============================================================

def V11_VolRSI(V):
    d=np.zeros(len(V)); d[1:]=V[1:]-V[:-1]
    g,l=np.maximum(d,0).astype(float),np.maximum(-d,0).astype(float)
    rsi=100-100/(1+_zdiv(_rma(g,14),_rma(l,14)))
    return _lscore(rsi,30,70)

def V15_VolOsc(V):
    return _lscore(_zdiv(_ema(V,9)-_ema(V,21),_ema(V,21))*100,-10,10)

# ============================================================
# ── MODULE H: MOMENTUM & VOLATILITY (H1-H10)
# ============================================================

def H2_ZScore(C, p=20):
    s=np.full(len(C),5.)
    for i in range(p,len(C)):
        w=C[i-p:i]; std=np.std(w)
        if std>0:
            z=(C[i]-np.mean(w))/std
            if z>=2: s[i]=0
            elif z<=-2: s[i]=10
            else: s[i]=float(np.clip(5-(z/2)*5,0,10))
    return s

def H3_STC(C, fast=23, slow=50, cyc=10):
    macd=_ema(C,fast)-_ema(C,slow)
    stc=np.full(len(C),50.)
    for i in range(cyc-1,len(macd)):
        w=macd[max(0,i-cyc+1):i+1]; v=w[~np.isnan(w)]
        if len(v)>=cyc:
            lo,hi=v.min(),v.max()
            if hi-lo>0: stc[i]=100*(macd[i]-lo)/(hi-lo)
    stc=_ema(_ema(stc,3),3)
    return np.where(stc>=75,0,np.where(stc<=25,10,np.clip((100-stc)/10,0,10)))

def H4_KAMA(C, n=10, fast=2, slow=30):
    fs,sl=2/(fast+1),2/(slow+1)
    kama=np.full(len(C),np.nan); kama[n]=C[n]
    for i in range(n+1,len(C)):
        ch=abs(C[i]-C[i-n])
        vl=np.sum(np.abs(np.diff(C[max(0,i-n):i+1])))
        er=ch/vl if vl>0 else 0
        sc=(er*(fs-sl)+sl)**2
        kama[i]=kama[i-1]+sc*(C[i]-kama[i-1])
    prev=np.concatenate(([np.nan],kama[:-1]))
    return np.where(np.isnan(kama)|np.isnan(prev),np.nan,
           np.where(kama>prev,10,np.where(kama<prev,0,5))).astype(float)

def H5_RVI(O, H, L, C):
    nr=(C-O)+2*np.roll(C-O,1)+2*np.roll(C-O,2)+np.roll(C-O,3)
    dr=(H-L)+2*np.roll(H-L,1)+2*np.roll(H-L,2)+np.roll(H-L,3)
    nr[:3]=0; dr[:3]=1
    rvi=_sma(np.where(dr>0,nr/dr,0),4)
    return np.where(np.isnan(rvi),np.nan,
           np.where(rvi>0.3,10,np.where(rvi<-0.3,0,np.clip(5+rvi*10,0,10)))).astype(float)

def H6_Aroon(H, L, p=14):
    s=np.full(len(H),5.)
    for i in range(p,len(H)):
        wh,wl=H[i-p:i+1],L[i-p:i+1]
        au=((p-( p-np.argmax(wh)))/p)*100
        ad=((p-(p-np.argmin(wl)))/p)*100
        osc=au-ad
        s[i]=float(np.clip(5+(osc/50)*5,0,10)) if abs(osc)<50 else (10 if osc>=50 else 0)
    return s

def H7_Breakout(H, L, C, p=20):
    s=np.full(len(C),5.)
    for i in range(p,len(C)):
        hi,lo=np.max(H[i-p:i]),np.min(L[i-p:i])
        if C[i]>hi: s[i]=10
        elif C[i]<lo: s[i]=0
        else:
            rng=hi-lo
            s[i]=float(np.clip((C[i]-lo)/rng*10,0,10)) if rng>0 else 5
    return s

def H9_Squeeze(C, H, L):
    bs=_sma(C,20); bst=_std(C,20)
    bbu=bs+2*bst; bbl=bs-2*bst
    tr=_tr(H,L,C); atr=_rma(tr,20); ke=_ema(C,20)
    kcu=ke+1.5*atr; kcl=ke-1.5*atr
    s=np.full(len(C),5.)
    for i in range(25,len(C)):
        bw=bbu[i]-bbl[i]; kw=kcu[i]-kcl[i]
        if np.isnan(bw) or np.isnan(kw) or kw<=0: continue
        if bw>=kw: s[i]=10 if C[i]>bs[i] else 0
    return s

def H10_Hurst(C, win=100, max_lag=20):
    s=np.full(len(C),5.)
    for i in range(win+max_lag,len(C)):
        series=C[i-win:i]
        taus,lags=[],[]
        for lag in range(2,min(max_lag,win//4)):
            diff=series[lag:]-series[:-lag]
            sd=np.std(diff[~np.isnan(diff)])
            if sd>0: taus.append(sd); lags.append(lag)
        if len(taus)<5: continue
        try:
            c=np.polyfit(np.log(lags),np.log(taus),1)
            h=float(np.clip(c[0],0,1))
            s[i]=10 if h>0.55 else (0 if h<0.45 else float(np.clip((h-0.45)/0.1*5+5,0,10)))
        except: pass
    return s

def H1_Fractal(H, L):
    s=np.full(len(H),5.)
    for i in range(2,len(H)-2):
        if H[i]>H[i-2] and H[i]>H[i-1] and H[i]>H[i+1] and H[i]>H[i+2]: s[i]=0
        elif L[i]<L[i-2] and L[i]<L[i-1] and L[i]<L[i+1] and L[i]<L[i+2]: s[i]=10
    return s

# ============================================================
# ── 5 SCANNERS — COMBINATION ENGINE
# ============================================================

def _vote(scores_list, threshold=5):
    """5/7 majority vote → BUY/SELL/NEUTRAL + confidence"""
    vals=[float(np.nanmean(s[-3:])) if len(s)>0 and not np.all(np.isnan(s)) else 5.
          for s in scores_list]
    buys=sum(1 for v in vals if v>=6.5)
    sells=sum(1 for v in vals if v<=3.5)
    avg=np.nanmean(vals)
    if buys>=5: sig,col="BUY","#00c853"
    elif sells>=5: sig,col="SELL","#ff3d3d"
    else: sig,col="NEUTRAL","#FFD700"
    conf=round(max(buys,sells)/len(vals)*100,1)
    return {"signal":sig,"color":col,"confidence":conf,"score":round(avg,1),
            "buy_count":buys,"sell_count":sells,"total":len(vals),
            "values":[round(v,1) for v in vals]}

def S1_SmartMoney(O,H,L,C,V):
    return _vote([A1_ADX(H,L,C), A2_EMA_Align(C), A4_Supertrend(H,L,C),
                  V1_VWAP(H,L,C,V), V2_CMF(H,L,C,V), H9_Squeeze(C,H,L), H10_Hurst(C)])

def S2_MomentumBurst(O,H,L,C,V):
    return _vote([A3_MACD(C), A5_TSI(C), H3_STC(C), H6_Aroon(H,L),
                  H7_Breakout(H,L,C), V11_VolRSI(V), V15_VolOsc(V)])

def S3_TrendBreakout(O,H,L,C,V):
    return _vote([A6_LinReg(C), A7_DI_Spread(H,L,C), A8_SMA200(C),
                  A10_HullMA(C), V4_OBV(C,V), H4_KAMA(C), H7_Breakout(H,L,C)])

def S4_SafeReversal(O,H,L,C,V):
    return _vote([A9_3Bar(H,L), H1_Fractal(H,L), H2_ZScore(C),
                  V3_VSA(H,L,C,V), V5_MFI(H,L,C,V), H5_RVI(O,H,L,C), H10_Hurst(C)])

def S5_VolumePower(O,H,L,C,V):
    return _vote([V1_VWAP(H,L,C,V), V2_CMF(H,L,C,V), V3_VSA(H,L,C,V),
                  V4_OBV(C,V), V5_MFI(H,L,C,V), V11_VolRSI(V), V15_VolOsc(V)])

SCANNERS = {
    "S1": ("SMART MONEY",    S1_SmartMoney),
    "S2": ("MOMENTUM BURST", S2_MomentumBurst),
    "S3": ("TREND BREAKOUT", S3_TrendBreakout),
    "S4": ("SAFE REVERSAL",  S4_SafeReversal),
    "S5": ("VOLUME POWER",   S5_VolumePower),
}

INDICATORS = {
    "S1": ["ADX(14)","EMA Align","Supertrend","VWAP","CMF","Squeeze","Hurst"],
    "S2": ["MACD","TSI","STC","Aroon","Breakout","Vol RSI","Vol Osc"],
    "S3": ["LinReg","DI Spread","vs SMA200","Hull MA","OBV","KAMA","Breakout"],
    "S4": ["3-Bar","Fractal","Z-Score","VSA","MFI","RVI","Hurst"],
    "S5": ["VWAP","CMF","VSA","OBV","MFI","Vol RSI","Vol Osc"],
}

# ============================================================
# ── DATA FETCH
# ============================================================

def fetch_data(symbol, period="6mo", interval="1d"):
    sym = symbol.upper()
    if not sym.endswith(".NS") and not sym.endswith(".BO"):
        sym = sym + ".NS"
    df = yf.download(sym, period=period, interval=interval, progress=False, auto_adjust=True)
    if df.empty or len(df) < 50:
        raise ValueError(f"Insufficient data for {sym}")
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.dropna()
    return df

# ============================================================
# ── FLASK API
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "Trishul Scanner API", "version": "1.0.0"})

@app.route('/scan', methods=['GET'])
def scan():
    symbol  = request.args.get('symbol', 'RELIANCE')
    scanner = request.args.get('scanner', 'S1').upper()

    if scanner not in SCANNERS:
        return jsonify({"error": f"Unknown scanner {scanner}. Use S1-S5"}), 400

    try:
        df = fetch_data(symbol)
        O = df['Open'].values.astype(float)
        H = df['High'].values.astype(float)
        L = df['Low'].values.astype(float)
        C = df['Close'].values.astype(float)
        V = df['Volume'].values.astype(float)

        name, fn = SCANNERS[scanner]
        result = fn(O, H, L, C, V)
        result['scanner']    = name
        result['scanner_id'] = scanner
        result['symbol']     = symbol.upper()
        result['price']      = round(float(C[-1]), 2)
        result['indicators'] = INDICATORS[scanner]
        result['indicator_detail'] = [
            {"name": INDICATORS[scanner][i], "score": result['values'][i],
             "signal": "BUY" if result['values'][i]>=6.5 else ("SELL" if result['values'][i]<=3.5 else "NEUTRAL")}
            for i in range(len(result['values']))
        ]
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/scan_all', methods=['GET'])
def scan_all():
    symbol = request.args.get('symbol', 'RELIANCE')
    try:
        df = fetch_data(symbol)
        O = df['Open'].values.astype(float)
        H = df['High'].values.astype(float)
        L = df['Low'].values.astype(float)
        C = df['Close'].values.astype(float)
        V = df['Volume'].values.astype(float)
        results = {}
        for sid, (name, fn) in SCANNERS.items():
            r = fn(O, H, L, C, V)
            results[sid] = {"name": name, "signal": r['signal'],
                            "score": r['score'], "confidence": r['confidence'],
                            "color": r['color']}
        return jsonify({"symbol": symbol.upper(), "price": round(float(C[-1]),2),
                        "scanners": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/multi_scan', methods=['GET'])
def multi_scan():
    """Scan multiple symbols with one scanner"""
    symbols = request.args.get('symbols', 'RELIANCE,TCS,HDFC').split(',')
    scanner = request.args.get('scanner', 'S1').upper()
    if scanner not in SCANNERS: return jsonify({"error":"Invalid scanner"}),400
    name, fn = SCANNERS[scanner]
    results = []
    for sym in symbols[:20]:
        try:
            df = fetch_data(sym.strip())
            O,H,L,C,V = (df[k].values.astype(float) for k in ['Open','High','Low','Close','Volume'])
            r = fn(O,H,L,C,V)
            results.append({"symbol":sym.strip().upper(),"signal":r['signal'],
                             "score":r['score'],"confidence":r['confidence'],
                             "color":r['color'],"price":round(float(C[-1]),2)})
        except Exception as e:
            results.append({"symbol":sym.strip().upper(),"error":str(e)})
    return jsonify({"scanner":name,"scanner_id":scanner,"results":results})

if __name__ == '__main__':
    print("=" * 60)
    print("🔱 TRISHUL PRO MASTER — SCANNER API v1.0.0")
    print("=" * 60)
    print("Scanners: S1=Smart Money | S2=Momentum | S3=Trend")
    print("          S4=Reversal   | S5=Volume")
    print("Endpoints:")
    print("  /scan?symbol=RELIANCE&scanner=S1")
    print("  /scan_all?symbol=TCS")
    print("  /multi_scan?symbols=RELIANCE,TCS,HDFC&scanner=S2")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
