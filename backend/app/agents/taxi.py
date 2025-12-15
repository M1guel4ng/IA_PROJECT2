from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import heapq
from itertools import count


# -------------------- MODELOS --------------------

@dataclass(frozen=True)
class TaxiState:
    """
    Estado mínimo (STRIPS):
    - taxi_node: nodo donde está el taxi
    - buyer_node: nodo donde está el comprador (si onboard=True, sigue al taxi)
    - onboard: si el comprador está dentro del taxi
    """
    taxi_node: str
    buyer_node: str
    onboard: bool


@dataclass(frozen=True)
class TaxiAction:
    """
    Acción STRIPS aplicada:
    - kind: "move" | "pickup" | "dropoff"
    - a: origen (para move)
    - b: destino (para move)
    - cost: costo del movimiento (0 para pickup/dropoff)
    """
    kind: str
    a: Optional[str] = None
    b: Optional[str] = None
    cost: float = 0.0


# -------------------- PLANNER (A* + STRIPS) --------------------

class TaxiSTRIPSPlanner:
    def __init__(self, nodes: Dict[str, dict], adj: Dict[str, List[Tuple[str, float]]]):
        self.nodes = nodes
        self.adj = adj

    def _xy(self, node_id: str) -> Tuple[float, float]:
        n = self.nodes.get(node_id) or {}
        return float(n.get("x", 0.0)), float(n.get("y", 0.0))

    def _dist(self, a: str, b: str) -> float:
        ax, ay = self._xy(a)
        bx, by = self._xy(b)
        return math.hypot(ax - bx, ay - by)

    def _h(self, s: TaxiState, store: str) -> float:
        """
        Heurística admisible (aprox):
        - si no onboard: ir taxi->buyer + buyer->store
        - si onboard: ir taxi->store
        """
        if s.onboard:
            return self._dist(s.taxi_node, store)
        return self._dist(s.taxi_node, s.buyer_node) + self._dist(s.buyer_node, store)

    def _is_goal(self, s: TaxiState, store: str) -> bool:
        return (not s.onboard) and (s.buyer_node == store)

    def _successors(self, s: TaxiState, buyer_home: str, store: str) -> List[Tuple[TaxiAction, TaxiState, float]]:
        out: List[Tuple[TaxiAction, TaxiState, float]] = []

        # MOVE: taxi se mueve por aristas; si onboard, comprador sigue al taxi
        for nxt, w in self.adj.get(s.taxi_node, []):
            ns = TaxiState(
                taxi_node=nxt,
                buyer_node=(nxt if s.onboard else s.buyer_node),
                onboard=s.onboard,
            )
            out.append((TaxiAction(kind="move", a=s.taxi_node, b=nxt, cost=float(w)), ns, float(w)))

        # PICKUP: si taxi está donde está el comprador (en casa) y no está onboard
        if (not s.onboard) and (s.taxi_node == s.buyer_node):
            ns = TaxiState(taxi_node=s.taxi_node, buyer_node=s.taxi_node, onboard=True)
            out.append((TaxiAction(kind="pickup", a=s.taxi_node, b=s.taxi_node, cost=0.0), ns, 0.0))

        # DROPOFF: si onboard y taxi llegó al store
        if s.onboard and (s.taxi_node == store):
            ns = TaxiState(taxi_node=s.taxi_node, buyer_node=store, onboard=False)
            out.append((TaxiAction(kind="dropoff", a=s.taxi_node, b=store, cost=0.0), ns, 0.0))

        return out

    def plan(self, taxi_start: str, buyer_home: str, store: str) -> List[TaxiAction]:
        """
        Plan STRIPS: A* sobre estados con acciones move/pickup/dropoff.
        """
        start = TaxiState(taxi_node=taxi_start, buyer_node=buyer_home, onboard=False)

        # frontier = (f, tie, g, state)
        seq = count()
        frontier: List[Tuple[float, int, float, TaxiState]] = []
        heapq.heappush(frontier, (self._h(start, store), next(seq), 0.0, start))

        best_g: Dict[TaxiState, float] = {start: 0.0}
        parent: Dict[TaxiState, TaxiState] = {}
        parent_action: Dict[TaxiState, TaxiAction] = {}

        while frontier:
            _, _, g, cur = heapq.heappop(frontier)

            # si esta entrada ya no es la mejor, skip
            if g != best_g.get(cur, float("inf")):
                continue

            if self._is_goal(cur, store):
                return self._reconstruct(cur, parent, parent_action)

            for act, nxt, step_cost in self._successors(cur, buyer_home, store):
                ng = g + float(step_cost)
                if ng < best_g.get(nxt, float("inf")):
                    best_g[nxt] = ng
                    parent[nxt] = cur
                    parent_action[nxt] = act
                    f = ng + self._h(nxt, store)
                    heapq.heappush(frontier, (f, next(seq), ng, nxt))

        # si no encuentra, devolver vacío (no debería pasar si grafo conecta)
        return []

    def _reconstruct(
        self,
        goal: TaxiState,
        parent: Dict[TaxiState, TaxiState],
        parent_action: Dict[TaxiState, TaxiAction],
    ) -> List[TaxiAction]:
        actions: List[TaxiAction] = []
        cur = goal
        while cur in parent:
            actions.append(parent_action[cur])
            cur = parent[cur]
        actions.reverse()
        return actions
