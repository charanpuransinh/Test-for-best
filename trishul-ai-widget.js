/**
 * 🔱 TRISHUL PRO — GEMINI AI DIAGNOSTIC WIDGET
 * File naam: trishul-ai-widget.js
 * Kahan daalein: GitHub repo ke ROOT folder mein (1_login.html ke saath waali jagah)
 *
 * Kisi bhi HTML page mein add karne ke liye </body> se pehle yeh line daalo:
 * <script src="trishul-ai-widget.js"></script>
 */

(function () {
  'use strict';

  const SYSTEM_INSTRUCTION = `You are TRISHUL AI — Trishul Pro trading app ka expert diagnostic assistant.

App Details:
- App Name: Trishul Pro
- URL: trishul-pro-znss.vercel.app
- Stack: Pure HTML, CSS, JavaScript — Vercel pe hosted
- GitHub: charanpuransinh/Trishul--pro
- Brokers: Angel One (SmartAPI), Shoonya, Zerodha, Upstox, Kotak, ICICI, HDFC, Dhan, Motilal, Groww
- Features: Live price feed, Scanner, PowerBox, T1/T2/T3/TSL targets, Signal strength, TOTP login, Combo Engine

Known Problems:
1. Angel One "Connected" dikhata hai lekin prices update nahi ho rahi
2. Dummy/hardcoded data prices mein stuck ho gaya
3. WebSocket reconnect nahi ho raha
4. SmartAPI token har roz midnight IST pe expire hota hai
5. App ek mahine se theek kaam nahi kar rahi

Angel One SmartAPI Key Info:
- Login: POST https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword
- WebSocket: wss://smartapisocket.angelone.in/smart-stream
- Token daily refresh zaroori — midnight IST pe expire
- Browser se direct API call CORS block hoti hai — Vercel serverless function chahiye
- Required headers: X-UserType, X-SourceID, X-ClientLocalIP, X-ClientPublicIP, X-MACAddress, X-PrivateKey

Tumhara kaam:
- Problem sun ke root cause dhundo
- Specific code fix batao jab possible ho
- Hinglish mein baat karo (Hindi + English mix)
- Direct raho, time waste mat karo`;

  // ── CSS ────────────────────────────────────────────────────────────────────
  const styleEl = document.createElement('style');
  styleEl.textContent = `
    #tai-fab {
      position: fixed; top: 16px; left: 16px;
      z-index: 2147483647;
    }
    #tai-btn {
      display: flex; align-items: center; gap: 8px;
      background: linear-gradient(135deg, #0d1b3e 0%, #1a237e 100%);
      border: 1.5px solid rgba(100,180,255,0.5);
      border-radius: 50px; padding: 8px 14px 8px 9px;
      cursor: pointer;
      box-shadow: 0 4px 24px rgba(66,133,244,0.4);
      transition: all 0.25s ease;
      animation: taiFabPulse 3s ease-in-out infinite;
    }
    #tai-btn:hover { transform: scale(1.06); box-shadow: 0 6px 32px rgba(66,133,244,0.6); }
    @keyframes taiFabPulse {
      0%,100% { box-shadow: 0 4px 24px rgba(66,133,244,0.4); }
      50% { box-shadow: 0 4px 24px rgba(66,133,244,0.4), 0 0 0 7px rgba(66,133,244,0.07); }
    }
    .tai-gem-logo { width: 26px; height: 26px; flex-shrink: 0; }
    .tai-fab-label { display: flex; flex-direction: column; line-height: 1.15; }
    .tai-fab-label .tai-top { font-size: 9.5px; font-weight: 700; color: #90caf9; letter-spacing: 1.2px; text-transform: uppercase; font-family: 'Courier New', monospace; }
    .tai-fab-label .tai-bot { font-size: 11.5px; font-weight: 600; color: #fff; font-family: -apple-system, sans-serif; }
    .tai-dot { width: 7px; height: 7px; border-radius: 50%; background: #00e676; flex-shrink: 0; animation: taiBlink 2s ease-in-out infinite; }
    @keyframes taiBlink { 0%,100%{opacity:1;} 50%{opacity:0.2;} }

    #tai-panel {
      display: none; position: fixed; inset: 0;
      z-index: 2147483646; flex-direction: column;
      background: #080810; font-family: -apple-system, 'Segoe UI', sans-serif;
    }
    #tai-panel.tai-open { display: flex; animation: taiSlide 0.28s ease; }
    @keyframes taiSlide { from{transform:translateY(20px);opacity:0;} to{transform:translateY(0);opacity:1;} }

    .tai-header {
      background: linear-gradient(135deg, #0d1b3e, #1a237e);
      border-bottom: 1px solid rgba(100,180,255,0.2);
      padding: 13px 15px; display: flex; align-items: center; gap: 10px; flex-shrink: 0;
    }
    .tai-header-text { flex: 1; }
    .tai-header-title { font-size: 15px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 6px; }
    .tai-header-sub { font-size: 10.5px; color: #90caf9; margin-top: 2px; }
    .tai-close {
      background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
      color: #fff; width: 34px; height: 34px; border-radius: 50%;
      cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: background 0.2s;
    }
    .tai-close:hover { background: rgba(255,255,255,0.15); }

    #tai-key-bar {
      background: rgba(255,152,0,0.1); border-bottom: 1px solid rgba(255,152,0,0.3);
      padding: 9px 14px; display: flex; gap: 8px; align-items: center; flex-shrink: 0; transition: all 0.3s;
    }
    #tai-key-bar.tai-saved { background: rgba(0,230,118,0.07); border-bottom-color: rgba(0,230,118,0.2); }
    #tai-key-input {
      flex: 1; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,152,0,0.4);
      border-radius: 8px; color: #fff; padding: 7px 10px;
      font-size: 12px; font-family: 'Courier New', monospace; outline: none; transition: border-color 0.2s;
    }
    #tai-key-input:focus { border-color: rgba(255,152,0,0.8); }
    #tai-key-input::placeholder { color: rgba(255,255,255,0.25); font-size: 11px; }
    #tai-key-save {
      background: #E65100; border: none; border-radius: 8px;
      color: #fff; font-weight: 700; font-size: 12px;
      padding: 7px 13px; cursor: pointer; white-space: nowrap; transition: background 0.2s;
    }
    #tai-key-save:hover { background: #FF6D00; }

    #tai-msgs {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 11px;
    }
    #tai-msgs::-webkit-scrollbar { width: 3px; }
    #tai-msgs::-webkit-scrollbar-thumb { background: rgba(100,180,255,0.25); border-radius: 2px; }

    .tai-msg { max-width: 87%; padding: 10px 13px; border-radius: 16px; font-size: 13.5px; line-height: 1.55; word-break: break-word; }
    .tai-msg.user { align-self: flex-end; background: linear-gradient(135deg,#bf360c,#E64A19); color:#fff; border-bottom-right-radius:4px; }
    .tai-msg.ai { align-self: flex-start; background: #12121f; border: 1px solid rgba(100,180,255,0.18); color: #dde; border-bottom-left-radius: 4px; }
    .tai-msg.ai .tai-sender { font-size: 9.5px; font-weight: 700; color: #90caf9; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 5px; }
    .tai-msg.sys { align-self: center; background: rgba(255,214,0,0.07); border: 1px solid rgba(255,214,0,0.2); color: #FFD600; font-size: 11.5px; border-radius: 20px; padding: 5px 14px; text-align: center; max-width: 95%; }

    .tai-typing { align-self: flex-start; background: #12121f; border: 1px solid rgba(100,180,255,0.18); border-radius: 16px; border-bottom-left-radius: 4px; padding: 13px 16px; display: flex; gap: 5px; align-items: center; }
    .tai-td { width: 7px; height: 7px; border-radius: 50%; background: #90caf9; animation: taiTyping 1.2s ease-in-out infinite; }
    .tai-td:nth-child(2){animation-delay:.2s;} .tai-td:nth-child(3){animation-delay:.4s;}
    @keyframes taiTyping { 0%,60%,100%{transform:translateY(0);opacity:0.3;} 30%{transform:translateY(-6px);opacity:1;} }

    #tai-chips {
      display: flex; gap: 6px; flex-wrap: nowrap; overflow-x: auto;
      padding: 0 14px 10px; flex-shrink: 0;
    }
    #tai-chips::-webkit-scrollbar { display: none; }
    .tai-chip {
      background: rgba(66,133,244,0.1); border: 1px solid rgba(66,133,244,0.28);
      border-radius: 20px; color: #90caf9; font-size: 11px;
      padding: 5px 12px; cursor: pointer; white-space: nowrap; flex-shrink: 0; transition: all 0.2s;
    }
    .tai-chip:hover { background: rgba(66,133,244,0.22); color: #fff; }

    #tai-input-area {
      border-top: 1px solid rgba(100,180,255,0.12); padding: 11px 14px;
      display: flex; gap: 9px; align-items: flex-end;
      background: #0e0e1a; flex-shrink: 0;
    }
    #tai-input {
      flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(100,180,255,0.22);
      border-radius: 13px; color: #fff; font-size: 14px; font-family: inherit;
      padding: 10px 13px; resize: none; outline: none;
      min-height: 42px; max-height: 110px; line-height: 1.45; transition: border-color 0.2s;
    }
    #tai-input:focus { border-color: rgba(100,180,255,0.55); }
    #tai-input::placeholder { color: rgba(255,255,255,0.22); }
    #tai-send {
      width: 42px; height: 42px; border-radius: 12px;
      background: linear-gradient(135deg,#1565C0,#1E88E5);
      border: none; color: #fff; font-size: 17px; cursor: pointer; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.15s, opacity 0.2s;
      box-shadow: 0 3px 12px rgba(30,136,229,0.4);
    }
    #tai-send:active { transform: scale(0.88); }
    #tai-send:disabled { opacity: 0.35; cursor: not-allowed; }
  `;
  document.head.appendChild(styleEl);

  // ── SVG ────────────────────────────────────────────────────────────────────
  const gemSVG = `<svg class="tai-gem-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="taiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#4285F4"/>
        <stop offset="50%" stop-color="#9C6FD6"/>
        <stop offset="100%" stop-color="#EA4335"/>
      </linearGradient>
    </defs>
    <path d="M16 2C16 10 10 16 2 16C10 16 16 22 16 30C16 22 22 16 30 16C22 16 16 10 16 2Z" fill="url(#taiGrad)"/>
  </svg>`;

  // ── FAB ────────────────────────────────────────────────────────────────────
  const fabEl = document.createElement('div');
  fabEl.id = 'tai-fab';
  fabEl.innerHTML = `
    <button id="tai-btn" title="Gemini AI Diagnostic">
      ${gemSVG}
      <div class="tai-fab-label">
        <span class="tai-top">Gemini AI</span>
        <span class="tai-bot">Diagnostic</span>
      </div>
      <div class="tai-dot"></div>
    </button>`;
  document.body.appendChild(fabEl);

  // ── Panel ──────────────────────────────────────────────────────────────────
  const panelEl = document.createElement('div');
  panelEl.id = 'tai-panel';
  panelEl.innerHTML = `
    <div class="tai-header">
      ${gemSVG}
      <div class="tai-header-text">
        <div class="tai-header-title">🔱 TRISHUL AI <div class="tai-dot" style="width:8px;height:8px;margin-left:4px;"></div></div>
        <div class="tai-header-sub">Gemini 2.0 Flash · Trishul App Diagnostics · Hinglish</div>
      </div>
      <button class="tai-close" id="tai-close">✕</button>
    </div>

    <div id="tai-key-bar">
      <input type="password" id="tai-key-input" placeholder="Gemini API Key — aistudio.google.com se bilkul FREE milti hai" autocomplete="off"/>
      <button id="tai-key-save">SAVE</button>
    </div>

    <div id="tai-msgs"></div>

    <div id="tai-chips">
      <div class="tai-chip" data-q="Angel One connect nahi ho raha, kya problem hai?">🔴 Angel One issue</div>
      <div class="tai-chip" data-q="Price update nahi ho rahi aur dummy data stuck lag raha hai, diagnose karo">📊 Price stuck</div>
      <div class="tai-chip" data-q="Poori app ka diagnostic karo, sab problems batao">🔍 Full Diagnostic</div>
      <div class="tai-chip" data-q="WebSocket connection kyun toot raha hai aur fix kaise karein?">🔌 WebSocket fix</div>
      <div class="tai-chip" data-q="Angel One SmartAPI token daily midnight expire hota hai, auto-refresh kaise karein?">🔑 Token refresh</div>
    </div>

    <div id="tai-input-area">
      <textarea id="tai-input" placeholder="Problem batao... Hindi ya English dono chalega" rows="1"></textarea>
      <button id="tai-send">➤</button>
    </div>`;
  document.body.appendChild(panelEl);

  // ── State ──────────────────────────────────────────────────────────────────
  let apiKey = localStorage.getItem('trishul_gem_key') || '';
  let chatHistory = [];
  let busy = false;

  const msgsEl   = document.getElementById('tai-msgs');
  const inputEl  = document.getElementById('tai-input');
  const sendEl   = document.getElementById('tai-send');
  const keyInput = document.getElementById('tai-key-input');
  const keyBar   = document.getElementById('tai-key-bar');
  const keySave  = document.getElementById('tai-key-save');

  if (apiKey) {
    keyInput.value = apiKey;
    keyBar.classList.add('tai-saved');
    keySave.textContent = '✓ SAVED';
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function esc(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function addMsg(role, text) {
    const d = document.createElement('div');
    d.className = 'tai-msg ' + role;
    if (role === 'ai') {
      d.innerHTML = `<div class="tai-sender">🔱 Trishul AI · Gemini</div>${esc(text).replace(/\n/g,'<br>')}`;
    } else {
      d.textContent = text;
    }
    msgsEl.appendChild(d);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function showTyping() {
    if (document.getElementById('tai-typing')) return;
    const d = document.createElement('div');
    d.className = 'tai-typing'; d.id = 'tai-typing';
    d.innerHTML = '<div class="tai-td"></div><div class="tai-td"></div><div class="tai-td"></div>';
    msgsEl.appendChild(d);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function hideTyping() { const d = document.getElementById('tai-typing'); if (d) d.remove(); }

  // ── Gemini API ─────────────────────────────────────────────────────────────
  async function askGemini(userMsg) {
    if (!apiKey) {
      addMsg('sys', '⚠️ Pehle Gemini API Key save karo — upar wale bar mein paste karo');
      return;
    }
    if (busy) return;
    busy = true;
    sendEl.disabled = true;

    chatHistory.push({ role: 'user', parts: [{ text: userMsg }] });
    addMsg('user', userMsg);
    showTyping();

    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            system_instruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
            contents: chatHistory,
            generationConfig: { temperature: 0.7, maxOutputTokens: 1200 }
          })
        }
      );

      const data = await res.json();

      if (!res.ok) {
        hideTyping();
        const errMsg = data?.error?.message || 'Unknown API error';
        addMsg('sys', '❌ Gemini Error: ' + errMsg + (errMsg.includes('API_KEY') ? ' — API Key galat hai, check karo' : ''));
        chatHistory.pop();
      } else {
        const reply = data.candidates?.[0]?.content?.parts?.[0]?.text || '(Koi response nahi mila)';
        hideTyping();
        addMsg('ai', reply);
        chatHistory.push({ role: 'model', parts: [{ text: reply }] });
      }
    } catch (e) {
      hideTyping();
      addMsg('sys', '❌ Network Error: ' + e.message);
      chatHistory.pop();
    }

    busy = false;
    sendEl.disabled = false;
    inputEl.focus();
  }

  // ── Event Listeners ────────────────────────────────────────────────────────
  document.getElementById('tai-btn').addEventListener('click', () => {
    panelEl.classList.add('tai-open');
    if (chatHistory.length === 0) {
      addMsg('ai', 'Namaste! 🔱 Main hoon TRISHUL AI — Gemini 2.0 se powered.\n\nAapki Trishul Pro app mein kya problem aa rahi hai?\n\n• Angel One connect nahi ho raha?\n• Prices update nahi ho rahi?\n• Koi aur issue?\n\nBatao — main diagnose karta hoon!');
    }
    setTimeout(() => inputEl.focus(), 350);
  });

  document.getElementById('tai-close').addEventListener('click', () => {
    panelEl.classList.remove('tai-open');
  });

  keySave.addEventListener('click', () => {
    const k = keyInput.value.trim();
    if (!k) { addMsg('sys', '⚠️ API Key khali hai — paste karo pehle'); return; }
    apiKey = k;
    localStorage.setItem('trishul_gem_key', k);
    keyBar.classList.add('tai-saved');
    keySave.textContent = '✓ SAVED';
    addMsg('sys', '✅ Gemini API Key save ho gayi! Ab kuch bhi poochho.');
  });

  document.getElementById('tai-send').addEventListener('click', send);

  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 110) + 'px';
  });

  document.querySelectorAll('.tai-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      panelEl.classList.add('tai-open');
      askGemini(chip.getAttribute('data-q'));
    });
  });

  function send() {
    const msg = inputEl.value.trim();
    if (!msg || busy) return;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    askGemini(msg);
  }

})();
                                
