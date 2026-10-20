#!/usr/bin/env python3
"""Generate a compact staged-corridor 9-key priority encoder."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from direct_router import split_segments_at_endpoints
from flat_builder import write_flat_project
from generate_hierarchical_keypad import (
    Gate,
    Pin,
    Stage,
    gate_inputs,
    validate_stage_grid,
)

INPUT_NAMES = [f"I{index}" for index in range(1, 10)]
OUTPUT_NAMES = ["nD3", "nD2", "nD1", "nD0"]


def build_stage() -> Stage:
    stage = Stage("main")
    for index in range(1, 10):
        stage.inputs.append(Pin(
            f"I{index}",
            (60, 200 + index * 100),
            False,
            "east",
        ))

    for index in range(1, 8):
        stage.gates.append(Gate(
            f"HIGH{index}",
            "OR",
            tuple(f"I{higher}" for higher in range(index + 1, 10)),
            (800, 200 + index * 100),
        ))
    for index in range(1, 9):
        inputs = ("I9",) if index == 8 else (f"HIGH{index}",)
        stage.gates.append(Gate(
            f"N{index}",
            "NOT",
            inputs,
            (1050, 200 + index * 100),
        ))
    for index in range(1, 9):
        stage.gates.append(Gate(
            f"T{index}",
            "AND",
            (f"I{index}", f"N{index}"),
            (1300, 200 + index * 100),
        ))

    bcd_terms = {
        0: ("T1", "T3", "T5", "T7", "I9"),
        1: ("T2", "T3", "T6", "T7"),
        2: ("T4", "T5", "T6", "T7"),
        3: ("T8", "I9"),
    }
    for bit in range(4):
        stage.gates.append(Gate(
            f"D{bit}",
            "OR",
            bcd_terms[bit],
            (1600, 300 + bit * 200),
        ))
        stage.gates.append(Gate(
            f"ND{bit}",
            "NOT",
            (f"D{bit}",),
            (1850, 300 + bit * 200),
        ))
        stage.outputs.append(Pin(
            f"nD{bit}",
            (2050, 300 + bit * 200),
            True,
            "west",
        ))

    sinks_by_input = {}
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            if wanted in INPUT_NAMES:
                sinks_by_input.setdefault(wanted, []).append((gate, terminal))

    corridor_wires = []
    lane_bases = {800: 550, 1050: 820, 1300: 1060, 1600: 1320}
    for index in range(1, 10):
        name = f"I{index}"
        source = stage.inputs[index - 1].point
        riser_x = 120 + (index - 1) * 10
        track_y = 20 + (index - 1) * 10
        grouped = {}
        for gate, terminal in sinks_by_input[name]:
            lane_x = lane_bases[gate.point[0]] + (index - 1) * 10
            grouped.setdefault(lane_x, []).append(terminal)
        max_lane = max(grouped)
        corridor_wires.extend([
            (source, (riser_x, source[1])),
            ((riser_x, source[1]), (riser_x, track_y)),
            ((riser_x, track_y), (max_lane, track_y)),
        ])
        for lane_x, terminals in grouped.items():
            ys = [track_y, *[point[1] for point in terminals]]
            corridor_wires.append(((lane_x, min(ys)), (lane_x, max(ys))))
            corridor_wires.extend(
                ((lane_x, point[1]), point)
                for point in terminals
            )

    stage.wires.extend(split_segments_at_endpoints(corridor_wires))

    for index in range(1, 8):
        y = 200 + index * 100
        stage.wires.append(((800, y), (1020, y)))
    for index in range(1, 9):
        y = 200 + index * 100
        stage.wires.extend([
            ((1050, y), (1240, y)),
            ((1240, y), (1240, y + 20)),
            ((1240, y + 20), (1250, y + 20)),
        ])

    term_wires = []
    term_names = {f"T{index}" for index in range(1, 9)}
    sinks_by_signal = {}
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            if wanted in term_names:
                sinks_by_signal.setdefault(wanted, []).append(terminal)
    sources = {gate.signal: gate.point for gate in stage.gates}
    for index in range(1, 9):
        name = f"T{index}"
        sinks = sinks_by_signal.get(name, [])
        if not sinks:
            continue
        lane_x = 1420 + (index - 1) * 10
        x, y = sources[name]
        ys = [y, *[point[1] for point in sinks]]
        term_wires.extend([
            ((x, y), (lane_x, y)),
            ((lane_x, min(ys)), (lane_x, max(ys))),
            *[((lane_x, point[1]), point) for point in sinks],
        ])
    stage.wires.extend(split_segments_at_endpoints(term_wires))

    for bit in range(4):
        y = 300 + bit * 200
        stage.wires.append(((1600, y), (1820, y)))
        stage.wires.append(((1850, y), (2050, y)))

    stage.wires = split_segments_at_endpoints(stage.wires)
    validate_stage_grid(stage)
    return stage


def vector_row(mask: int) -> dict[str, int]:
    pressed = [index for index in range(1, 10) if mask & (1 << (index - 1))]
    digit = max(pressed) if pressed else 0
    row = {
        f"I{index}": (mask >> (index - 1)) & 1
        for index in range(1, 10)
    }
    for bit in range(4):
        row[f"nD{bit}"] = 0 if (digit >> bit) & 1 else 1
    return row


def write_table(path: Path) -> None:
    columns = INPUT_NAMES + OUTPUT_NAMES
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for mask in range(1 << 9):
            row = vector_row(mask)
            writer.writerow({name: row[name] for name in columns})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path)
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(
        args.out.stem + "_vectors.tsv"
    )
    stage = build_stage()
    write_flat_project(stage, args.out, [
        ("9-KEY PRIORITY ENCODER - STAGED CORRIDOR LAYOUT", 60, 50),
        ("SUPPRESSION OR", 470, 70),
        ("INVERT", 690, 70),
        ("ONE-HOT TERMS", 900, 70),
        ("ACTIVE-LOW BCD", 1160, 70),
    ])
    write_table(table_path)
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
