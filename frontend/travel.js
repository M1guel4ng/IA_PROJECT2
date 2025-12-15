const el = (id) => document.getElementById(id);
const setText = (node, txt) => { if(node) node.textContent = txt; };
const setHTML = (node, html) => { if(node) node.innerHTML = html; };

const LS = {
  API_BASE: "sm_api_base",
  CALIB: "travel_calib_rect",   // {x,y,w,h} en % (0..1) sobre la imagen
  PICK_TAXI: "travel_pick_taxi",
  PICK_HOME: "travel_pick_home",
};

const canvas = el("mapCanvas");
const ctx = canvas?.getContext("2d");

const baseUrlInput = el("baseUrl");
const subtitle = el("subtitle");
const pillStatus = el("pillStatus");
const pillPicked = el("pillPicked");
const pillTarget = el("pillTarget");

const btnReload = el("btnReload");
const btnReset = el("btnReset");
const btnStep = el("btnStep");
const btnStep10 = el("btnStep10");
const btnPlay = el("btnPlay");
const btnPause = el("btnPause");
const btnCalibrate = el("btnCalibrate");
const btnClearPick = el("btnClearPick");

const speedRange = el("speed");
const speedLabel = el("speedLabel");

const stStep = el("stStep");
const stTaxi = el("stTaxi");
const stOnboard = el("stOnboard");
const stBuyer = el("stBuyer");
const stHome = el("stHome");
const stStore = el("stStore");
const stBranch = el("stBranch");
const stPlan = el("stPlan");

const logEl = el("log");
const hud = el("hud");

function apiBase(){
  return (baseUrlInput?.value || localStorage.getItem(LS.API_BASE) || "http://localhost:8000").replace(/\/$/, "");
}
function saveBase(){
  if(baseUrlInput) localStorage.setItem(LS.API_BASE, baseUrlInput.value);
}

let BG_SRC = "cbba_bg.png";
const bgImg = new Image();
bgImg.src = BG_SRC;

let graph = null;
let state = null;

let nodeIndex = new Map();
let nodes = [];
let edges = [];

let playTimer = null;
let anim = { active:false, from:{x:0,y:0}, to:{x:0,y:0}, t:0, dur:260, cur:{x:0,y:0} };

let selectedTaxiStart = localStorage.getItem(LS.PICK_TAXI) || "";
let selectedHomeId = localStorage.getItem(LS.PICK_HOME) || "";

// Calibración: rect en porcentaje
let calib = (() => {
  try { return JSON.parse(localStorage.getItem(LS.CALIB) || ""); } catch {}
  return null;
})();
if(!calib){
  calib = { x: 0.07, y: 0.08, w: 0.86, h: 0.84 };
}
let calibrating = false;

// ✅ cache dims para que mouse/handles no se descalibren
let lastDims = null;

// Drag state
let dragMode = null;   // "handle" | "move" | null
let dragHandle = null; // "tl"|"tr"|"br"|"bl"
let dragStart = { mx:0, my:0, calib:null };

function setStatus(ok, msg){
  if(!pillStatus) return;
  pillStatus.style.background = ok ? "rgba(34,197,94,.12)" : "rgba(239,68,68,.12)";
  pillStatus.style.borderColor = ok ? "rgba(34,197,94,.25)" : "rgba(239,68,68,.25)";
  pillStatus.textContent = ok ? "● OK" : "● ERROR";
  setText(subtitle, msg || "");
}

async function apiGet(path){
  const r = await fetch(`${apiBase()}${path}`);
  if(!r.ok) throw new Error(`${path} ${r.status}`);
  return await r.json();
}
async function apiPost(path){
  const r = await fetch(`${apiBase()}${path}`, { method:"POST" });
  if(!r.ok) throw new Error(`${path} ${r.status}`);
  return await r.json();
}

function rebuildIndex(){
  nodeIndex = new Map();
  nodes = graph?.nodes || [];
  edges = graph?.edges || [];
  for(const n of nodes) nodeIndex.set(n.id, n);
}

function getNodeBounds(){
  let minX=1e9, minY=1e9, maxX=-1e9, maxY=-1e9;
  for(const n of nodes){
    const x = Number(n.x), y = Number(n.y);
    if(Number.isFinite(x) && Number.isFinite(y)){
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
  }
  if(minX === 1e9) return {minX:0,minY:0,maxX:1,maxY:1};
  return {minX,minY,maxX,maxY};
}

/**
 * ✅ SOLO draw() puede redimensionar el canvas.
 * Esto evita que hitHandle() cambie el tamaño mientras clickeas.
 */
function fitCanvasToImage(){
  if(!canvas || !ctx) return null;

  const wrapW = canvas.parentElement.clientWidth;
  const imgW = bgImg.naturalWidth || 800;
  const imgH = bgImg.naturalHeight || 600;
  const ratio = imgH / imgW;

  const cssW = wrapW;
  const cssH = Math.round(cssW * ratio);

  const dpr = window.devicePixelRatio || 1;
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);

  return { cssW, cssH, imgW, imgH };
}

function getDims(){
  // ✅ si no hay dims cacheado, usamos el actual del canvas sin recalcular layout
  if(lastDims) return lastDims;
  if(!canvas) return { cssW: 800, cssH: 600 };
  const rect = canvas.getBoundingClientRect();
  return { cssW: rect.width, cssH: rect.height };
}

function nodeToCanvas(n, dims, bounds){
  const { cssW, cssH } = dims;
  const { minX, minY, maxX, maxY } = bounds;

  const nx = (Number(n.x) - minX) / Math.max(1e-9, (maxX - minX));
  const ny = (Number(n.y) - minY) / Math.max(1e-9, (maxY - minY));

  const rx = calib.x * cssW;
  const ry = calib.y * cssH;
  const rw = calib.w * cssW;
  const rh = calib.h * cssH;

  const x = rx + nx * rw;
  const y = ry + ny * rh;
  return { x, y };
}

function rectPx(dims){
  return {
    rx: calib.x * dims.cssW,
    ry: calib.y * dims.cssH,
    rw: calib.w * dims.cssW,
    rh: calib.h * dims.cssH,
  };
}

function pointInRect(mx, my, r){
  return mx >= r.rx && mx <= r.rx + r.rw && my >= r.ry && my <= r.ry + r.rh;
}

function draw(){
  if(!ctx || !canvas) return;
  if(!bgImg.complete) return;

  // ✅ acá sí recalculamos y cacheamos dims
  lastDims = fitCanvasToImage();
  const dims = lastDims;
  const bounds = getNodeBounds();

  // fondo
  ctx.clearRect(0,0,dims.cssW,dims.cssH);
  ctx.drawImage(bgImg, 0, 0, dims.cssW, dims.cssH);

  // edges
  ctx.lineWidth = 1.2;
  for(const e of edges){
    const a = nodeIndex.get(e.a);
    const b = nodeIndex.get(e.b);
    if(!a || !b) continue;

    const pa = nodeToCanvas(a, dims, bounds);
    const pb = nodeToCanvas(b, dims, bounds);

    const isArterial = (e.class === "arterial");
    ctx.strokeStyle = isArterial ? "rgba(59,130,246,.55)" : "rgba(148,163,184,.35)";

    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.stroke();
  }

  // nodos
  for(const n of nodes){
    const p = nodeToCanvas(n, dims, bounds);

    let r = 3.2;
    let fill = "rgba(148,163,184,.95)";

    if(n.kind === "home"){ r = 6; fill = "rgba(34,197,94,.95)"; }
    if(n.kind === "store"){ r = 6; fill = "rgba(239,68,68,.95)"; }
    if(n.kind === "taxi_stand"){ r = 5; fill = "rgba(251,113,133,.95)"; }

    const selected = (n.id === selectedTaxiStart) || (n.id === selectedHomeId);
    if(selected){
      ctx.beginPath();
      ctx.arc(p.x, p.y, r+4, 0, Math.PI*2);
      ctx.fillStyle = "rgba(17,24,39,.25)";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI*2);
    ctx.fillStyle = fill;
    ctx.fill();

    ctx.strokeStyle = "rgba(15,23,42,.15)";
    ctx.stroke();
  }

  // taxi (anim)
  if(state){
    const taxiNode = nodeIndex.get(state.taxi?.node || "");
    if(taxiNode){
      const pt = nodeToCanvas(taxiNode, dims, bounds);
      const drawPos = anim.active ? anim.cur : pt;

      ctx.beginPath();
      ctx.arc(drawPos.x, drawPos.y, 12, 0, Math.PI*2);
      ctx.fillStyle = "rgba(245,158,11,.20)";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(drawPos.x, drawPos.y, 7, 0, Math.PI*2);
      ctx.fillStyle = "rgba(245,158,11,.95)";
      ctx.fill();
      ctx.strokeStyle = "rgba(15,23,42,.18)";
      ctx.stroke();

      ctx.font = "12px ui-sans-serif";
      ctx.fillStyle = "rgba(15,23,42,.85)";
      ctx.fillText("🚕", drawPos.x - 6, drawPos.y + 4);
    }
  }

  // ✅ overlay calibración
  if(calibrating){
    const r = rectPx(dims);

    ctx.setLineDash([6,4]);
    ctx.strokeStyle = "rgba(17,24,39,.8)";
    ctx.lineWidth = 2;
    ctx.strokeRect(r.rx, r.ry, r.rw, r.rh);
    ctx.setLineDash([]);

    // handles grandes
    const handles = getHandles(dims);
    for(const h of handles){
      ctx.beginPath();
      ctx.rect(h.x-8, h.y-8, 16, 16);
      ctx.fillStyle = "rgba(255,255,255,.95)";
      ctx.fill();
      ctx.strokeStyle = "rgba(17,24,39,.85)";
      ctx.stroke();
    }

    // hint
    ctx.font = "12px ui-sans-serif";
    ctx.fillStyle = "rgba(17,24,39,.9)";
    ctx.fillText("Arrastra esquinas (□) o arrastra dentro para mover", r.rx + 8, r.ry - 10);
  }

  setText(hud, `Nodos: ${nodes.length} • Aristas: ${edges.length} • Calib: ${calibrating ? "ON" : "OFF"}`);
}

function getHandles(dims){
  const r = rectPx(dims);
  return [
    { id:"tl", x: r.rx,       y: r.ry },
    { id:"tr", x: r.rx+r.rw,  y: r.ry },
    { id:"br", x: r.rx+r.rw,  y: r.ry+r.rh },
    { id:"bl", x: r.rx,       y: r.ry+r.rh }
  ];
}

// ✅ hitbox más grande
function hitHandle(mx, my){
  const dims = getDims();
  const handles = getHandles(dims);
  for(const h of handles){
    if(Math.abs(mx - h.x) <= 16 && Math.abs(my - h.y) <= 16) return h.id;
  }
  return null;
}

function clamp01(v){ return Math.max(0, Math.min(1, v)); }

function saveCalib(){
  localStorage.setItem(LS.CALIB, JSON.stringify(calib));
}

function updateCalibFromHandle(handleId, mx, my, dims){
  const x = clamp01(mx / dims.cssW);
  const y = clamp01(my / dims.cssH);

  const x2 = calib.x + calib.w;
  const y2 = calib.y + calib.h;

  if(handleId === "tl"){
    calib.w = Math.max(0.05, x2 - x);
    calib.h = Math.max(0.05, y2 - y);
    calib.x = x;
    calib.y = y;
  }
  if(handleId === "tr"){
    calib.w = Math.max(0.05, x - calib.x);
    calib.h = Math.max(0.05, y2 - y);
    calib.y = y;
  }
  if(handleId === "br"){
    calib.w = Math.max(0.05, x - calib.x);
    calib.h = Math.max(0.05, y - calib.y);
  }
  if(handleId === "bl"){
    calib.w = Math.max(0.05, x2 - x);
    calib.h = Math.max(0.05, y - calib.y);
    calib.x = x;
  }

  saveCalib();
}

function moveCalib(mx, my, dims){
  // mover el rect completo manteniendo w/h
  const dx = (mx - dragStart.mx) / dims.cssW;
  const dy = (my - dragStart.my) / dims.cssH;

  calib.x = clamp01(dragStart.calib.x + dx);
  calib.y = clamp01(dragStart.calib.y + dy);

  // evitar salir del canvas
  calib.x = Math.min(calib.x, 1 - calib.w);
  calib.y = Math.min(calib.y, 1 - calib.h);

  saveCalib();
}

function pickNodeAt(mx, my){
  if(!graph) return null;
  const dims = getDims();
  const bounds = getNodeBounds();

  let best = null;
  let bestD = 1e9;
  for(const n of nodes){
    const p = nodeToCanvas(n, dims, bounds);
    const d = Math.hypot(mx - p.x, my - p.y);
    if(d < bestD){
      bestD = d;
      best = n;
    }
  }
  return (bestD <= 12) ? best : null;
}

function updatePickedPills(){
  setText(pillPicked, `Taxi: ${selectedTaxiStart || "—"} | Casa: ${selectedHomeId || "—"}`);
  if(selectedHomeId) localStorage.setItem(LS.PICK_HOME, selectedHomeId); else localStorage.removeItem(LS.PICK_HOME);
  if(selectedTaxiStart) localStorage.setItem(LS.PICK_TAXI, selectedTaxiStart); else localStorage.removeItem(LS.PICK_TAXI);
}

function animateTaxiMove(prevNodeId, nextNodeId){
  const a = nodeIndex.get(prevNodeId);
  const b = nodeIndex.get(nextNodeId);
  if(!a || !b) return;

  const dims = getDims();
  const bounds = getNodeBounds();
  const pa = nodeToCanvas(a, dims, bounds);
  const pb = nodeToCanvas(b, dims, bounds);

  anim.active = true;
  anim.from = pa;
  anim.to = pb;
  anim.t = 0;
  anim.dur = Number(speedRange?.value || 240);
  anim.cur = {x: pa.x, y: pa.y};

  const start = performance.now();
  function frame(now){
    const dt = now - start;
    const t = Math.min(1, dt / anim.dur);
    const tt = t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2)/2;
    anim.cur = {
      x: anim.from.x + (anim.to.x - anim.from.x) * tt,
      y: anim.from.y + (anim.to.y - anim.from.y) * tt,
    };
    draw();
    if(t < 1) requestAnimationFrame(frame);
    else { anim.active = false; draw(); }
  }
  requestAnimationFrame(frame);
}

function updateUI(){
  if(!state) return;

  setText(stStep, String(state.step ?? "-"));
  setText(stTaxi, state.taxi?.node ?? "-");
  setText(stOnboard, state.taxi?.onboard ? "Sí" : "No");
  setText(stBuyer, state.buyer?.node ?? "-");
  setText(stHome, state.buyer?.home ?? "-");
  setText(stStore, state.target?.store_node ?? "-");
  setText(stBranch, state.target?.branch_id ?? "-");
  setText(stPlan, `${state.plan?.index ?? 0}/${state.plan?.len ?? 0}`);

  setText(pillTarget, `Destino: ${state.target?.branch_id || "—"}`);
  if(state.finished){
    pillTarget.style.background = "rgba(34,197,94,.12)";
    pillTarget.style.borderColor = "rgba(34,197,94,.25)";
  }else{
    pillTarget.style.background = "rgba(15,23,42,.02)";
    pillTarget.style.borderColor = "rgba(15,23,42,.12)";
  }

  const msgs = state.messages || [];
  setHTML(logEl, msgs.length ? msgs.map(m=>`<div>${escapeHtml(m)}</div>`).join("") : "—");
}

function escapeHtml(str){
  return String(str)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

async function loadAll(){
  try{
    saveBase();
    setStatus(true, "Cargando grafo/estado…");

    graph = await apiGet("/api/travel/graph");
    rebuildIndex();

    state = await apiGet("/api/travel/state");
    updateUI();
    updatePickedPills();

    setStatus(true, "Listo.");
    draw();
  }catch(e){
    console.error(e);
    setStatus(false, "No conecta al backend o faltan endpoints (/api/travel/*).");
  }
}

async function doReset(){
  stopPlay();
  try{
    const qs = new URLSearchParams();
    if(selectedHomeId) qs.set("home_id", selectedHomeId);
    if(selectedTaxiStart) qs.set("taxi_start", selectedTaxiStart);

    const prevTaxi = state?.taxi?.node;
    state = await apiPost(`/api/travel/reset?${qs.toString()}`);
    updateUI();

    if(prevTaxi && state?.taxi?.node && prevTaxi !== state.taxi.node){
      animateTaxiMove(prevTaxi, state.taxi.node);
    }else{
      draw();
    }

    setStatus(true, "Reset OK");
  }catch(e){
    console.error(e);
    setStatus(false, "Error en reset");
  }
}

async function doStep(n=1){
  try{
    const prevTaxi = state?.taxi?.node;
    state = await apiPost(`/api/travel/step?n=${n}`);
    updateUI();

    const nextTaxi = state?.taxi?.node;
    if(prevTaxi && nextTaxi && prevTaxi !== nextTaxi){
      animateTaxiMove(prevTaxi, nextTaxi);
    }else{
      draw();
    }

    if(state?.finished){
      stopPlay();
      setStatus(true, "✅ Llegó al destino (finished=true)");
    }else{
      setStatus(true, "OK");
    }
  }catch(e){
    console.error(e);
    stopPlay();
    setStatus(false, "Error step");
  }
}

function startPlay(){
  if(playTimer) return;
  btnPlay.disabled = true;
  btnPause.disabled = false;

  const tick = async () => {
    if(!playTimer) return;
    await doStep(1);
    if(state?.finished) stopPlay();
  };

  const interval = Number(speedRange?.value || 240);
  playTimer = setInterval(tick, interval);
}

function stopPlay(){
  if(!playTimer) return;
  clearInterval(playTimer);
  playTimer = null;
  btnPlay.disabled = false;
  btnPause.disabled = true;
}

btnReload?.addEventListener("click", loadAll);
btnReset?.addEventListener("click", doReset);
btnStep?.addEventListener("click", ()=>doStep(1));
btnStep10?.addEventListener("click", ()=>doStep(10));
btnPlay?.addEventListener("click", startPlay);
btnPause?.addEventListener("click", stopPlay);

btnCalibrate?.addEventListener("click", ()=>{
  calibrating = !calibrating;
  dragMode = null; dragHandle = null;
  draw();
});

btnClearPick?.addEventListener("click", ()=>{
  selectedTaxiStart = "";
  selectedHomeId = "";
  updatePickedPills();
  draw();
});

speedRange?.addEventListener("input", ()=>{
  setText(speedLabel, speedRange.value);
  if(playTimer){ stopPlay(); startPlay(); }
});

if(baseUrlInput){
  const saved = localStorage.getItem(LS.API_BASE);
  if(saved) baseUrlInput.value = saved;
  baseUrlInput.addEventListener("change", saveBase);
}
setText(speedLabel, speedRange?.value || "240");

// ✅ clicks en canvas: calibración o selección de nodos
canvas?.addEventListener("mousedown", (ev)=>{
  if(!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const mx = ev.clientX - rect.left;
  const my = ev.clientY - rect.top;

  if(calibrating){
    const dims = getDims();
    const h = hitHandle(mx, my);

    dragStart = { mx, my, calib: { ...calib } };

    if(h){
      dragMode = "handle";
      dragHandle = h;
      return;
    }

    // mover rect completo si clic dentro
    const r = rectPx(dims);
    if(pointInRect(mx, my, r)){
      dragMode = "move";
      dragHandle = null;
      return;
    }

    // clic fuera no hace nada
    return;
  }

  const n = pickNodeAt(mx, my);
  if(!n) return;

  if(n.kind === "home"){
    selectedHomeId = n.id;
  }else{
    selectedTaxiStart = n.id;
  }
  updatePickedPills();
  draw();
});

canvas?.addEventListener("mousemove", (ev)=>{
  if(!canvas) return;

  if(!calibrating || !dragMode) return;

  const rect = canvas.getBoundingClientRect();
  const mx = ev.clientX - rect.left;
  const my = ev.clientY - rect.top;

  const dims = getDims();

  // restaurar base antes de aplicar
  calib = { ...dragStart.calib };

  if(dragMode === "handle" && dragHandle){
    updateCalibFromHandle(dragHandle, mx, my, dims);
  }else if(dragMode === "move"){
    // mover completo (usa dragStart.calib)
    calib = { ...dragStart.calib };
    moveCalib(mx, my, dims);
  }

  draw();
});

window.addEventListener("mouseup", ()=>{
  dragMode = null;
  dragHandle = null;
});

window.addEventListener("resize", ()=> draw());

// inicial
bgImg.onload = () => draw();
loadAll();
