#!/usr/bin/env python3
"""Parse, structurally check, and simulate a scalar Logisim gate netlist.

Supported primitives are input/output Pins, Power, Ground, Tunnels, and the
basic AND/OR/NOT/NAND/NOR/XOR/XNOR gates. Duplicate tunnel labels join nets.
This checker is intentionally independent from the circuit generator.

Usage:
  python check_circ.py circuit.circ
  python check_circ.py circuit.circ A=1 B=0
  python check_circ.py circuit.circ --table vectors.tsv
  python check_circ.py circuit.circ --table exhaustive.tsv --require-exhaustive
"""
from __future__ import annotations

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from logisim_geometry import (
    GATE_NAMES,
    gate_body_half_height,
    gate_input_axis,
    port_offsets,
)

GATES = set(GATE_NAMES.values())
TERMINAL_COMPONENTS = {"Pin", "Tunnel", "Power", "Ground"}
Point = tuple[int, int]


def point(text: str) -> Point:
    if not (text.startswith("(") and text.endswith(")")):
        raise ValueError(f"invalid location {text!r}")
    x, y = (int(value.strip()) for value in text[1:-1].split(",", 1))
    return x, y


def parse(path: Path, circuit_name: str | None = None):
    root = ET.parse(path).getroot()
    circuits = {element.get("name"): element for element in root.findall("circuit")}
    main_element = root.find("main")
    main_name = main_element.get("name") if main_element is not None else "main"
    selected_name = circuit_name or main_name
    if selected_name not in circuits:
        raise ValueError(f"circuit {selected_name!r} not found")
    circuit = circuits[selected_name]
    components = []
    for element in circuit.findall("comp"):
        location = element.get("loc")
        if not location:
            continue
        x, y = point(location)
        attributes = {
            attribute.get("name"): attribute.get("val", "")
            for attribute in element.findall("a")
        }
        components.append({
            "name": element.get("name", ""),
            "library": element.get("lib"),
            "x": x,
            "y": y,
            "attributes": attributes,
        })
    wires = []
    for element in circuit.findall("wire"):
        wires.append((point(element.get("from")), point(element.get("to"))))
    for index, (start, end) in enumerate(wires):
        for other_start, other_end in wires[index + 1:]:
            horizontal = start[1] == end[1] == other_start[1] == other_end[1]
            vertical = start[0] == end[0] == other_start[0] == other_end[0]
            if horizontal:
                overlap = min(max(start[0], end[0]), max(other_start[0], other_end[0])) - max(
                    min(start[0], end[0]), min(other_start[0], other_end[0])
                )
            elif vertical:
                overlap = min(max(start[1], end[1]), max(other_start[1], other_end[1])) - max(
                    min(start[1], end[1]), min(other_start[1], other_end[1])
                )
            else:
                overlap = 0
            if overlap > 0:
                components.append({
                    "name": "Overlapping wire",
                    "library": None,
                    "x": start[0],
                    "y": start[1],
                    "attributes": {
                        "detail": f"{start}->{end} overlaps {other_start}->{other_end}"
                    },
                })
    terminal_points = set()
    for component in components:
        name = component["name"]
        location = (component["x"], component["y"])
        if name in {"Pin", "Power", "Ground", "Tunnel"}:
            terminal_points.add(location)
        elif name in GATES:
            inputs, output = gate_ports(component)
            terminal_points.update(inputs)
            terminal_points.add(output)
    endpoint_counts = defaultdict(int)
    for start, end in wires:
        endpoint_counts[start] += 1
        endpoint_counts[end] += 1
    for wire_index, (start, end) in enumerate(wires):
        for endpoint in (start, end):
            if endpoint in terminal_points or endpoint_counts[endpoint] > 1:
                continue
            if any(
                index != wire_index and on_segment(endpoint, other_start, other_end)
                for index, (other_start, other_end) in enumerate(wires)
            ):
                continue
            components.append({
                "name": "Dangling wire",
                "library": None,
                "x": endpoint[0],
                "y": endpoint[1],
                "attributes": {
                    "detail": f"free endpoint at {endpoint} on wire {start}->{end}"
                },
            })
    return selected_name, components, wires


def rotate(dx: int, dy: int, facing: str) -> Point:
    try:
        return {
            "east": (dx, dy),
            "south": (-dy, dx),
            "west": (-dx, -dy),
            "north": (dy, -dx),
        }[facing]
    except KeyError as error:
        raise ValueError(f"unsupported facing {facing!r}") from error


def gate_ports(component: dict):
    name, x, y = component["name"], component["x"], component["y"]
    if name not in GATES:
        return None
    attributes = component["attributes"]
    facing = attributes.get("facing", "east")
    if name == "NOT Gate":
        relative_inputs = [(-30, 0)]
    else:
        count = int(attributes.get("inputs", "2"))
        if count < 2:
            raise ValueError(f"invalid input count {count} on {name}")
        offset = gate_input_axis(name)
        relative_inputs = [(-offset, value) for value in port_offsets(count)]
    inputs = []
    for dx, dy in relative_inputs:
        rx, ry = rotate(dx, dy, facing)
        inputs.append((x + rx, y + ry))
    output = (x, y)
    return inputs, output


def on_segment(target: Point, start: Point, end: Point) -> bool:
    x, y = target
    x1, y1 = start
    x2, y2 = end
    if x1 == x2 == x:
        return min(y1, y2) <= y <= max(y1, y2)
    if y1 == y2 == y:
        return min(x1, x2) <= x <= max(x1, x2)
    return False


class Nets:
    def __init__(self, wires, terminals: set[Point]):
        self.parent: dict[Point, Point] = {}

        def find(item: Point) -> Point:
            self.parent.setdefault(item, item)
            if self.parent[item] != item:
                self.parent[item] = find(self.parent[item])
            return self.parent[item]

        def union(left: Point, right: Point) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                self.parent[right_root] = left_root

        markers = {item for wire in wires for item in wire} | terminals
        wire_covered: set[Point] = set()
        for start, end in wires:
            if start[0] != end[0] and start[1] != end[1]:
                raise ValueError(f"diagonal wire {start} -> {end}")
            touched = [item for item in markers if on_segment(item, start, end)]
            touched.sort(key=lambda item: item[1] if start[0] == end[0] else item[0])
            wire_covered.update(touched)
            for left, right in zip(touched, touched[1:]):
                union(left, right)
        self.wire_covered = wire_covered
        self._find = find
        self._union = union

    def find(self, item: Point) -> Point:
        return self._find(item)

    def union(self, left: Point, right: Point) -> None:
        self._union(left, right)


def evaluate(components, wires, forced: dict[str, int]):
    input_pins: dict[str, Point] = {}
    output_pins: dict[str, Point] = {}
    tunnels: list[tuple[str, Point]] = []
    constants: list[tuple[int, Point, str]] = []
    gate_info = []
    terminals: set[Point] = set()
    unsupported = []
    missing_labels = []
    duplicate_locations = defaultdict(int)

    for index, component in enumerate(components):
        if component["name"] not in {"Overlapping wire", "Dangling wire"}:
            duplicate_locations[(component["x"], component["y"])] += 1
        name = component["name"]
        location = (component["x"], component["y"])
        attributes = component["attributes"]
        if name == "Pin":
            width = int(attributes.get("width", "1"))
            if width != 1:
                unsupported.append(f"Pin {attributes.get('label', '')!r} has width {width}")
                continue
            label = attributes.get("label") or f"pin{index}"
            if not attributes.get("label"):
                missing_labels.append(f"Pin at {location}")
            is_output = attributes.get("output") == "true" or attributes.get("type") == "output"
            target = output_pins if is_output else input_pins
            if label in target:
                raise ValueError(f"duplicate Pin label {label!r}")
            target[label] = location
            terminals.add(location)
        elif name == "Tunnel":
            label = attributes.get("label", "")
            if not label:
                missing_labels.append(f"Tunnel at {location}")
            tunnels.append((label, location))
            terminals.add(location)
        elif name in {"Power", "Ground"}:
            constants.append((1 if name == "Power" else 0, location, name))
            terminals.add(location)
        elif name in GATES:
            inputs, output = gate_ports(component)
            terminals.update(inputs)
            terminals.add(output)
            gate_info.append((index, component, inputs, output))
        elif name != "Text":
            unsupported.append(f"{name} at {location}")

    nets = Nets(wires, terminals)
    for label, location in tunnels:
        if not label:
            continue
        first = next((point_value for other_label, point_value in tunnels
                      if other_label == label), None)
        if first is not None:
            nets.union(location, first)

    floating = []
    for label, location in input_pins.items():
        if location not in nets.wire_covered:
            floating.append(f"input Pin {label}")
    for label, location in output_pins.items():
        if location not in nets.wire_covered:
            floating.append(f"output Pin {label}")
    for label, location in tunnels:
        if location not in nets.wire_covered:
            floating.append(f"Tunnel {label or '<unlabeled>'} at {location}")
    for value, location, name in constants:
        if location not in nets.wire_covered:
            floating.append(f"{name} at {location}")
    for _, component, inputs, output in gate_info:
        for index, location in enumerate(inputs, 1):
            if location not in nets.wire_covered:
                floating.append(f"{component['name']} input {index}")
        if output not in nets.wire_covered:
            floating.append(f"{component['name']} output")

    gate_rects = []
    for _, component, inputs, output in gate_info:
        name = component["name"]
        count = 1 if name == "NOT Gate" else int(component["attributes"].get("inputs", "2"))
        left_padding = gate_input_axis(name)
        half_height = gate_body_half_height(name, count)
        left, top, right, bottom = (
            output[0] - left_padding,
            output[1] - half_height,
            output[0],
            output[1] + half_height,
        )
        gate_rects.append((component, (left, top, right, bottom)))
    for index, (left_component, left) in enumerate(gate_rects):
        for right_component, right in gate_rects[index + 1:]:
            if (max(left[0], right[0]) < min(left[2], right[2])
                    and max(left[1], right[1]) < min(left[3], right[3])):
                unsupported.append(
                    f"overlapping gate bodies at "
                    f"({left_component['x']},{left_component['y']}) and "
                    f"({right_component['x']},{right_component['y']})"
                )
        gate_left, gate_top, gate_right, gate_bottom = left
        for wire_start, wire_end in wires:
            if wire_start[1] == wire_end[1] and gate_top < wire_start[1] < gate_bottom:
                overlap = min(max(wire_start[0], wire_end[0]), gate_right) - max(
                    min(wire_start[0], wire_end[0]), gate_left
                )
                if overlap > 0:
                    unsupported.append(
                        f"horizontal wire enters gate body at "
                        f"({left_component['x']},{left_component['y']})"
                    )
            if wire_start[0] == wire_end[0] and gate_left < wire_start[0] < gate_right:
                overlap = min(max(wire_start[1], wire_end[1]), gate_bottom) - max(
                    min(wire_start[1], wire_end[1]), gate_top
                )
                if overlap > 0:
                    unsupported.append(
                        f"vertical wire enters gate body at "
                        f"({left_component['x']},{left_component['y']})"
                    )

    drivers: dict[Point, list[str]] = defaultdict(list)
    for label, location in input_pins.items():
        drivers[nets.find(location)].append(f"input {label}")
    for value, location, name in constants:
        drivers[nets.find(location)].append(name)
    for _, component, _, output in gate_info:
        drivers[nets.find(output)].append(
            f"{component['name']} at ({component['x']},{component['y']})"
        )
    multiple = {
        root: names for root, names in drivers.items()
        if len(names) > 1
    }

    for key in list(duplicate_locations):
        if duplicate_locations[key] > 1:
            duplicates = [
                f"{component['name']} at {key}"
                for component in components
                if (component["x"], component["y"]) == key
            ]
            unsupported.append("duplicate component locations: " + ", ".join(duplicates))

    values: dict[Point, int | None] = {}
    for label, location in input_pins.items():
        values[nets.find(location)] = forced.get(label, 0)
    for value, location, _ in constants:
        values[nets.find(location)] = value

    for _ in range(max(1, len(gate_info) + 1)):
        changed = False
        for _, component, inputs, output in gate_info:
            input_values = [values.get(nets.find(location)) for location in inputs]
            if any(value is None for value in input_values):
                continue
            name = component["name"]
            if name == "NOT Gate":
                result = 1 - input_values[0]
            elif name in {"AND Gate", "NAND Gate"}:
                result = int(all(input_values))
                if name == "NAND Gate":
                    result = 1 - result
            elif name in {"OR Gate", "NOR Gate"}:
                result = int(any(input_values))
                if name == "NOR Gate":
                    result = 1 - result
            else:
                result = sum(input_values) % 2
                if name == "XNOR Gate":
                    result = 1 - result
            net = nets.find(output)
            if values.get(net) != result:
                values[net] = result
                changed = True
        if not changed:
            break

    outputs = {
        label: values.get(nets.find(location))
        for label, location in output_pins.items()
    }
    signal_values = {}
    for label, location in input_pins.items():
        signal_values[label] = values.get(nets.find(location))
    tunnel_labels = {
        location: label for label, location in tunnels if label
    }
    unnamed_gate = 1
    for _, component, _, output in gate_info:
        logical_name = tunnel_labels.get((output[0] + 70, output[1]))
        if logical_name is None:
            logical_name = f"gate{unnamed_gate}_{component['name']}"
            unnamed_gate += 1
        signal_values[logical_name] = values.get(nets.find(output))
    return {
        "outputs": outputs,
        "input_pins": input_pins,
        "output_pins": output_pins,
        "signal_values": signal_values,
        "floating": floating,
        "multiple": multiple,
        "missing_labels": missing_labels,
        "unsupported": unsupported,
    }


def read_table(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise ValueError("truth table has no data rows")
    return rows


def print_findings(result) -> None:
    print(f"Input pins: {len(result['input_pins'])}; "
          f"output pins: {len(result['output_pins'])}")
    print(f"Floating terminals: {len(result['floating'])}")
    for item in result["floating"][:16]:
        print("  ", item)
    print(f"Multiple-driver nets: {len(result['multiple'])}")
    for item in list(result["multiple"].values())[:12]:
        print("  ", item)
    print(f"Missing labels: {len(result['missing_labels'])}")
    for item in result["missing_labels"][:12]:
        print("  ", item)
    print(f"Unsupported or duplicate components: {len(result['unsupported'])}")
    for item in result["unsupported"][:12]:
        print("  ", item)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path)
    parser.add_argument("assignments", nargs="*", help="input assignments such as A=1")
    parser.add_argument("--table", type=Path, help="tab-separated reference vectors")
    parser.add_argument("--circuit-name", default=None)
    parser.add_argument("--require-exhaustive", action="store_true")
    parser.add_argument("--trace", action="append", default=[],
                        help="Print the value of a named internal signal")
    args = parser.parse_args()
    try:
        forced: dict[str, int] = {}
        for item in args.assignments:
            label, separator, value = item.partition("=")
            if not separator or value not in {"0", "1"}:
                raise ValueError(f"invalid assignment {item!r}; expected NAME=0 or NAME=1")
            forced[label] = int(value)
        name, components, wires = parse(args.circuit, args.circuit_name)
        if not components:
            raise ValueError(f"circuit {name!r} contains no components")
        result = evaluate(components, wires, forced)
        print(f"Circuit: {name}; components: {len(components)}; wires: {len(wires)}")
        print_findings(result)
        if args.trace:
            print("Trace:", {
                signal: result["signal_values"].get(signal)
                for signal in args.trace
            })

        failed = bool(
            result["floating"]
            or result["multiple"]
            or result["missing_labels"]
            or result["unsupported"]
            or any(value is None for value in result["outputs"].values())
        )
        if args.table:
            rows = read_table(args.table)
            input_labels = list(result["input_pins"])
            output_labels = list(result["output_pins"])
            missing_columns = [
                column for column in input_labels + output_labels
                if column not in rows[0]
            ]
            if missing_columns:
                raise ValueError(f"table is missing columns: {missing_columns}")
            mismatches = []
            for line, row in enumerate(rows, 2):
                state = {}
                for label in input_labels:
                    value = row[label].strip()
                    if value not in {"0", "1"}:
                        raise ValueError(f"line {line}: invalid value {value!r} for {label}")
                    state[label] = int(value)
                row_result = evaluate(components, wires, state)
                bad = {
                    label: (row[label].strip(), row_result["outputs"][label])
                    for label in output_labels
                    if row_result["outputs"][label] is None
                    or str(row_result["outputs"][label]) != row[label].strip()
                }
                if bad:
                    mismatches.append((line, bad))
            print(f"Reference rows: {len(rows)}; mismatches: {len(mismatches)}")
            for item in mismatches[:20]:
                print("  ", item)
            if args.require_exhaustive:
                expected = 1 << len(input_labels)
                if len(rows) != expected:
                    print(f"ERROR: expected {expected} exhaustive rows, found {len(rows)}")
                    return 2
            failed = failed or bool(mismatches)
        else:
            print("Outputs:", result["outputs"])
        return int(failed)
    except (OSError, ET.ParseError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
