from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from .models import Grid, Pos


def neighbors4(grid: Grid, p: Pos) -> List[Pos]:
    candidates = [Pos(p.x + 1, p.y), Pos(p.x - 1, p.y), Pos(p.x, p.y + 1), Pos(p.x, p.y - 1)]
    return [c for c in candidates if grid.is_walkable(c)]


def reconstruct(came_from: Dict[Pos, Optional[Pos]], goal: Pos) -> List[Pos]:
    if goal not in came_from:
        return []
    path: List[Pos] = []
    cur: Optional[Pos] = goal
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    path.reverse()
    return path


def bfs(grid: Grid, start: Pos, goal: Pos) -> List[Pos]:
    if start == goal:
        return [start]
    from collections import deque
    q = deque([start])
    came_from: Dict[Pos, Optional[Pos]] = {start: None}
    while q:
        cur = q.popleft()
        for nb in neighbors4(grid, cur):
            if nb in came_from:
                continue
            came_from[nb] = cur
            if nb == goal:
                return reconstruct(came_from, goal)
            q.append(nb)
    return []


def dijkstra(grid: Grid, start: Pos, goal: Pos) -> List[Pos]:
    if start == goal:
        return [start]

    # ✅ contador para desempates (evita comparar Pos en heap)
    counter = 0
    pq: List[Tuple[int, int, Pos]] = [(0, counter, start)]
    dist: Dict[Pos, int] = {start: 0}
    came_from: Dict[Pos, Optional[Pos]] = {start: None}

    while pq:
        d, _, cur = heapq.heappop(pq)
        if cur == goal:
            return reconstruct(came_from, goal)
        if d != dist.get(cur, 10**18):
            continue

        for nb in neighbors4(grid, cur):
            nd = d + 1
            if nd < dist.get(nb, 10**18):
                dist[nb] = nd
                came_from[nb] = cur
                counter += 1
                heapq.heappush(pq, (nd, counter, nb))

    return []


def astar(grid: Grid, start: Pos, goal: Pos) -> List[Pos]:
    if start == goal:
        return [start]

    counter = 0
    g: Dict[Pos, int] = {start: 0}
    came_from: Dict[Pos, Optional[Pos]] = {start: None}

    # (f, counter, node)
    pq: List[Tuple[int, int, Pos]] = [(start.manhattan(goal), counter, start)]

    while pq:
        _, _, cur = heapq.heappop(pq)
        if cur == goal:
            return reconstruct(came_from, goal)

        gcost = g.get(cur, 10**18)

        for nb in neighbors4(grid, cur):
            ng = gcost + 1
            if ng < g.get(nb, 10**18):
                g[nb] = ng
                came_from[nb] = cur
                counter += 1
                f = ng + nb.manhattan(goal)
                heapq.heappush(pq, (f, counter, nb))

    return []


def find_path(algo: str, grid: Grid, start: Pos, goal: Pos) -> List[Pos]:
    algo = (algo or "astar").lower()
    if algo in ("bfs",):
        return bfs(grid, start, goal)
    if algo in ("dijkstra", "dijsktra", "dj"):
        return dijkstra(grid, start, goal)
    if algo in ("astar", "a*", "a-star"):
        return astar(grid, start, goal)
    raise ValueError(f"Unknown algo: {algo}")
