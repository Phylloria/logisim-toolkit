from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from direct_router import (
    Bounds,
    DirectRouter,
    WireNet,
    remove_path_loops,
    split_segments_at_endpoints,
)
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    comp,
    route_stage,
    validate_stage_grid,
    wire,
)
from flat_builder import write_flat_project


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

    def test_route_stage_rips_up_and_retries_net(self) -> None:
        class FakeRouter:
            instances = []

            def __init__(
                self,
                bounds: Bounds,
                grid: int = 10,
                corridor_lanes=None,
            ) -> None:
                self.routed: list[str | None] = []
                self.instances.append(self)

            def occupy_wire(self, start, end) -> None:
                pass

            def add_obstacle(self, rect) -> None:
                pass

            def reserve(self, point) -> None:
                pass

            def route(
                self,
                terminals,
                preferred_bend_cost=None,
                net_name=None,
            ):
                if net_name == "B" and "A" in self.routed:
                    raise RuntimeError("blocked by A")
                self.routed.append(net_name)
                return []

        stage = Stage("main")
        nets = [
            WireNet("A", ((0, 0), (10, 0))),
            WireNet("B", ((0, 20), (10, 20))),
        ]
        with patch(
            "generate_hierarchical_keypad.DirectRouter",
            FakeRouter,
        ):
            route_stage(stage, Bounds(0, 0, 100, 100), nets)
        self.assertEqual(len(FakeRouter.instances), 2)
        self.assertEqual(FakeRouter.instances[1].routed, ["B", "A"])

    def test_route_stage_rejects_unconnected_top_level_pin(self) -> None:
        stage = Stage("main")
        stage.inputs.append(Pin("UNUSED", (0, 0), False, "east"))
        with self.assertRaisesRegex(ValueError, "UNUSED"):
            route_stage(
                stage,
                Bounds(0, 0, 100, 100),
                [WireNet("A", ((0, 20), (10, 20)))],
            )

    def test_component_emission_rejects_off_grid_location(self) -> None:
        root = ET.Element("project")
        circuit = ET.SubElement(root, "circuit")
        with self.assertRaisesRegex(ValueError, r"Text.*100, 105"):
            comp(circuit, "6", (100, 105), "Text")

    def test_wire_emission_rejects_off_grid_endpoint(self) -> None:
        root = ET.Element("project")
        circuit = ET.SubElement(root, "circuit")
        with self.assertRaisesRegex(ValueError, r"off-grid wire"):
            wire(circuit, (100, 100), (115, 100))

    def test_flat_project_fails_before_writing_off_grid_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="off-grid-emission-") as temporary:
            path = Path(temporary) / "bad.circ"
            with self.assertRaisesRegex(ValueError, r"Text.*1105"):
                write_flat_project(
                    Stage("main"),
                    path,
                    [("SELECT", 60, 1105)],
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
