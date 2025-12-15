from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .sim.world import World

app = FastAPI(title="Supermercado Multiagente Backend", version="0.1.0")

# CORS para frontend separado (localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORLD = World()


@app.get("/api/map")
def get_map():
    # Mapa + estado actual
    return WORLD.to_dict()


@app.post("/api/reset")
def reset(
    voucher: float = Query(120.0, ge=0.0),
    algo: str = Query("astar"),
    cashier_register: str = Query("R1")
):
    WORLD.reset(voucher_amount=voucher, algo=algo, cashier_register_id=cashier_register)
    return WORLD.to_dict()


@app.post("/api/step")
def step(n: int = Query(1, ge=1, le=500)):
    WORLD.step(steps=n)
    return WORLD.to_dict()


@app.get("/health")
def health():
    return {"ok": True}
