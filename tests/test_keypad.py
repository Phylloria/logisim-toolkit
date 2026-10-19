from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class KeypadEncoderRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="keypad-skill-test-")
        cls.directory = Path(cls.temp.name)
        cls.circuit = cls.directory / "keypad.circ"
        cls.exhaustive = cls.directory / "keypad_exhaustive.tsv"
        cls.smoke = cls.directory / "keypad_smoke.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_keypad_encoder.py"),
                "--out", str(cls.circuit),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_generator_emits_1024_row_exhaustive_table(self) -> None:
        self.assertTrue(self.circuit.is_file())
        self.assertEqual(len(self.exhaustive.read_text(encoding="utf-8").splitlines()), 1025)

    def test_exhaustive_priority_encoding(self) -> None:
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
