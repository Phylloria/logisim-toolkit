from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from direct_router import remove_path_loops, split_segments_at_endpoints


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


if __name__ == "__main__":
    unittest.main()
