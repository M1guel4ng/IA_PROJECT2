from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .models import Grid, MapData, Pos, Rect, Register, Product, Section, Shelf


def _project_root() -> Path:
    # backend/app/data_loader.py -> backend/app -> backend -> project_root
    return Path(__file__).resolve().parents[2]


def load_map(map_path: Path | None = None) -> MapData:
    if map_path is None:
        map_path = _project_root() / "data" / "Hipermaxi_El_Prado.json"

    data = json.loads(Path(map_path).read_text(encoding="utf-8"))

    width = int(data["grid"]["width"])
    height = int(data["grid"]["height"])
    grid = Grid(width=width, height=height, walkable=[[True for _ in range(width)] for _ in range(height)])

    # Border walls (perimeter blocked)
    for x in range(width):
        grid.set_blocked(Pos(x, 0), True)
        grid.set_blocked(Pos(x, height - 1), True)
    for y in range(height):
        grid.set_blocked(Pos(0, y), True)
        grid.set_blocked(Pos(width - 1, y), True)

    shelves: Dict[str, Shelf] = {}
    for s in data.get("shelves", []):
        rect = Rect(**s["rect"])
        shelf = Shelf(id=s["id"], rect=rect, section=s["section"])
        shelves[shelf.id] = shelf
        for cell in rect.iter_cells():
            grid.set_blocked(cell, True)

    registers: Dict[str, Register] = {}
    for r in data.get("registers", []):
        reg = Register(
            id=r["id"],
            cashier_spot=Pos(**r["cashier_spot"]),
            queue_spot=Pos(**r["queue_spot"])
        )
        registers[reg.id] = reg
        # Reserve tiles as walkable (ensure not blocked)
        grid.set_blocked(reg.cashier_spot, False)
        grid.set_blocked(reg.queue_spot, False)

    sections: Dict[str, Section] = {}
    for sec in data.get("sections", []):
        section = Section(id=sec["id"], label=sec["label"])
        sections[section.id] = section

    products: Dict[str, Product] = {}
    for p in data.get("products", []):
        prod = Product(
            sku=p["sku"],
            name=p["name"],
            price=float(p["price"]),
            section=p["section"],
            shelf=p["shelf"],
            pick=Pos(**p["pick"]),
        )
        products[prod.sku] = prod
        # Pick points must be walkable
        grid.set_blocked(prod.pick, False)

    entrance = Pos(**data["entrance"])
    exit_ = Pos(**data["exit"])
    grid.set_blocked(entrance, False)
    grid.set_blocked(exit_, False)

    return MapData(
        name=data["meta"]["name"],
        city=data["meta"]["city"],
        grid=grid,
        entrance=entrance,
        exit=exit_,
        shelves=shelves,
        registers=registers,
        sections=sections,
        products=products
    )

def _project_root() -> Path:
    # Ajusta si tu estructura difiere:
    # backend/app/data_loader.py -> backend/app -> backend -> project_root
    return Path(__file__).resolve().parents[2]

def load_city_graph(graph_file: str | None = None) -> dict:
    """
    Carga grafo de ciudad para simulación de taxi.
    Default: <project_root>/data/city_graph_cbba_sim.json
    """
    root = _project_root()
    path = Path(graph_file) if graph_file else (root / "data" / "city_graph_cbba_sim.json")
    if not path.is_absolute():
        path = root / path

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
        raise ValueError("city graph inválido (necesita 'nodes' y 'edges')")
    return data