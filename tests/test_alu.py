from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class AluRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="logisim-skill-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "alu2.circ"
        cls.table = cls.directory / "alu2_vectors.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_alu.py"),
                "--bits", "2",
                "--exhaustive-table",
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_generator_emits_circuit_and_full_table(self) -> None:
        self.assertTrue(self.circuit.is_file())
        self.assertTrue(self.table.is_file())
        self.assertEqual(len(self.table.read_text(encoding="utf-8").splitlines()), 257)

    def test_exhaustive_static_simulation(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_circ.py"),
                str(self.circuit),
                "--table", str(self.table),
                "--require-exhaustive",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("mismatches: 0", result.stdout)
        self.assertIn("Floating terminals: 0", result.stdout)
        self.assertIn("Multiple-driver nets: 0", result.stdout)

    def test_xor_input_wires_end_on_source_verified_terminals(self) -> None:
        root = ET.parse(self.circuit).getroot()
        circuit = root.find("circuit")
        self.assertIsNotNone(circuit)
        endpoints = set()
        for wire in circuit.findall("wire"):
            for attribute in ("from", "to"):
                x, y = (int(value.strip()) for value in wire.get(attribute)[1:-1].split(",", 1))
                endpoints.add((x, y))
        xor_gates = [
            component for component in circuit.findall("comp")
            if component.get("name") == "XOR Gate"
        ]
        self.assertTrue(xor_gates)
        for gate in xor_gates:
            x, y = (int(value.strip()) for value in gate.get("loc")[1:-1].split(",", 1))
            for input_y in (y - 20, y + 20):
                self.assertIn((x - 60, input_y), endpoints)
                self.assertNotIn((x - 50, input_y), endpoints)

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
                "--table", str(self.table),
                "--logisim", logisim,
                "--limit", "3",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: 3 vector(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
