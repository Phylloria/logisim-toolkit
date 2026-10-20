#!/usr/bin/env python3
"""Generate a hierarchical, direct-wire decimal keypad priority encoder.

The project contains three internal circuits:
  PriorityStage  - suffix priority scan and valid detection
  TermStage      - one selected term per digit 1..9
  BCDStage       - BCD output combination

main contains only the top-level Pins, three subcircuit instances, and direct
orthogonal wires. No Tunnel component is emitted anywhere.
"""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from direct_router import Bounds, DirectRouter, split_segments_at_endpoints
from logisim_geometry import GATE_NAMES, gate_body_half_height, gate_input_axis, port_offsets


Point = tuple[int, int]
INPUT_NAMES = [f"K{index}" for index in range(9, -1, -1)]
OUTPUT_NAMES = ["B0", "B1", "B2", "B3", "VALID"]


@dataclass(frozen=True)
class Pin:
    name: str
    point: Point
    is_output: bool
    facing: str


@dataclass(frozen=True)
class Gate:
    signal: str
    kind: str
    inputs: tuple[str, ...]
    point: Point


@dataclass
class Stage:
    name: str
    inputs: list[Pin] = field(default_factory=list)
    outputs: list[Pin] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    wires: list[tuple[Point, Point]] = field(default_factory=list)


def gate_inputs(gate: Gate) -> list[Point]:
    axis = gate_input_axis(GATE_NAMES[gate.kind])
    return [
        (gate.point[0] - axis, gate.point[1] + offset)
        for offset in port_offsets(len(gate.inputs))
    ]


def gate_rect(gate: Gate) -> tuple[int, int, int, int]:
    axis = gate_input_axis(GATE_NAMES[gate.kind])
    half = gate_body_half_height(GATE_NAMES[gate.kind], len(gate.inputs))
    x, y = gate.point
    return x - axis, y - half, x, y + half


def pin_rect(pin: Pin) -> tuple[int, int, int, int]:
    x, y = pin.point
    if pin.is_output:
        return x, y - 15, x + 55, y + 15
    return x - 55, y - 15, x, y + 15


def route_stage(
    stage: Stage,
    bounds: Bounds,
    nets: list[list[Point]],
    preferred_bend_cost: int | None = None,
) -> None:
    router = DirectRouter(bounds, grid=10)
    escapes: dict[Point, Point] = {}

    def add_escape(terminal: Point, outward: Point) -> None:
        escape = (terminal[0] + outward[0] * 20, terminal[1] + outward[1] * 20)
        escapes[terminal] = escape
        stage.wires.append((terminal, escape))
        router.occupy_wire(terminal, escape)

    for gate in stage.gates:
        for terminal in gate_inputs(gate):
            add_escape(terminal, (-1, 0))
        add_escape(gate.point, (1, 0))
    for pin in stage.inputs:
        add_escape(pin.point, (1, 0) if pin.facing == "east" else (0, 1))
    for pin in stage.outputs:
        add_escape(pin.point, (-1, 0) if pin.facing == "west" else (0, -1))

    for gate in stage.gates:
        router.add_obstacle(gate_rect(gate))
    for pin in stage.inputs + stage.outputs:
        router.add_obstacle(pin_rect(pin))
        router.reserve(pin.point)
    for gate in stage.gates:
        for terminal in gate_inputs(gate):
            router.reserve(terminal)
        router.reserve(gate.point)
    for terminals in nets:
        routed = router.route(
            [escapes.get(point, point) for point in terminals],
            preferred_bend_cost=preferred_bend_cost,
        )
        stage.wires.extend(split_segments_at_endpoints(routed))


def make_priority_stage() -> Stage:
    stage = Stage("PriorityStage")
    input_rows = {digit: 100 + (9 - digit) * 140 for digit in range(10)}
    k_inputs = {}
    for digit in range(10):
        pin = Pin(f"K{digit}", (200, input_rows[digit]), False, "east")
        stage.inputs.append(pin)
        k_inputs[digit] = pin

    s_gates = {}
    h_gates = {}
    previous = "K9"
    for digit in range(8, -1, -1):
        gate = Gate(
            f"S{digit}", "OR", (previous, f"K{digit}"),
            (500, input_rows[digit]),
        )
        stage.gates.append(gate)
        s_gates[digit] = gate
        previous = f"S{digit}"

    for digit in range(1, 9):
        higher = "K9" if digit == 8 else f"S{digit + 1}"
        gate = Gate(f"H{digit}", "NOT", (higher,),
                    (800, input_rows[digit + 1] if digit < 8 else input_rows[9]))
        stage.gates.append(gate)
        h_gates[digit] = gate

    k_outputs = {}
    h_outputs = {}
    for digit in range(1, 10):
        output = Pin(f"K{digit}", (1050, input_rows[digit] - 70), True, "west")
        stage.outputs.append(output)
        k_outputs[digit] = output
    for digit in range(1, 9):
        output = Pin(f"H{digit}", (1300, h_gates[digit].point[1]), True, "west")
        stage.outputs.append(output)
        h_outputs[digit] = output
    valid = Pin("VALID", (1300, 1500), True, "west")
    stage.outputs.append(valid)

    nets: list[list[Point]] = []
    for digit in range(8, -1, -1):
        sinks = []
        if digit >= 1:
            sinks.append(gate_inputs(s_gates[digit - 1])[0])
        if digit >= 2:
            sinks.append(gate_inputs(h_gates[digit - 1])[0])
        if digit == 0:
            sinks.append(valid.point)
        nets.append([s_gates[digit].point] + sinks)

    for digit in range(1, 9):
        nets.append([h_gates[digit].point, h_outputs[digit].point])

    for digit in range(9, -1, -1):
        source = k_inputs[digit].point
        if digit == 9:
            sinks = [
                gate_inputs(s_gates[8])[0],
                gate_inputs(h_gates[8])[0],
                k_outputs[9].point,
            ]
        else:
            sinks = [gate_inputs(s_gates[digit])[1]]
            if digit >= 1:
                sinks.append(k_outputs[digit].point)
        nets.append([source] + sinks)

    route_stage(stage, Bounds(0, 0, 1500, 1600), nets)
    return stage


def make_term_stage() -> Stage:
    stage = Stage("TermStage")
    rows = {digit: 200 + digit * 100 for digit in range(1, 10)}
    k_pins = {}
    h_pins = {}
    for digit in range(1, 10):
        k_pin = Pin(f"K{digit}", (200, rows[digit] - 20), False, "east")
        stage.inputs.append(k_pin)
        k_pins[digit] = k_pin
    for digit in range(1, 9):
        h_pin = Pin(f"H{digit}", (400, rows[digit] + 20), False, "east")
        stage.inputs.append(h_pin)
        h_pins[digit] = h_pin

    terms = {}
    for digit in range(1, 9):
        gate = Gate(f"T{digit}", "AND", (f"K{digit}", f"H{digit}"),
                    (800, rows[digit]))
        stage.gates.append(gate)
        terms[digit] = gate
    for digit in range(1, 10):
        output_y = rows[digit] - 20 if digit == 9 else rows[digit]
        output = Pin(f"T{digit}", (1050, output_y), True, "west")
        stage.outputs.append(output)
        if digit < 9:
            stage.wires.extend([
                (k_pins[digit].point, gate_inputs(terms[digit])[0]),
                (h_pins[digit].point, gate_inputs(terms[digit])[1]),
                (terms[digit].point, output.point),
            ])
        else:
            stage.wires.append((k_pins[9].point, output.point))
    return stage


def make_bcd_stage() -> Stage:
    stage = Stage("BCDStage")
    rows = {digit: digit * 100 for digit in range(1, 10)}
    pins = {}
    for digit in range(1, 10):
        pin = Pin(f"T{digit}", (200, rows[digit]), False, "east")
        stage.inputs.append(pin)
        pins[digit] = pin

    gates = {
        "B0": Gate("B0", "OR", ("T1", "T3", "T5", "T7", "T9"), (700, 245)),
        "B1": Gate("B1", "OR", ("T2", "T3", "T6", "T7"), (700, 545)),
        "B2": Gate("B2", "OR", ("T4", "T5", "T6", "T7"), (700, 845)),
        "B3": Gate("B3", "OR", ("T8", "T9"), (700, 1145)),
    }
    stage.gates.extend(gates.values())
    outputs = {
        "B0": Pin("B0", (950, 245), True, "west"),
        "B1": Pin("B1", (950, 545), True, "west"),
        "B2": Pin("B2", (950, 845), True, "west"),
        "B3": Pin("B3", (950, 1145), True, "west"),
    }
    stage.outputs.extend(outputs.values())

    for name, gate in gates.items():
        stage.wires.append((gate.point, outputs[name].point))
    for digit in range(1, 10):
        lane_x = 300 + (digit - 1) * 20
        source = pins[digit].point
        target_ys = []
        for gate in gates.values():
            for signal, terminal in zip(gate.inputs, gate_inputs(gate)):
                if signal == f"T{digit}":
                    target_ys.append((terminal[1], terminal))
        if not target_ys:
            continue
        stage.wires.append((source, (lane_x, source[1])))
        ordered = sorted(set(target_ys))
        current_y = source[1]
        for target_y, target in ordered:
            if target_y != current_y:
                stage.wires.append(((lane_x, current_y), (lane_x, target_y)))
            stage.wires.append(((lane_x, target_y), target))
            current_y = target_y
    return stage


def comp(parent: ET.Element, library: str | None, point: Point, name: str,
         attributes: Iterable[tuple[str, str | int]] = ()) -> ET.Element:
    values = {
        "loc": f"({point[0]},{point[1]})",
        "name": name,
    }
    if library is not None:
        values["lib"] = library
    node = ET.SubElement(parent, "comp", values)
    for key, value in sorted(attributes):
        ET.SubElement(node, "a", {"name": key, "val": str(value)})
    return node


def wire(parent: ET.Element, start: Point, end: Point) -> None:
    if start == end:
        return
    if start[0] != end[0] and start[1] != end[1]:
        raise ValueError(f"diagonal wire {start} -> {end}")
    ET.SubElement(parent, "wire", {
        "from": f"({start[0]},{start[1]})",
        "to": f"({end[0]},{end[1]})",
    })


def emit_stage(root: ET.Element, stage: Stage) -> None:
    circuit = ET.SubElement(root, "circuit", {"name": stage.name})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": stage.name})

    appear = ET.SubElement(circuit, "appear")
    ET.SubElement(appear, "rect", {
        "fill": "#ffffff", "height": "280", "rx": "4", "ry": "4",
        "stroke": "#000000", "stroke-width": "2", "width": "820",
        "x": "120", "y": "80",
    })
    for index, pin in enumerate(stage.inputs):
        center = (140 + index * 40, 80)
        ET.SubElement(appear, "circ-port", {
            "height": "8", "pin": f"{pin.point[0]},{pin.point[1]}",
            "width": "8", "x": str(center[0] - 4), "y": str(center[1] - 4),
        })
    for index, pin in enumerate(stage.outputs):
        center = (140 + index * 40, 360)
        ET.SubElement(appear, "circ-port", {
            "height": "10", "pin": f"{pin.point[0]},{pin.point[1]}",
            "width": "10", "x": str(center[0] - 5), "y": str(center[1] - 5),
        })
    ET.SubElement(appear, "circ-anchor", {
        "facing": "east", "height": "6", "width": "6", "x": "97", "y": "77",
    })

    for pin in stage.inputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", pin.facing), ("label", pin.name),
            ("labelloc", "west"), ("tristate", "false"),
        ))
    for gate in stage.gates:
        attrs = [("facing", "east")]
        if gate.kind != "NOT":
            attrs.append(("inputs", len(gate.inputs)))
        comp(circuit, "1", gate.point, GATE_NAMES[gate.kind], attrs)
    for pin in stage.outputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", pin.facing), ("label", pin.name),
            ("labelloc", "east"), ("output", "true"),
        ))
    for start, end in stage.wires:
        wire(circuit, start, end)


def emit_main(root: ET.Element, stages: dict[str, Stage]) -> None:
    circuit = ET.SubElement(root, "circuit", {"name": "main"})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": "main"})
    for text, x, y in (
        ("DECIMAL KEYPAD PRIORITY ENCODER - HIERARCHICAL DIRECT-WIRE VERSION", 320, 35),
        ("No Tunnels. PriorityStage -> TermStage -> BCDStage.", 320, 75),
    ):
        comp(circuit, "6", (x, y), "Text", (
            ("font", "SansSerif plain 14"), ("halign", "left"),
            ("text", text), ("valign", "base"),
        ))

    stage_locations = {
        "PriorityStage": (300, 100),
        "TermStage": (300, 520),
        "BCDStage": (300, 940),
    }
    for name, point in stage_locations.items():
        comp(circuit, None, point, name, (
            ("facing", "east"), ("label", name),
        ))

    for index, digit in enumerate(range(10)):
        pin_point = (340 + index * 40, 20)
        comp(circuit, "0", pin_point, "Pin", (
            ("facing", "south"), ("label", f"K{digit}"),
            ("labelloc", "west"), ("tristate", "false"),
        ))
        wire(circuit, pin_point, (340 + index * 40, 100))

    priority = stages["PriorityStage"]
    term = stages["TermStage"]
    bcd = stages["BCDStage"]
    priority_outputs = [pin.name for pin in priority.outputs]
    term_inputs = [pin.name for pin in term.inputs]
    if priority_outputs[:17] != term_inputs:
        raise ValueError("PriorityStage outputs do not align with TermStage inputs")
    for index in range(17):
        x = 340 + index * 40
        wire(circuit, (x, 380), (x, 520))

    term_outputs = [pin.name for pin in term.outputs]
    bcd_inputs = [pin.name for pin in bcd.inputs]
    if term_outputs != bcd_inputs:
        raise ValueError("TermStage outputs do not align with BCDStage inputs")
    for index in range(9):
        x = 340 + index * 40
        wire(circuit, (x, 800), (x, 940))

    for index in range(4):
        x = 340 + index * 40
        comp(circuit, "0", (x, 1320), "Pin", (
            ("facing", "north"), ("label", f"B{index}"),
            ("labelloc", "east"), ("output", "true"),
        ))
        wire(circuit, (x, 1220), (x, 1320))

    comp(circuit, "0", (800, 1320), "Pin", (
        ("facing", "north"), ("label", "VALID"),
        ("labelloc", "east"), ("output", "true"),
    ))
    wire(circuit, (1020, 380), (1120, 380))
    wire(circuit, (1120, 380), (1120, 1320))
    wire(circuit, (1120, 1320), (800, 1320))


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


def write_table(path: Path, rows: Iterable[dict[str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INPUT_NAMES + OUTPUT_NAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in columns})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path)
    parser.add_argument("--smoke-out", type=Path)
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(args.out.stem + "_exhaustive.tsv")
    smoke_path = args.smoke_out or args.out.with_name(args.out.stem + "_smoke.tsv")

    stages = {
        "PriorityStage": make_priority_stage(),
        "TermStage": make_term_stage(),
        "BCDStage": make_bcd_stage(),
    }
    root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
    ET.SubElement(root, "lib", {"desc": "#Wiring", "name": "0"})
    ET.SubElement(root, "lib", {"desc": "#Gates", "name": "1"})
    ET.SubElement(root, "lib", {"desc": "#Base", "name": "6"})
    ET.SubElement(root, "main", {"name": "main"})
    options = ET.SubElement(root, "options")
    for key, value in (("gateUndefined", "ignore"), ("simlimit", "1000"), ("simrand", "0")):
        ET.SubElement(options, "a", {"name": key, "val": value})

    for stage in stages.values():
        emit_stage(root, stage)
    emit_main(root, stages)

    ET.indent(root, space="  ")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(args.out, encoding="utf-8", xml_declaration=True)

    rows = [vector_row(mask) for mask in range(1024)]
    write_table(table_path, rows)
    smoke_masks = [0] + [1 << digit for digit in range(10)] + [
        0b0000000011, 0b0000100010, 0b1000100000, 0b1111111111,
        0b1100000000, 0b0100010000, 0b0010101010, 0b0001001001,
    ]
    write_table(smoke_path, [vector_row(mask) for mask in smoke_masks])
    print(f"Circuit: {args.out}")
    print(f"Exhaustive vectors: {table_path}")
    print(f"Smoke vectors: {smoke_path}")
    print("Circuits: main, PriorityStage, TermStage, BCDStage")
    print(f"Gates: {sum(len(stage.gates) for stage in stages.values())}")
    print(f"Wires: {sum(len(stage.wires) for stage in stages.values()) + 43}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
