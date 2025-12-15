from __future__ import annotations

from typing import Any, Dict, Optional

from ..data_loader import load_map
from ..models import BuyerState, CashierState, MapData, Pos, WorldState
from ..agents.buyer import BuyerAgent
from ..agents.cashier import CashierAgent


class World:
    """Orquestador de la simulación."""

    def __init__(self, map_data: Optional[MapData] = None):
        self.map_data = map_data or load_map()
        self.buyer_agent = BuyerAgent()
        self.cashier_agent = CashierAgent()
        self.state: Optional[WorldState] = None
        self.finished: bool = False
        self.reiniciar(voucher_amount=120.0, algo="astar")

    # --------- Alias/propiedades en español ---------
    @property
    def datos_mapa(self) -> MapData:
        return self.map_data

    @property
    def agente_comprador(self) -> BuyerAgent:
        return self.buyer_agent

    @property
    def agente_cajero(self) -> CashierAgent:
        return self.cashier_agent

    @property
    def estado(self) -> Optional[WorldState]:
        return self.state

    @property
    def terminado(self) -> bool:
        return self.finished

    @terminado.setter
    def terminado(self, value: bool) -> None:
        self.finished = value

    def reiniciar(self, voucher_amount: float = 120.0, algo: str = "astar", cashier_register_id: str = "R1") -> WorldState:
        self.finished = False
        reg = self.map_data.registers.get(cashier_register_id) or list(self.map_data.registers.values())[0]

        buyer = BuyerState(
            pos=self.map_data.entrance,
            voucher_amount=float(voucher_amount),
            budget_remaining=float(voucher_amount),
            algo=(algo or "astar").lower(),
        )
        cashier = CashierState(register_id=reg.id, pos=reg.cashier_spot)

        self.state = WorldState(step_count=0, map_data=self.map_data, buyer=buyer, cashier=cashier, messages=[])
        self.state.log(f"Reset: voucher={voucher_amount:.2f}, algo={buyer.algo}")
        return self.state

    def paso(self, steps: int = 1) -> WorldState:
        assert self.state is not None

        if self.finished:
            self.state.messages = []
            self.state.log("⏹️ Simulación finalizada. (Reset para iniciar de nuevo)")
            return self.state

        for _ in range(max(1, int(steps))):
            if self.finished:
                break

            self.state.step_count += 1
            self.state.messages = []

            self.buyer_agent.paso(self.state)
            self.cashier_agent.paso(self.state)

            if self.state.buyer.paid and self.state.buyer.pos == self.map_data.exit:
                self.state.log("✅ Compra finalizada: salió del supermercado.")
                self.finished = True

        return self.state

    def a_dict(self) -> Dict[str, Any]:
        s = self.state
        assert s is not None
        md = s.map_data

        def pos(p: Pos) -> Dict[str, int]:
            return {"x": p.x, "y": p.y}

        return {
            "meta": {"name": md.name, "city": md.city, "step": s.step_count, "finished": self.finished},
            "grid": {"width": md.grid.width, "height": md.grid.height},
            "entrance": pos(md.entrance),
            "exit": pos(md.exit),
            "shelves": [
                {"id": sh.id, "rect": {"x": sh.rect.x, "y": sh.rect.y, "w": sh.rect.w, "h": sh.rect.h}, "section": sh.section}
                for sh in md.shelves.values()
            ],
            "registers": [
                {"id": r.id, "cashier_spot": pos(r.cashier_spot), "queue_spot": pos(r.queue_spot)}
                for r in md.registers.values()
            ],
            "sections": [{"id": sec.id, "label": sec.label} for sec in md.sections.values()],
            "products": [
                {"sku": p.sku, "name": p.name, "price": p.price, "section": p.section, "shelf": p.shelf, "pick": pos(p.pick)}
                for p in md.products.values()
            ],
            "agents": {
                "buyer": {
                    "pos": pos(s.buyer.pos),
                    "algo": s.buyer.algo,
                    "voucher_amount": s.buyer.voucher_amount,
                    "budget_remaining": round(s.buyer.budget_remaining, 2),
                    "selected_skus": s.buyer.selected_skus,
                    "cart": s.buyer.cart,
                    "purchase_log": s.buyer.purchase_log,
                    "steps_moved": s.buyer.steps_moved,
                    "goal": pos(s.buyer.goal) if s.buyer.goal else None,
                    "goal_kind": s.buyer.goal_kind,
                    "paid": s.buyer.paid,
                    "path": [pos(p) for p in s.buyer.path[:200]],
                    "change_received": round(s.buyer.change_received, 2),
                },
                "cashier": {
                    "pos": pos(s.cashier.pos),
                    "register_id": s.cashier.register_id,
                    "busy_ticks": s.cashier.busy_ticks,
                    "status": s.cashier.status,
                    "scan_index": s.cashier.scan_index,
                    "scanned_skus": s.cashier.scanned_skus,
                    "subtotal": round(s.cashier.subtotal, 2),
                    "redeemed_amount": round(s.cashier.redeemed_amount, 2),
                    "voucher_remaining": round(s.cashier.voucher_remaining, 2),
                    "last_scan": s.cashier.last_scan,
                    "scan_log": s.cashier.scan_log,
                    "change_given": round(s.cashier.change_given, 2),
                },
            },
            "messages": s.messages,
        }

    # --------- Alias compatibilidad (inglés) ---------
    def reset(self, voucher_amount: float = 120.0, algo: str = "astar", cashier_register_id: str = "R1") -> WorldState:
        return self.reiniciar(voucher_amount=voucher_amount, algo=algo, cashier_register_id=cashier_register_id)

    def step(self, steps: int = 1) -> WorldState:
        return self.paso(steps=steps)

    def to_dict(self) -> Dict[str, Any]:
        return self.a_dict()

    # ✅ FIX: ahora SÍ está dentro de la clase
    def recargar_mapa(self, map_file: str | None = None) -> None:
        """
        Carga un nuevo mapa desde /data y reinicia la simulación.
        """
        from pathlib import Path
        from ..data_loader import load_map

        if map_file is None:
            self.map_data = load_map()
        else:
            p = Path(map_file)
            if not p.suffix:
                p = p.with_suffix(".json")

            if str(p).startswith("data/") or str(p).startswith("data\\"):
                root = Path(__file__).resolve().parents[3]  # .../backend/app/sim/world.py -> project_root
                p = root / p

            self.map_data = load_map(p)

        voucher = 120.0
        algo = "astar"
        reg = "R1"
        if self.state:
            voucher = float(self.state.buyer.voucher_amount)
            algo = str(self.state.buyer.algo)
            reg = str(self.state.cashier.register_id)

        self.reiniciar(voucher_amount=voucher, algo=algo, cashier_register_id=reg)

    # ✅ FIX: para que /api/patch no reviente
    def aplicar_parche(self, payload: Dict[str, Any]) -> None:
        """
        Soporta ops:
          - move_product: {"op":"move_product","sku":"P010","to":{"x":10,"y":2}}
          - set_blocked:  {"op":"set_blocked","at":{"x":7,"y":7},"blocked":true}
        """
        ops = payload.get("ops", [])
        if not isinstance(ops, list):
            return

        # si no hay state aún, igual permitimos modificar map_data
        for op in ops:
            if not isinstance(op, dict):
                continue

            kind = op.get("op")

            if kind == "move_product":
                sku = op.get("sku")
                to = op.get("to") or {}
                if not sku or sku not in self.map_data.products:
                    if self.state:
                        self.state.log(f"⚠️ move_product: sku inválido ({sku})")
                    continue
                try:
                    x = int(to.get("x"))
                    y = int(to.get("y"))
                except Exception:
                    if self.state:
                        self.state.log("⚠️ move_product: coordenadas inválidas")
                    continue

                self.map_data.products[sku].pick = Pos(x=x, y=y)
                if self.state:
                    self.state.map_data = self.map_data
                    self.state.log(f"🧩 Producto {sku} movido a ({x},{y})")

            elif kind == "set_blocked":
                at = op.get("at") or {}
                blocked = bool(op.get("blocked", True))
                try:
                    x = int(at.get("x"))
                    y = int(at.get("y"))
                except Exception:
                    if self.state:
                        self.state.log("⚠️ set_blocked: coordenadas inválidas")
                    continue

                p = Pos(x=x, y=y)

                # Solo si tu MapData tiene estructura de bloqueados
                if hasattr(self.map_data, "blocked"):
                    if blocked:
                        self.map_data.blocked.add(p)
                    else:
                        self.map_data.blocked.discard(p)
                    if self.state:
                        self.state.map_data = self.map_data
                        self.state.log(f"🧱 Bloqueo ({x},{y}) = {blocked}")
                else:
                    if self.state:
                        self.state.log("⚠️ MapData no tiene atributo 'blocked' (ignorado).")

            else:
                if self.state:
                    self.state.log(f"⚠️ op desconocida: {kind}")
