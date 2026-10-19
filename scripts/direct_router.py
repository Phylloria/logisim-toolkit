"""Deterministic orthogonal maze routing for direct-wire Logisim circuits.

The router accepts fixed component coordinates and routes each net as a tree.
It never creates Tunnel components. Existing nets are obstacles, so separate
nets do not overlap or form accidental junctions.
"""
from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


Point = tuple[int, int]


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int


def rect_points(rect: tuple[int, int, int, int], grid: int) -> set[Point]:
    """Return grid points strictly inside a component body."""
    left, top, right, bottom = rect
    points = set()
    x = ((left // grid) + 1) * grid
    while x < right:
        y = ((top // grid) + 1) * grid
        while y < bottom:
            points.add((x, y))
            y += grid
        x += grid
    return points


def manhattan(left: Point, right: Point) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def compress_path(points: list[Point]) -> list[tuple[Point, Point]]:
    if len(points) < 2:
        return []
    for left, right in zip(points, points[1:]):
        distance = abs(left[0] - right[0]) + abs(left[1] - right[1])
        if distance == 0:
            raise RuntimeError("route contains a duplicate point")
        if distance != 10:
            raise RuntimeError(f"route contains non-adjacent points {left} -> {right}")
    segments = []
    start = points[0]
    previous = points[0]
    direction = (
        "H",
        1 if points[1][0] > previous[0] else -1,
    ) if points[1][0] != previous[0] else (
        "V",
        1 if points[1][1] > previous[1] else -1,
    )
    for point in points[1:]:
        new_direction = (
            "H",
            1 if point[0] > previous[0] else -1,
        ) if point[0] != previous[0] else (
            "V",
            1 if point[1] > previous[1] else -1,
        )
        if new_direction != direction:
            if previous != start:
                segments.append((start, previous))
            start = previous
            direction = new_direction
        previous = point
    if previous != start:
        segments.append((start, previous))
    return segments


def route_net(
    terminals: list[Point],
    *,
    bounds: Bounds,
    grid: int,
    obstacle_nodes: set[Point],
    occupied: set[Point],
    occupied_edges: set[tuple[Point, Point]],
    occupied_junctions: set[Point],
    reserved: set[Point],
    max_states: int = 800_000,
) -> list[tuple[Point, Point]]:
    """Route a source/fanout tree from terminals[0] to every other terminal."""
    if len(terminals) < 2:
        return []
    own_terminals = set(terminals)
    tree = {terminals[0]}
    pending = sorted(terminals[1:], key=lambda point: manhattan(point, terminals[0]))
    all_segments: list[tuple[Point, Point]] = []
    moves = ((grid, 0), (-grid, 0), (0, grid), (0, -grid))
    directions = {(grid, 0): 0, (-grid, 0): 1, (0, grid): 2, (0, -grid): 3}

    while pending:
        target = pending.pop(0)

        def edge_key(left: Point, right: Point) -> tuple[Point, Point]:
            return (left, right) if left <= right else (right, left)

        def allowed(point: Point, direction: int, previous_direction: int) -> bool:
            x, y = point
            if not (bounds.left <= x <= bounds.right and bounds.top <= y <= bounds.bottom):
                return False
            if point in tree:
                return True
            if point in obstacle_nodes:
                return False
            if point in reserved and point not in own_terminals:
                return False
            if point in occupied and point not in own_terminals:
                # A perpendicular crossing is unconnected in Logisim, but a turn
                # at the crossing would create an endpoint and accidentally join nets.
                if (previous_direction == -1 or previous_direction != direction
                        or point in occupied_junctions):
                    return False
            if edge_key((x, y), (x + moves[direction][0], y + moves[direction][1])) in occupied_edges:
                return False
            return True

        start_state = (target[0], target[1], -1)
        queue = [(0, 0, start_state)]
        costs = {start_state: 0}
        parents: dict[tuple[int, int, int], tuple[int, int, int] | None] = {
            start_state: None
        }
        found = None
        states = 0
        while queue and states < max_states:
            _, cost, state = heapq.heappop(queue)
            if cost != costs.get(state):
                continue
            states += 1
            x, y, previous_direction = state
            if (x, y) in tree:
                found = state
                break
            for dx, dy in moves:
                next_point = (x + dx, y + dy)
                direction = directions[(dx, dy)]
                if not allowed(next_point, direction, previous_direction):
                    continue
                if edge_key((x, y), next_point) in occupied_edges:
                    continue
                next_cost = cost + 1 + (2 if previous_direction not in (-1, direction) else 0)
                next_state = (next_point[0], next_point[1], direction)
                if next_cost >= costs.get(next_state, 1 << 60):
                    continue
                costs[next_state] = next_cost
                parents[next_state] = state
                heuristic = manhattan(next_point, min(tree, key=lambda p: manhattan(p, next_point)))
                heapq.heappush(queue, (next_cost + heuristic, next_cost, next_state))
        if found is None:
            raise RuntimeError(
                f"no direct route from {target} to net {terminals[0]} "
                f"({states} states)"
            )
        path = []
        state = found
        while state is not None:
            path.append((state[0], state[1]))
            state = parents[state]
        path.reverse()
        # Starting from a sink means the path is target -> existing tree.
        all_segments.extend(compress_path(path))
        tree.update(path)
        occupied.update(path)
        for left, right in zip(path, path[1:]):
            occupied_edges.add(edge_key(left, right))
        for segment_start, segment_end in compress_path(path):
            occupied_junctions.add(segment_start)
            occupied_junctions.add(segment_end)
    return all_segments


class DirectRouter:
    def __init__(self, bounds: Bounds, grid: int = 10) -> None:
        self.bounds = bounds
        self.grid = grid
        self.obstacles: set[Point] = set()
        self.reserved: set[Point] = set()
        self.occupied: set[Point] = set()
        self.occupied_edges: set[tuple[Point, Point]] = set()
        self.occupied_junctions: set[Point] = set()

    def add_obstacle(self, rect: tuple[int, int, int, int]) -> None:
        self.obstacles.update(rect_points(rect, self.grid))

    def reserve(self, point: Point) -> None:
        self.reserved.add(point)

    def occupy_wire(self, start: Point, end: Point) -> None:
        if start == end:
            return
        if start[0] != end[0] and start[1] != end[1]:
            raise ValueError("occupied wire must be orthogonal")
        points = [start, end]
        self.occupied.update(points)
        self.occupied_junctions.update(points)
        left, right = (start, end) if start <= end else (end, start)
        self.occupied_edges.add((left, right))

    def route(self, terminals: Iterable[Point]) -> list[tuple[Point, Point]]:
        segments = route_net(
            list(terminals),
            bounds=self.bounds,
            grid=self.grid,
            obstacle_nodes=self.obstacles,
            occupied=self.occupied,
            occupied_edges=self.occupied_edges,
            occupied_junctions=self.occupied_junctions,
            reserved=self.reserved,
        )
        return segments
