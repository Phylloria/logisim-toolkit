#!/usr/bin/env python3
"""Simulate and check a hierarchical Logisim project with direct wiring.

Subcircuit instance ports are resolved from each child circuit's custom
appearance. The checker supports nested subcircuits, scalar Pins, basic gates,
Power/Ground, and Tunnel components, although the bundled hierarchical keypad
does not use Tunnels.
"""
from __future__ import annotations

import argparse
import copy
import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from check_circ import GATES, Nets, gate_ports, point
from logisim_geometry import gate_body_half_height, gate_input_axis


def bare_point(text: str) -> tuple[int, int]:
    x, y = (int(value.strip()) for value in text.split(",", 1))
    return x, y


class HierarchicalChecker:
    def __init__(self, path: Path) -> None:
        self.root = ET.parse(path).getroot()
        self.circuits = {
            circuit.get("name"): circuit for circuit in self.root.findall("circuit")
        }
        self.main = self.root.find("main").get("name")
        self.pins = {}
        self.ports = {}
        self.findings = defaultdict(list)
        self._cache = {}
        for name, circuit in self.circuits.items():
            pin_map = {}
            for component in circuit.findall("comp"):
                if component.get("name") != "Pin" or not component.get("loc"):
                    continue
                values = {
                    item.get("name"): item.get("val", "")
                    for item in component.findall("a")
                }
                location = point(component.get("loc"))
                output = values.get("output") == "true" or values.get("type") == "output"
                pin_map[location] = (
                    values.get("label", ""),
                    output,
                    int(values.get("width", "1")),
                )
            self.pins[name] = pin_map
            self.ports[name] = self._read_appearance(name, circuit)

    def _read_appearance(self, name: str, circuit: ET.Element):
        appear = circuit.find("appear")
        pins = self.pins[name]
        if appear is None:
            if name == self.main:
                return []
            if pins:
                self.findings[name].append("subcircuit with Pins has no custom appearance")
            return []
        anchor_node = appear.find("circ-anchor")
        if anchor_node is None:
            self.findings[name].append("custom appearance has no anchor")
            return []
        anchor = (
            int(anchor_node.get("x")) + 3,
            int(anchor_node.get("y")) + 3,
        )
        ports = []
        seen = set()
        for index, node in enumerate(appear.findall("circ-port"), 1):
            pin_location = bare_point(node.get("pin"))
            if pin_location not in pins:
                self.findings[name].append(
                    f"appearance port {index} references missing Pin at {pin_location}"
                )
                continue
            if pin_location in seen:
                self.findings[name].append(
                    f"Pin at {pin_location} is mapped by more than one appearance port"
                )
            seen.add(pin_location)
            center = (
                int(node.get("x")) + int(node.get("width")) // 2,
                int(node.get("y")) + int(node.get("height")) // 2,
            )
            ports.append((
                (center[0] - anchor[0], center[1] - anchor[1]),
                pins[pin_location],
            ))
        missing = set(pins) - seen
        if missing:
            self.findings[name].append(
                f"Pins missing from appearance: {sorted(missing)}"
            )
        return ports

    def _gate_rect(self, component):
        name = component["name"]
        count = 1 if name == "NOT Gate" else int(component["attributes"].get("inputs", "2"))
        x, y = component["x"], component["y"]
        axis = gate_input_axis(name)
        half = gate_body_half_height(name, count)
        return x - axis, y - half, x, y + half

    def evaluate(self, circuit_name: str | None = None, forced=None):
        circuit_name = circuit_name or self.main
        forced = forced or {}
        key = (circuit_name, tuple(sorted(forced.items())))
        if key in self._cache:
            return self._cache[key]
        circuit = self.circuits[circuit_name]
        comps = []
        for element in circuit.findall("comp"):
            if not element.get("loc"):
                continue
            x, y = point(element.get("loc"))
            comps.append({
                "name": element.get("name", ""),
                "library": element.get("lib"),
                "x": x,
                "y": y,
                "attributes": {
                    item.get("name"): item.get("val", "")
                    for item in element.findall("a")
                },
            })
        wires = [
            (point(element.get("from")), point(element.get("to")))
            for element in circuit.findall("wire")
        ]

        input_pins = {}
        output_pins = {}
        constants = []
        gates = []
        instances = []
        terminals = set()
        duplicate_locations = defaultdict(int)
        for index, component in enumerate(comps):
            name = component["name"]
            location = (component["x"], component["y"])
            duplicate_locations[location] += 1
            if name == "Pin":
                values = component["attributes"]
                label = values.get("label") or f"pin{index}"
                if int(values.get("width", "1")) != 1:
                    self.findings[circuit_name].append(
                        f"hierarchical checker requires scalar Pin {label}"
                    )
                is_output = (
                    values.get("output") == "true"
                    or values.get("type") == "output"
                )
                (output_pins if is_output else input_pins)[label] = location
                terminals.add(location)
            elif name in {"Power", "Ground"}:
                constants.append((1 if name == "Power" else 0, location))
                terminals.add(location)
            elif name == "Tunnel":
                terminals.add(location)
            elif name in GATES:
                inputs, output = gate_ports(component)
                gates.append((component, inputs, output))
                terminals.update(inputs)
                terminals.add(output)
            elif name == "Text":
                continue
            elif name in self.circuits:
                child_ports = []
                for relative, (label, is_output, width) in self.ports[name]:
                    if width != 1:
                        self.findings[circuit_name].append(
                            f"hierarchical checker requires scalar port {name}.{label}"
                        )
                    port_point = (
                        component["x"] + relative[0],
                        component["y"] + relative[1],
                    )
                    child_ports.append((port_point, label, is_output))
                    terminals.add(port_point)
                instances.append((component, child_ports))
            else:
                self.findings[circuit_name].append(
                    f"unsupported component {name} at {location}"
                )

        nets = Nets(wires, terminals)
        tunnel_points = defaultdict(list)
        for component in comps:
            if component["name"] == "Tunnel":
                label = component["attributes"].get("label", "")
                if label:
                    tunnel_points[label].append((component["x"], component["y"]))
        for locations in tunnel_points.values():
            for location in locations[1:]:
                nets.union(locations[0], location)

        for location, count in duplicate_locations.items():
            if count > 1:
                self.findings[circuit_name].append(
                    f"{count} components share location {location}"
                )

        floating = []
        for label, location in input_pins.items():
            if location not in nets.wire_covered:
                floating.append(f"input Pin {label}")
        for label, location in output_pins.items():
            if location not in nets.wire_covered:
                floating.append(f"output Pin {label}")
        for component, inputs, output in gates:
            for index, location in enumerate(inputs, 1):
                if location not in nets.wire_covered:
                    floating.append(f"{component['name']} input {index}")
            if output not in nets.wire_covered:
                floating.append(f"{component['name']} output")
        for component, child_ports in instances:
            for location, label, _ in child_ports:
                if location not in nets.wire_covered:
                    floating.append(
                        f"{component['name']}.{label} at {location}"
                    )
        for value, location in constants:
            if location not in nets.wire_covered:
                floating.append(f"constant at {location}")
        if floating:
            self.findings[circuit_name].extend(floating)

        gate_rects = [(component, self._gate_rect(component)) for component, _, _ in gates]
        for component, rect in gate_rects:
            left, top, right, bottom = rect
            for wire_start, wire_end in wires:
                if wire_start[1] == wire_end[1] and top < wire_start[1] < bottom:
                    overlap = min(max(wire_start[0], wire_end[0]), right) - max(
                        min(wire_start[0], wire_end[0]), left
                    )
                    if overlap > 0:
                        self.findings[circuit_name].append(
                            f"wire enters gate body at "
                            f"({component['x']},{component['y']})"
                        )
                if wire_start[0] == wire_end[0] and left < wire_start[0] < right:
                    overlap = min(max(wire_start[1], wire_end[1]), bottom) - max(
                        min(wire_start[1], wire_end[1]), top
                    )
                    if overlap > 0:
                        self.findings[circuit_name].append(
                            f"wire enters gate body at "
                            f"({component['x']},{component['y']})"
                        )

        drivers = defaultdict(list)
        for label, location in input_pins.items():
            drivers[nets.find(location)].append(f"input {label}")
        for value, location in constants:
            drivers[nets.find(location)].append("constant")
        for component, _, output in gates:
            drivers[nets.find(output)].append(component["name"])
        for component, child_ports in instances:
            for location, label, is_output in child_ports:
                if is_output:
                    drivers[nets.find(location)].append(f"{component['name']}.{label}")
        multiple = {
            root: names for root, names in drivers.items() if len(names) > 1
        }
        for names in multiple.values():
            self.findings[circuit_name].append(
                "multiple drivers: " + ", ".join(names)
            )

        values = {}
        for label, location in input_pins.items():
            values[nets.find(location)] = forced.get(label, 0)
        for value, location in constants:
            values[nets.find(location)] = value

        instance_results = {}
        for _ in range(max(1, len(gates) + len(instances) + 1)):
            changed = False
            for component, inputs, output in gates:
                input_values = [values.get(nets.find(item)) for item in inputs]
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
            for instance_index, (component, child_ports) in enumerate(instances):
                child_inputs = {}
                ready = True
                for location, label, is_output in child_ports:
                    if is_output:
                        continue
                    value = values.get(nets.find(location))
                    if value is None:
                        ready = False
                        break
                    child_inputs[label] = value
                if not ready:
                    continue
                child_outputs, _ = self.evaluate(component["name"], child_inputs)
                for location, label, is_output in child_ports:
                    if not is_output:
                        continue
                    value = child_outputs.get(label)
                    net = nets.find(location)
                    if value is not None and values.get(net) != value:
                        values[net] = value
                        changed = True
                instance_results[instance_index] = child_outputs
            if not changed:
                break

        outputs = {
            label: values.get(nets.find(location))
            for label, location in output_pins.items()
        }
        result = outputs, {
            "input_pins": input_pins,
            "output_pins": output_pins,
            "instances": len(instances),
            "gates": len(gates),
            "wires": len(wires),
        }
        self._cache[key] = result
        return result


def read_table(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path)
    parser.add_argument("--table", type=Path)
    parser.add_argument("--require-exhaustive", action="store_true")
    args = parser.parse_args()
    try:
        checker = HierarchicalChecker(args.circuit)
        outputs, details = checker.evaluate()
        print(f"Main: {checker.main}")
        print(f"Main inputs: {len(details['input_pins'])}; "
              f"outputs: {len(details['output_pins'])}; "
              f"instances: {details['instances']}")
        for name, findings in checker.findings.items():
            print(f"{name}: {len(findings)} structural finding(s)")
            for finding in findings[:10]:
                print("  ", finding)
        failed = any(checker.findings.values()) or any(
            value is None for value in outputs.values()
        )
        if args.table:
            rows = read_table(args.table)
            mismatches = []
            for line, row in enumerate(rows, 2):
                forced = {
                    label: int(row[label])
                    for label in details["input_pins"]
                }
                got, _ = checker.evaluate(forced=forced)
                bad = {
                    label: (row[label].strip(), got[label])
                    for label in details["output_pins"]
                    if got[label] is None or str(got[label]) != row[label].strip()
                }
                if bad:
                    mismatches.append((line, bad))
            print(f"Reference rows: {len(rows)}; mismatches: {len(mismatches)}")
            for item in mismatches[:20]:
                print("  ", item)
            if args.require_exhaustive:
                expected = 1 << len(details["input_pins"])
                if len(rows) != expected:
                    print(f"ERROR: expected {expected} rows, found {len(rows)}")
                    return 2
            failed = failed or bool(mismatches)
        else:
            print("Outputs:", outputs)
        return int(failed)
    except (OSError, ET.ParseError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
