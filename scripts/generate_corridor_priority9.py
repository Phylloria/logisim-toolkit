#!/usr/bin/env python3
"""Generate a compact staged-corridor 9-key priority encoder."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from corridor_planner import assign_interval_tracks
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
            (60, 120 + index * 90),
            False,
            "east",
        ))

    for index in range(1, 8):
        stage.gates.append(Gate(
            f"HIGH{index}",
            "OR",
            tuple(f"I{higher}" for higher in range(index + 1, 10)),
            (600, 120 + index * 90),
        ))
    for index in range(1, 9):
        inputs = ("I9",) if index == 8 else (f"HIGH{index}",)
        stage.gates.append(Gate(
            f"N{index}",
            "NOT",
            inputs,
            (760, 120 + index * 90),
        ))
    for index in range(1, 9):
        stage.gates.append(Gate(
            f"T{index}",
            "AND",
            (f"I{index}", f"N{index}"),
            (970, 120 + index * 90),
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
            (1230, 220 + bit * 180),
        ))
        stage.gates.append(Gate(
            f"ND{bit}",
            "NOT",
            (f"D{bit}",),
            (1400, 220 + bit * 180),
        ))
        stage.outputs.append(Pin(
            f"nD{bit}",
            (1550, 220 + bit * 180),
            True,
            "west",
        ))

    sinks_by_input = {}
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            if wanted in INPUT_NAMES:
                sinks_by_input.setdefault(wanted, []).append((gate, terminal))

    corridor_wires = []
    lane_bases = {760: 610, 970: 820, 1230: 1000}
    bypass_spans = {}
    for index in range(1, 10):
        name = f"I{index}"
        remaining = [
            terminal for gate, terminal in sinks_by_input[name]
            if gate.point[0] != 600
        ]
        if remaining:
            bypass_spans[name] = (
                100 + (index - 1) * 10,
                max(point[0] for point in remaining),
            )
    bypass_tracks = assign_interval_tracks(
        bypass_spans,
        base=20,
        step=10,
    )
    for index in range(1, 10):
        name = f"I{index}"
        source = stage.inputs[index - 1].point
        local_lane = 100 + (index - 1) * 10
        track_y = bypass_tracks[name]
        first_stage = [
            terminal for gate, terminal in sinks_by_input[name]
            if gate.point[0] == 600
        ]
        grouped = {}
        for gate, terminal in sinks_by_input[name]:
            if gate.point[0] == 600:
                continue
            lane_x = lane_bases[gate.point[0]] + (index - 1) * 10
            grouped.setdefault(lane_x, []).append(terminal)
        corridor_wires.append((source, (local_lane, source[1])))
        ys = [track_y, source[1], *[point[1] for point in first_stage]]
        corridor_wires.append(((local_lane, min(ys)), (local_lane, max(ys))))
        if first_stage:
            corridor_wires.extend([
                *[
                    ((local_lane, point[1]), point)
                    for point in first_stage
                ],
            ])
        if not grouped:
            continue
        max_lane = max(grouped)
        corridor_wires.extend([
            ((local_lane, track_y), (max_lane, track_y)),
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
        y = 120 + index * 90
        stage.wires.append(((600, y), (730, y)))
    for index in range(1, 9):
        y = 120 + index * 90
        stage.wires.extend([
            ((760, y), (910, y)),
            ((910, y), (910, y + 20)),
            ((910, y + 20), (920, y + 20)),
        ])

    term_names = {f"T{index}" for index in range(1, 9)}
    sinks_by_signal = {}
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            if wanted in term_names:
                sinks_by_signal.setdefault(wanted, []).append(terminal)
    sources = {gate.signal: gate.point for gate in stage.gates}
    term_intervals = {}
    for index in range(1, 9):
        name = f"T{index}"
        y = 120 + index * 90
        term_intervals[name] = (
            min([y, *[point[1] for point in sinks_by_signal[name]]]),
            max([y, *[point[1] for point in sinks_by_signal[name]]]),
        )
    term_lanes = assign_interval_tracks(
        term_intervals,
        base=1090,
        step=10,
    )
    term_wires = []
    for index in range(1, 9):
        name = f"T{index}"
        sinks = sinks_by_signal.get(name, [])
        if not sinks:
            continue
        lane_x = term_lanes[name]
        x, y = sources[name]
        ys = [y, *[point[1] for point in sinks]]
        term_wires.extend([
            ((x, y), (lane_x, y)),
            ((lane_x, min(ys)), (lane_x, max(ys))),
            *[((lane_x, point[1]), point) for point in sinks],
        ])
    stage.wires.extend(split_segments_at_endpoints(term_wires))

    for bit in range(4):
        y = 220 + bit * 180
        stage.wires.append(((1230, y), (1370, y)))
        stage.wires.append(((1400, y), (1550, y)))

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
        ("SUPPRESSION OR", 540, 70),
        ("INVERT", 730, 70),
        ("ONE-HOT TERMS", 930, 70),
        ("ACTIVE-LOW BCD", 1190, 70),
    ])
    write_table(table_path)
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Gates: {len(stage.gates)}; wires: {len(stage.wires)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
