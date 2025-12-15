from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from ..data_loader import load_city_graph
from ..agents.taxi import TaxiSTRIPSPlanner, TaxiAction


@dataclass
class TravelState:
    step: int = 0
    finished: bool = False

    buyer_home: str = ""
    buyer_node: str = ""      # si va en taxi, sigue a taxi_node
    taxi_node: str = ""
    taxi_onboard: bool = False

    store_node: str = ""
    branch_id: str = ""

    plan: List[TaxiAction] = field(default_factory=list)
    plan_index: int = 0

    messages: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.messages.append(msg)


class TravelWorld:
    def __init__(self, graph_file: str | None = None, seed: int = 123):
        random.seed(seed)

        g = load_city_graph(graph_file)
        self.meta = g.get("meta", {})
        self.nodes: Dict[str, dict] = {n["id"]: n for n in g.get("nodes", [])}

        # adj usa COST si existe, si no DISTANCE
        self.adj: Dict[str, List[Tuple[str, float]]] = {}
        for e in g.get("edges", []):
            a = e["a"]
            b = e["b"]
            w = float(e.get("cost", e.get("distance", 1.0)))
            self.adj.setdefault(a, []).append((b, w))
            if e.get("bidirectional", True):
                self.adj.setdefault(b, []).append((a, w))

        self.edges = g.get("edges", [])
        self.stores = g.get("stores", [])  # {branch_id,node_id,name}
        self.homes = [nid for nid, n in self.nodes.items() if n.get("kind") == "home"]
        self.taxi_stands = [nid for nid, n in self.nodes.items() if n.get("kind") in ("taxi_stand", "taxi")]

        self.planner = TaxiSTRIPSPlanner(self.nodes, self.adj)
        self.state = TravelState()
        self.reset()

    def _dijkstra(self, start: str, goal: str) -> float:
        import heapq
        pq = [(0.0, start)]
        best = {start: 0.0}
        while pq:
            d, u = heapq.heappop(pq)
            if u == goal:
                return d
            if d != best.get(u):
                continue
            for v, w in self.adj.get(u, []):
                nd = d + float(w)
                if nd < best.get(v, 1e18):
                    best[v] = nd
                    heapq.heappush(pq, (nd, v))
        return float("inf")

    def _nearest_store(self, home_node: str) -> tuple[str, str]:
        best = (float("inf"), "", "")
        for s in self.stores:
            node_id = s.get("node_id", "")
            branch_id = s.get("branch_id", "")
            if node_id and branch_id and node_id in self.nodes:
                d = self._dijkstra(home_node, node_id)
                if d < best[0]:
                    best = (d, branch_id, node_id)
        if not best[1]:
            raise RuntimeError("No hay stores válidos en el grafo.")
        return best[1], best[2]

    def reset(self, home_id: Optional[str] = None, taxi_start: Optional[str] = None) -> TravelState:
        home = home_id or (random.choice(self.homes) if self.homes else random.choice(list(self.nodes.keys())))
        if home not in self.nodes:
            raise ValueError("home_id inválido")

        taxi = taxi_start or (random.choice(self.taxi_stands) if self.taxi_stands else random.choice(list(self.nodes.keys())))
        if taxi not in self.nodes:
            raise ValueError("taxi_start inválido")

        branch_id, store_node = self._nearest_store(home)

        plan = self.planner.plan(taxi_start=taxi, buyer_home=home, store=store_node)

        self.state = TravelState(
            step=0,
            finished=False,
            buyer_home=home,
            buyer_node=home,
            taxi_node=taxi,
            taxi_onboard=False,
            store_node=store_node,
            branch_id=branch_id,
            plan=plan,
            plan_index=0,
            messages=[],
        )
        self.state.log(f"🏠 Casa={home}")
        self.state.log(f"🏬 Destino={branch_id} (node={store_node})")
        self.state.log(f"🚕 Taxi inicia en {taxi} | Plan={len(plan)} acciones")
        return self.state

    def step(self, n: int = 1) -> TravelState:
        for _ in range(n):
            if self.state.finished:
                break
            if self.state.plan_index >= len(self.state.plan):
                self.state.finished = True
                self.state.log("✅ Fin (sin más acciones).")
                break

            act = self.state.plan[self.state.plan_index]
            self._apply(act)
            self.state.plan_index += 1
            self.state.step += 1

            if (self.state.buyer_node == self.state.store_node) and (not self.state.taxi_onboard):
                self.state.finished = True
                self.state.log("✅ Llegaron al Hipermaxi.")
                break

        return self.state

    def _apply(self, act: TaxiAction) -> None:
        s = self.state

        if act.kind == "move":
            s.taxi_node = act.b or s.taxi_node
            if s.taxi_onboard:
                s.buyer_node = s.taxi_node
            s.log(f"🚕 move {act.a}→{act.b} (cost={act.cost:.3f})")
            return

        if act.kind == "pickup":
            s.taxi_onboard = True
            s.buyer_node = s.taxi_node
            s.log("🧍‍♂️➡️🚕 pickup")
            return

        if act.kind == "dropoff":
            s.taxi_onboard = False
            s.buyer_node = s.store_node
            s.log("🚕➡️🏬 dropoff")
            return

        s.log(f"⚠️ acción desconocida: {act.kind}")

    def graph_dict(self) -> dict:
        return {
            "meta": self.meta,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "stores": self.stores,
            "homes": self.homes,
            "taxi_stands": self.taxi_stands,
        }

    def to_dict(self) -> dict:
        s = self.state
        next_act = None
        if s.plan_index < len(s.plan):
            a = s.plan[s.plan_index]
            next_act = {"kind": a.kind, "a": a.a, "b": a.b, "cost": a.cost}

        return {
            "step": s.step,
            "finished": s.finished,
            "buyer": {"home": s.buyer_home, "node": s.buyer_node},
            "taxi": {"node": s.taxi_node, "onboard": s.taxi_onboard},
            "target": {"branch_id": s.branch_id, "store_node": s.store_node},
            "plan": {"len": len(s.plan), "index": s.plan_index, "next": next_act},
            "messages": s.messages[-200:],
        }
