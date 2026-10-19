from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StandaloneCliTest(unittest.TestCase):
    def run_cli(self, *arguments: str):
        return subprocess.run(
            [sys.executable, "-m", "scripts.cli", *arguments],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_lists_tools(self) -> None:
        result = self.run_cli("list-tools")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("generate encoder-8to3", result.stdout)
        self.assertIn("validate-clocked", result.stdout)

    def test_generates_and_checks_from_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="logisim-cli-test-") as temporary:
            out = Path(temporary) / "encoder.circ"
            generated = self.run_cli(
                "generate", "encoder-8to3", "--out", str(out)
            )
            self.assertEqual(
                generated.returncode, 0, generated.stdout + generated.stderr
            )
            table = out.with_name(out.stem + "_vectors.tsv")
            checked = self.run_cli(
                "check", str(out), "--table", str(table), "--require-exhaustive"
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("Reference rows: 256; mismatches: 0", checked.stdout)


if __name__ == "__main__":
    unittest.main()
