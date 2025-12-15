from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from ..models import WorldState
from ..bitacora import write_event

EPS = 1e-6


@dataclass
class CashierAgent:
    """
    Agente cajero.

    - Encuentra la caja activa (donde está esperando el comprador).
    - Escanea productos del carrito y calcula subtotal.
    - Canjea el vale y registra el pago/cambio.
    """

    identificador: str = "cajero"

    # Alias de compatibilidad (inglés): `id`
    @property
    def id(self) -> str:
        return self.identificador

    @id.setter
    def id(self, value: str) -> None:
        self.identificador = value

    # ---------- Helpers ----------
    def _encontrar_caja_activa(self, world: WorldState) -> Optional[str]:
        """
        Devuelve el id de la caja cuyo queue_spot coincide con la posición del comprador.
        """
        b = world.buyer
        for r in world.map_data.registers.values():
            if b.pos == r.queue_spot:
                return r.id
        return None

    def _siguiente_sku_a_escanear(self, world: WorldState) -> Optional[str]:
        """
        Escanea SOLO lo que el comprador realmente tiene en el carrito.
        """
        b = world.buyer
        c = world.cashier
        scanned = set(c.scanned_skus or [])

        for sku in b.cart or []:
            if sku not in scanned:
                return sku
        return None

    def _registrar_escaneo(self, world: WorldState, sku: str) -> None:
        c = world.cashier
        prod = world.map_data.products.get(sku)
        if not prod:
            return

        if c.scanned_skus is None:
            c.scanned_skus = []
        if c.scan_log is None:
            c.scan_log = []
        if c.subtotal is None:
            c.subtotal = 0.0

        c.scanned_skus.append(sku)
        c.subtotal = float(c.subtotal) + float(prod.price)

        ev: Dict[str, Any] = {
            "event": "scan",
            "world_step": world.step_count,
            "agent": "cashier",
            "sku": prod.sku,
            "name": prod.name,
            "price": float(prod.price),
            "subtotal": round(float(c.subtotal), 2),
        }
        c.scan_log.append(ev)
        c.last_scan = ev
        write_event(ev)

        world.log(f"🧾 Cajero escaneó: {prod.name} (+{prod.price:.2f}) subtotal={c.subtotal:.2f}")

    def _canjear_vale(self, world: WorldState) -> None:
        """
        Canjea el vale y, si sobra dinero, devuelve cambio.
        """
        b = world.buyer
        c = world.cashier

        if c.scan_log is None:
            c.scan_log = []
        if c.subtotal is None:
            c.subtotal = 0.0
        if c.redeemed_amount is None:
            c.redeemed_amount = 0.0
        if c.voucher_remaining is None:
            c.voucher_remaining = float(b.voucher_amount)
        if c.change_given is None:
            c.change_given = 0.0

        voucher = float(b.voucher_amount or 0.0)
        subtotal = float(c.subtotal or 0.0)

        redeemed = min(subtotal, voucher)
        change = max(0.0, voucher - subtotal)

        c.redeemed_amount = float(redeemed)
        c.change_given = float(change)

        # el vale se consume al pagar
        c.voucher_remaining = 0.0

        # cerrar compra en comprador
        b.budget_remaining = 0.0
        b.change_received = float(change)

        ev: Dict[str, Any] = {
            "event": "redeem",
            "world_step": world.step_count,
            "agent": "cashier",
            "subtotal": round(subtotal, 2),
            "voucher": round(voucher, 2),
            "redeemed": round(redeemed, 2),
            "change_given": round(change, 2),
        }
        c.scan_log.append(ev)
        c.last_scan = ev
        write_event(ev)

        world.log(
            f"✅ Pago: subtotal={subtotal:.2f} vale={voucher:.2f} "
            f"canjeado={redeemed:.2f} cambio={change:.2f}"
        )

        b.paid = True
        c.status = "done"

    # ---------- Ciclo principal ----------
    def paso(self, world: WorldState) -> None:
        """
        Se ejecuta en cada tick.
        - Solo trabaja si el comprador está en la cola de una caja.
        - Escanea 1 SKU por tick.
        - Al final canjea vale y devuelve cambio si corresponde.
        """
        b = world.buyer
        c = world.cashier

        # Si ya pagó, no hacer nada
        if b.paid:
            c.status = "idle"
            return

        reg_id = self._encontrar_caja_activa(world)
        if not reg_id:
            c.status = "idle"
            c.register_id = None
            return

        # Enganchar caja
        c.register_id = reg_id
        c.status = c.status or "scanning"

        # Fijar posición del cajero en su caja
        reg = world.map_data.registers[reg_id]
        c.pos = reg.cashier_spot

        # Inicializar campos
        if c.scanned_skus is None:
            c.scanned_skus = []
        if c.scan_log is None:
            c.scan_log = []
        if c.subtotal is None:
            c.subtotal = 0.0
        if c.redeemed_amount is None:
            c.redeemed_amount = 0.0
        if c.voucher_remaining is None:
            c.voucher_remaining = float(b.voucher_amount or 0.0)
        if c.change_given is None:
            c.change_given = 0.0

        # Si no hay carrito -> canje directo (redeem=0 si voucher=0)
        if not (b.cart or []):
            c.subtotal = 0.0
            c.status = "redeeming"
            self._canjear_vale(world)
            return

        # Escanea 1 por paso
        next_sku = self._siguiente_sku_a_escanear(world)
        if next_sku:
            c.status = "scanning"
            self._registrar_escaneo(world, next_sku)
            return

        # Ya escaneó todo -> canjear
        c.status = "redeeming"
        self._canjear_vale(world)

    # Alias inglés (por compatibilidad)
    def step(self, world: WorldState) -> None:
        return self.paso(world)

    def _find_active_register(self, world: WorldState) -> Optional[str]:
        return self._encontrar_caja_activa(world)

    def _next_sku_to_scan(self, world: WorldState) -> Optional[str]:
        return self._siguiente_sku_a_escanear(world)

    def _log_scan(self, world: WorldState, sku: str) -> None:
        return self._registrar_escaneo(world, sku)

    def _redeem_voucher(self, world: WorldState) -> None:
        return self._canjear_vale(world)
