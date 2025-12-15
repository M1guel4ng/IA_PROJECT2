from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .sim.world import World
from .sim.travel import TravelWorld

app = FastAPI(title="Supermercado Multiagente Backend", version="0.2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORLD = World()
WORLD.reset(voucher_amount=120.0, algo="astar", cashier_register_id="R1")

TRAVEL = TravelWorld()


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").exists():
            return parent
    return here.parents[2]


def _data_dir() -> Path:
    return _project_root() / "data"


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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


@app.post("/api/reload")
def reload_map(map_file: str | None = Query(None)):
    WORLD.recargar_mapa(map_file=map_file)
    return WORLD.to_dict()


@app.post("/api/patch")
def patch_env(payload: dict = Body(...)):
    WORLD.aplicar_parche(payload)
    return WORLD.to_dict()


@app.get("/api/branches")
def branches():
    dd = _data_dir()
    dd.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    for f in sorted(dd.glob("*.json")):
        if f.name.lower().startswith("bitacora"):
            continue

        data = _safe_read_json(f)
        if not data:
            continue

        meta = data.get("meta", {}) if isinstance(data.get("meta", {}), dict) else {}
        grid = data.get("grid", {}) if isinstance(data.get("grid", {}), dict) else {}

        if "width" not in grid or "height" not in grid:
            continue

        items.append(
            {
                "id": f.stem,
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


# ---------------- TRAVEL (TAXI) ----------------

@app.get("/api/travel/graph")
def travel_graph():
    return TRAVEL.graph_dict()


@app.get("/api/travel/state")
def travel_state():
    return TRAVEL.to_dict()


@app.post("/api/travel/reset")
def travel_reset(
    home_id: str | None = Query(None),
    taxi_start: str | None = Query(None),
):
    TRAVEL.reset(home_id=home_id, taxi_start=taxi_start)
    return TRAVEL.to_dict()


@app.post("/api/travel/step")
def travel_step(n: int = Query(1, ge=1, le=500)):
    TRAVEL.step(n=n)
    return TRAVEL.to_dict()
