const el = (id) => document.getElementById(id);
const setText = (node, txt) => { if (node) node.textContent = txt; };
const setHTML = (node, html) => { if (node) node.innerHTML = html; };


// ---- Persistencia (localStorage) ----
const LS = {
  API_BASE: "sm_api_base",
  BRANCH_ID: "sm_branch_id",
  BRANCH_NAME: "sm_branch_name",
  BRANCH_CITY: "sm_branch_city",
};

function getBranchId(){
  return localStorage.getItem(LS.BRANCH_ID) || "";
}

function setBranchLabel(){
  const elSub = document.getElementById("branchSubtitle");
  if(!elSub) return;

  const id = getBranchId();
  const name = localStorage.getItem(LS.BRANCH_NAME);
  const city = localStorage.getItem(LS.BRANCH_CITY);

  const label = name
    ? `${name}${city ? " • " + city : ""}`
    : (id ? id : "—");

  elSub.textContent = `Sucursal: ${label}`;
}

const canvas = el("canvas");
const ctx = canvas?.getContext("2d");
const tooltip = el("tooltip");

const baseUrlInput = el("baseUrl");
const voucherInput = el("voucher");
const algoSelect = el("algo");

const btnBranch = el("btnBranch");
const btnReset = el("btnReset");
const btnStep = el("btnStep");
const btnStep10 = el("btnStep10");
const btnPlay = el("btnPlay");
const btnPause = el("btnPause");

const speedRange = el("speed");
const speedLabel = el("speedLabel");

const tabMapBtn = el("tabMapBtn");
const tabCashierBtn = el("tabCashierBtn");
const viewMap = el("viewMap");
const viewCashier = el("viewCashier");

const statusText = el("statusText");

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

// ✅ NUEVO (vista mapa)
const buyProgressText = el("buyProgressText");
const buyProgressBar = el("buyProgressBar");
const buyVoucher = el("buyVoucher");
const buySpent = el("buySpent");
const buyRemain = el("buyRemain");
const buyItems = el("buyItems");
const mapCartBox = el("mapCartBox");

let state = null;
let playTimer = null;
let cellSize = 18;
let currentTab = "map";

function setStatus(msg){ setText(statusText, msg); }

function setTab(tab){
  currentTab = tab;
  const isMap = tab === "map";
  tabMapBtn?.classList.toggle("active", isMap);
  tabCashierBtn?.classList.toggle("active", !isMap);
  viewMap?.classList.toggle("active", isMap);
  viewCashier?.classList.toggle("active", !isMap);
  if (state){
    if (isMap) render(state);
    if (!isMap) updateCashierUI(state);
  }
}

function apiBase(){
  return (baseUrlInput?.value || localStorage.getItem(LS.API_BASE) || "http://localhost:8000").replace(/\/$/, "");
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
  const branchId = getBranchId();
  if(branchId) qs.set("map_id", branchId);
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
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function gridToPx(p){
  return { x: p.x * cellSize, y: p.y * cellSize };
}

function drawRect(x,y,w,h,fill,stroke){
  if (!ctx) return;
  ctx.fillStyle = fill;
  ctx.fillRect(x,y,w,h);
  if (stroke){
    ctx.strokeStyle = stroke;
    ctx.strokeRect(x+.5,y+.5,w-1,h-1);
  }
}

function drawCircle(cx,cy,r,fill,stroke){
  if (!ctx) return;
  ctx.beginPath();
  ctx.arc(cx,cy,r,0,Math.PI*2);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  if(stroke){
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
}

function drawText(txt, x, y){
  if (!ctx) return;
  ctx.fillStyle="rgba(15,23,42,.78)";
  ctx.font = `bold ${Math.max(10, cellSize*0.55)}px ui-sans-serif, system-ui`;
  ctx.fillText(txt, x, y);
}

// ---- Tooltip helpers (FIX hover) ----
function fmt(n){
  const v = Number(n);
  if (Number.isNaN(v)) return "0.00";
  return v.toFixed(2);
}

function hideTooltip(){
  if(!tooltip) return;
  tooltip.style.display="none";
}

function showTooltipAtMouse(ev, html){
  if(!tooltip || !canvas) return;

  const stage = canvas.parentElement;
  const srect = stage.getBoundingClientRect();

  const left = (ev.clientX - srect.left) + 16;
  const top  = (ev.clientY - srect.top) + 16;

  tooltip.style.display = "block";
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
  tooltip.innerHTML = html;
}

function getCanvasPosFromMouse(ev){
  if(!canvas) return { x: 0, y: 0 };
  const rect = canvas.getBoundingClientRect();
  return { x: (ev.clientX - rect.left), y: (ev.clientY - rect.top) };
}

/** Formatea eventos del cajero */
function formatCashierEvent(ev){
  if(!ev) return "-";
  if(typeof ev === "string") return ev;

  if(ev.event === "scan"){
    const price = (Number(ev.price)||0).toFixed(2);
    const sub = (Number(ev.subtotal)||0).toFixed(2);
    return `🧾 Scan ${ev.sku} • ${ev.name} (+${price}) subtotal=${sub}`;
  }

  if(ev.event === "redeem"){
    const sub = (Number(ev.subtotal)||0).toFixed(2);
    const v = (Number(ev.voucher)||0).toFixed(2);
    const red = (Number(ev.redeemed)||0).toFixed(2);
    const ch = (Number(ev.change_given)||0).toFixed(2);
    return `✅ Pago subtotal=${sub} vale=${v} canjeado=${red} cambio=${ch}`;
  }

  try { return JSON.stringify(ev); } catch { return String(ev); }
}

/** ✅ NUEVO: genera un index sku->producto para el carrito visible */
function buildProductIndex(s){
  const idx = new Map();
  for(const p of (s.products || [])){
    idx.set(p.sku, p);
  }
  return idx;
}

/** ✅ NUEVO: pinta el carrito en la vista mapa + progreso */
function updateMapPurchaseUI(s){
  const buyer = s.agents?.buyer;
  if(!buyer) return;

  const voucher = Number(buyer.voucher_amount ?? 0);
  const remaining = Number(buyer.budget_remaining ?? 0);
  const spent = Math.max(0, voucher - remaining);

  // progreso (gastado/vale)
  const pct = voucher > 0 ? Math.min(100, Math.round((spent / voucher) * 100)) : 0;

  setText(buyVoucher, voucher.toFixed(2));
  setText(buySpent, spent.toFixed(2));
  setText(buyRemain, remaining.toFixed(2));
  setText(buyItems, String((buyer.cart || []).length));

  setText(buyProgressText, `${pct}% (${spent.toFixed(2)}/${voucher.toFixed(2)})`);
  if(buyProgressBar) buyProgressBar.style.width = `${pct}%`;

  // carrito detallado
  const idx = buildProductIndex(s);
  const cart = buyer.cart || [];

  if(!mapCartBox) return;

  if(!cart.length){
    setHTML(mapCartBox, "—");
    return;
  }

  let total = 0;
  const rows = cart.map((sku)=>{
    const p = idx.get(sku);
    const name = p?.name || sku;
    const price = Number(p?.price ?? 0);
    total += price;

    return `
      <div class="cartRow">
        <div>
          <div class="cartName">${name}</div>
          <div class="cartSku">${sku}</div>
        </div>
        <div class="cartPrice">Bs ${price.toFixed(2)}</div>
      </div>
    `;
  }).join("");

  const footer = `
    <div class="cartRow" style="border-top:1px solid rgba(148,163,184,.18);border-bottom:none">
      <div style="font-weight:800">TOTAL</div>
      <div class="cartPrice" style="font-weight:900">Bs ${total.toFixed(2)}</div>
    </div>
  `;

  setHTML(mapCartBox, rows + footer);
}

function render(s){
  if(!s || !ctx || !canvas) return;

  const grid = s.grid;
  resizeCanvasForGrid(grid);

  ctx.clearRect(0,0,grid.width*cellSize,grid.height*cellSize);

  for(let y=0;y<grid.height;y++){
    for(let x=0;x<grid.width;x++){
      const px = x*cellSize, py = y*cellSize;
      drawRect(px,py,cellSize,cellSize,"rgba(148,163,184,.08)","rgba(15,23,42,.05)");
    }
  }

  for(const sh of s.shelves){
    const r = sh.rect;
    const px = r.x * cellSize;
    const py = r.y * cellSize;
    drawRect(px,py,r.w*cellSize,r.h*cellSize,"rgba(148,163,184,.20)","rgba(15,23,42,.18)");
    drawText(sh.id, px+4, py+Math.max(12, cellSize));
  }

  const en = gridToPx(s.entrance);
  drawRect(en.x,en.y,cellSize,cellSize,"rgba(34,197,94,.55)","rgba(15,23,42,.15)");
  drawText("IN", en.x+4, en.y+Math.max(12, cellSize));

  const ex = gridToPx(s.exit);
  drawRect(ex.x,ex.y,cellSize,cellSize,"rgba(239,68,68,.65)","rgba(15,23,42,.15)");
  drawText("OUT", ex.x+1, ex.y+Math.max(12, cellSize));

  for(const r of s.registers){
    const q = gridToPx(r.queue_spot);
    const c = gridToPx(r.cashier_spot);
    drawRect(q.x,q.y,cellSize,cellSize,"rgba(16,185,129,.12)","rgba(16,185,129,.35)");
    drawRect(c.x,c.y,cellSize,cellSize,"rgba(251,113,133,.18)","rgba(251,113,133,.45)");
  }

  // Products hover index por celda
  const prodByCell = new Map();
  for(const p of s.products){
    prodByCell.set(`${p.pick.x},${p.pick.y}`, p);

    const px = gridToPx(p.pick);
    const cx = px.x + cellSize/2, cy = px.y + cellSize/2;
    drawCircle(cx,cy,Math.max(3,cellSize*0.18),"rgba(245,158,11,.90)","rgba(15,23,42,.20)");
  }
  render._prodByCell = prodByCell;

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

  const goal = s.agents?.buyer?.goal;
  if(goal){
    const gp=gridToPx(goal);
    drawRect(gp.x,gp.y,cellSize,cellSize,"rgba(59,130,246,.22)","rgba(59,130,246,.60)");
  }

  const buyer = s.agents?.buyer;
  if(buyer){
    const bp=gridToPx(buyer.pos);
    drawCircle(bp.x+cellSize/2,bp.y+cellSize/2,Math.max(5,cellSize*0.28),"rgba(59,130,246,.95)","rgba(15,23,42,.20)");
  }

  const cashier = s.agents?.cashier;
  if(cashier){
    const cp=gridToPx(cashier.pos);
    drawCircle(cp.x+cellSize/2,cp.y+cellSize/2,Math.max(5,cellSize*0.26),"rgba(251,113,133,.95)","rgba(15,23,42,.20)");
  }

  updateUI(s);

  // ✅ NUEVO: actualizar barra + carrito en el mapa
  updateMapPurchaseUI(s);

  if (currentTab === "cashier") updateCashierUI(s);
}

function updateUI(s){
  const buyer = s.agents?.buyer;
  if(!buyer) return;

  setText(stStep, String(s.meta?.step ?? "-"));
  setText(stBuyerPos, `(${buyer.pos.x}, ${buyer.pos.y})`);
  setText(stVoucher, String(buyer.voucher_amount ?? "-"));
  setText(stRemaining, String(buyer.budget_remaining ?? "-"));
  const spent = (buyer.voucher_amount ?? 0) - (buyer.budget_remaining ?? 0);
  setText(stSpent, spent.toFixed(2));
  const pct = (buyer.voucher_amount ?? 0) > 0 ? (spent / buyer.voucher_amount) * 100 : 0;
  setText(stSpentPct, `${pct.toFixed(0)}%`);
  setText(stItems, String((buyer.cart || []).length));
  setText(stBuyerSteps, String(buyer.steps_moved ?? "-"));
  setText(stPaid, buyer.paid ? "Sí" : "No");
  setText(stGoal, buyer.goal ? `(${buyer.goal.x}, ${buyer.goal.y}) • ${buyer.goal_kind}` : "—");
  setText(stAlgo, buyer.algo || "-");

  const msgs = s.messages || [];
  if (!msgs.length) setHTML(logEl, "—");
  else setHTML(logEl, msgs.map(m=>`<div class="logLine">${m}</div>`).join(""));
}

function updateCashierUI(s){
  const cashier = s.agents?.cashier;
  const buyer = s.agents?.buyer;

  if(!cashier){
    setText(pillCashierStatus, "🧾 -");
    setText(pillRegister, "🏷️ -");
    setText(stCashierStatus, "-");
    setText(stCashierReg, "-");
    setText(stCashierScanned, "-");
    setText(stCashierSubtotal, "-");
    setText(stCashierRedeemed, "-");
    setText(stCashierRemaining, "-");
    setText(stCashierLast, "-");
    setHTML(cashierLog, "—");
    setHTML(cartList, "—");
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

  setText(stCashierSubtotal, (cashier.subtotal ?? 0).toFixed(2));
  setText(stCashierRedeemed, (cashier.redeemed_amount ?? 0).toFixed(2));
  setText(stCashierRemaining, (cashier.change_given ?? 0).toFixed(2)); // cambio

  setText(stCashierLast, formatCashierEvent(cashier.last_scan));

  const log = cashier.scan_log || [];
  if (!log.length) setHTML(cashierLog, "—");
  else setHTML(cashierLog, log.map(ev=>`<div class="logLine">${formatCashierEvent(ev)}</div>`).join(""));

  const cart = buyer?.cart || [];
  if(!cart.length) setHTML(cartList, "—");
  else setHTML(cartList, cart.map(sku=>`<div class="cartItem">${sku}</div>`).join(""));

  const total = Math.max(cart.length, 1);
  const pct = Math.min(100, Math.round((scannedCount / total) * 100));
  if (cashierProgressBar) cashierProgressBar.style.width = `${pct}%`;
  setText(stCashierProgressText, `${pct}% (${scannedCount}/${cart.length || 0})`);
}

// ---- Hover tooltip FIX (por celda) ----
canvas?.addEventListener("mousemove", (ev)=>{
  if(!state || !render._prodByCell) return;
  if(currentTab !== "map") { hideTooltip(); return; }

  const pos = getCanvasPosFromMouse(ev);
  const gx = Math.floor(pos.x / cellSize);
  const gy = Math.floor(pos.y / cellSize);

  const gw = state.grid?.width ?? 0;
  const gh = state.grid?.height ?? 0;

  if(gx < 0 || gy < 0 || gx >= gw || gy >= gh){
    hideTooltip();
    return;
  }

  const p = render._prodByCell.get(`${gx},${gy}`);
  if(p){
    showTooltipAtMouse(ev,
      `<b>${p.name}</b><br><span class="muted">${p.sku}</span><br>💲${fmt(p.price)}<br>📦 ${p.section} • ${p.shelf}`
    );
  }else{
    hideTooltip();
  }
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
  playTimer = null;
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
if (baseUrlInput){
  const saved = localStorage.getItem(LS.API_BASE);
  if(saved) baseUrlInput.value = saved;

  baseUrlInput.addEventListener("change", ()=>{
    localStorage.setItem(LS.API_BASE, baseUrlInput.value);
  });
}

setBranchLabel();

btnBranch?.addEventListener("click", ()=>{
  if(baseUrlInput) localStorage.setItem(LS.API_BASE, baseUrlInput.value);
  location.href = "branch.html";
});

setText(speedLabel, speedRange?.value || "200");
setTab("map");
doReset();
