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


class Stress256RegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="stress-256-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "stress256.circ"
        cls.vectors = cls.directory / "stress256_vectors.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_stress_256.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_flat_256_gate_structure(self) -> None:
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
        self.assertEqual(len(gates), 256)
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "AND Gate"]),
            96,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "XOR Gate"]),
            96,
        )
        self.assertEqual(
            len([gate for gate in gates if gate.get("name") == "OR Gate"]),
            64,
        )

    def test_reference_vectors(self) -> None:
        with self.vectors.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 68)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_universal.py"),
                str(self.circuit),
                "--table", str(self.vectors),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 68; mismatches: 0", result.stdout)

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
                "--table", str(self.vectors),
                "--logisim", logisim,
                "--limit", "2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: 2 vector(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
