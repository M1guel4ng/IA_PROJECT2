const el = (id) => document.getElementById(id);
const setText = (node, txt) => { if (node) node.textContent = txt; };
const setHTML = (node, html) => { if (node) node.innerHTML = html; };

const LS = {
  API_BASE: "sm_api_base",
  BRANCH_ID: "sm_branch_id",
  BRANCH_NAME: "sm_branch_name",
  BRANCH_CITY: "sm_branch_city",
};

const baseUrlInput = el("baseUrl");
const btnReload = el("btnReload");
const btnGoIndex = el("btnGoIndex");
const branchesStatus = el("branchesStatus");
const branchesList = el("branchesList");
const manualMapId = el("manualMapId");
const btnUseManual = el("btnUseManual");

function apiBase(){
  return (baseUrlInput?.value || localStorage.getItem(LS.API_BASE) || "http://localhost:8000").replace(/\/$/, "");
}

function saveBaseUrl(){
  if(baseUrlInput) localStorage.setItem(LS.API_BASE, baseUrlInput.value);
}

async function selectBranch(branch){
  // branch puede ser string (map_id) o un objeto {id,name,city}
  const id = typeof branch === "string" ? branch : (branch.id || "");
  if(!id) return;

  localStorage.setItem(LS.BRANCH_ID, id);

  if(typeof branch === "object"){
    if(branch.name) localStorage.setItem(LS.BRANCH_NAME, branch.name);
    else localStorage.removeItem(LS.BRANCH_NAME);

    if(branch.city) localStorage.setItem(LS.BRANCH_CITY, branch.city);
    else localStorage.removeItem(LS.BRANCH_CITY);
  }else{
    localStorage.removeItem(LS.BRANCH_NAME);
    localStorage.removeItem(LS.BRANCH_CITY);
  }

  // Intentar cargar la sucursal en el backend (si existe /api/reload)
  try{
    // Por convención: los mapas viven en /data y el id suele ser el nombre del .json sin extensión.
    const idForFile = id.endsWith(".json") ? id : `${id}.json`;
    const mapFile = idForFile.startsWith("data/") ? idForFile : `data/${idForFile}`;

    const r = await fetch(`${apiBase()}/api/reload?map_file=${encodeURIComponent(mapFile)}`, { method: "POST" });
    // Si no existe el endpoint, normalmente devuelve 404; lo ignoramos y seguimos.
    if(r.ok){
      // ok
    }
  }catch(e){
    // ignorar
  }

  saveBaseUrl();
  location.href = "index.html";
}

function renderBranches(items){
  if(!branchesList) return;
  if(!items || !items.length){
    setHTML(branchesList, '<div class="hint">No se encontraron sucursales.</div>');
    return;
  }

  const html = items.map(b => {
    const id = b.id || b.map_id || b.slug || b.file || "";
    const name = b.name || b.meta?.name || id || "Sucursal";
    const city = b.city || b.meta?.city || "";
    const size = b.grid ? `${b.grid.width}×${b.grid.height}` : (b.size || "");
    const subtitle = [city, size].filter(Boolean).join(" • ");

    return `
      <button class="branchTile" type="button" data-branch="${id}">
        <div class="branchTitle">${escapeHtml(name)}</div>
        <div class="branchSub">${escapeHtml(subtitle || id)}</div>
      </button>
    `;
  }).join("");

  setHTML(branchesList, html);

  // bind
  for(const btn of branchesList.querySelectorAll("[data-branch]")){
    btn.addEventListener("click", ()=>{
      const id = btn.getAttribute("data-branch");
      const title = btn.querySelector(".branchTitle")?.textContent || "";
      const sub = btn.querySelector(".branchSub")?.textContent || "";
      selectBranch({ id, name: title, city: sub.includes("•") ? sub.split("•")[0].trim() : "" });
    });
  }
}

function escapeHtml(str){
  return String(str)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

async function loadBranches(){
  try{
    setText(branchesStatus, "Cargando…");
    const r = await fetch(`${apiBase()}/api/branches`);
    if(!r.ok) throw new Error(`GET /api/branches ${r.status}`);
    const data = await r.json();

    // Aceptamos varios formatos:
    // - {branches:[...]}
    // - [...]
    const items = Array.isArray(data) ? data : (data.branches || []);
    renderBranches(items);
    setText(branchesStatus, `${items.length} sucursal(es)`);
  }catch(e){
    console.error(e);
    setText(branchesStatus, "No se pudo cargar la lista (usa selección manual).");
    renderBranches([]);
  }
}

// Eventos
btnReload?.addEventListener("click", ()=>{
  saveBaseUrl();
  loadBranches();
});

btnGoIndex?.addEventListener("click", ()=>{
  saveBaseUrl();
  location.href = "index.html";
});

btnUseManual?.addEventListener("click", ()=>{
  const id = (manualMapId?.value || "").trim();
  if(!id){
    manualMapId?.focus();
    return;
  }
  selectBranch(id);
});

// Init
if(baseUrlInput){
  const saved = localStorage.getItem(LS.API_BASE);
  if(saved) baseUrlInput.value = saved;
  baseUrlInput.addEventListener("change", saveBaseUrl);
}

const current = localStorage.getItem(LS.BRANCH_ID);
if(current && manualMapId) manualMapId.value = current;

loadBranches();
