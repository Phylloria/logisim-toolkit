"""Standalone command-line interface for the Logisim toolkit."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__


TOOLS = {
    "check": "check_universal.py",
    "check-scalar": "check_circ.py",
    "check-hierarchy": "check_hierarchical.py",
    "validate": "validate_logisim.py",
    "validate-clocked": "validate_logisim_clocked.py",
    "stats": "verify.py",
    "render": "render.py",
}

GENERATORS = {
    "alu": "generate_alu.py",
    "cla-4bit": "generate_cla_4bit.py",
    "keypad": "generate_keypad_encoder.py",
    "keypad-flat": "generate_flat_keypad.py",
    "keypad-hierarchy": "generate_hierarchical_keypad.py",
    "encoder-8to3": "generate_encoder_8to3.py",
    "encoder-9-corridor": "generate_corridor_priority9.py",
    "multiplier-4x4": "generate_multiplier_4x4.py",
    "stress-256": "generate_stress_256.py",
    "probes": "generate_probes.py",
}


def script_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / filename


def run_script(filename: str, arguments: list[str]) -> int:
    command = [sys.executable, str(script_path(filename)), *arguments]
    return subprocess.run(command).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="logisim-toolkit",
        description="Design, inspect, check, generate, and validate Logisim 2.7.1 projects.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    for command, filename in TOOLS.items():
        sub = subparsers.add_parser(command, add_help=False)
        sub.add_argument("arguments", nargs=argparse.REMAINDER)

    generate = subparsers.add_parser("generate")
    generate.add_argument("generator", choices=sorted(GENERATORS))
    generate.add_argument("arguments", nargs=argparse.REMAINDER)

    subparsers.add_parser("list-tools")
    args = parser.parse_args()
    if args.command == "list-tools":
        print("Check and validate:")
        for command in TOOLS:
            print(f"  {command}")
        print("Generators:")
        for command in GENERATORS:
            print(f"  generate {command}")
        return 0
    if args.command in TOOLS:
        return run_script(TOOLS[args.command], args.arguments)
    if args.command == "generate":
        return run_script(GENERATORS[args.generator], args.arguments)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
