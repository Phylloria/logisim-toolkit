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


class HierarchicalKeypadRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="hier-keypad-skill-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "keypad_hier.circ"
        cls.exhaustive = cls.directory / "keypad_hier_exhaustive.tsv"
        cls.smoke = cls.directory / "keypad_hier_smoke.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_hierarchical_keypad.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_structure_is_hierarchical_and_has_no_tunnels(self) -> None:
        root = ET.parse(self.circuit).getroot()
        self.assertEqual(
            [circuit.get("name") for circuit in root.findall("circuit")],
            ["PriorityStage", "TermStage", "BCDStage", "main"],
        )
        main = root.find("circuit[@name='main']")
        self.assertIsNotNone(main)
        instances = [
            component for component in main.findall("comp")
            if component.get("name") in {"PriorityStage", "TermStage", "BCDStage"}
        ]
        self.assertEqual(len(instances), 3)
        self.assertEqual(
            sum(
                len(circuit.findall(".//comp[@name='Tunnel']"))
                for circuit in root.findall("circuit")
            ),
            0,
        )

    def test_hierarchical_exhaustive_simulation(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_hierarchical.py"),
                str(self.circuit),
                "--table", str(self.exhaustive),
                "--require-exhaustive",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 1024; mismatches: 0", result.stdout)

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
