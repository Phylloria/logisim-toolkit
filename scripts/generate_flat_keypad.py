#!/usr/bin/env python3
"""Generate a single-circuit, direct-wire decimal keypad priority encoder.

No subcircuits and no Tunnel components are used. The flat layout is organized
as five visual columns: inputs, suffix priority, higher-key suppression,
one-hot terms, and BCD output.
"""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from direct_router import split_segments_at_endpoints
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    comp,
    gate_inputs,
    wire,
)


INPUT_NAMES = [f"K{index}" for index in range(9, -1, -1)]
OUTPUT_NAMES = ["B0", "B1", "B2", "B3", "VALID"]


def make_flat_circuit():
    stage = Stage("main")
    inputs = {}
    for digit in range(9, -1, -1):
        if digit == 9:
            y = 180
        else:
            y = 320 + (8 - digit) * 140
        pin = Pin(f"K{digit}", (100, y), False, "east")
        stage.inputs.append(pin)
        inputs[digit] = pin

    suffix = {}
    previous = "K9"
    for digit in range(8, -1, -1):
        gate = Gate(
            f"S{digit}", "OR", (previous, f"K{digit}"),
            (500, 300 + (8 - digit) * 140),
        )
        stage.gates.append(gate)
        suffix[digit] = gate
        previous = f"S{digit}"

    higher = {}
    h8 = Gate("H8", "NOT", ("K9",), (750, 200))
    stage.gates.append(h8)
    higher[8] = h8
    for digit in range(7, 0, -1):
        gate = Gate(
            f"H{digit}", "NOT", (f"S{digit + 1}",),
            (750, suffix[digit + 1].point[1]),
        )
        stage.gates.append(gate)
        higher[digit] = gate

    terms = {}
    for digit in range(1, 9):
        gate = Gate(
            f"T{digit}", "AND", (f"K{digit}", f"H{digit}"),
            (1000, 300 + (8 - digit) * 140),
        )
        stage.gates.append(gate)
        terms[digit] = gate

    bcd = {
        "B0": Gate("B0", "OR", ("T9", "T7", "T5", "T3", "T1"), (1450, 550)),
        "B1": Gate("B1", "OR", ("T7", "T6", "T3", "T2"), (1450, 900)),
        "B2": Gate("B2", "OR", ("T7", "T6", "T5", "T4"), (1450, 1250)),
        "B3": Gate("B3", "OR", ("T9", "T8"), (1450, 1600)),
    }
    stage.gates.extend(bcd.values())

    outputs = {}
    for name, y in (("B0", 550), ("B1", 900), ("B2", 1250), ("B3", 1600)):
        pin = Pin(name, (1650, y), True, "west")
        stage.outputs.append(pin)
        outputs[name] = pin
    valid = Pin("VALID", (1650, 1800), True, "west")
    stage.outputs.append(valid)

    wires = [
        # K9 trunk and branches to S8, H8, B0.T9 and B3.T9.
        ((100, 180), (150, 180)),
        ((150, 180), (150, 120)),
        ((150, 120), (1250, 120)),
        ((250, 120), (250, 380)),
        ((250, 380), (400, 380)),
        ((400, 380), (400, 280)),
        ((400, 280), (450, 280)),
        ((620, 120), (620, 200)),
        ((620, 200), (720, 200)),
        ((1250, 120), (1250, 1620)),
        ((1250, 530), (1400, 530)),
        ((1250, 1620), (1400, 1620)),
    ]

    # Kd goes to Sd low input and Td low input through separate local channels.
    for digit in range(1, 9):
        row = 300 + (8 - digit) * 140
        wires.extend([
            ((100, row + 20), (450, row + 20)),
            ((350, row + 20), (350, row + 50)),
            ((350, row + 50), (930, row + 50)),
            ((930, row + 50), (930, row + 20)),
            ((930, row + 20), (950, row + 20)),
        ])
    wires.append(((100, 1440), (450, 1440)))

    # S-digit outputs feed the next S gate and the adjacent suppression gate.
    wires.extend([
        ((500, 300), (520, 300)),
        ((520, 300), (720, 300)),
        ((520, 300), (520, 500)),
        ((520, 500), (400, 500)),
        ((400, 500), (400, 420)),
        ((400, 420), (450, 420)),
    ])
    for digit in range(7, 0, -1):
        row = 300 + (8 - digit) * 140
        next_row = row + 140
        lane_x = 520 + (8 - digit) * 20
        wires.extend([
            ((500, row), (lane_x, row)),
        ])
        if digit >= 2:
            wires.append(((lane_x, row), (720, row)))
        wires.extend([
            ((lane_x, row), (lane_x, next_row + 60)),
            ((lane_x, next_row + 60), (400, next_row + 60)),
            ((400, next_row + 60), (400, next_row - 20)),
            ((400, next_row - 20), (450, next_row - 20)),
        ])
    # H8 = NOT K9; Hd = NOT S(d+1). Each drives one term gate.
    wires.extend([
        ((750, 200), (820, 200)),
        ((820, 200), (820, 280)),
        ((820, 280), (950, 280)),
    ])
    for digit in range(7, 0, -1):
        source_y = 300 + (8 - (digit + 1)) * 140
        target_y = 300 + (8 - digit) * 140 - 20
        wires.extend([
            ((750, source_y), (820, source_y)),
            ((820, source_y), (820, target_y)),
            ((820, target_y), (950, target_y)),
        ])

    # VALID and S0 output run below the functional columns.
    wires.extend([
        ((500, 1420), (800, 1420)),
        ((800, 1420), (800, 1800)),
        ((800, 1800), (1650, 1800)),
    ])

    # BCD term lanes. Target y values intentionally avoid all source rows.
    target_rows = {
        ("B0", "T7"): (540, 1),
        ("B0", "T5"): (550, 2),
        ("B0", "T3"): (560, 3),
        ("B0", "T1"): (570, 4),
        ("B1", "T7"): (880, 0),
        ("B1", "T6"): (890, 1),
        ("B1", "T3"): (910, 2),
        ("B1", "T2"): (920, 3),
        ("B2", "T7"): (1230, 0),
        ("B2", "T6"): (1240, 1),
        ("B2", "T5"): (1260, 2),
        ("B2", "T4"): (1270, 3),
        ("B3", "T8"): (1580, 0),
    }
    term_targets = {}
    for (output_name, term), (target_y, _) in target_rows.items():
        term_targets.setdefault(term, []).append((target_y, output_name))

    for digit in range(1, 9):
        source_y = 300 + (8 - digit) * 140
        lane_x = 1020 + (digit - 1) * 20
        wires.append(((1000, source_y), (lane_x, source_y)))
        targets = sorted(term_targets.get(f"T{digit}", []))
        target_ys = [target_y for target_y, _ in targets]
        low = min([source_y, *target_ys])
        high = max([source_y, *target_ys])
        wires.append(((lane_x, low), (lane_x, high)))
        for target_y, _ in targets:
            wires.append(((lane_x, target_y), (1400, target_y)))

    for name, gate in bcd.items():
        wires.append((gate.point, outputs[name].point))

    stage.wires.extend(wires)
    stage.wires = split_segments_at_endpoints(stage.wires)
    return stage


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


def write_table(path: Path, masks) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=INPUT_NAMES + OUTPUT_NAMES,
            delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        for mask in masks:
            row = vector_row(mask)
            writer.writerow({name: row[name] for name in INPUT_NAMES + OUTPUT_NAMES})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path)
    parser.add_argument("--smoke-out", type=Path)
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(args.out.stem + "_exhaustive.tsv")
    smoke_path = args.smoke_out or args.out.with_name(args.out.stem + "_smoke.tsv")
    stage = make_flat_circuit()

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
        ("DECIMAL KEYPAD PRIORITY ENCODER - FLAT DIRECT-WIRE VERSION", 100, 50),
        ("K9 highest priority; no subcircuits and no Tunnels.", 100, 90),
        ("SUFFIX PRIORITY", 420, 210),
        ("HIGHER-KEY SUPPRESSION", 670, 210),
        ("ONE-HOT TERMS", 930, 210),
        ("BCD OUTPUT", 1390, 210),
    ):
        comp(circuit, "6", (x, y), "Text", (
            ("font", "SansSerif plain 14"),
            ("halign", "left"),
            ("text", text),
            ("valign", "base"),
        ))
    for pin in stage.inputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", "east"), ("label", pin.name),
            ("labelloc", "west"), ("tristate", "false"),
        ))
    for gate in stage.gates:
        attributes = [("facing", "east")]
        if gate.kind != "NOT":
            attributes.append(("inputs", len(gate.inputs)))
        comp(circuit, "1", gate.point, {
            "AND": "AND Gate", "OR": "OR Gate", "NOT": "NOT Gate"
        }[gate.kind], attributes)
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
    write_table(table_path, range(1024))
    write_table(
        smoke_path,
        [0] + [1 << digit for digit in range(10)] + [
            0b0000000011, 0b0000100010, 0b1000100000, 0b1111111111,
            0b1100000000, 0b0100010000, 0b0010101010, 0b0001001001,
        ],
    )
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Smoke vectors: {smoke_path}")
    print(f"Circuits: 1; gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
