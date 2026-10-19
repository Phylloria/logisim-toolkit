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


class Encoder8To3RegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="encoder-8to3-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "encoder.circ"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_encoder_8to3.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_flat_structure(self) -> None:
        root = ET.parse(self.circuit).getroot()
        self.assertEqual(len(root.findall("circuit")), 1)
        self.assertEqual(
            len(root.findall(".//comp[@name='Tunnel']")),
            0,
        )
        self.assertEqual(
            len([
                component for component in root.findall(".//comp")
                if component.get("name", "").endswith(" Gate")
            ]),
            22,
        )

    def test_exhaustive_priority_encoding(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_universal.py"),
                str(self.circuit),
                "--table", str(self.directory / "encoder_vectors.tsv"),
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
                "--table", str(self.directory / "encoder_smoke.tsv"),
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
