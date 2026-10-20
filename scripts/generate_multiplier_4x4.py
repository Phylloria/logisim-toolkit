#!/usr/bin/env python3
"""Generate a flat gate-level 4x4 array multiplier with direct wiring."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from direct_router import Bounds
from flat_builder import build_wire_nets, write_flat_project
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    route_stage,
)

INPUT_NAMES = [f"A{index}" for index in range(4)] + [
    f"B{index}" for index in range(4)
]
OUTPUT_NAMES = [f"P{index}" for index in range(8)]

A_Y = 90
B_Y = 500
INPUT_STEP = 90
PP_X = 420
PP_X_STEP = 140
PP_Y = 90
PP_Y_STEP = 110
FA_STEP = 520
ROW_STARTS = (0, 900, 1400, 1900)
ROW_YS = (0, 600, 920, 1240)
OUTPUT_X = 4100
OUTPUT_Y = 1480
OUTPUT_STEP = 50


def add_ha(stage, prefix, x, y, a, b):
    sum_gate = Gate(f"{prefix}_S", "XOR", (a, b), (x, y))
    carry_gate = Gate(f"{prefix}_C", "AND", (a, b), (x, y + 100))
    stage.gates.extend((sum_gate, carry_gate))
    return sum_gate.signal, carry_gate.signal


def add_fa(stage, prefix, x, y, a, b, cin):
    p = Gate(f"{prefix}_P", "XOR", (a, b), (x, y))
    sum_gate = Gate(f"{prefix}_S", "XOR", (p.signal, cin), (x + 220, y))
    generate = Gate(f"{prefix}_G", "AND", (a, b), (x, y + 100))
    carry_prop = Gate(f"{prefix}_CP", "AND", (p.signal, cin), (x + 220, y + 100))
    carry = Gate(f"{prefix}_C", "OR", (generate.signal, carry_prop.signal),
                 (x + 440, y + 100))
    stage.gates.extend((p, sum_gate, generate, carry_prop, carry))
    return sum_gate.signal, carry.signal


def make_circuit() -> tuple[Stage, dict[int, str]]:
    stage = Stage("main")
    for index in range(4):
        stage.inputs.append(Pin(f"A{index}", (100, A_Y + index * INPUT_STEP), False, "east"))
    for index in range(4):
        stage.inputs.append(Pin(f"B{index}", (100, B_Y + index * INPUT_STEP), False, "east"))

    partial = {}
    for bit_b in range(4):
        for bit_a in range(4):
            name = f"PP{bit_a}{bit_b}"
            stage.gates.append(Gate(
                name, "AND", (f"A{bit_a}", f"B{bit_b}"),
                (PP_X + bit_a * PP_X_STEP, PP_Y + bit_b * PP_Y_STEP),
            ))
            partial[(bit_a, bit_b)] = name

    initial = {
        0: partial[(0, 0)],
        1: partial[(1, 0)],
        2: partial[(2, 0)],
        3: partial[(3, 0)],
    }
    current = initial
    for bit_b in range(1, 4):
        x = ROW_STARTS[bit_b]
        y = ROW_YS[bit_b]
        updated = {key: value for key, value in current.items() if key < bit_b}

        sum_signal, carry = add_ha(
            stage, f"R{bit_b}C{bit_b}", x, y,
            partial[(0, bit_b)], current[bit_b],
        )
        updated[bit_b] = sum_signal

        sum_signal, carry = add_fa(
            stage, f"R{bit_b}C{bit_b + 1}", x + FA_STEP, y,
            partial[(1, bit_b)], current[bit_b + 1], carry,
        )
        updated[bit_b + 1] = sum_signal

        sum_signal, carry = add_fa(
            stage, f"R{bit_b}C{bit_b + 2}", x + FA_STEP * 2, y,
            partial[(2, bit_b)], current[bit_b + 2], carry,
        )
        updated[bit_b + 2] = sum_signal

        if bit_b == 1:
            sum_signal, carry = add_ha(
                stage, f"R{bit_b}C{bit_b + 3}", x + FA_STEP * 3, y,
                partial[(3, bit_b)], carry,
            )
        else:
            sum_signal, carry = add_fa(
                stage, f"R{bit_b}C{bit_b + 3}", x + FA_STEP * 3, y,
                partial[(3, bit_b)], current[bit_b + 3], carry,
            )
        updated[bit_b + 3] = sum_signal
        updated[bit_b + 4] = carry
        current = updated

    for index in range(8):
        pin = Pin(
            f"P{index}",
            (OUTPUT_X, OUTPUT_Y + index * OUTPUT_STEP),
            True,
            "west",
        )
        stage.outputs.append(pin)

    for index in range(8):
        if index not in current:
            raise ValueError(f"missing product bit P{index}")
    nets = build_wire_nets(stage, {
        f"P{index}": current[index]
        for index in range(8)
    })

    output_points = {pin.point for pin in stage.outputs}
    nets.sort(key=lambda net: not any(
        point in output_points for point in net.terminals[1:]
    ))
    route_stage(
        stage,
        Bounds(0, 0, 4300, 1900),
        nets,
        preferred_bend_cost=8,
    )
    return stage, current


def vector_row(a: int, b: int) -> dict[str, int]:
    product = a * b
    row = {
        f"A{index}": (a >> index) & 1
        for index in range(4)
    }
    row.update({
        f"B{index}": (b >> index) & 1
        for index in range(4)
    })
    row.update({
        f"P{index}": (product >> index) & 1
        for index in range(8)
    })
    return row


def write_table(path: Path, vectors: list[tuple[int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INPUT_NAMES + OUTPUT_NAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for a, b in vectors:
            row = vector_row(a, b)
            writer.writerow({name: row[name] for name in columns})


def smoke_vectors() -> list[tuple[int, int]]:
    return [
        (0, 0), (1, 0), (0, 1), (1, 1),
        (15, 15), (15, 1), (1, 15),
        (2, 8), (8, 2), (7, 9), (9, 7),
        (4, 4), (3, 5), (5, 3), (12, 11), (11, 12),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path)
    parser.add_argument("--smoke-out", type=Path)
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(
        args.out.stem + "_vectors.tsv"
    )
    smoke_path = args.smoke_out or args.out.with_name(
        args.out.stem + "_smoke.tsv"
    )
    stage, _ = make_circuit()

    write_flat_project(stage, args.out, [
        ("4x4 ARRAY MULTIPLIER - GATE-LEVEL DIRECT-WIRE", 60, 50),
        ("PARTIAL PRODUCTS: PPij = Ai AND Bj", PP_X, 60),
        ("ACCUMULATION ROW B1", ROW_STARTS[1], ROW_YS[1] - 40),
        ("ACCUMULATION ROW B2", ROW_STARTS[2], ROW_YS[2] - 40),
        ("ACCUMULATION ROW B3", ROW_STARTS[3], ROW_YS[3] - 40),
        ("8-BIT PRODUCT", OUTPUT_X - 100, OUTPUT_Y - 40),
    ])
    write_table(
        table_path,
        [(a, b) for a in range(16) for b in range(16)],
    )
    write_table(smoke_path, smoke_vectors())
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Smoke vectors: {smoke_path}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
