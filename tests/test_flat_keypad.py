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


class FlatKeypadRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="flat-keypad-skill-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "keypad_flat.circ"
        cls.exhaustive = cls.directory / "keypad_flat_exhaustive.tsv"
        cls.smoke = cls.directory / "keypad_flat_smoke.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_flat_keypad.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_single_flat_circuit_without_tunnels(self) -> None:
        root = ET.parse(self.circuit).getroot()
        circuits = root.findall("circuit")
        self.assertEqual(len(circuits), 1)
        self.assertEqual(
            len(circuits[0].findall(".//comp[@name='Tunnel']")),
            0,
        )
        self.assertEqual(
            len([
                component for component in circuits[0].findall("comp")
                if component.get("name", "").endswith(" Gate")
            ]),
            29,
        )

    def test_flat_exhaustive_simulation(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_circ.py"),
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
        self.assertIn("Floating terminals: 0", result.stdout)
        self.assertIn("Multiple-driver nets: 0", result.stdout)
        self.assertIn("Unsupported or duplicate components: 0", result.stdout)

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
