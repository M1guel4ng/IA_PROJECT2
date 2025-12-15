const el = (id) => document.getElementById(id);
const setText = (node, txt) => { if (node) node.textContent = txt; };
const setHTML = (node, html) => { if (node) node.innerHTML = html; };

const canvas = el("canvas");
const ctx = canvas?.getContext("2d");
const tooltip = el("tooltip");

const baseUrlInput = el("baseUrl");
const voucherInput = el("voucher");
const algoSelect = el("algo");

const btnReset = el("btnReset");
const btnStep = el("btnStep");
const btnStep10 = el("btnStep10");
const btnPlay = el("btnPlay");
const btnPause = el("btnPause");

const speedRange = el("speed");
const speedLabel = el("speedLabel");
const statusText = el("statusText");

// Tabs
const tabMapBtn = el("tabMapBtn");
const tabCashierBtn = el("tabCashierBtn");
const viewMap = el("viewMap");
const viewCashier = el("viewCashier");
let currentTab = "map";
let autoSwitched = false;

// Sidebar
const stStep = el("stStep");
const stBuyerPos = el("stBuyerPos");
const stVoucher = el("stVoucher");
const stRemaining = el("stRemaining");
const stSpent = el("stSpent");
const stSpentPct = el("stSpentPct");
const stItems = el("stItems");
const stBuyerSteps = el("stBuyerSteps");
const stPaid = el("stPaid");
const stGoal = el("stGoal");
const stAlgo = el("stAlgo");
const logEl = el("log");

// Cashier view
const pillCashierStatus = el("pillCashierStatus");
const pillRegister = el("pillRegister");

const stCashierStatus = el("stCashierStatus");
const stCashierReg = el("stCashierReg");
const stCashierScanned = el("stCashierScanned");
const stCashierSubtotal = el("stCashierSubtotal");
const stCashierRedeemed = el("stCashierRedeemed");
const stCashierRemaining = el("stCashierRemaining");
const stCashierLast = el("stCashierLast");
const stCashierProgressText = el("stCashierProgressText");
const cashierProgressBar = el("cashierProgressBar");

const cashierLog = el("cashierLog");
const cartList = el("cartList");

let state = null;
let playTimer = null;
let cellSize = 18;

function setStatus(msg){ setText(statusText, msg); }

function setTab(tab){
  currentTab = tab;
  viewMap?.classList.toggle("active", tab === "map");
  viewCashier?.classList.toggle("active", tab === "cashier");
  tabMapBtn?.classList.toggle("active", tab === "map");
  tabCashierBtn?.classList.toggle("active", tab === "cashier");
  hideTooltip();
  if (state && tab === "map") render(state);
  if (state && tab === "cashier") updateUI(state);
}

function apiBase(){
  return (baseUrlInput?.value || "http://localhost:8000").replace(/\/$/, "");
}

async function apiGetMap(){
  const r = await fetch(`${apiBase()}/api/map`);
  if (!r.ok) throw new Error(`GET /api/map ${r.status}`);
  return await r.json();
}

async function apiReset(){
  const voucher = Number(voucherInput?.value || 0);
  const algo = algoSelect?.value || "astar";
  const qs = new URLSearchParams({ voucher: String(voucher), algo });
  const r = await fetch(`${apiBase()}/api/reset?${qs}`, { method: "POST" });
  if (!r.ok) throw new Error(`POST /api/reset ${r.status}`);
  return await r.json();
}

async function apiStep(n=1){
  const qs = new URLSearchParams({ n: String(n) });
  const r = await fetch(`${apiBase()}/api/step?${qs}`, { method: "POST" });
  if (!r.ok) throw new Error(`POST /api/step ${r.status}`);
  return await r.json();
}

function resizeCanvasForGrid(grid){
  if (!canvas || !ctx) return;

  const maxW = Math.min(1100, canvas.parentElement.clientWidth - 28);
  const maxH = 700;
  const csW = Math.floor(maxW / grid.width);
  const csH = Math.floor(maxH / grid.height);
  cellSize = Math.max(10, Math.min(24, Math.min(csW, csH)));

  const w = grid.width * cellSize;
  const h = grid.height * cellSize;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function gridToPx(p){ return { x: p.x * cellSize, y: p.y * cellSize }; }
function clear(){ if (ctx && canvas) ctx.clearRect(0,0,canvas.width,canvas.height); }

function drawRect(x,y,w,h,fill,stroke=null){
  if(!ctx) return;
  ctx.fillStyle=fill; ctx.fillRect(x,y,w,h);
  if(stroke){ ctx.strokeStyle=stroke; ctx.strokeRect(x+0.5,y+0.5,w-1,h-1); }
}
function drawCircle(cx,cy,r,fill,stroke=null){
  if(!ctx) return;
  ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.closePath();
  ctx.fillStyle=fill; ctx.fill();
  if(stroke){ ctx.strokeStyle=stroke; ctx.stroke(); }
}
function drawText(txt,x,y,color="rgba(15,23,42,.85)",font="12px ui-monospace"){
  if(!ctx) return;
  ctx.fillStyle=color; ctx.font=font; ctx.fillText(txt,x,y);
}

function fmt(n){ return Number(n||0).toFixed(2); }

function buyerOnQueue(s){
  const b = s?.agents?.buyer;
  if(!b) return false;
  const regs = s.registers || [];
  return regs.some(r => (b.pos.x === r.queue_spot.x && b.pos.y === r.queue_spot.y));
}

function maybeAutoSwitch(s){
  if (autoSwitched) return;
  const cashier = s?.agents?.cashier;
  const b = s?.agents?.buyer;
  if (!cashier || !b) return;

  const activeCashier = cashier.status && cashier.status !== "idle";
  const onQueue = buyerOnQueue(s);

  if (activeCashier || onQueue){
    autoSwitched = true;
    setTab("cashier");
    setStatus("🧾 En caja (auto)");
  }
}

function render(s){
  if(!s) return;
  if (currentTab !== "map"){ updateUI(s); return; }

  const grid = s.grid;
  resizeCanvasForGrid(grid);
  clear();

  // Fondo
  drawRect(0,0,grid.width*cellSize,grid.height*cellSize,"rgba(15,23,42,.02)");

  // Estantes
  for(const sh of s.shelves){
    const x=sh.rect.x*cellSize, y=sh.rect.y*cellSize, w=sh.rect.w*cellSize, h=sh.rect.h*cellSize;
    drawRect(x,y,w,h,"rgba(148,163,184,.55)","rgba(15,23,42,.12)");
  }

  // Entrada/salida
  const en = gridToPx(s.entrance);
  drawRect(en.x,en.y,cellSize,cellSize,"rgba(34,197,94,.65)","rgba(15,23,42,.15)");
  drawText("IN", en.x+4, en.y+14);

  const ex = gridToPx(s.exit);
  drawRect(ex.x,ex.y,cellSize,cellSize,"rgba(239,68,68,.65)","rgba(15,23,42,.15)");
  drawText("OUT", ex.x+1, ex.y+14);

  // Cajas
  for(const r of s.registers){
    const q = gridToPx(r.queue_spot);
    const c = gridToPx(r.cashier_spot);
    drawRect(q.x,q.y,cellSize,cellSize,"rgba(16,185,129,.12)","rgba(16,185,129,.35)");
    drawRect(c.x,c.y,cellSize,cellSize,"rgba(251,113,133,.18)","rgba(251,113,133,.45)");
  }

  // Productos
  const prodPoints = [];
  for(const p of s.products){
    const px = gridToPx(p.pick);
    const cx = px.x + cellSize/2, cy = px.y + cellSize/2;
    drawCircle(cx,cy,Math.max(3,cellSize*0.18),"rgba(245,158,11,.90)","rgba(15,23,42,.20)");
    prodPoints.push({ p, cx, cy, r: Math.max(6, cellSize*0.35) });
  }
  render._prodPoints = prodPoints;

  // Path
  const path = s.agents?.buyer?.path || [];
  if(path.length>1 && ctx){
    ctx.strokeStyle="rgba(59,130,246,.35)";
    ctx.lineWidth=Math.max(2,cellSize*0.12);
    ctx.beginPath();
    const p0=gridToPx(path[0]);
    ctx.moveTo(p0.x+cellSize/2,p0.y+cellSize/2);
    for(let i=1;i<path.length;i++){
      const pi=gridToPx(path[i]);
      ctx.lineTo(pi.x+cellSize/2,pi.y+cellSize/2);
    }
    ctx.stroke();
  }

  // Goal
  const goal = s.agents?.buyer?.goal;
  if(goal){
    const g=gridToPx(goal);
    drawRect(g.x,g.y,cellSize,cellSize,"rgba(16,185,129,.14)","rgba(16,185,129,.55)");
  }

  // Cajero
  const cashier = s.agents?.cashier;
  if(cashier){
    const c = gridToPx(cashier.pos);
    drawRect(c.x+cellSize*0.15,c.y+cellSize*0.15,cellSize*0.7,cellSize*0.7,"rgba(251,113,133,.95)","rgba(15,23,42,.20)");
  }

  // Comprador
  const buyer = s.agents?.buyer;
  if(buyer){
    const b = gridToPx(buyer.pos);
    drawCircle(b.x+cellSize/2,b.y+cellSize/2,Math.max(6,cellSize*0.28),"rgba(59,130,246,.95)","rgba(15,23,42,.20)");
  }

  updateUI(s);
}

function updateCartUI(s){
  const buyer = s?.agents?.buyer;
  if(!buyer){ setHTML(cartList, "—"); return; }

  const prodMap = new Map((s.products||[]).map(p => [p.sku, p]));
  const scannedSet = new Set((s.agents?.cashier?.scanned_skus || []));

  if(!buyer.cart?.length){
    setHTML(cartList, "<div class='tiny'>— vacío —</div>");
    return;
  }

  const rows = buyer.cart.map(sku => {
    const p = prodMap.get(sku);
    const name = p?.name || sku;
    const price = p?.price ?? 0;
    const scanned = scannedSet.has(sku);

    return `
      <div class="row">
        <div class="left">
          <div>
            <span class="sku">${sku}</span>
            <span class="badge ${scanned ? "" : "pending"}">${scanned ? "✅ escaneado" : "⏳ pendiente"}</span>
          </div>
          <div class="name">${name}</div>
        </div>
        <div class="price">${fmt(price)}</div>
      </div>
    `;
  }).join("");

  setHTML(cartList, rows);
}

function updateCashierUI(s){
  const cashier = s?.agents?.cashier;
  const buyer = s?.agents?.buyer;

  if(!cashier){
    setText(pillCashierStatus, "🟦 idle");
    setText(pillRegister, "🏷️ Caja: -");
    setText(stCashierStatus, "-");
    setText(stCashierReg, "-");
    setText(stCashierScanned, "-");
    setText(stCashierSubtotal, "-");
    setText(stCashierRedeemed, "-");
    setText(stCashierRemaining, "-");
    setText(stCashierLast, "-");
    setHTML(cashierLog, "—");
    if (cashierProgressBar) cashierProgressBar.style.width = "0%";
    setText(stCashierProgressText, "-");
    return;
  }

  const status = cashier.status || "idle";
  setText(pillCashierStatus, `🧾 ${status}`);
  setText(pillRegister, `🏷️ Caja: ${cashier.register_id || "-"}`);

  setText(stCashierStatus, status);
  setText(stCashierReg, cashier.register_id || "-");

  const scannedCount = (cashier.scanned_skus || []).length;
  setText(stCashierScanned, String(scannedCount));

  setText(stCashierSubtotal, fmt(cashier.subtotal));
  setText(stCashierRedeemed, fmt(cashier.redeemed_amount));
  setText(stCashierRemaining, fmt(cashier.voucher_remaining));

  if(cashier.last_scan?.event==="scan"){
    setText(stCashierLast, `${cashier.last_scan.sku} (+${fmt(cashier.last_scan.price)})`);
  }else if(cashier.last_scan?.event==="redeem"){
    setText(stCashierLast, `canje (${fmt(cashier.last_scan.redeemed)})`);
  }else{
    setText(stCashierLast, "—");
  }

  const voucher = Number(buyer?.voucher_amount || 0);
  const redeemed = Number(cashier.redeemed_amount || 0);
  const pct = voucher > 0 ? Math.max(0, Math.min(1, redeemed / voucher)) : 0;
  if (cashierProgressBar) cashierProgressBar.style.width = `${Math.round(pct * 100)}%`;
  setText(stCashierProgressText, `${Math.round(pct * 100)}%`);

  const logs = (cashier.scan_log || []).slice(-40);
  if(!logs.length){
    setHTML(cashierLog, "<div class='tiny'>—</div>");
  }else{
    setHTML(cashierLog, logs.map(ev => {
      if(ev.event==="scan"){
        return `
          <div class="item">
            <div class="bullet"></div>
            <div>
              <div class="line1">🛒 SCAN ${ev.sku} • ${ev.name}</div>
              <div class="line2">+${fmt(ev.price)} • subtotal: ${fmt(ev.subtotal)} • step #${ev.world_step}</div>
            </div>
          </div>
        `;
      }
      if(ev.event==="redeem"){
        return `
          <div class="item redeem">
            <div class="bullet"></div>
            <div>
              <div class="line1">✅ CANJE • vale aplicado</div>
              <div class="line2">subtotal: ${fmt(ev.subtotal)} • vale: ${fmt(ev.voucher)} • restante: ${fmt(ev.remaining)} • step #${ev.world_step}</div>
            </div>
          </div>
        `;
      }
      return `
        <div class="item">
          <div class="bullet"></div>
          <div>
            <div class="line1">Evento</div>
            <div class="line2">${JSON.stringify(ev)}</div>
          </div>
        </div>
      `;
    }).join(""));
  }

  updateCartUI(s);
}

function updateUI(s){
  const buyer = s.agents?.buyer;
  setText(stStep, String(s.meta?.step ?? "-"));

  if(buyer){
    const voucher = Number(buyer.voucher_amount||0);
    const remaining = Number(buyer.budget_remaining||0);
    const spent = Math.max(0, voucher-remaining);
    const pct = voucher>0 ? (spent/voucher) : 0;

    setText(stBuyerPos, `(${buyer.pos.x},${buyer.pos.y})`);
    setText(stVoucher, fmt(voucher));
    setText(stRemaining, fmt(remaining));
    setText(stSpent, fmt(spent));
    setText(stSpentPct, `${Math.round(pct*100)}%`);
    setText(stItems, `${buyer.cart.length}/${buyer.selected_skus.length}`);
    setText(stBuyerSteps, String(buyer.steps_moved ?? 0));
    setText(stPaid, buyer.paid ? "sí" : "no");
    setText(stGoal, buyer.goal ? `${buyer.goal_kind} (${buyer.goal.x},${buyer.goal.y})` : buyer.goal_kind);
    setText(stAlgo, buyer.algo);
  }else{
    setText(stBuyerPos, "-");
    setText(stVoucher, "-");
    setText(stRemaining, "-");
    setText(stSpent, "-");
    setText(stSpentPct, "-");
    setText(stItems, "-");
    setText(stBuyerSteps, "-");
    setText(stPaid, "-");
    setText(stGoal, "-");
    setText(stAlgo, "-");
  }

  setText(logEl, (s.messages||[]).length ? (s.messages||[]).join("\n") : "—");

  updateCashierUI(s);
  maybeAutoSwitch(s);
}

function pointDist(ax,ay,bx,by){
  const dx=ax-bx, dy=ay-by;
  return Math.sqrt(dx*dx+dy*dy);
}
function showTooltip(x,y,html){
  if(!tooltip) return;
  tooltip.style.display="block";
  tooltip.style.left=x+"px";
  tooltip.style.top=y+"px";
  tooltip.innerHTML=html;
}
function hideTooltip(){ if(tooltip) tooltip.style.display="none"; }

canvas?.addEventListener("mousemove",(ev)=>{
  if(!state || currentTab!=="map") return;
  const rect=canvas.getBoundingClientRect();
  const mx=ev.clientX-rect.left;
  const my=ev.clientY-rect.top;

  const prodPoints = render._prodPoints || [];
  let found=null;
  for(const it of prodPoints){
    if(pointDist(mx,my,it.cx,it.cy)<=it.r){ found=it.p; break; }
  }

  if(found){
    showTooltip(mx+16,my+16,`
      <div style="font-weight:900;margin-bottom:4px;">${found.name}</div>
      <div><span style="opacity:.75">SKU:</span> ${found.sku}</div>
      <div><span style="opacity:.75">Precio:</span> ${fmt(found.price)}</div>
      <div><span style="opacity:.75">Pick:</span> (${found.pick.x},${found.pick.y})</div>
    `);
  }else hideTooltip();
});
canvas?.addEventListener("mouseleave", hideTooltip);

async function refreshMap(){
  try{
    setStatus("Cargando mapa…");
    state = await apiGetMap();
    render(state);
    setStatus("OK");
  }catch(e){
    console.error(e);
    setStatus("❌ No conecta al backend");
  }
}

async function doReset(){
  stopPlay();
  try{
    setStatus("Reseteando…");
    autoSwitched = false;
    setTab("map");
    state = await apiReset();
    render(state);
    setStatus("OK");
  }catch(e){
    console.error(e);
    setStatus("❌ Error reset");
  }
}

async function doStep(n=1){
  try{
    state = await apiStep(n);
    render(state);

    if(state?.meta?.finished){
      stopPlay();
      setStatus("✅ Finalizado (Reset para reiniciar)");
    }else{
      setStatus("OK");
    }
  }catch(e){
    console.error(e);
    setStatus("❌ Error step");
    stopPlay();
  }
}

function startPlay(){
  if(playTimer) return;
  if(btnPlay) btnPlay.disabled=true;
  if(btnPause) btnPause.disabled=false;
  const interval = Number(speedRange?.value || 200);
  playTimer = setInterval(()=>doStep(1), interval);
}

function stopPlay(){
  if(!playTimer) return;
  clearInterval(playTimer);
  playTimer=null;
  if(btnPlay) btnPlay.disabled=false;
  if(btnPause) btnPause.disabled=true;
}

btnReset?.addEventListener("click", doReset);
btnStep?.addEventListener("click", ()=>doStep(1));
btnStep10?.addEventListener("click", ()=>doStep(10));
btnPlay?.addEventListener("click", startPlay);
btnPause?.addEventListener("click", stopPlay);

tabMapBtn?.addEventListener("click", ()=>setTab("map"));
tabCashierBtn?.addEventListener("click", ()=>setTab("cashier"));

speedRange?.addEventListener("input", ()=>{
  setText(speedLabel, speedRange.value);
  if(playTimer){ stopPlay(); startPlay(); }
});

window.addEventListener("resize", ()=>{ if(state && currentTab==="map") render(state); });

// Init
setText(speedLabel, speedRange?.value || "200");
setTab("map");
refreshMap();
