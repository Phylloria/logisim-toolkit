#!/usr/bin/env python3
"""Generate a gate-level 8-to-3 priority encoder with direct wiring."""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from corridor_planner import assign_interval_tracks
from direct_router import split_segments_at_endpoints
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    comp,
    gate_inputs,
    wire,
)


INPUTS = [f"I{index}" for index in range(7, -1, -1)]


def encode_priority(mask: int):
    pressed = [index for index in range(8) if mask & (1 << index)]
    valid = int(bool(pressed))
    value = max(pressed) if pressed else 0
    return {
        "Y0": value & 1,
        "Y1": (value >> 1) & 1,
        "Y2": (value >> 2) & 1,
        "VALID": valid,
    }


def make_circuit() -> Stage:
    stage = Stage("main")
    inputs = {}
    for index in range(7, -1, -1):
        pin = Pin(f"I{index}", (100, 100 + (7 - index) * 100), False, "east")
        stage.inputs.append(pin)
        inputs[index] = pin

    suffix = {}
    previous = "I7"
    for index in range(6, -1, -1):
        gate = Gate(
            f"S{index}", "OR", (previous, f"I{index}"),
            (400, 200 + (6 - index) * 100),
        )
        stage.gates.append(gate)
        suffix[index] = gate
        previous = f"S{index}"

    nots = {}
    n7 = Gate("N7", "NOT", ("I7",), (650, 100))
    stage.gates.append(n7)
    nots[7] = n7
    for index in range(6, 1, -1):
        gate = Gate(f"N{index}", "NOT", (f"S{index}",),
                    (650, 200 + (6 - index) * 100))
        stage.gates.append(gate)
        nots[index] = gate

    terms = {}
    for index in range(6, 0, -1):
        gate = Gate(f"T{index}", "AND", (f"I{index}", f"N{index + 1}"),
                    (950, 200 + (6 - index) * 100))
        stage.gates.append(gate)
        terms[index] = gate

    outputs_gates = {
        "Y0": Gate("Y0", "OR", ("I7", "T5", "T3", "T1"), (1250, 300)),
        "Y1": Gate("Y1", "OR", ("I7", "T6", "T3", "T2"), (1250, 500)),
        "Y2": Gate("Y2", "OR", ("I7", "T6", "T5", "T4"), (1250, 700)),
    }
    stage.gates.extend(outputs_gates.values())
    outputs = {}
    for label, y in (("Y0", 300), ("Y1", 500), ("Y2", 700)):
        pin = Pin(label, (1500, y), True, "west")
        stage.outputs.append(pin)
        outputs[label] = pin
    valid = Pin("VALID", (1500, 900), True, "west")
    stage.outputs.append(valid)

    stage.wires.extend([
        # I7 trunk to S6, N7, and the three output OR gates.
        ((100, 100), (150, 100)),
        ((150, 100), (150, 50)),
        ((150, 50), (1150, 50)),
        ((300, 50), (300, 180)),
        ((300, 180), (350, 180)),
        ((600, 50), (600, 100)),
        ((600, 100), (620, 100)),
        ((1150, 50), (1150, 680)),
        ((1150, 280), (1200, 280)),
        ((1150, 480), (1200, 480)),
        ((1150, 680), (1200, 680)),
    ])

    for index in range(6, 0, -1):
        row = 100 + (7 - index) * 100
        stage.wires.extend([
            ((100, row), (250, row)),
            ((250, row), (250, row + 50)),
            ((250, row + 20), (350, row + 20)),
            ((250, row + 50), (880, row + 50)),
            ((880, row + 50), (880, row + 20)),
            ((880, row + 20), (900, row + 20)),
        ])
    stage.wires.extend([
        ((100, 800), (250, 800)),
        ((250, 800), (250, 820)),
        ((250, 820), (350, 820)),
    ])

    # S outputs fan out to the next priority stage and the matching inverter.
    for index in range(6, 0, -1):
        y = 200 + (6 - index) * 100
        lane = 430 + (6 - index) * 20
        next_y = y + 100
        stage.wires.extend([
            ((400, y), (lane, y)),
        ])
        if index >= 2:
            stage.wires.extend([
                ((lane, y), (620, y)),
                ((lane, y), (lane, next_y + 60)),
                ((lane, next_y + 60), (300, next_y + 60)),
                ((300, next_y + 60), (300, next_y - 20)),
                ((300, next_y - 20), (350, next_y - 20)),
            ])
        else:
            stage.wires.extend([
                ((lane, y), (lane, 860)),
                ((lane, 860), (300, 860)),
                ((300, 860), (300, 780)),
                ((300, 780), (350, 780)),
            ])

    # N7 -> T6; N6..N2 -> T5..T1.
    stage.wires.extend([
        ((650, 100), (800, 100)),
        ((800, 100), (800, 180)),
        ((800, 180), (900, 180)),
    ])
    for index in range(6, 1, -1):
        source_y = 200 + (6 - index) * 100
        target_y = 200 + (7 - index) * 100 - 20
        stage.wires.extend([
            ((650, source_y), (800, source_y)),
            ((800, source_y), (800, target_y)),
            ((800, target_y), (900, target_y)),
        ])

    term_targets = {
        6: (490, 690),
        5: (290, 710),
        4: (720,),
        3: (310, 510),
        2: (520,),
        1: (320,),
    }
    term_intervals = {}
    for index in range(6, 0, -1):
        source_y = 200 + (6 - index) * 100
        target_ys = list(term_targets[index])
        term_intervals[f"T{index}"] = (
            min([source_y, *target_ys]),
            max([source_y, *target_ys]),
        )
    term_lanes = assign_interval_tracks(
        term_intervals,
        base=1000,
        step=20,
    )
    for index in range(6, 0, -1):
        y = 200 + (6 - index) * 100
        lane = term_lanes[f"T{index}"]
        stage.wires.append(((950, y), (lane, y)))
        targets = sorted(term_targets[index])
        low = min([y, *targets])
        high = max([y, *targets])
        stage.wires.append(((lane, low), (lane, high)))
        for target_y in targets:
            stage.wires.extend([
                ((lane, target_y), (1200, target_y)),
            ])

    stage.wires.extend([
        ((1250, 300), (1500, 300)),
        ((1250, 500), (1500, 500)),
        ((1250, 700), (1500, 700)),
        ((400, 800), (700, 800)),
        ((700, 800), (700, 900)),
        ((700, 900), (1500, 900)),
    ])
    stage.wires = split_segments_at_endpoints(stage.wires)
    return stage


def write_table(path, masks):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for mask in masks:
        values = {f"I{index}": (mask >> index) & 1 for index in range(8)}
        values.update(encode_priority(mask))
        rows.append(values)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=INPUTS + ["Y0", "Y1", "Y2", "VALID"],
            delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    stage = make_circuit()
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
        ("8-TO-3 PRIORITY ENCODER", 100, 40),
        ("I7 highest priority; Y2..Y0 binary digit; VALID detects any input.", 100, 75),
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
            "AND": "AND Gate", "OR": "OR Gate", "NOT": "NOT Gate"
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
    table = args.out.with_name(args.out.stem + "_vectors.tsv")
    write_table(table, range(1 << 8))
    smoke = args.out.with_name(args.out.stem + "_smoke.tsv")
    write_table(smoke, [0] + [1 << index for index in range(8)] + [
        0b00000011, 0b00010100, 0b11000000, 0b11111111, 0b00101010,
    ])
    print(f"Circuit: {args.out}")
    print(f"Vectors: {table}")
    print(f"Smoke: {smoke}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")


if __name__ == "__main__":
    main()
