/* ============================================
   ai-btn.js — Trishul Pro AI Assistant Button
   1_login.html में </body> से पहले add करो:
   <script src="ai-btn.js"></script>
   ============================================ */

(function(){

// ── STYLES ──────────────────────────────────
const css=`
.ai-fab{
  position:fixed;bottom:22px;right:18px;z-index:9999;
  width:52px;height:52px;border-radius:50%;
  background:linear-gradient(135deg,#1a1400,#2a2000);
  border:2px solid #f5c518;color:#f5c518;font-size:22px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 18px rgba(245,197,24,.3),0 4px 12px rgba(0,0,0,.6);
  animation:aiFab 3s ease-in-out infinite;
}
@keyframes aiFab{0%,100%{box-shadow:0 0 18px rgba(245,197,24,.3)}50%{box-shadow:0 0 32px rgba(245,197,24,.65)}}

.ai-ov{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.75);z-index:9998;
}
.ai-ov.on{display:block;}

.ai-dr{
  position:fixed;bottom:0;left:0;right:0;z-index:9999;
  background:#060608;border-top:2px solid rgba(245,197,24,.3);
  border-radius:18px 18px 0 0;height:80vh;max-height:620px;
  display:flex;flex-direction:column;
  transform:translateY(100%);
  transition:transform .38s cubic-bezier(.16,1,.3,1);
}
.ai-dr.on{transform:translateY(0);}
.ai-handle{width:38px;height:4px;background:#333;border-radius:2px;margin:10px auto 0;flex-shrink:0;}

.ai-hd{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px 8px;border-bottom:1px solid #1e1e2e;flex-shrink:0;
}
.ai-hd-l{display:flex;align-items:center;gap:10px;}
.ai-av{
  width:34px;height:34px;border-radius:50%;
  background:linear-gradient(135deg,#f5c518,#c9a000);
  display:flex;align-items:center;justify-content:center;font-size:17px;
}
.ai-ttl{font-size:14px;font-weight:700;color:#f5c518;font-family:'Rajdhani',sans-serif;}
.ai-sub{font-size:10px;color:#555566;}
.ai-badge{
  font-size:9px;padding:2px 9px;
  background:rgba(245,197,24,.1);border:1px solid rgba(245,197,24,.3);
  border-radius:20px;color:#f5c518;letter-spacing:1px;
}
.ai-cls{
  width:28px;height:28px;border-radius:50%;
  background:#1a1a22;border:1px solid #333;color:#888;
  font-size:15px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}

.ai-key{
  display:flex;gap:7px;align-items:center;
  padding:7px 13px;background:#0d0d10;
  border-bottom:1px solid #1e1e2e;flex-shrink:0;
}
.ai-ki{
  flex:1;background:#1a1a22;border:1px solid #2a2a3a;
  border-radius:8px;padding:7px 11px;color:#c8c8d8;
  font-size:11px;font-family:'Courier New',monospace;outline:none;
}
.ai-ki:focus{border-color:#f5c518;}
.ai-ki::placeholder{color:#444;}
.ai-ks{
  padding:7px 12px;background:#f5c518;color:#000;
  border:none;border-radius:8px;font-size:11px;font-weight:700;
  font-family:'Rajdhani',sans-serif;cursor:pointer;white-space:nowrap;
}
.ai-kok{font-size:12px;color:#00c853;display:none;}

.ai-msgs{
  flex:1;overflow-y:auto;padding:11px;
  display:flex;flex-direction:column;gap:9px;
}
.ai-msgs::-webkit-scrollbar{width:3px;}
.ai-msgs::-webkit-scrollbar-thumb{background:#333;border-radius:3px;}

.am{display:flex;gap:6px;align-items:flex-end;}
.am.u{flex-direction:row-reverse;}
.am-av{font-size:15px;flex-shrink:0;}
.am-b{
  max-width:84%;padding:8px 12px;border-radius:13px;
  font-size:13px;line-height:1.5;white-space:pre-wrap;
  font-family:'Rajdhani',sans-serif;
}
.am.b .am-b{background:#1a1a22;border:1px solid #2a2a3a;border-bottom-left-radius:3px;color:#c8c8d8;}
.am.u .am-b{background:linear-gradient(135deg,#1a2800,#243800);border:1px solid #3a5500;border-bottom-right-radius:3px;color:#cce88a;}
.am.e .am-b{background:rgba(255,61,61,.08);border:1px solid rgba(255,61,61,.25);color:#ff8890;border-bottom-left-radius:3px;}

.ai-typ{display:flex;gap:4px;align-items:center;padding:9px 12px;background:#1a1a22;border:1px solid #2a2a3a;border-radius:13px;border-bottom-left-radius:3px;width:fit-content;}
.ai-typ span{width:6px;height:6px;border-radius:50%;background:#f5c518;animation:td .8s ease-in-out infinite;}
.ai-typ span:nth-child(2){animation-delay:.15s;}
.ai-typ span:nth-child(3){animation-delay:.3s;}
@keyframes td{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}

.ai-qk{
  padding:7px 11px;display:flex;gap:6px;
  overflow-x:auto;border-top:1px solid #1e1e2e;
  background:#0d0d12;flex-shrink:0;
}
.ai-qk::-webkit-scrollbar{display:none;}
.aq{
  flex-shrink:0;padding:5px 10px;background:transparent;
  border:1px solid #2a2a3a;border-radius:20px;color:#666;
  font-size:11px;font-family:'Rajdhani',sans-serif;
  cursor:pointer;white-space:nowrap;transition:all .2s;
}
.aq:hover{border-color:#f5c518;color:#f5c518;}

.ai-ir{
  display:flex;gap:8px;padding:10px 12px;
  background:#0d0d12;border-top:1px solid #1e1e2e;flex-shrink:0;
}
.ai-in{
  flex:1;background:#1a1a22;border:1px solid #2a2a3a;
  border-radius:22px;padding:9px 15px;color:#c8c8d8;
  font-size:13px;font-family:'Rajdhani',sans-serif;outline:none;
}
.ai-in:focus{border-color:#f5c518;}
.ai-in::placeholder{color:#444;}
.ai-sd{
  width:40px;height:40px;border-radius:50%;border:none;
  background:#f5c518;color:#000;font-size:15px;
  cursor:pointer;flex-shrink:0;transition:all .2s;
  display:flex;align-items:center;justify-content:center;
}
.ai-sd:hover{background:#c9a000;transform:scale(1.05);}
.ai-sd:disabled{background:#333;color:#555;cursor:default;transform:none;}

/* Angel One Token Alert */
.angel-alert{
  margin:8px 13px;padding:9px 12px;
  background:rgba(255,109,0,.08);border:1px solid rgba(255,109,0,.35);
  border-radius:8px;font-size:11px;color:#ff9944;
  font-family:'Rajdhani',sans-serif;line-height:1.5;
  display:none;flex-shrink:0;
}
.angel-alert.show{display:block;}
.angel-alert strong{color:#f5c518;}
`;
const st=document.createElement('style');
st.textContent=css;
document.head.appendChild(st);

// ── HTML ────────────────────────────────────
const html=`
<button class="ai-fab" onclick="aiTog()" title="AI Assistant">🤖</button>
<div class="ai-ov" id="aiOv" onclick="aiCls()"></div>
<div class="ai-dr" id="aiDr">
  <div class="ai-handle"></div>
  <div class="ai-hd">
    <div class="ai-hd-l">
      <div class="ai-av">🤖</div>
      <div>
        <div class="ai-ttl">Trading AI Assistant</div>
        <div class="ai-sub">Angel One · Dhan · Token Help · 24/7</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:8px">
      <span class="ai-badge">CLAUDE AI</span>
      <button class="ai-cls" onclick="aiCls()">✕</button>
    </div>
  </div>

  <div class="angel-alert" id="angelAlert">
    ⚠️ <strong>Angel One Token:</strong> रोज़ midnight पर expire होता है।
    सुबह आकर <strong>BROKER → Angel One → GET TOKEN</strong> दबाओ।
    IP <strong>13.232.74.202</strong> whitelist होना ज़रूरी है।
  </div>

  <div class="ai-key">
    <input class="ai-ki" id="aiKi" type="password" placeholder="Anthropic API Key: sk-ant-api03-..."/>
    <button class="ai-ks" onclick="aiSvK()">💾</button>
    <span class="ai-kok" id="aiKok">✅</span>
  </div>

  <div class="ai-msgs" id="aiMs">
    <div class="am b">
      <span class="am-av">🤖</span>
      <div class="am-b">Namaste Charan ji! 🙏

Main Trading AI hoon. Pooch sakte ho:
✅ Angel One token problem
✅ Dhan connection issue
✅ Broker setup help
✅ Koi bhi trading error

Pehle upar API key save karo! 🚀</div>
    </div>
  </div>

  <div class="ai-qk">
    <button class="aq" onclick="aiQ('Angel One token expire ho gaya kya karu')">🟡 Angel Token</button>
    <button class="aq" onclick="aiQ('Dhan connected hai kya check karo')">🔵 Dhan Status</button>
    <button class="aq" onclick="aiQ('Network error aa raha hai fix karo')">⚠️ Network Error</button>
    <button class="aq" onclick="aiQ('Broker reconnect kaise karu')">🔄 Reconnect</button>
    <button class="aq" onclick="aiQ('IP whitelist kaise karte hain 13.232.74.202')">🌐 IP Whitelist</button>
  </div>

  <div class="ai-ir">
    <input class="ai-in" id="aiIn" placeholder="Kuch bhi poochein..."
      onkeydown="if(event.key==='Enter')aiSnd()"/>
    <button class="ai-sd" id="aiSd" onclick="aiSnd()">➤</button>
  </div>
</div>`;

document.body.insertAdjacentHTML('beforeend',html);

// ── LOGIC ───────────────────────────────────
const SYS=`You are a trading assistant for Trishul Pro (Indian stock trading app).
User: Charan Puransinh Ranjitsinh
Angel One Client ID: C116947 | Dhan Client ID: 1111293264
Server IP: 13.232.74.202 | App: trishul-pro-znss.vercel.app

ANGEL ONE TOKEN PROBLEM:
- Token expires every midnight (12 AM IST)
- Fix: Go to BROKER tab → Select Angel One → Click GET TOKEN
- TOTP secret must be correctly entered for auto-generation
- IP 13.232.74.202 must be whitelisted in Angel One SmartAPI settings
- If token fails: login to angelone.in → My Profile → API → Whitelist IP → then GET TOKEN again

DHAN PROBLEM:
- Access token from dhanhq.co dashboard
- More stable than Angel One, lasts longer
- Vendor code: DNNV38291K

NETWORK ERROR:
- Check internet connection
- Disable VPN if active
- Try Chrome browser
- Check if server 13.232.74.202 is running

Always respond in Hinglish (Hindi+English). Be friendly, use emojis. Keep it short and actionable.`;

let _k=localStorage.getItem('tri_ai_k')||'';
let _ms=[];
let _open=false;

// Check Angel One token time on load
(function(){
  if(_k){
    document.getElementById('aiKi').value=_k;
    document.getElementById('aiKok').style.display='inline';
  }
  // Show Angel One alert if time is near midnight (11 PM to 1 AM)
  const h=new Date().getHours();
  if(h>=23||h<=1){
    document.getElementById('angelAlert').classList.add('show');
  }
})();

window.aiTog=function(){_open?aiCls():aiOpn();}
window.aiOpn=function(){
  _open=true;
  document.getElementById('aiOv').classList.add('on');
  document.getElementById('aiDr').classList.add('on');
}
window.aiCls=function(){
  _open=false;
  document.getElementById('aiOv').classList.remove('on');
  document.getElementById('aiDr').classList.remove('on');
}

window.aiSvK=function(){
  const k=document.getElementById('aiKi').value.trim();
  if(k.length<10)return;
  _k=k;
  localStorage.setItem('tri_ai_k',k);
  document.getElementById('aiKok').style.display='inline';
  _add('b','✅ API Key save ho gayi!\n\nAb pooch sakte ho kuch bhi. Angel One problem bhi solve kar sakta hoon! 😊');
}

window.aiQ=function(t){_chat(t);}
window.aiSnd=function(){
  const i=document.getElementById('aiIn');
  const t=i.value.trim();if(!t)return;
  i.value='';_chat(t);
}

function _add(role,text,isErr){
  if(role!=='sys')_ms.push({role:role==='u'?'user':'assistant',content:text});
  const box=document.getElementById('aiMs');
  const d=document.createElement('div');
  d.className=`am ${role==='u'?'u':isErr?'e':'b'}`;
  d.innerHTML=`<span class="am-av">${role==='u'?'👤':'🤖'}</span><div class="am-b">${text.replace(/\n/g,'<br>')}</div>`;
  box.appendChild(d);
  box.scrollTop=box.scrollHeight;
}
function _showT(){
  const box=document.getElementById('aiMs');
  const d=document.createElement('div');
  d.className='am b';d.id='ait';
  d.innerHTML=`<span class="am-av">🤖</span><div class="ai-typ"><span></span><span></span><span></span></div>`;
  box.appendChild(d);box.scrollTop=box.scrollHeight;
}
function _hideT(){const t=document.getElementById('ait');if(t)t.remove();}

async function _chat(text){
  if(!_k){
    aiOpn();
    _add('b','⚠️ Pehle API key enter karo!\n\nconsole.anthropic.com/settings/keys\nse free key milti hai 🙏',true);
    document.getElementById('aiKi').focus();
    return;
  }
  document.getElementById('aiSd').disabled=true;
  _add('u',text);
  _showT();

  const msgs=[
    ..._ms.slice(-8,-1),
    {role:'user',content:`Context: Angel One C116947 midnight token expiry | Dhan 1111293264 | Server 13.232.74.202\nQuery: ${text}`}
  ];

  try{
    const res=await fetch('https://api.anthropic.com/v1/messages',{
      method:'POST',
      headers:{
        'Content-Type':'application/json',
        'x-api-key':_k,
        'anthropic-version':'2023-06-01',
        'anthropic-dangerous-direct-browser-calls':'true'
      },
      body:JSON.stringify({
        model:'claude-haiku-4-5-20251001',
        max_tokens:600,
        system:SYS,
        messages:msgs
      })
    });
    if(!res.ok){
      const e=await res.json().catch(()=>({}));
      _hideT();
      if(res.status===401)_add('b','❌ API Key galat hai!\nconsole.anthropic.com se sahi key lo.',true);
      else if(res.status===429)_add('b','⏳ Rate limit. Thoda ruko phir try karo.',true);
      else _add('b',`⚠️ Error ${res.status}: ${e.error?.message||'Unknown'}`,true);
    } else {
      const d=await res.json();
      _hideT();
      _add('b',d.content?.map(x=>x.text||'').join('')||'Dobara try karein.');
    }
  }catch(e){
    _hideT();
    _add('b',`⚠️ Network Error!\n\n1️⃣ Internet check karo\n2️⃣ VPN band karo\n3️⃣ Chrome use karo\n\nError: ${e.message}`,true);
  }
  document.getElementById('aiSd').disabled=false;
}

})();
