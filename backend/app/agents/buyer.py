from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models import Pos, WorldState
from ..pathfinding import find_path
from ..bitacora import write_event


EPS = 1e-6


def choose_products_greedy(world: WorldState, voucher: float) -> List[str]:
    """
    Compra "la mayoría": meter la mayor cantidad posible (por precio ascendente)
    sin exceder el vale.
    """
    prods = sorted(world.map_data.products.values(), key=lambda p: p.price)
    selected: List[str] = []
    total = 0.0
    for p in prods:
        if total + p.price <= voucher + EPS:
            selected.append(p.sku)
            total += p.price
    return selected


def order_goals_nearest_neighbor(start: Pos, goals: List[Pos]) -> List[Pos]:
    remaining = goals[:]
    ordered: List[Pos] = []
    cur = start
    while remaining:
        nxt = min(remaining, key=lambda g: cur.manhattan(g))
        ordered.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    return ordered


@dataclass
class BuyerAgent:
    """
    Agente comprador.

    - Planifica qué productos recoger según el vale.
    - Se mueve por el mapa usando pathfinding (A*, Dijkstra, etc.).
    - Cuando termina de recoger o ya no le alcanza, se dirige a la caja y luego a la salida.
    """

    identificador: str = "comprador"

    # Alias de compatibilidad (inglés): `id`
    @property
    def id(self) -> str:
        return self.identificador

    @id.setter
    def id(self, value: str) -> None:
        self.identificador = value

    # ---------- Helpers ----------
    def _esta_en_cola_de_caja(self, world: WorldState) -> bool:
        b = world.buyer
        return any(b.pos == r.queue_spot for r in world.map_data.registers.values())

    def _cola_de_caja_mas_cercana(self, world: WorldState, from_pos: Pos) -> Pos:
        regs = list(world.map_data.registers.values())
        reg = min(regs, key=lambda r: from_pos.manhattan(r.queue_spot))
        return reg.queue_spot

    def _precio_minimo_restante(self, world: WorldState) -> Optional[float]:
        """
        Precio mínimo de los productos seleccionados que aún NO están en el carrito.
        Si no quedan productos, retorna None.
        """
        b = world.buyer
        remaining = [world.map_data.products[sku].price for sku in b.selected_skus if sku not in b.cart]
        if not remaining:
            return None
        return float(min(remaining))

    def _redireccionar_a_caja(self, world: WorldState, reason: str) -> None:
        """
        Corta cualquier ruta de picks y manda directo a cola de caja -> salida.
        """
        b = world.buyer

        # Si ya está pagado o ya está saliendo, no tocar
        if b.paid or b.goal_kind == "exit":
            return

        queue_spot = self._cola_de_caja_mas_cercana(world, b.pos)

        b.goal_queue = [queue_spot, world.map_data.exit]
        b.goal = b.goal_queue[0]
        b.goal_kind = "register"
        b.path = []

        world.log(f"➡️ Buyer va directo a caja ({reason}). Restante={b.budget_remaining:.2f}")

    # ---------- Planning ----------
        # ---------- Planificación ----------
    # Decide qué metas (estantes/cajas/salida) debe seguir el comprador.
    def planificar_si_es_necesario(self, world: WorldState) -> None:
        b = world.buyer

        # ya hay plan
        if b.selected_skus and b.goal_queue:
            return

        b.selected_skus = choose_products_greedy(world, b.voucher_amount)
        b.budget_remaining = b.voucher_amount

        pick_points = [world.map_data.products[sku].pick for sku in b.selected_skus]
        ordered_picks = order_goals_nearest_neighbor(b.pos, pick_points)

        # Caja más cercana al último pick (o a la posición actual si no hay picks)
        registers = list(world.map_data.registers.values())
        reg = min(
            registers,
            key=lambda r: (ordered_picks[-1].manhattan(r.queue_spot) if ordered_picks else b.pos.manhattan(r.queue_spot)),
        )

        world.log(
            f"Buyer seleccionó {len(b.selected_skus)} productos con vale={b.voucher_amount:.2f}. Caja elegida: {reg.id}"
        )

        # cola de metas: picks -> cola caja -> salida
        b.goal_queue = ordered_picks + [reg.queue_spot, world.map_data.exit]

        b.goal = b.goal_queue[0] if b.goal_queue else None
        b.goal_kind = "pick" if ordered_picks else "register"
        b.path = []

    # ---------- Pathing ----------
    def _asegurar_ruta(self, world: WorldState) -> None:
        b = world.buyer
        if b.goal is None:
            return
        if b.path and b.path[0] == b.pos:
            return
        b.path = find_path(b.algo, world.map_data.grid, b.pos, b.goal)

    # ---------- Goal transitions ----------
    def _avanzar_meta_si_alcanzo(self, world: WorldState) -> None:
        b = world.buyer
        if b.goal is None or b.pos != b.goal:
            return

        # Si estamos en la cola de una caja, NO avanzar hasta pagar
        if any(b.pos == r.queue_spot for r in world.map_data.registers.values()):
            b.goal_kind = "register"
            b.path = []

            # Solo cuando pagó, avanzar a salida
            if not b.paid:
                return

            # Pagó: consumir meta actual (la cola) y setear salida
            if b.goal_queue and b.goal_queue[0] == b.goal:
                b.goal_queue.pop(0)

            if not b.goal_queue:
                b.goal_queue = [world.map_data.exit]

            b.goal = b.goal_queue[0]
            b.goal_kind = "exit"
            b.path = []
            return

        # Si estamos en un punto pick, intentar tomar producto
        pick_to_sku = {world.map_data.products[sku].pick: sku for sku in b.selected_skus if sku not in b.cart}
        if b.goal in pick_to_sku:
            sku = pick_to_sku[b.goal]
            prod = world.map_data.products[sku]

            if prod.price <= b.budget_remaining + EPS:
                b.cart.append(sku)
                b.budget_remaining -= float(prod.price)

                ev = {
                    "event": "pick",
                    "world_step": world.step_count,
                    "agent": "buyer",
                    "sku": prod.sku,
                    "name": prod.name,
                    "price": float(prod.price),
                    "remaining": round(b.budget_remaining, 2),
                }
                b.purchase_log.append(ev)
                write_event(ev)

                world.log(f"Pick: {prod.name} (-{prod.price:.2f}) restante={b.budget_remaining:.2f}")
            else:
                world.log(f"No alcanza para {prod.name} (precio {prod.price:.2f}), se omite.")

        # ✅ Regla nueva:
        # Si el vale llegó a 0 (o ya no alcanza para ningún producto pendiente), ir directo a caja.
        if b.budget_remaining <= EPS:
            self._redireccionar_a_caja(world, "vale agotado (0)")
            return

        min_price = self._precio_minimo_restante(world)
        if min_price is None:
            # ya no quedan productos por recoger
            self._redireccionar_a_caja(world, "no quedan productos")
            return
        if min_price > b.budget_remaining + EPS:
            self._redireccionar_a_caja(world, "ya no alcanza para ningún producto")
            return

        # Consumir meta actual (si seguimos en modo pick)
        if b.goal_queue and b.goal_queue[0] == b.goal:
            b.goal_queue.pop(0)

        # Siguiente meta
        if b.goal_queue:
            b.goal = b.goal_queue[0]
            if b.goal == world.map_data.exit:
                b.goal_kind = "exit"
            elif any(b.goal == r.queue_spot for r in world.map_data.registers.values()):
                b.goal_kind = "register"
            else:
                b.goal_kind = "pick"
            b.path = []
        else:
            b.goal = None
            b.goal_kind = "idle"
            b.path = []

    # ---------- Step ----------
        # ---------- Ciclo principal del agente ----------
    # Se ejecuta en cada tick de simulación.
    def paso(self, world: WorldState) -> None:
        b = world.buyer

        self.planificar_si_es_necesario(world)

        # ✅ Si el vale se agotó en cualquier momento, a caja inmediatamente
        if b.budget_remaining <= EPS and not b.paid:
            self._redireccionar_a_caja(world, "vale agotado (0)")
            # si ya está en cola, se quedará esperando al cajero
            if self._esta_en_cola_de_caja(world):
                return

        # ✅ Si ya no puede comprar nada más, también a caja
        if not b.paid:
            mp = self._precio_minimo_restante(world)
            if mp is not None and mp > b.budget_remaining + EPS:
                self._redireccionar_a_caja(world, "ya no alcanza para ningún producto")

        # Si ya está parado en la cola, esperar al cajero
        if self._esta_en_cola_de_caja(world):
            b.goal_kind = "register"
            b.goal = b.pos
            b.path = []
            if not b.paid:
                return

        self._avanzar_meta_si_alcanzo(world)
        self._asegurar_ruta(world)

        if b.goal is None:
            return

        if not b.path:
            world.log("No se encontró ruta a la meta (posible bloqueo).")
            b.goal = None
            b.goal_kind = "idle"
            b.path = []
            return

        # Mover 1 celda
        if len(b.path) >= 2:
            old = b.pos
            b.pos = b.path[1]
            b.path = b.path[1:]
            if b.pos != old:
                b.steps_moved += 1



    # --- Alias de compatibilidad (inglés) ---
    # Mantiene el API previo del proyecto (frontend / endpoints / tests),
    # pero la lógica real vive en los métodos en español.
    def step(self, world: WorldState) -> None:
        """Alias: llama a :meth:`paso`."""
        return self.paso(world)

    def plan_if_needed(self, world: WorldState) -> None:
        return self.planificar_si_es_necesario(world)

    def _ensure_path(self, world: WorldState) -> None:
        return self._asegurar_ruta(world)

    def _advance_goal_if_reached(self, world: WorldState) -> None:
        return self._avanzar_meta_si_alcanzo(world)

    def _is_on_register_queue(self, world: WorldState) -> bool:
        return self._esta_en_cola_de_caja(world)

    def _nearest_register_queue(self, world: WorldState, from_pos: Pos) -> Pos:
        return self._cola_de_caja_mas_cercana(world, from_pos)

    def _min_price_remaining(self, world: WorldState) -> Optional[float]:
        return self._precio_minimo_restante(world)

    def _reroute_to_register(self, world: WorldState, reason: str) -> None:
        return self._redireccionar_a_caja(world, reason)
