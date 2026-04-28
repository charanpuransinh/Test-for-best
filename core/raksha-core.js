/* ============================================================
   RAKSHA CORE - Mogal Industries Trading Pipeline
   Author: Charan | Project: Trishul + Trinetra
   File: raksha-core.js  (load this in EVERY HTML page first)
   ============================================================
   Ye file ek central nervous system hai. Saare 7 pages
   (home, power, scanner, chart, watchlist, control, index)
   isi file se data leke kaam karenge. Koi dummy data nahi.
   ============================================================ */

(function (global) {
  'use strict';

  /* ---------- 1. CONFIG ---------- */
  const CONFIG = {
    APP_NAME: 'TRISHUL',                       // ya 'TRINETRA' Trinetra build mein
    VERSION: '1.0.0',
    AWS_BACKEND: 'http://13.206.70.60:8080',   // aapka AWS server
    WS_ENDPOINT: 'ws://13.206.70.60:8081/live',// live tick stream
    REFRESH_MS: 3000,                          // 3 sec polling fallback
    SIGNAL_THRESHOLDS: {
      ORANGE_ALERT:  [55, 60],
      CONFIRMED_BUY: [61, 75],
      STRONG_BUY:    [76, 89],
      ULTRA_STRONG:  [90, 100]
    },
    SCANNERS: [
      'morning_bell', 'mahakal', 'bherve', 'index_power',
      'trishul_news', 'sudarshan', 'brahmastra',
      'expiry_scalper', 'all_in_one_van'
    ],
    BROKERS: [
      'zerodha','upstox','angel','fyers','dhan',
      'iifl','5paisa','groww','icici','kotak'
    ]
  };

  /* ---------- 2. STORAGE LAYER ---------- */
  // Cross-page persistent storage. localStorage = same-origin sab pages share karte hain.
  const Store = {
    set(key, val) {
      try { localStorage.setItem(`raksha:${key}`, JSON.stringify({ v: val, t: Date.now() })); }
      catch (e) { console.warn('Store.set fail', key, e); }
    },
    get(key) {
      try {
        const raw = localStorage.getItem(`raksha:${key}`);
        return raw ? JSON.parse(raw).v : null;
      } catch { return null; }
    },
    age(key) {
      const raw = localStorage.getItem(`raksha:${key}`);
      return raw ? Date.now() - JSON.parse(raw).t : Infinity;
    },
    clear(prefix = '') {
      Object.keys(localStorage)
        .filter(k => k.startsWith(`raksha:${prefix}`))
        .forEach(k => localStorage.removeItem(k));
    }
  };

  /* ---------- 3. EVENT BUS (cross-tab) ---------- */
  // BroadcastChannel = ek tab mein update hua to dusre tabs ko bhi pata chal jaye
  const channel = ('BroadcastChannel' in global) ? new BroadcastChannel('raksha') : null;
  const listeners = {};
  const Bus = {
    on(evt, fn)   { (listeners[evt] = listeners[evt] || []).push(fn); },
    off(evt, fn)  { listeners[evt] = (listeners[evt]||[]).filter(f => f !== fn); },
    emit(evt, data) {
      (listeners[evt] || []).forEach(fn => { try { fn(data); } catch(e){ console.error(e); } });
      if (channel) channel.postMessage({ evt, data });
    }
  };
  if (channel) channel.onmessage = (m) => {
    (listeners[m.data.evt] || []).forEach(fn => fn(m.data.data));
  };

  /* ---------- 4. SESSION / AUTH ---------- */
  const Session = {
    get user()   { return Store.get('user'); },
    get broker() { return Store.get('broker'); },
    isLoggedIn() {
      const u = this.user, b = this.broker;
      return !!(u && b && b.token && Store.age('broker') < 8 * 3600 * 1000);
    },
    login(user, broker) {
      Store.set('user', user);
      Store.set('broker', broker);
      Bus.emit('session:login', { user, broker });
    },
    logout() {
      Store.clear();
      Bus.emit('session:logout');
      location.href = 'index.html';
    },
    requireAuth() {
      if (!this.isLoggedIn() && !location.pathname.endsWith('index.html')) {
        location.href = 'index.html';
      }
    }
  };

  /* ---------- 5. DATA PIPELINE (live market data) ---------- */
  // Backend se REST + WebSocket. Koi mock data nahi.
  let ws = null, pollTimer = null;
  const Pipeline = {
    async fetch(path, opts = {}) {
      const broker = Session.broker;
      const headers = {
        'Content-Type': 'application/json',
        'X-App': CONFIG.APP_NAME,
        ...(broker ? { 'Authorization': `Bearer ${broker.token}` } : {}),
        ...(opts.headers || {})
      };
      const res = await fetch(`${CONFIG.AWS_BACKEND}${path}`, { ...opts, headers });
      if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
      return res.json();
    },

    // Real-time tick stream
    connectLive(symbols = []) {
      this.disconnectLive();
      try {
        ws = new WebSocket(`${CONFIG.WS_ENDPOINT}?token=${Session.broker?.token || ''}`);
        ws.onopen    = () => { ws.send(JSON.stringify({ subscribe: symbols })); Bus.emit('ws:open'); };
        ws.onmessage = (e) => {
          const tick = JSON.parse(e.data);                       // {symbol, ltp, ch, vol, ts}
          const map = Store.get('ticks') || {};
          map[tick.symbol] = tick;
          Store.set('ticks', map);
          Bus.emit('tick', tick);
        };
        ws.onclose = () => { Bus.emit('ws:close'); setTimeout(() => this.connectLive(symbols), 5000); };
        ws.onerror = (e) => Bus.emit('ws:error', e);
      } catch (e) {
        console.warn('WS fail, polling fallback', e);
        this.startPolling(symbols);
      }
    },
    disconnectLive() {
      if (ws) { try { ws.close(); } catch{} ws = null; }
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    },
    startPolling(symbols) {
      pollTimer = setInterval(async () => {
        try {
          const data = await this.fetch(`/quotes?symbols=${symbols.join(',')}`);
          Store.set('ticks', data);
          Bus.emit('ticks:bulk', data);
        } catch(e){ console.error('poll err', e); }
      }, CONFIG.REFRESH_MS);
    }
  };

  /* ---------- 6. SCANNER ENGINE (saare 9 scanners) ---------- */
  // Har scanner backend pe chalta hai, hum sirf score lete hain
  const Scanners = {
    scores: {},        // { morning_bell: 78, mahakal: 65, ... }
    signals: {},       // { TCS: { score: 82, type: 'STRONG_BUY' }, ... }

    classify(score) {
      const t = CONFIG.SIGNAL_THRESHOLDS;
      if (score >= t.ULTRA_STRONG[0])  return 'ULTRA_STRONG_BUY';
      if (score >= t.STRONG_BUY[0])    return 'STRONG_BUY';
      if (score >= t.CONFIRMED_BUY[0]) return 'CONFIRMED_BUY';
      if (score >= t.ORANGE_ALERT[0])  return 'ORANGE_ALERT';
      return 'NEUTRAL';
    },

    async runOne(name, symbol) {
      const data = await Pipeline.fetch(`/scanner/${name}?symbol=${symbol}`);
      const out  = { name, symbol, score: data.score, type: this.classify(data.score), meta: data, ts: Date.now() };
      this.scores[`${name}:${symbol}`] = out;
      Store.set('scanner_scores', this.scores);
      Bus.emit('scanner:update', out);
      return out;
    },

    async runAll(symbol) {
      const results = await Promise.allSettled(
        CONFIG.SCANNERS.filter(s => s !== 'all_in_one_van').map(s => this.runOne(s, symbol))
      );
      return this.aggregate(symbol, results);
    },

    /* ALL-IN-ONE-VAN logic: 5/8 scanners BUY = CONFIRM */
    aggregate(symbol, results) {
      const ok = results.filter(r => r.status === 'fulfilled').map(r => r.value);
      const buyCount = ok.filter(r => ['CONFIRMED_BUY','STRONG_BUY','ULTRA_STRONG_BUY'].includes(r.type)).length;
      const avgScore = ok.reduce((a,b) => a + b.score, 0) / (ok.length || 1);

      const verdict = {
        symbol,
        scannersFired: buyCount,
        totalScanners: ok.length,
        avgScore: Math.round(avgScore),
        type: this.classify(avgScore),
        confirmed: buyCount >= 5,        // Sabka Baap rule
        powerTable: null,
        ts: Date.now()
      };

      if (verdict.confirmed) {
        verdict.powerTable = this.buildPowerTable(symbol, avgScore, ok);
        Bus.emit('mustbuy:alert', verdict);
      }
      this.signals[symbol] = verdict;
      Store.set('signals', this.signals);
      Bus.emit('signal:update', verdict);
      return verdict;
    },

    buildPowerTable(symbol, score, scannerOutputs) {
      const ltp = (Store.get('ticks') || {})[symbol]?.ltp;
      if (!ltp) return null;
      // Backend se proper ATR-based levels lena better hai, ye sirf safe fallback
      const buffer = ltp * 0.005 * (1 + (score - 60) / 100);
      return {
        entry:  +(ltp).toFixed(2),
        target: +(ltp + buffer * 3).toFixed(2),
        sl:     +(ltp - buffer * 1.5).toFixed(2),
        exit:   +(ltp + buffer * 5).toFixed(2),
        rr:     '1:2',
        score
      };
    }
  };

  /* ---------- 7. WATCHLIST ---------- */
  const Watchlist = {
    get list() { return Store.get('watchlist') || []; },
    add(symbol) {
      const l = this.list;
      if (!l.includes(symbol)) { l.push(symbol); Store.set('watchlist', l); Bus.emit('watchlist:add', symbol); }
    },
    remove(symbol) {
      Store.set('watchlist', this.list.filter(s => s !== symbol));
      Bus.emit('watchlist:remove', symbol);
    },
    has(symbol) { return this.list.includes(symbol); }
  };

  /* ---------- 8. PAGE ROUTER ---------- */
  // Har page apna ID set kare. Auto-init ke liye useful.
  const Router = {
    pages: {
      'index':         'index.html',
      'home':          '2_home_page.html',
      'power':         '3_power_box.html',
      'scanner':       '5_scanner.html',
      'chart':         '4_chart_page.html',
      'watchlist':     '6_watchlist.html',
      'control':       '8_control_panel.html'
    },
    go(name) {
      if (this.pages[name]) location.href = this.pages[name];
    },
    current() {
      const path = location.pathname.split('/').pop();
      return Object.entries(this.pages).find(([,v]) => v === path)?.[0] || 'unknown';
    }
  };

  /* ---------- 9. BOOT ---------- */
  function boot() {
    console.log(`[Raksha] ${CONFIG.APP_NAME} v${CONFIG.VERSION} booting on ${Router.current()}`);
    Session.requireAuth();

    // Login hua hai to live stream aur scanner refresh shuru
    if (Session.isLoggedIn()) {
      const wl = Watchlist.list;
      if (wl.length) Pipeline.connectLive(wl);
    }

    // Login event hone par auto-reconnect
    Bus.on('session:login', () => {
      const wl = Watchlist.list;
      if (wl.length) Pipeline.connectLive(wl);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* ---------- 10. EXPORT ---------- */
  global.Raksha = { CONFIG, Store, Bus, Session, Pipeline, Scanners, Watchlist, Router };
})(window);
