from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

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
        (Evita 'ghost scans' cuando vale=0 o carrito vacío.)
        """
        b = world.buyer
        c = world.cashier
        scanned = set(c.scanned_skus)

        for sku in b.cart:
            if sku not in scanned:
                return sku
        return None

    def _registrar_escaneo(self, world: WorldState, sku: str) -> None:
        b = world.buyer
        c = world.cashier
        prod = world.map_data.products.get(sku)
        if not prod:
            return

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
        Canjea el vale (si vale=0, simplemente termina sin escanear nada).
        """
        b = world.buyer
        c = world.cashier

        voucher = float(b.voucher_amount)
        subtotal = float(c.subtotal)

        # El comprador ya debería haber comprado <= vale,
        # pero igual protegemos:
        redeemed = min(subtotal, voucher)

        c.redeemed_amount = float(redeemed)
        c.voucher_remaining = float(max(0.0, voucher - redeemed))

        # Mantener coherencia con el comprador
        b.budget_remaining = float(c.voucher_remaining)

        ev: Dict[str, Any] = {
            "event": "redeem",
            "world_step": world.step_count,
            "agent": "cashier",
            "subtotal": round(subtotal, 2),
            "voucher": round(voucher, 2),
            "redeemed": round(redeemed, 2),
            "remaining": round(float(c.voucher_remaining), 2),
        }
        c.scan_log.append(ev)
        c.last_scan = ev
        write_event(ev)

        world.log(f"✅ Canje vale: subtotal={subtotal:.2f} vale={voucher:.2f} restante={c.voucher_remaining:.2f}")

        b.paid = True
        c.status = "done"

        # ---------- Ciclo principal del agente ----------
    # Se ejecuta en cada tick: escanea o finaliza el pago.
    def paso(self, world: WorldState) -> None:
        """
        Reglas:
        - El cajero NO se mueve y NO cuenta pasos.
        - Solo trabaja si el comprador está en la cola de una caja.
        - Solo escanea productos que existen en buyer.cart.
        - Si el carrito está vacío (vale=0 o no compró nada): redeem directo (0) y termina.
        """
        b = world.buyer
        c = world.cashier

        # Si el comprador ya pagó, el cajero no hace nada
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

        # Fijar posición del cajero en su caja (sin "caminar")
        reg = world.map_data.registers[reg_id]
        c.pos = reg.cashier_spot  # el cajero es estático

        # Inicializar campos si vienen None
        if c.scanned_skus is None:
            c.scanned_skus = []
        if c.scan_log is None:
            c.scan_log = []
        if c.subtotal is None:
            c.subtotal = 0.0
        if c.redeemed_amount is None:
            c.redeemed_amount = 0.0
        if c.voucher_remaining is None:
            c.voucher_remaining = float(b.voucher_amount)

        # ✅ Caso crítico: vale=0 o no compró nada => carrito vacío
        if not b.cart:
            # no generes scans fantasma
            c.subtotal = 0.0
            self._canjear_vale(world)  # redeem será 0 si voucher=0
            return

        # Escanea 1 por step
        next_sku = self._siguiente_sku_a_escanear(world)
        if next_sku:
            c.status = "scanning"
            self._registrar_escaneo(world, next_sku)
            return

        # Ya escaneó todo el carrito -> canjear
        c.status = "redeeming"
        self._canjear_vale(world)
    # --- Alias de compatibilidad (inglés) ---
    def step(self, world: WorldState) -> None:
        """Alias: llama a :meth:`paso`."""
        return self.paso(world)

    def _find_active_register(self, world: WorldState) -> Optional[str]:
        return self._encontrar_caja_activa(world)

    def _next_sku_to_scan(self, world: WorldState) -> Optional[str]:
        return self._siguiente_sku_a_escanear(world)

    def _log_scan(self, world: WorldState, scan: Dict[str, Any]) -> None:
        return self._registrar_escaneo(world, scan)

    def _redeem_voucher(self, world: WorldState) -> None:
        return self._canjear_vale(world)
