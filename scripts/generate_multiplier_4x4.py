#!/usr/bin/env python3
"""Generate a flat gate-level 4x4 array multiplier with direct wiring."""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from direct_router import Bounds
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    comp,
    gate_inputs,
    route_stage,
    wire,
)

INPUT_NAMES = [f"A{index}" for index in range(4)] + [
    f"B{index}" for index in range(4)
]
OUTPUT_NAMES = [f"P{index}" for index in range(8)]


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
        stage.inputs.append(Pin(f"A{index}", (100, 100 + index * 100), False, "east"))
    for index in range(4):
        stage.inputs.append(Pin(f"B{index}", (100, 600 + index * 100), False, "east"))

    partial = {}
    for bit_b in range(4):
        for bit_a in range(4):
            name = f"PP{bit_a}{bit_b}"
            stage.gates.append(Gate(
                name, "AND", (f"A{bit_a}", f"B{bit_b}"),
                (500 + bit_a * 160, 100 + bit_b * 120),
            ))
            partial[(bit_a, bit_b)] = name

    initial = {
        0: partial[(0, 0)],
        1: partial[(1, 0)],
        2: partial[(2, 0)],
        3: partial[(3, 0)],
    }
    current = initial
    row_starts = (0, 1400, 2000, 2600)
    row_ys = (0, 650, 1000, 1350)
    for bit_b in range(1, 4):
        x = row_starts[bit_b]
        y = row_ys[bit_b]
        updated = {key: value for key, value in current.items() if key < bit_b}

        sum_signal, carry = add_ha(
            stage, f"R{bit_b}C{bit_b}", x, y,
            partial[(0, bit_b)], current[bit_b],
        )
        updated[bit_b] = sum_signal

        sum_signal, carry = add_fa(
            stage, f"R{bit_b}C{bit_b + 1}", x + 600, y,
            partial[(1, bit_b)], current[bit_b + 1], carry,
        )
        updated[bit_b + 1] = sum_signal

        sum_signal, carry = add_fa(
            stage, f"R{bit_b}C{bit_b + 2}", x + 1200, y,
            partial[(2, bit_b)], current[bit_b + 2], carry,
        )
        updated[bit_b + 2] = sum_signal

        if bit_b == 1:
            sum_signal, carry = add_ha(
                stage, f"R{bit_b}C{bit_b + 3}", x + 1800, y,
                partial[(3, bit_b)], carry,
            )
        else:
            sum_signal, carry = add_fa(
                stage, f"R{bit_b}C{bit_b + 3}", x + 1800, y,
                partial[(3, bit_b)], current[bit_b + 3], carry,
            )
        updated[bit_b + 3] = sum_signal
        updated[bit_b + 4] = carry
        current = updated

    output_y = 1750
    for index in range(8):
        pin = Pin(f"P{index}", (5000, output_y + index * 60), True, "west")
        stage.outputs.append(pin)

    sinks: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            sinks[wanted].append(terminal)
    for index in range(8):
        if index not in current:
            raise ValueError(f"missing product bit P{index}")
        sinks[current[index]].append(stage.outputs[index].point)

    sources = {pin.name: pin.point for pin in stage.inputs}
    sources.update({gate.signal: gate.point for gate in stage.gates})
    nets = []
    for signal, terminals in sinks.items():
        try:
            source = sources[signal]
        except KeyError as error:
            raise ValueError(f"signal {signal!r} has no driver") from error
        nets.append([source, *terminals])

    used_signals = set(sinks)
    unused = set(sources) - used_signals
    if unused:
        raise ValueError(f"unused signal(s): {sorted(unused)}")

    route_stage(stage, Bounds(0, 0, 5200, 2300), nets)
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

    root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
    ET.SubElement(root, "lib", {"desc": "#Wiring", "name": "0"})
    ET.SubElement(root, "lib", {"desc": "#Gates", "name": "1"})
    ET.SubElement(root, "lib", {"desc": "#Base", "name": "6"})
    ET.SubElement(root, "main", {"name": "main"})
    options = ET.SubElement(root, "options")
    for key, value in (("gateUndefined", "ignore"), ("simlimit", "1000"), ("simrand", "0")):
        ET.SubElement(options, "a", {"name": key, "val": value})
    circuit = ET.SubElement(root, "circuit", {"name": "main"})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": "main"})

    for text, x, y in (
        ("4x4 ARRAY MULTIPLIER - GATE-LEVEL DIRECT-WIRE", 60, 50),
        ("PARTIAL PRODUCTS: PPij = Ai AND Bj", 500, 70),
        ("ACCUMULATION ROW B1", 1400, 610),
        ("ACCUMULATION ROW B2", 2000, 960),
        ("ACCUMULATION ROW B3", 2600, 1310),
        ("8-BIT PRODUCT", 4900, 1700),
    ):
        comp(circuit, "6", (x, y), "Text", (
            ("font", "SansSerif plain 14"), ("halign", "left"),
            ("text", text), ("valign", "base"),
        ))
    for pin in stage.inputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", "east"), ("label", pin.name),
            ("labelloc", "west"), ("tristate", "false"),
        ))
    for gate in stage.gates:
        attrs = [("facing", "east")]
        if gate.kind != "NOT":
            attrs.append(("inputs", len(gate.inputs)))
        comp(circuit, "1", gate.point, {
            "AND": "AND Gate", "OR": "OR Gate", "XOR": "XOR Gate", "NOT": "NOT Gate"
        }[gate.kind], attrs)
    for pin in stage.outputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", "west"), ("label", pin.name),
            ("labelloc", "east"), ("output", "true"),
        ))
    for start, end in stage.wires:
        wire(circuit, start, end)

    ET.indent(root, space="  ")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(args.out, encoding="utf-8", xml_declaration=True)
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
