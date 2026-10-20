from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class CarryLookaheadAdderRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="cla-4bit-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "cla4.circ"
        cls.vectors = cls.directory / "cla4_vectors.tsv"
        cls.smoke = cls.directory / "cla4_smoke.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_cla_4bit.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_flat_gate_level_structure(self) -> None:
        root = ET.parse(self.circuit).getroot()
        circuits = root.findall("circuit")
        self.assertEqual(len(circuits), 1)
        self.assertEqual(
            len(circuits[0].findall(".//comp[@name='Tunnel']")),
            0,
        )
        gates = [
            component for component in circuits[0].findall("comp")
            if component.get("name", "").endswith(" Gate")
        ]
        self.assertEqual(len(gates), 32)
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "AND Gate"]),
            16,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "XOR Gate"]),
            8,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "OR Gate"]),
            8,
        )

    def test_every_input_combination(self) -> None:
        with self.vectors.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 512)
        self.assertEqual(
            list(rows[0]),
            [f"A{index}" for index in range(4)]
            + [f"B{index}" for index in range(4)]
            + ["CIN"]
            + [f"S{index}" for index in range(4)]
            + ["COUT"],
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_universal.py"),
                str(self.circuit),
                "--table", str(self.vectors),
                "--require-exhaustive",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 512; mismatches: 0", result.stdout)

    def test_route_bend_budget(self) -> None:
        circuit = ET.parse(self.circuit).getroot().find("circuit")
        self.assertIsNotNone(circuit)
        directions = defaultdict(list)
        for wire in circuit.findall("wire"):
            start = tuple(
                int(value) for value in wire.get("from")[1:-1].split(",")
            )
            end = tuple(
                int(value) for value in wire.get("to")[1:-1].split(",")
            )
            orientation = "H" if start[1] == end[1] else "V"
            directions[start].append(orientation)
            directions[end].append(orientation)
        bends = sum(
            "H" in values and "V" in values
            for values in directions.values()
        )
        self.assertLessEqual(len(circuit.findall("wire")), 334)
        self.assertLessEqual(bends, 211)

    def test_real_logisim_when_available(self) -> None:
        logisim = os.environ.get("LOGISIM_JAR") or os.environ.get("LOGISIM_EXE")
        if not logisim:
            default = Path(r"C:\Logisim\logisim-win-2.7.1.exe")
            if not default.is_file():
                self.skipTest("Logisim runtime is not configured")
            logisim = str(default)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_logisim.py"),
                str(self.circuit),
                "--table", str(self.smoke),
                "--logisim", logisim,
                "--limit", "5",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: 5 vector(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
