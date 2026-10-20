from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from direct_router import (
    Bounds,
    DirectRouter,
    remove_path_loops,
    split_segments_at_endpoints,
)
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    validate_stage_grid,
)


class DirectRouterTest(unittest.TestCase):
    def test_remove_path_loops_discards_retraced_branch(self) -> None:
        points = [
            (0, 0), (10, 0), (20, 0), (10, 0), (10, 10),
        ]
        self.assertEqual(
            remove_path_loops(points),
            [(0, 0), (10, 0), (10, 10)],
        )

    def test_split_segments_makes_t_junctions_explicit(self) -> None:
        segments = [
            ((0, 0), (30, 0)),
            ((20, 0), (20, 20)),
        ]
        self.assertEqual(
            split_segments_at_endpoints(segments),
            [
                ((0, 0), (20, 0)),
                ((20, 0), (30, 0)),
                ((20, 0), (20, 20)),
            ],
        )

    def test_off_grid_pin_is_rejected_before_routing(self) -> None:
        stage = Stage("main")
        stage.inputs.append(Pin("A0", (105, 100), False, "east"))
        with self.assertRaisesRegex(ValueError, r"A0.*10-unit grid"):
            validate_stage_grid(stage)

    def test_off_grid_gate_terminal_is_rejected(self) -> None:
        stage = Stage("main")
        stage.gates.append(Gate("G", "AND", ("A", "B"), (200, 105)))
        with self.assertRaisesRegex(ValueError, r"gate 'G' at.*10-unit grid"):
            validate_stage_grid(stage)

    def test_route_failure_reports_net_name(self) -> None:
        router = DirectRouter(Bounds(0, 0, 100, 100), grid=10)
        for point in ((40, 50), (60, 50), (50, 40), (50, 60)):
            router.reserve(point)
        with self.assertRaisesRegex(RuntimeError, "CIN"):
            router.route([(0, 50), (50, 50)], net_name="CIN")


if __name__ == "__main__":
    unittest.main()
