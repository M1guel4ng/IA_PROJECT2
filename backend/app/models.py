from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterator


@dataclass(frozen=True, slots=True)
class Pos:
    x: int
    y: int

    # Alias semánticos en español (para lectura)
    @property
    def columna(self) -> int:
        return self.x

    @property
    def fila(self) -> int:
        return self.y

    def distancia_manhattan(self, otro: "Pos") -> int:
        """Distancia Manhattan (|dx| + |dy|) entre dos posiciones."""
        return abs(self.x - otro.x) + abs(self.y - otro.y)

    # Alias de compatibilidad (inglés)
    def manhattan(self, other: "Pos") -> int:
        return self.distancia_manhattan(other)



@dataclass(slots=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def contiene(self, p: Pos) -> bool:
        """True si una posición está dentro del rectángulo."""
        return self.x <= p.x < self.x + self.w and self.y <= p.y < self.y + self.h

    # Alias de compatibilidad (inglés)
    def contains(self, p: Pos) -> bool:
        return self.contiene(p)

    def iterar_celdas(self) -> Iterator[Pos]:
        """Itera todas las celdas cubiertas por el rectángulo."""
        for yy in range(self.y, self.y + self.h):
            for xx in range(self.x, self.x + self.w):
                yield Pos(xx, yy)

    # ✅ FIX: data_loader.py usa rect.iter_cells()
    # Alias de compatibilidad (inglés)
    def iter_cells(self) -> Iterator[Pos]:
        return self.iterar_celdas()



@dataclass(slots=True)
class Grid:
    width: int
    height: int
    walkable: List[List[bool]]

    # ---- Helpers en español ----
    def en_limites(self, p: Pos) -> bool:
        """True si p está dentro de [0,width) x [0,height)."""
        return 0 <= p.x < self.width and 0 <= p.y < self.height

    def es_transitable(self, p: Pos) -> bool:
        """True si la celda es caminable/transitable."""
        if not self.en_limites(p):
            return False
        return bool(self.walkable[p.y][p.x])

    def bloquear(self, p: Pos, bloqueado: bool = True) -> None:
        """Marca una celda como bloqueada (no caminable)."""
        if self.en_limites(p):
            self.walkable[p.y][p.x] = not bloqueado

    def bloquear_rectangulo(self, r: Rect) -> None:
        """Bloquea todas las celdas cubiertas por un rectángulo."""
        for cell in r.iter_cells():
            self.bloquear(cell, True)

    def iterar_celdas(self):
        """Itera todas las posiciones (Pos) del grid."""
        for y in range(self.height):
            for x in range(self.width):
                yield Pos(x, y)

    # ---- Alias de compatibilidad (inglés) ----
    def in_bounds(self, p: Pos) -> bool:
        return self.en_limites(p)

    def is_walkable(self, p: Pos) -> bool:
        return self.es_transitable(p)

    def set_blocked(self, p: Pos, blocked: bool = True) -> None:
        return self.bloquear(p, bloqueado=blocked)

    def block_rect(self, r: Rect) -> None:
        return self.bloquear_rectangulo(r)

    def iter_cells(self):
        return self.iterar_celdas()



@dataclass(slots=True)
class Shelf:
    id: str
    rect: Rect
    section: str


@dataclass(slots=True)
class Register:
    id: str
    cashier_spot: Pos
    queue_spot: Pos


@dataclass(slots=True)
class Section:
    id: str
    label: str


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    price: float
    section: str
    shelf: str
    pick: Pos


@dataclass(slots=True)
class MapData:
    name: str
    city: str
    grid: Grid
    entrance: Pos
    exit: Pos
    shelves: Dict[str, Shelf]
    registers: Dict[str, Register]
    sections: Dict[str, Section]
    products: Dict[str, Product]


@dataclass(slots=True)
class BuyerState:
    pos: Pos
    algo: str = "dijkstra"
    voucher_amount: float = 120.0
    budget_remaining: float = 120.0

    selected_skus: List[str] = field(default_factory=list)
    cart: List[str] = field(default_factory=list)

    goal: Optional[Pos] = None
    goal_kind: str = "idle"  # idle | pick | register | exit
    path: List[Pos] = field(default_factory=list)
    goal_queue: List[Pos] = field(default_factory=list)

    paid: bool = False

    # ✅ Utilidad + cambio
    utility_total: float = 0.0
    change_received: float = 0.0
    section_weights: Dict[str, float] = field(default_factory=dict)

    # métricas
    steps_moved: int = 0

    # bitácora del buyer (pick)
    purchase_log: List[dict] = field(default_factory=list)

    # --- Alias en español (propiedades) ---
    @property
    def posicion(self) -> Pos:
        return self.pos

    @posicion.setter
    def posicion(self, value: Pos) -> None:
        self.pos = value

    @property
    def algoritmo(self) -> str:
        return self.algo

    @algoritmo.setter
    def algoritmo(self, value: str) -> None:
        self.algo = value

    @property
    def monto_vale(self) -> float:
        return self.voucher_amount

    @monto_vale.setter
    def monto_vale(self, value: float) -> None:
        self.voucher_amount = float(value)

    @property
    def presupuesto_restante(self) -> float:
        return self.budget_remaining

    @presupuesto_restante.setter
    def presupuesto_restante(self, value: float) -> None:
        self.budget_remaining = float(value)

    @property
    def skus_seleccionados(self) -> List[str]:
        return self.selected_skus

    @property
    def carrito(self) -> List[str]:
        return self.cart

    @property
    def meta(self) -> Optional[Pos]:
        return self.goal

    @meta.setter
    def meta(self, value: Optional[Pos]) -> None:
        self.goal = value

    @property
    def tipo_meta(self) -> str:
        return self.goal_kind

    @tipo_meta.setter
    def tipo_meta(self, value: str) -> None:
        self.goal_kind = value

    @property
    def ruta(self) -> List[Pos]:
        return self.path

    @property
    def cola_metas(self) -> List[Pos]:
        return self.goal_queue

    @property
    def pagado(self) -> bool:
        return self.paid

    @pagado.setter
    def pagado(self, value: bool) -> None:
        self.paid = bool(value)

    @property
    def utilidad(self) -> float:
        return self.utility_total

    @property
    def cambio_recibido(self) -> float:
        return self.change_received

    @property
    def pasos_movidos(self) -> int:
        return self.steps_moved

    @property
    def bitacora_compra(self) -> List[dict]:
        return self.purchase_log



@dataclass(slots=True)
class CashierState:
    pos: Pos
    register_id: str = "R1"
    status: str = "idle"  # idle | scanning | redeeming | done
    busy_ticks: int = 0

    scan_index: int = 0
    scanned_skus: List[str] = field(default_factory=list)
    subtotal: float = 0.0
    redeemed_amount: float = 0.0
    voucher_remaining: float = 0.0

    # ✅ cambio entregado
    change_given: float = 0.0

    last_scan: Optional[dict] = None
    scan_log: List[dict] = field(default_factory=list)

    # --- Alias en español (propiedades) ---
    @property
    def posicion(self) -> Pos:
        return self.pos

    @posicion.setter
    def posicion(self, value: Pos) -> None:
        self.pos = value

    @property
    def id_caja(self) -> str:
        return self.register_id

    @id_caja.setter
    def id_caja(self, value: str) -> None:
        self.register_id = value

    @property
    def estado(self) -> str:
        return self.status

    @estado.setter
    def estado(self, value: str) -> None:
        self.status = value

    @property
    def subtotal_actual(self) -> float:
        return self.subtotal

    @property
    def monto_canjeado(self) -> float:
        return self.redeemed_amount

    @property
    def vale_restante(self) -> float:
        return self.voucher_remaining

    @property
    def cambio_entregado(self) -> float:
        return self.change_given

    @property
    def ultimo_escaneo(self) -> Optional[dict]:
        return self.last_scan

    @property
    def bitacora_escaneo(self) -> List[dict]:
        return self.scan_log



@dataclass(slots=True)
class WorldState:
    map_data: MapData
    buyer: BuyerState
    cashier: CashierState
    step_count: int = 0
    messages: List[str] = field(default_factory=list)

    def registrar_mensaje(self, msg: str) -> None:
        """Agrega un mensaje al log del mundo (para mostrar en el frontend)."""
        self.messages.append(msg)

    # Alias de compatibilidad (inglés)
    def log(self, msg: str) -> None:
        return self.registrar_mensaje(msg)

    # --- Alias en español (propiedades) ---
    @property
    def datos_mapa(self) -> "MapData":
        return self.map_data

    @property
    def comprador(self) -> "BuyerState":
        return self.buyer

    @property
    def cajero(self) -> "CashierState":
        return self.cashier

    @property
    def contador_pasos(self) -> int:
        return self.step_count

    @property
    def mensajes(self) -> List[str]:
        return self.messages

