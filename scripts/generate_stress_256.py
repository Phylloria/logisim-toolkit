#!/usr/bin/env python3
"""Generate a 256-gate layered combinational circuit for layout stress tests."""
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

LAYERS = 32
ROWS = 8
INPUT_COUNT = 16
OUTPUT_COUNT = 4
INPUT_NAMES = [f"I{index}" for index in range(INPUT_COUNT)]
OUTPUT_NAMES = [f"O{index}" for index in range(OUTPUT_COUNT)]
KINDS = ("XOR", "AND", "OR", "AND", "XOR", "OR", "AND", "XOR")


def gate_specs() -> list[tuple[str, str, tuple[str, str]]]:
    specs = []
    for layer in range(LAYERS):
        for row in range(ROWS):
            name = f"G{layer}_{row}"
            if layer == 0:
                inputs = (f"I{row}", f"I{row + ROWS}")
            else:
                inputs = (
                    f"G{layer - 1}_{row}",
                    f"G{layer - 1}_{(row + 3) % ROWS}",
                )
            specs.append((name, KINDS[row], inputs))
    return specs


def make_circuit() -> Stage:
    stage = Stage("main")
    for index in range(8):
        stage.inputs.append(Pin(f"I{index}", (60, 100 + index * 70), False, "east"))
    for index in range(8, 16):
        stage.inputs.append(
            Pin(f"I{index}", (220, 100 + (index - 8) * 70), False, "east")
        )

    specs = gate_specs()
    for index, (name, kind, inputs) in enumerate(specs):
        layer, row = divmod(index, ROWS)
        stage.gates.append(Gate(
            name,
            kind,
            inputs,
            (500 + layer * 220, 100 + row * 130),
        ))

    output_x = 500 + (LAYERS - 1) * 220 + 300
    for index in range(OUTPUT_COUNT):
        stage.outputs.append(Pin(
            f"O{index}",
            (output_x, 100 + index * 130),
            True,
            "west",
        ))

    nets = build_wire_nets(
        stage,
        {
            f"O{index}": f"G{LAYERS - 1}_{index}"
            for index in range(OUTPUT_COUNT)
        },
        require_all_drivers=False,
    )
    output_points = {pin.point for pin in stage.outputs}
    nets.sort(key=lambda net: (
        not any(point in output_points for point in net.terminals[1:]),
        -len(net.terminals),
    ))
    route_stage(
        stage,
        Bounds(0, 0, output_x + 150, 1200),
        nets,
        preferred_bend_cost=8,
        ripup_limit=2,
        corridor_mode=True,
    )
    return stage


def evaluate(values: dict[str, int]) -> dict[str, int]:
    signals = dict(values)
    for name, kind, inputs in gate_specs():
        left, right = (signals[input_name] for input_name in inputs)
        if kind == "AND":
            result = left & right
        elif kind == "OR":
            result = left | right
        else:
            result = left ^ right
        signals[name] = result
    return {
        f"O{index}": signals[f"G{LAYERS - 1}_{index}"]
        for index in range(OUTPUT_COUNT)
    }


def write_table(path: Path, masks: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INPUT_NAMES + OUTPUT_NAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for mask in masks:
            values = {
                f"I{index}": (mask >> index) & 1
                for index in range(INPUT_COUNT)
            }
            values.update(evaluate(values))
            writer.writerow({name: values[name] for name in columns})


def stress_masks() -> list[int]:
    masks = [0, (1 << INPUT_COUNT) - 1]
    masks.extend(1 << index for index in range(INPUT_COUNT))
    masks.extend((0x5555, 0xAAAA, 0x0F0F, 0xF0F0))
    value = 0xACE1
    for _ in range(46):
        value ^= (value << 7) & 0xFFFF
        value ^= value >> 9
        value ^= (value << 8) & 0xFFFF
        masks.append(value)
    return masks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path)
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(
        args.out.stem + "_vectors.tsv"
    )
    stage = make_circuit()

    write_flat_project(stage, args.out, [
        ("256-GATE DIRECT-WIRE STRESS NETLIST", 60, 50),
        ("32 LAYERS x 8 GATES", 500, 70),
    ])
    write_table(table_path, stress_masks())
    print(f"Circuit: {args.out}")
    print(f"Vectors: {table_path}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
