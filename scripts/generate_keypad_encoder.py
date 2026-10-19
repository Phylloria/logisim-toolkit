#!/usr/bin/env python3
"""Generate a gate-only decimal keypad priority encoder for Logisim 2.7.1.

Inputs K0..K9 are active high. K9 has the highest priority. Outputs B0..B3
form the BCD digit, with B0 as the least significant bit. VALID is high when
at least one key is pressed. No high-level encoder or multiplexer components
are used.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_alu import CircuitBuilder


INPUT_NAMES = [f"K{index}" for index in range(9, -1, -1)]
OUTPUT_NAMES = ["B0", "B1", "B2", "B3", "VALID"]


def encode_priority(mask: int) -> dict[str, int]:
    pressed = [digit for digit in range(10) if mask & (1 << digit)]
    valid = int(bool(pressed))
    digit = max(pressed) if pressed else 0
    return {
        "B0": digit & 1,
        "B1": (digit >> 1) & 1,
        "B2": (digit >> 2) & 1,
        "B3": (digit >> 3) & 1,
        "VALID": valid,
    }


def vector_row(mask: int) -> dict[str, int]:
    row = {f"K{index}": (mask >> index) & 1 for index in range(10)}
    row.update(encode_priority(mask))
    return row


def exhaustive_rows():
    for mask in range(1 << 10):
        yield vector_row(mask)


def smoke_rows():
    masks = [0]
    masks.extend(1 << digit for digit in range(10))
    masks.extend([
        0b0000000011,  # K0 and K1 -> 1
        0b0000100010,  # K1 and K5 -> 5
        0b1000100000,  # K5 and K9 -> 9
        0b1111111111,  # all keys -> 9
        0b1100000000,  # K8 and K9 -> 9
        0b0100010000,  # K4 and K8 -> 8
        0b0010101010,  # K1,K3,K5,K7 -> 7
        0b0001001001,  # K0,K3,K6 -> 6
    ])
    return [vector_row(mask) for mask in masks]


def write_table(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INPUT_NAMES + OUTPUT_NAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in columns})


def build_encoder() -> CircuitBuilder:
    builder = CircuitBuilder()
    builder.add_text("DECIMAL KEYPAD PRIORITY ENCODER", 500, 35)
    builder.add_text("K0..K9: 1 = pressed. Highest pressed digit wins (K9 highest).", 500, 75)
    builder.add_text("B3..B0: BCD digit. VALID = at least one key pressed.", 500, 115)
    builder.add_text("SUFFIX PRIORITY", 720, 1140)
    builder.add_text("TERM SELECT", 1320, 1140)
    builder.add_text("BCD OUTPUT", 1740, 1140)

    for index in range(9, -1, -1):
        builder.add_input(f"K{index}", 180, 100 + (9 - index) * 100)

    # S8 = K9 | K8, then continue down to S0. S9 is the K9 input itself.
    previous = "K9"
    for digit in range(8, -1, -1):
        signal = f"S{digit}"
        builder.add_gate(signal, "OR", [previous, f"K{digit}"], 700,
                         150 + (8 - digit) * 100)
        previous = signal

    # N9..N1 suppress lower-priority terms whenever a higher key is present.
    for digit in range(8, -1, -1):
        higher = "K9" if digit == 8 else f"S{digit + 1}"
        builder.add_gate(f"N{digit + 1}", "NOT", [higher], 1000,
                         150 + (8 - digit) * 100)

    # T9 is K9. Build T8..T0 as one selected key each.
    for digit in range(8, -1, -1):
        builder.add_gate(f"T{digit}", "AND", [f"K{digit}", f"N{digit + 1}"],
                         1300, 200 + (8 - digit) * 100)

    builder.add_gate("B0", "OR", ["K9", "T7", "T5", "T3", "T1"], 1700, 300)
    builder.add_gate("B1", "OR", ["T7", "T6", "T3", "T2"], 1700, 500)
    builder.add_gate("B2", "OR", ["T7", "T6", "T5", "T4"], 1700, 700)
    builder.add_gate("B3", "OR", ["K9", "T8"], 1700, 900)

    for name, y in (("B0", 300), ("B1", 500), ("B2", 700), ("B3", 900)):
        builder.add_output(name, name, 2200, y)
    builder.add_output("VALID", "S0", 2200, 1050)
    return builder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path,
                        help="Defaults to <out stem>_exhaustive.tsv")
    parser.add_argument("--smoke-out", type=Path,
                        help="Defaults to <out stem>_smoke.tsv")
    parser.add_argument("--main-name", default="main")
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(args.out.stem + "_exhaustive.tsv")
    smoke_path = args.smoke_out or args.out.with_name(args.out.stem + "_smoke.tsv")
    builder = build_encoder()
    builder.emit(args.out, args.main_name)
    write_table(table_path, exhaustive_rows())
    write_table(smoke_path, smoke_rows())
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Smoke vectors: {smoke_path}")
    print(f"Inputs: {len(builder.inputs)}; outputs: {len(builder.outputs)}; "
          f"gates: {len(builder.gates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
