/* ============================================================
   RAKSHA ACCURACY TRACKER
   File: raksha-tracker.js   (load AFTER raksha-watchdog.js)
   ============================================================
   Har scanner signal ko log karta hai, decided time-window ke
   baad real price se compare karta hai aur batata hai:
     - Kaun sa scanner sahi trade de raha hai (high win rate)
     - Kaun sa galat de raha hai (high SL hit / false alerts)
   Auto-disable karta hai consistently galat scanners ko.
   ============================================================ */

(function (global) {
  'use strict';
  if (!global.Raksha) { console.error('raksha-core.js pehle load karo'); return; }

  const { CONFIG, Store, Bus, Pipeline, Scanners } = global.Raksha;

  /* ---------- CONFIG ---------- */
  const TRACK = {
    EVAL_WINDOW_MS: 30 * 60 * 1000,        // 30 min baad signal evaluate
    MIN_SIGNALS_FOR_RANK: 10,              // 10 signals ke baad ranking valid
    AUTO_DISABLE_THRESHOLD: 30,            // win rate < 30% = auto disable
    AUTO_PROMOTE_THRESHOLD: 65,            // win rate > 65% = "trusted" tag
    EVAL_INTERVAL_MS: 60 * 1000,           // har 1 min mein pending signals check
    HISTORY_RETAIN: 500                    // last 500 signals per scanner
  };

  /* ---------- STORAGE ---------- */
  // Structure:
  // signals_pending: [ {id, scanner, symbol, score, type, entry, target, sl, ts, evalAt} ]
  // signals_done:    { scanner_name: [ {...signal, outcome, exitPrice, pnlPct, evalTs} ] }
  // scanner_stats:   { scanner_name: { total, wins, losses, neutral, winRate, avgPnl, status } }

  function getPending()  { return Store.get('signals_pending') || []; }
  function setPending(x) { Store.set('signals_pending', x); }
  function getDone()     { return Store.get('signals_done') || {}; }
  function setDone(x)    { Store.set('signals_done', x); }
  function getStats()    { return Store.get('scanner_stats') || {}; }
  function setStats(x)   { Store.set('scanner_stats', x); Bus.emit('tracker:stats', x); }

  /* ---------- 1. LOG SIGNAL (jab bhi scanner BUY de) ---------- */
  function logSignal(payload) {
    // payload = { scanner, symbol, score, type, entry, target, sl }
    if (!payload.entry || !payload.target || !payload.sl) {
      console.warn('[Tracker] signal skip - missing levels', payload);
      return null;
    }
    const sig = {
      id:      `${payload.scanner}_${payload.symbol}_${Date.now()}`,
      ...payload,
      ts:      Date.now(),
      evalAt:  Date.now() + TRACK.EVAL_WINDOW_MS,
      status:  'pending'
    };
    const list = getPending();
    list.push(sig);
    setPending(list);
    Bus.emit('tracker:signal_logged', sig);
    console.log(`[Tracker] LOGGED ${sig.scanner} ${sig.symbol} @ ${sig.entry}`);
    return sig;
  }

  /* ---------- 2. EVALUATE PENDING SIGNALS ---------- */
  // Har 1 min check karta hai jin signals ka time aa gaya hai unko
  async function evaluatePending() {
    const now = Date.now();
    const pending = getPending();
    const ready = pending.filter(s => s.evalAt <= now);
    if (!ready.length) return;

    const stillPending = pending.filter(s => s.evalAt > now);
    const done = getDone();

    for (const sig of ready) {
      try {
        // Real exit price backend se lo (NOT current LTP - actual high/low between entry and now)
        const result = await Pipeline.fetch(
          `/eval?symbol=${sig.symbol}&from=${sig.ts}&to=${now}&entry=${sig.entry}&target=${sig.target}&sl=${sig.sl}`
        );
        // Backend returns: { hitTarget: bool, hitSL: bool, exitPrice, maxFavorable, maxAdverse }

        let outcome = 'NEUTRAL';
        if (result.hitTarget && !result.hitSLBefore)      outcome = 'WIN';
        else if (result.hitSL)                            outcome = 'LOSS';
        else if (result.exitPrice > sig.entry)            outcome = 'PARTIAL_WIN';

        const pnlPct = ((result.exitPrice - sig.entry) / sig.entry) * 100;

        const finalized = {
          ...sig,
          status: 'evaluated',
          outcome,
          exitPrice: result.exitPrice,
          pnlPct: +pnlPct.toFixed(2),
          maxFavorable: result.maxFavorable,
          maxAdverse: result.maxAdverse,
          evalTs: now
        };

        // Store under scanner name
        if (!done[sig.scanner]) done[sig.scanner] = [];
        done[sig.scanner].unshift(finalized);
        done[sig.scanner] = done[sig.scanner].slice(0, TRACK.HISTORY_RETAIN);

        Bus.emit('tracker:evaluated', finalized);
        console.log(`[Tracker] ${sig.scanner} ${sig.symbol} → ${outcome} (${pnlPct.toFixed(2)}%)`);
      } catch (e) {
        // Backend down / data missing - retry next cycle
        stillPending.push({ ...sig, evalAt: now + 5*60*1000, retries: (sig.retries||0) + 1 });
        console.warn(`[Tracker] eval failed for ${sig.id}, retry`, e.message);
      }
    }

    setPending(stillPending);
    setDone(done);
    recomputeStats();
  }

  /* ---------- 3. RECOMPUTE PER-SCANNER STATS ---------- */
  function recomputeStats() {
    const done = getDone();
    const stats = {};

    for (const [scanner, signals] of Object.entries(done)) {
      const total   = signals.length;
      const wins    = signals.filter(s => s.outcome === 'WIN').length;
      const partial = signals.filter(s => s.outcome === 'PARTIAL_WIN').length;
      const losses  = signals.filter(s => s.outcome === 'LOSS').length;
      const neutral = signals.filter(s => s.outcome === 'NEUTRAL').length;

      const effectiveWins = wins + (partial * 0.5);
      const winRate = total > 0 ? (effectiveWins / total) * 100 : 0;
      const avgPnl  = total > 0 ? signals.reduce((a,s) => a + s.pnlPct, 0) / total : 0;
      const last20  = signals.slice(0, 20);
      const recentWinRate = last20.length
        ? (last20.filter(s => s.outcome === 'WIN' || s.outcome === 'PARTIAL_WIN').length / last20.length) * 100
        : 0;

      // Status assign karo
      let status = 'evaluating';
      if (total >= TRACK.MIN_SIGNALS_FOR_RANK) {
        if (winRate >= TRACK.AUTO_PROMOTE_THRESHOLD)      status = 'trusted';
        else if (winRate < TRACK.AUTO_DISABLE_THRESHOLD)  status = 'disabled';
        else if (winRate >= 50)                            status = 'good';
        else                                               status = 'weak';
      }

      stats[scanner] = {
        total, wins, partial, losses, neutral,
        winRate: +winRate.toFixed(1),
        recentWinRate: +recentWinRate.toFixed(1),
        avgPnl: +avgPnl.toFixed(2),
        status,
        verdict: rateScanner(winRate, recentWinRate, avgPnl, total)
      };
    }
    setStats(stats);
    enforceAutoDisable(stats);
    return stats;
  }

  /* ---------- 4. HUMAN-READABLE VERDICT ---------- */
  function rateScanner(winRate, recent, avgPnl, total) {
    if (total < TRACK.MIN_SIGNALS_FOR_RANK) return `🟡 Need more data (${total}/${TRACK.MIN_SIGNALS_FOR_RANK})`;
    if (winRate >= 70 && avgPnl > 0)        return '🟢 SAHI - Trust kar sakte ho';
    if (winRate >= 55)                       return '🟢 Good - Reliable scanner';
    if (winRate >= 40)                       return '🟡 Average - Filter laga ke use karo';
    if (winRate >= 30)                       return '🔴 Weak - Sell signals jyada';
    return '⛔ GALAT - Auto disabled';
  }

  /* ---------- 5. AUTO DISABLE / RE-ENABLE ---------- */
  // Galat scanner ko aggregation se hata do
  function enforceAutoDisable(stats) {
    const disabled = Object.entries(stats)
      .filter(([,s]) => s.status === 'disabled')
      .map(([n]) => n);
    Store.set('disabled_scanners', disabled);
    if (disabled.length) {
      Bus.emit('tracker:auto_disabled', disabled);
    }
  }

  /* ---------- 6. RANKINGS ---------- */
  function getRanking() {
    const stats = getStats();
    return Object.entries(stats)
      .map(([name, s]) => ({ name, ...s }))
      .sort((a, b) => {
        // Trusted > Good > Evaluating > Weak > Disabled
        const order = { trusted: 5, good: 4, evaluating: 3, weak: 2, disabled: 1 };
        if (order[a.status] !== order[b.status]) return order[b.status] - order[a.status];
        return b.winRate - a.winRate;
      });
  }

  /* ---------- 7. AUTO-HOOK INTO SCANNER ENGINE ---------- */
  // Jab bhi koi scanner ya aggregate signal aaye, automatically log ho
  Bus.on('scanner:update', (result) => {
    // Sirf BUY signals track karte hain
    if (!['CONFIRMED_BUY', 'STRONG_BUY', 'ULTRA_STRONG_BUY'].includes(result.type)) return;

    const ticks = Store.get('ticks') || {};
    const ltp = ticks[result.symbol]?.ltp;
    if (!ltp) return;

    // Quick power table for tracking
    const buffer = ltp * 0.005 * (1 + (result.score - 60) / 100);
    logSignal({
      scanner: result.name,
      symbol: result.symbol,
      score: result.score,
      type: result.type,
      entry: ltp,
      target: +(ltp + buffer * 3).toFixed(2),
      sl: +(ltp - buffer * 1.5).toFixed(2)
    });
  });

  Bus.on('mustbuy:alert', (verdict) => {
    if (!verdict.powerTable) return;
    logSignal({
      scanner: 'all_in_one_van',
      symbol: verdict.symbol,
      score: verdict.avgScore,
      type: verdict.type,
      entry: verdict.powerTable.entry,
      target: verdict.powerTable.target,
      sl: verdict.powerTable.sl
    });
  });

  /* ---------- 8. AGGREGATION OVERRIDE - galat scanners ignore ---------- */
  // Original aggregate ko wrap karte hain
  const origAggregate = Scanners.aggregate.bind(Scanners);
  Scanners.aggregate = function (symbol, results) {
    const disabled = Store.get('disabled_scanners') || [];
    const filtered = results.filter(r =>
      r.status === 'fulfilled' && !disabled.includes(r.value.name)
    );
    return origAggregate(symbol, filtered);
  };

  /* ---------- 9. EVAL LOOP ---------- */
  setInterval(evaluatePending, TRACK.EVAL_INTERVAL_MS);
  setTimeout(evaluatePending, 5000);    // first run after 5s

  /* ---------- 10. PUBLIC API ---------- */
  global.Raksha.Tracker = {
    logSignal,
    evaluateNow: evaluatePending,
    getStats,
    getRanking,
    getPending,
    getHistory: (scanner) => (getDone()[scanner] || []),
    resetScanner: (scanner) => {
      const d = getDone(); delete d[scanner]; setDone(d); recomputeStats();
    },
    resetAll: () => {
      setPending([]); setDone({}); setStats({});
      Store.set('disabled_scanners', []);
      Bus.emit('tracker:reset');
    },
    enableScanner: (scanner) => {
      const d = Store.get('disabled_scanners') || [];
      Store.set('disabled_scanners', d.filter(x => x !== scanner));
    }
  };

  console.log('[Tracker] Accuracy tracker active');
})(window);
