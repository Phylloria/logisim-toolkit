from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class UniversalModelRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="universal-logisim-test-")
        cls.directory = Path(cls.temp.name)
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_probes.py"),
                "--out-dir", str(cls.directory),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def run_check(self, circuit: str, table: str, *extra: str):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_universal.py"),
                str(self.directory / circuit),
                "--table", str(self.directory / table),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_bus_gate_model(self) -> None:
        result = self.run_check("probe_bus_gate.circ", "probe_bus_gate_vectors.tsv")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 4; mismatches: 0", result.stdout)

    def test_splitter_decode_and_combine(self) -> None:
        result = self.run_check("probe_splitter.circ", "probe_splitter_vectors.tsv")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 4; mismatches: 0", result.stdout)

    def test_register_sequence_model(self) -> None:
        result = self.run_check(
            "probe_register.circ", "probe_register_sequence.tsv", "--sequential"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 6; mismatches: 0", result.stdout)

    def test_adder_comparator_multiplexer_model(self) -> None:
        result = self.run_check(
            "probe_wide_components.circ", "probe_wide_components_vectors.tsv"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 5; mismatches: 0", result.stdout)

    def test_decoder_model(self) -> None:
        result = self.run_check("probe_decoder.circ", "probe_decoder_vectors.tsv")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reference rows: 4; mismatches: 0", result.stdout)

    def test_real_logisim_bus_and_sequential_when_available(self) -> None:
        logisim = os.environ.get("LOGISIM_JAR") or os.environ.get("LOGISIM_EXE")
        if not logisim:
            default = Path(r"C:\Logisim\logisim-win-2.7.1.exe")
            if not default.is_file():
                self.skipTest("Logisim runtime is not configured")
            logisim = str(default)
        for circuit, table in (
            ("probe_bus_gate.circ", "probe_bus_gate_vectors.tsv"),
            ("probe_splitter.circ", "probe_splitter_vectors.tsv"),
            ("probe_wide_components.circ", "probe_wide_components_vectors.tsv"),
            ("probe_decoder.circ", "probe_decoder_vectors.tsv"),
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_logisim.py"),
                    str(self.directory / circuit),
                    "--table", str(self.directory / table),
                    "--logisim", logisim,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_logisim_clocked.py"),
                str(self.directory / "probe_register.circ"),
                "--clock", "CLK",
                "--cycles", "3",
                "--input", "D=5",
                "--input", "CLR=0",
                "--input", "EN=1",
                "--logisim", logisim,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: 3 clocked cycle(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
