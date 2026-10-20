from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class Multiplier4x4RegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="multiplier-4x4-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "multiplier4.circ"
        cls.vectors = cls.directory / "multiplier4_vectors.tsv"
        cls.smoke = cls.directory / "multiplier4_smoke.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_multiplier_4x4.py"),
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
        self.assertEqual(len(gates), 64)
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "AND Gate"]),
            36,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "XOR Gate"]),
            20,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "OR Gate"]),
            8,
        )

    def test_every_operand_pair(self) -> None:
        with self.vectors.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 256)
        self.assertEqual(
            list(rows[0]),
            [f"A{index}" for index in range(4)]
            + [f"B{index}" for index in range(4)]
            + [f"P{index}" for index in range(8)],
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
        self.assertIn("Reference rows: 256; mismatches: 0", result.stdout)

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
