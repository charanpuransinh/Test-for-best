/* ============================================================
   RAKSHA WATCHDOG + SELF-REPAIR
   File: raksha-watchdog.js   (load AFTER raksha-core.js)
   ============================================================
   30 sec ka heartbeat loop. Saari 7 HTML files, backend,
   WebSocket, broker session, har scanner check karta hai.
   Problem mile to khud fix karne ki koshish karta hai.
   ============================================================ */

(function (global) {
  'use strict';
  if (!global.Raksha) { console.error('raksha-core.js pehle load karo'); return; }

  const { CONFIG, Store, Bus, Session, Pipeline, Scanners, Router } = global.Raksha;

  /* ---------- CONFIG ---------- */
  const WATCH = {
    INTERVAL_MS: 30000,                    // 30 sec
    TICK_STALE_MS: 60000,                  // tick 60s purana = WS dead
    SCANNER_TIMEOUT_MS: 8000,              // scanner 8s mein response na de = degraded
    PAGE_PING_MS: 5000,                    // har page itne mein heartbeat bheje
    MAX_CONSECUTIVE_FAILS: 3,              // 3 baar fail to escalate
    AUTO_RELOAD_ON_FREEZE: true,
    ALERT_CHANNEL: 'raksha:watchdog'
  };

  /* ---------- HEALTH STATE ---------- */
  // Sab kuch yahan track hota hai, control panel pe dikhega
  const Health = Store.get('health') || {
    backend:    { status: 'unknown', lastOk: 0, fails: 0 },
    websocket:  { status: 'unknown', lastTick: 0, fails: 0 },
    session:    { status: 'unknown', expiresAt: 0 },
    scanners:   {},                        // { morning_bell: { status, lastOk, fails, avgMs } }
    pages:      {},                        // { home: { lastSeen, status } }
    repairs:    [],                        // history of self-repair actions (last 50)
    lastCheck:  0
  };
  // Initialize scanner state
  CONFIG.SCANNERS.forEach(s => {
    if (!Health.scanners[s]) Health.scanners[s] = { status: 'unknown', lastOk: 0, fails: 0, avgMs: 0 };
  });

  function logRepair(action, detail, success) {
    const entry = { ts: Date.now(), action, detail, success };
    Health.repairs.unshift(entry);
    Health.repairs = Health.repairs.slice(0, 50);
    Store.set('health', Health);
    Bus.emit('watchdog:repair', entry);
    console.log(`[Watchdog] REPAIR ${success ? '✓' : '✗'} ${action}: ${detail}`);
  }

  function setHealth(component, patch) {
    Object.assign(Health[component] || (Health[component] = {}), patch);
    Health.lastCheck = Date.now();
    Store.set('health', Health);
    Bus.emit('watchdog:health', { component, state: Health[component] });
  }

  /* ---------- CHECK 1: BACKEND ---------- */
  async function checkBackend() {
    const t0 = Date.now();
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 5000);
      const res = await fetch(`${CONFIG.AWS_BACKEND}/health`, { signal: ctrl.signal });
      clearTimeout(timer);
      if (!res.ok) throw new Error(res.status);
      setHealth('backend', { status: 'ok', lastOk: Date.now(), fails: 0, latencyMs: Date.now() - t0 });
      return true;
    } catch (e) {
      Health.backend.fails = (Health.backend.fails || 0) + 1;
      setHealth('backend', { status: 'down', error: e.message });
      // SELF-REPAIR: fallback to cached data, retry next cycle
      if (Health.backend.fails >= WATCH.MAX_CONSECUTIVE_FAILS) {
        logRepair('backend_fallback', 'Switching to cached mode', true);
        Bus.emit('mode:offline');
      }
      return false;
    }
  }

  /* ---------- CHECK 2: WEBSOCKET / LIVE TICKS ---------- */
  function checkWebSocket() {
    const ticks = Store.get('ticks') || {};
    const lastTickTs = Math.max(0, ...Object.values(ticks).map(t => t.ts || 0));
    const stale = Date.now() - lastTickTs > WATCH.TICK_STALE_MS;

    if (stale && Session.isLoggedIn() && Object.keys(ticks).length) {
      Health.websocket.fails++;
      setHealth('websocket', { status: 'stale', lastTick: lastTickTs });
      // SELF-REPAIR: reconnect WebSocket
      logRepair('ws_reconnect', `Last tick ${Math.round((Date.now()-lastTickTs)/1000)}s ago`, true);
      try {
        Pipeline.disconnectLive();
        Pipeline.connectLive(global.Raksha.Watchlist.list);
      } catch (e) {
        logRepair('ws_reconnect', e.message, false);
      }
    } else {
      setHealth('websocket', { status: stale ? 'idle' : 'ok', lastTick: lastTickTs, fails: 0 });
    }
  }

  /* ---------- CHECK 3: SESSION / BROKER TOKEN ---------- */
  async function checkSession() {
    if (!Session.isLoggedIn()) {
      setHealth('session', { status: 'logged_out' });
      return;
    }
    const broker = Session.broker;
    const ageHr = Store.age('broker') / 3600000;

    // Token 7+ hour purana ho gaya = pre-emptive refresh
    if (ageHr > 7) {
      try {
        const res = await fetch(`${CONFIG.AWS_BACKEND}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${broker.token}` }
        });
        if (res.ok) {
          const data = await res.json();
          Session.login(Session.user, { ...broker, token: data.token });
          logRepair('token_refresh', `Token refreshed (was ${ageHr.toFixed(1)}h old)`, true);
          setHealth('session', { status: 'ok', expiresAt: Date.now() + 8*3600000 });
        } else {
          throw new Error('refresh failed');
        }
      } catch (e) {
        logRepair('token_refresh', e.message, false);
        setHealth('session', { status: 'expiring' });
      }
    } else {
      setHealth('session', { status: 'ok' });
    }
  }

  /* ---------- CHECK 4: SCANNERS (har ek ka health) ---------- */
  async function checkScanners() {
    const probeSymbol = (global.Raksha.Watchlist.list[0]) || 'RELIANCE';
    if (!Session.isLoggedIn()) return;

    for (const name of CONFIG.SCANNERS) {
      if (name === 'all_in_one_van') continue;     // ye aggregate hai, alag check
      const t0 = Date.now();
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), WATCH.SCANNER_TIMEOUT_MS);
        const res = await fetch(`${CONFIG.AWS_BACKEND}/scanner/${name}?symbol=${probeSymbol}`, {
          signal: ctrl.signal,
          headers: { Authorization: `Bearer ${Session.broker.token}` }
        });
        clearTimeout(timer);
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        const ms = Date.now() - t0;
        const prev = Health.scanners[name];
        const avg = prev.avgMs ? (prev.avgMs * 0.7 + ms * 0.3) : ms;
        Health.scanners[name] = { status: 'ok', lastOk: Date.now(), fails: 0, avgMs: Math.round(avg), lastScore: data.score };
      } catch (e) {
        const sc = Health.scanners[name];
        sc.fails = (sc.fails || 0) + 1;
        sc.status = sc.fails >= WATCH.MAX_CONSECUTIVE_FAILS ? 'degraded' : 'flaky';
        sc.lastError = e.message;
        // SELF-REPAIR: degraded scanner ko aggregation se exclude
        if (sc.status === 'degraded') {
          logRepair('scanner_disable', `${name} disabled (${sc.fails} fails)`, true);
        }
      }
    }
    Store.set('health', Health);
    Bus.emit('watchdog:scanners', Health.scanners);
  }

  /* ---------- CHECK 5: PAGES (heartbeat from each open tab) ---------- */
  // Har page apna heartbeat localStorage mein update karega
  function checkPages() {
    const now = Date.now();
    Object.keys(Health.pages).forEach(p => {
      const last = Health.pages[p].lastSeen || 0;
      const idle = now - last;
      if (idle > WATCH.PAGE_PING_MS * 4) {
        Health.pages[p].status = 'frozen';
        // SELF-REPAIR: agar wahi tab hai aur frozen hai, reload
        if (WATCH.AUTO_RELOAD_ON_FREEZE && Router.current() === p) {
          logRepair('page_reload', `${p} frozen ${idle}ms`, true);
          setTimeout(() => location.reload(), 500);
        }
      } else {
        Health.pages[p].status = 'ok';
      }
    });
    Store.set('health', Health);
  }

  // Current page apna heartbeat har 5s pe register kare
  function startHeartbeat() {
    const me = Router.current();
    const beat = () => {
      Health.pages[me] = { lastSeen: Date.now(), status: 'ok' };
      Store.set('health', Health);
    };
    beat();
    setInterval(beat, WATCH.PAGE_PING_MS);
  }

  /* ---------- CHECK 6: STORAGE INTEGRITY ---------- */
  function checkStorage() {
    try {
      // Test write/read
      const testKey = 'raksha:_wd_test';
      localStorage.setItem(testKey, JSON.stringify({ t: Date.now() }));
      const back = JSON.parse(localStorage.getItem(testKey));
      localStorage.removeItem(testKey);
      if (!back || !back.t) throw new Error('roundtrip fail');

      // Quota check
      const used = JSON.stringify(localStorage).length;
      if (used > 4 * 1024 * 1024) {     // 4MB
        // SELF-REPAIR: oldest non-critical entries clear
        ['ticks_history', 'scanner_history_old'].forEach(k => Store.set(k, null));
        logRepair('storage_cleanup', `Cleared old data (${(used/1024).toFixed(0)}KB)`, true);
      }
      setHealth('storage', { status: 'ok', usedKB: Math.round(used/1024) });
    } catch (e) {
      logRepair('storage_reset', e.message, false);
      try { localStorage.clear(); location.reload(); } catch {}
    }
  }

  /* ---------- MASTER LOOP ---------- */
  let cycleRunning = false;
  async function runCycle() {
    if (cycleRunning) return;             // overlapping prevent
    cycleRunning = true;
    try {
      checkStorage();
      const beOk = await checkBackend();
      checkWebSocket();
      checkPages();
      if (beOk) {
        await checkSession();
        await checkScanners();
      }
      Bus.emit('watchdog:cycle', { ts: Date.now(), health: Health });
    } catch (e) {
      console.error('[Watchdog] cycle err', e);
    } finally {
      cycleRunning = false;
    }
  }

  /* ---------- API ---------- */
  const Watchdog = {
    Health,
    runNow: runCycle,
    getReport() {
      return {
        backend:   Health.backend.status,
        websocket: Health.websocket.status,
        session:   Health.session.status,
        scanners:  Object.entries(Health.scanners).map(([k,v]) => ({ name: k, ...v })),
        pages:     Health.pages,
        recentRepairs: Health.repairs.slice(0, 10)
      };
    },
    reset() {
      Store.set('health', null);
      location.reload();
    }
  };

  /* ---------- BOOT ---------- */
  function start() {
    startHeartbeat();
    runCycle();                            // first run immediately
    setInterval(runCycle, WATCH.INTERVAL_MS);
    console.log('[Watchdog] Started, interval', WATCH.INTERVAL_MS, 'ms');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  global.Raksha.Watchdog = Watchdog;
})(window);
