# RAKSHA PIPELINE - Integration Guide
**Project:** Mogal Industries - Trishul + Trinetra
**Author:** Charan

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│              AWS UBUNTU SERVER (13.206.70.60)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  FastAPI     │  │  WebSocket   │  │  10 Brokers  │    │
│  │  REST :8080  │  │  Live :8081  │  │  Adapters    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         └─────────────────┴─────────────────┘            │
│                  Scanner Engine (9)                      │
└─────────────────────────┬────────────────────────────────┘
                          │  HTTPS / WSS
┌─────────────────────────┴────────────────────────────────┐
│              GITHUB PAGES (frontend)                     │
│                  raksha-core.js                          │
│  ┌────────┬────────┬────────┬────────┬────────┬───────┐  │
│  │ index  │ home   │ power  │scanner │ chart  │ wlist │  │
│  └────────┴────────┴────────┴────────┴────────┴───────┘  │
│            All share ONE state via localStorage          │
│            All sync via BroadcastChannel                 │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 File 1: `index.html` (Login)

```html
<!-- HEAD mein, sabse pehle -->
<script src="raksha-core.js"></script>

<!-- Login button par -->
<script>
document.getElementById('loginBtn').onclick = async () => {
  const broker = document.getElementById('brokerSelect').value;
  const creds  = { username: u.value, password: p.value, totp: t.value };

  try {
    const res = await fetch(`${Raksha.CONFIG.AWS_BACKEND}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ broker, credentials: creds })
    });
    const data = await res.json();

    Raksha.Session.login(
      { name: u.value },
      { name: broker, token: data.token }
    );
    Raksha.Router.go('home');
  } catch (e) {
    alert('Login fail: ' + e.message);
  }
};
</script>
```

---

## 📁 File 2: `1_home_page.html`

```html
<script src="raksha-core.js"></script>
<script>
// Auto-redirect agar login nahi (core mein already hai)

// Live ticks ke liye watchlist subscribe
const wl = Raksha.Watchlist.list;
if (wl.length) Raksha.Pipeline.connectLive(wl);

// Tick aaye to UI update
Raksha.Bus.on('tick', (t) => {
  const el = document.getElementById(`ltp-${t.symbol}`);
  if (el) {
    el.textContent = t.ltp;
    el.style.color = t.ch >= 0 ? '#0f0' : '#f00';
  }
});

// Scanner signal aaye to home dashboard pe alert
Raksha.Bus.on('signal:update', (sig) => {
  if (sig.confirmed) showToast(`${sig.symbol} - ${sig.scannersFired}/8 fired!`);
});
</script>
```

---

## 📁 File 3: `2_power_box.html`

```html
<script src="raksha-core.js"></script>
<script>
async function refreshPower() {
  const symbols = Raksha.Watchlist.list;
  for (const sym of symbols) {
    const verdict = await Raksha.Scanners.runAll(sym);
    renderRow(sym, verdict);  // aapka existing UI function
  }
}
refreshPower();
setInterval(refreshPower, 30000);   // har 30 sec
</script>
```

---

## 📁 File 4: `3_scanner.html` (individual scanner select)

```html
<script src="raksha-core.js"></script>
<script>
document.getElementById('runScannerBtn').onclick = async () => {
  const name   = document.getElementById('scannerSelect').value;
  const symbol = document.getElementById('symbolInput').value;
  const result = await Raksha.Scanners.runOne(name, symbol);

  document.getElementById('score').textContent = result.score;
  document.getElementById('signal').textContent = result.type;
  document.getElementById('signal').className = `badge ${result.type.toLowerCase()}`;
};
</script>
```

---

## 📁 File 5: `4_chart_page.html`

```html
<script src="raksha-core.js"></script>
<script>
const symbol = new URLSearchParams(location.search).get('s') || 'NIFTY';
async function loadChart() {
  const data = await Raksha.Pipeline.fetch(`/history?symbol=${symbol}&interval=5minute&days=5`);
  drawChart(data);  // aapka chart lib (lightweight-charts/tradingview)
}
loadChart();

// Live tick se chart update
Raksha.Bus.on('tick', t => { if (t.symbol === symbol) updateLastBar(t); });
</script>
```

---

## 📁 File 6: `5_watchlist.html`

```html
<script src="raksha-core.js"></script>
<script>
function render() {
  const ul = document.getElementById('wlist');
  ul.innerHTML = '';
  Raksha.Watchlist.list.forEach(sym => {
    const tick = (Raksha.Store.get('ticks') || {})[sym] || {};
    ul.insertAdjacentHTML('beforeend', `
      <li>
        <span>${sym}</span>
        <span id="ltp-${sym}">${tick.ltp || '--'}</span>
        <button onclick="Raksha.Watchlist.remove('${sym}')">×</button>
      </li>`);
  });
}
render();
Raksha.Bus.on('watchlist:add', render);
Raksha.Bus.on('watchlist:remove', render);
Raksha.Bus.on('tick', render);
</script>
```

---

## 📁 File 7: `6_control_panel.html`

```html
<script src="raksha-core.js"></script>
<script>
// Master kill-switch, scanner toggle, threshold edit
document.getElementById('logoutBtn').onclick = () => Raksha.Session.logout();

document.getElementById('clearCacheBtn').onclick = () => {
  Raksha.Store.clear();
  alert('Saara cache clear');
};

document.getElementById('thresholdForm').onsubmit = (e) => {
  e.preventDefault();
  Raksha.CONFIG.SIGNAL_THRESHOLDS.CONFIRMED_BUY = [
    +e.target.cb_min.value, +e.target.cb_max.value
  ];
  Raksha.Store.set('config_override', Raksha.CONFIG);
};
</script>
```

---

## 🚀 Deployment Steps

### Frontend (GitHub Pages)
1. `raksha-core.js` ko apne repo ke root mein commit karo
2. Har 7 HTML file ke `<head>` mein **sabse pehla** script tag:
   ```html
   <script src="raksha-core.js"></script>
   ```
3. GitHub Pages enable: Settings → Pages → Source: `main` branch

### Backend (AWS)
```bash
ssh -i arun.pem ubuntu@13.206.70.60
sudo apt update && sudo apt install -y python3-pip nginx
pip3 install fastapi uvicorn websockets httpx pandas numpy kiteconnect

# server.py upload karo
scp -i arun.pem server.py ubuntu@13.206.70.60:~/

# Service banao
sudo nano /etc/systemd/system/raksha.service
# (paste service config below)

sudo systemctl enable raksha
sudo systemctl start raksha

# Security group mein 8080, 8081 open karna mat bhulna
```

### Systemd Service
```ini
[Unit]
Description=Raksha API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8080
Restart=always
Environment="KITE_KEY=your_key_here"

[Install]
WantedBy=multi-user.target
```

---

## ✅ Pending Items (aapki memory se)

1. **All In One Van rebuild** → `Raksha.Scanners.aggregate()` already 5/8 logic implement karta hai. Bas UI mein counter dikhaane wala JS likhna hai.
2. **Trishul SELL bug** → `server.py` mein `scanner_trishul_news()` function complete karna hai, vahin se SELL logic fix hoga.
3. **Trinetra build** → `CONFIG.APP_NAME = 'TRINETRA'` set karke alag repo mein same code, bas brokers list change.

---

## 🎯 Why this design = "smooth without prior, no dummy data"

| Feature | Solution |
|---------|----------|
| Cross-page state | `localStorage` (`Raksha.Store`) - sab pages ek hi state share |
| Cross-tab sync | `BroadcastChannel` - ek tab mein change, sab tabs mein dikhe |
| Live data | WebSocket primary, REST polling fallback |
| No dummy data | Sab kuch real broker API se, frontend mein hardcode kuch nahi |
| Auto-init | Har page sirf `<script src="raksha-core.js">` chahiye |
| Auth gate | `Session.requireAuth()` automatic redirect |
| Scanner pipeline | `Scanners.runAll()` parallel call, aggregate logic built-in |
