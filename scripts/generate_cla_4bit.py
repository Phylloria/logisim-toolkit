#!/usr/bin/env python3
"""Generate a flat gate-level 4-bit carry-lookahead adder."""
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
] + ["CIN"]
OUTPUT_NAMES = [f"S{index}" for index in range(4)] + ["COUT"]

BIT_YS = (100, 280, 460, 640)
PG_X = 600
G_X = 780
GROUP_X = 1050
FULL_X = 1320
CARRY_X = 1600
CARRY2_X = 1900
C3_X = 2150
C4_X = 2350
SUM_X = 2600
OUTPUT_X = 2850


def make_circuit() -> Stage:
    stage = Stage("main")
    for index, y in enumerate(BIT_YS):
        stage.inputs.append(Pin(f"A{index}", (100, y), False, "east"))
        stage.inputs.append(Pin(f"B{index}", (300, y), False, "east"))
    stage.inputs.append(Pin("CIN", (100, 820), False, "east"))

    for index, y in enumerate(BIT_YS):
        stage.gates.append(
            Gate(f"P{index}", "XOR", (f"A{index}", f"B{index}"), (PG_X, y))
        )
        stage.gates.append(
            Gate(f"G{index}", "AND", (f"A{index}", f"B{index}"), (G_X, y))
        )

    for name, kind, inputs, point in (
        ("P10", "AND", ("P1", "P0"), (GROUP_X, 170)),
        ("P1G0", "AND", ("P1", "G0"), (GROUP_X, 240)),
        ("G10", "OR", ("G1", "P1G0"), (GROUP_X, 300)),
        ("P32", "AND", ("P3", "P2"), (GROUP_X, 480)),
        ("P3G2", "AND", ("P3", "G2"), (GROUP_X, 540)),
        ("G32", "OR", ("G3", "P3G2"), (GROUP_X, 610)),
        ("P30", "AND", ("P32", "P10"), (FULL_X, 430)),
        ("P32G10", "AND", ("G10", "P32"), (FULL_X, 490)),
        ("G30", "OR", ("G32", "P32G10"), (FULL_X, 560)),
        ("C1T", "AND", ("P0", "CIN"), (CARRY_X, 170)),
        ("C1", "OR", ("G0", "C1T"), (CARRY2_X, 230)),
        ("C2T", "AND", ("P10", "CIN"), (CARRY_X, 300)),
        ("C2", "OR", ("G10", "C2T"), (CARRY2_X, 360)),
        ("P2G10", "AND", ("G10", "P2"), (CARRY_X, 440)),
        ("G21", "OR", ("G2", "P2G10"), (CARRY2_X, 520)),
        ("P21", "AND", ("P2", "P10"), (CARRY_X, 620)),
        ("C3T", "AND", ("P21", "CIN"), (CARRY2_X, 700)),
        ("C3", "OR", ("G21", "C3T"), (C3_X, 780)),
        ("C4T", "AND", ("P30", "CIN"), (C3_X, 450)),
        ("C4", "OR", ("G30", "C4T"), (C4_X, 530)),
    ):
        stage.gates.append(Gate(name, kind, inputs, point))

    sum_signals = []
    for index, y in enumerate(BIT_YS):
        carry = "CIN" if index == 0 else f"C{index}"
        name = f"S{index}"
        stage.gates.append(Gate(name, "XOR", (f"P{index}", carry), (SUM_X, y)))
        sum_signals.append(name)

    for index, y in enumerate(BIT_YS):
        stage.outputs.append(Pin(f"S{index}", (OUTPUT_X, y), True, "west"))
    stage.outputs.append(Pin("COUT", (OUTPUT_X, 840), True, "west"))

    nets = build_wire_nets(stage, {
        **{
            f"S{index}": sum_signals[index]
            for index in range(4)
        },
        "COUT": "C4",
    })

    def signal_priority(signal: str) -> int:
        if signal == "CIN":
            return 100
        if signal.startswith("P") and signal[1:].isdigit():
            return 80 + int(signal[1:])
        if signal.startswith("G") and signal[1:].isdigit():
            return 70 + int(signal[1:])
        return 0

    nets.sort(key=lambda net: (
        -len(net.terminals),
        -signal_priority(net.name),
    ))
    route_stage(
        stage,
        Bounds(0, 0, 3050, 1000),
        nets,
        preferred_bend_cost=20,
    )
    return stage


def vector_row(a: int, b: int, cin: int) -> dict[str, int]:
    total = a + b + cin
    row = {
        f"A{index}": (a >> index) & 1
        for index in range(4)
    }
    row.update({
        f"B{index}": (b >> index) & 1
        for index in range(4)
    })
    row["CIN"] = cin
    row.update({
        f"S{index}": (total >> index) & 1
        for index in range(4)
    })
    row["COUT"] = (total >> 4) & 1
    return row


def write_table(path: Path, vectors: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INPUT_NAMES + OUTPUT_NAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for a, b, cin in vectors:
            row = vector_row(a, b, cin)
            writer.writerow({name: row[name] for name in columns})


def smoke_vectors() -> list[tuple[int, int, int]]:
    return [
        (0, 0, 0), (0, 0, 1), (1, 0, 0), (0, 1, 0),
        (1, 1, 0), (1, 1, 1), (15, 15, 0), (15, 15, 1),
        (8, 7, 0), (8, 7, 1), (7, 8, 0), (10, 5, 1),
        (3, 12, 0), (4, 4, 1), (6, 9, 0), (11, 4, 1),
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
    stage = make_circuit()

    write_flat_project(stage, args.out, [
        ("4-BIT BLOCK CARRY-LOOKAHEAD ADDER - GATE-LEVEL DIRECT-WIRE", 60, 50),
        ("PROPAGATE P = A XOR B", 520, 60),
        ("GENERATE G = A AND B", 740, 60),
        ("PAIR GROUPS", GROUP_X - 20, 60),
        ("BLOCK GROUPS", FULL_X - 20, 60),
        ("LOOKAHEAD CARRIES", CARRY_X - 20, 60),
        ("SUMS", SUM_X - 10, 60),
    ])
    write_table(
        table_path,
        [(a, b, cin) for a in range(16) for b in range(16) for cin in range(2)],
    )
    write_table(smoke_path, smoke_vectors())
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Smoke vectors: {smoke_path}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
