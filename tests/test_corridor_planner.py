from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corridor_planner import assign_interval_tracks


class CorridorPlannerTest(unittest.TestCase):
    def test_disjoint_intervals_share_track(self) -> None:
        tracks = assign_interval_tracks(
            {
                "left": (0, 100),
                "middle": (50, 150),
                "right": (200, 250),
            },
            base=100,
            step=10,
        )
        self.assertEqual(tracks["left"], 100)
        self.assertEqual(tracks["middle"], 110)
        self.assertEqual(tracks["right"], 100)

    def test_touching_intervals_do_not_share(self) -> None:
        tracks = assign_interval_tracks(
            {
                "top": (0, 100),
                "bottom": (100, 150),
            },
            base=100,
            step=10,
        )
        self.assertNotEqual(tracks["top"], tracks["bottom"])

    def test_layer_inputs_and_previous_outputs_share_assignment(self) -> None:
        tracks = assign_interval_tracks(
            {
                "input": (20, 180),
                "previous_output": (200, 260),
                "second_output": (40, 220),
            },
            base=500,
            step=10,
        )
        self.assertEqual(tracks["input"], 500)
        self.assertEqual(tracks["previous_output"], 500)
        self.assertEqual(tracks["second_output"], 510)


if __name__ == "__main__":
    unittest.main()
