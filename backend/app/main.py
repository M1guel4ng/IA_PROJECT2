from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .sim.world import World

app = FastAPI(title="Supermercado Multiagente Backend", version="0.2.1")

# CORS para frontend separado (localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORLD = World()
WORLD.reset(voucher_amount=120.0, algo="astar", cashier_register_id="R1")


# ---------- Helpers de rutas ----------
def _project_root() -> Path:
    """
    Encuentra la carpeta raíz del proyecto (la que contiene /data).
    Esto evita errores cuando cambias de PC/ruta (Windows/Linux).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").exists():
            return parent
    # fallback razonable: .../supermercado_multiagente (desde backend/app/main.py)
    return here.parents[2]


def _data_dir() -> Path:
    return _project_root() / "data"


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------- API ----------
@app.get("/api/state")
def state():
    return WORLD.to_dict()


@app.post("/api/reset")
def reset(
    voucher: float = Query(120.0, ge=0, le=10_000),
    algo: str = Query("astar"),
    cashier_register: str = Query("R1"),
):
    WORLD.reset(voucher_amount=voucher, algo=algo, cashier_register_id=cashier_register)
    return WORLD.to_dict()


@app.post("/api/step")
def step(n: int = Query(1, ge=1, le=500)):
    WORLD.step(steps=n)
    return WORLD.to_dict()


# ---------- Entorno moldeable ----------
@app.post("/api/reload")
def reload_map(map_file: str | None = Query(None)):
    """
    Recarga el mapa desde JSON (por defecto usa data/supermarket_cbba_v1.json).

    Ejemplos:
    - /api/reload
    - /api/reload?map_file=data/supermarket_cbba_v1.json
    """
    WORLD.recargar_mapa(map_file=map_file)
    return WORLD.to_dict()


@app.post("/api/patch")
def patch_env(payload: dict = Body(...)):
    """
    Aplica un parche en caliente al entorno.

    Body ejemplo:
    {
      "ops": [
        {"op":"move_product","sku":"P010","to":{"x":10,"y":2}},
        {"op":"set_blocked","at":{"x":7,"y":7},"blocked":true}
      ]
    }
    """
    WORLD.aplicar_parche(payload)
    return WORLD.to_dict()


# ---------- Sucursales ----------
@app.get("/api/branches")
def branches():
    """
    Lista sucursales disponibles leyendo data/*.json
    Devuelve: { "branches": [ {id,name,city,grid:{width,height},file} ... ] }
    """
    dd = _data_dir()
    dd.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    for f in sorted(dd.glob("*.json")):
        # ignora cosas que no son mapas
        if f.name.lower().startswith("bitacora"):
            continue

        data = _safe_read_json(f)
        if not data:
            continue

        meta = data.get("meta", {}) if isinstance(data.get("meta", {}), dict) else {}
        grid = data.get("grid", {}) if isinstance(data.get("grid", {}), dict) else {}

        # Validación mínima para considerarlo "sucursal"
        if "width" not in grid or "height" not in grid:
            continue

        items.append(
            {
                "id": f.stem,  # nombre sin .json (map_id)
                "name": meta.get("name", f.stem),
                "city": meta.get("city", ""),
                "grid": {
                    "width": int(grid.get("width", 0) or 0),
                    "height": int(grid.get("height", 0) or 0),
                },
                "file": f.name,
            }
        )

    return {"branches": items}


@app.get("/health")
def health():
    return {"ok": True}
