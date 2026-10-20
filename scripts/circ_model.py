"""Universal Logisim 2.7.1 circuit model for buses and sequential logic.

Supported core components:
  Pin, Tunnel, Power, Ground, Constant, Clock, Splitter
  AND/OR/NAND/NOR/XOR/XNOR/NOT gates
  D Flip-Flop, Register, Counter
  nested subcircuits with custom appearances

The model resolves geometry to bit-level nets, so bus pins, splitter decoding,
splitter combining, bus gates, hierarchy, and register feedback share one
simulation engine.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from check_circ import Nets, gate_ports, point
from logisim_geometry import (
    GATE_NAMES,
    gate_body_half_height,
    gate_input_axis,
    implicit_t_junctions,
    on_wire_segment,
    splitter_definition,
)


GATES = set(GATE_NAMES.values())


@dataclass(frozen=True)
class Port:
    name: str
    point: tuple[int, int]
    width: int
    role: str
    required: bool = True


@dataclass
class Component:
    index: int
    name: str
    library: str | None
    point: tuple[int, int]
    attributes: dict[str, str]
    ports: list[Port] = field(default_factory=list)
    port_bits: dict[str, list[tuple[Any, int]]] = field(default_factory=dict)
    splitter_mapping: list[int] | None = None


@dataclass
class CircuitModel:
    name: str
    components: list[Component]
    wires: list[tuple[tuple[int, int], tuple[int, int]]]
    findings: list[str]
    wire_covered: set[tuple[int, int]]
    input_pins: dict[str, Component]
    output_pins: dict[str, Component]
    drivers: dict[tuple[Any, int], list[str]]


class BitUF:
    def __init__(self) -> None:
        self.parent: dict[tuple[Any, int], tuple[Any, int]] = {}

    def find(self, item):
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _pin_output(attributes: dict[str, str]) -> bool:
    return attributes.get("output") == "true" or attributes.get("type") == "output"


def _width(attributes: dict[str, str], default: int = 1) -> int:
    return int(attributes.get("width", str(default)))


def _triggered(previous: int | None, current: int | None, trigger: str) -> bool:
    if current is None:
        return False
    if trigger in {"high", "level-high"}:
        return current == 1
    if trigger in {"low", "level-low"}:
        return current == 0
    if previous is None:
        return False
    if trigger == "falling":
        return previous == 1 and current == 0
    return previous == 0 and current == 1


class UniversalProject:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.root = ET.parse(path).getroot()
        self.circuits = {
            circuit.get("name"): circuit for circuit in self.root.findall("circuit")
        }
        main = self.root.find("main")
        self.main = main.get("name") if main is not None else "main"
        self.pins: dict[str, dict[tuple[int, int], tuple[str, bool, int]]] = {}
        self.appearances: dict[str, list[tuple[tuple[int, int], tuple[str, bool, int]]]] = {}
        self.models: dict[str, CircuitModel] = {}
        self.state: dict[tuple[Any, ...], int] = {}
        self.clock_state: dict[tuple[Any, ...], int] = {}
        self._read_pins()

    def _read_pins(self) -> None:
        for name, circuit in self.circuits.items():
            pins = {}
            for component in circuit.findall("comp"):
                if component.get("name") != "Pin" or not component.get("loc"):
                    continue
                attrs = {
                    item.get("name"): item.get("val", "")
                    for item in component.findall("a")
                }
                pins[point(component.get("loc"))] = (
                    attrs.get("label", ""),
                    _pin_output(attrs),
                    _width(attrs),
                )
            self.pins[name] = pins
            appear = circuit.find("appear")
            ports = []
            if appear is not None:
                anchor = appear.find("circ-anchor")
                if anchor is not None:
                    ax, ay = int(anchor.get("x")) + 3, int(anchor.get("y")) + 3
                    for node in appear.findall("circ-port"):
                        px, py = (
                            int(value.strip())
                            for value in node.get("pin").split(",", 1)
                        )
                        center = (
                            int(node.get("x")) + int(node.get("width")) // 2,
                            int(node.get("y")) + int(node.get("height")) // 2,
                        )
                        ports.append((
                            (center[0] - ax, center[1] - ay),
                            pins[(px, py)],
                        ))
            self.appearances[name] = ports

    def _component_ports(self, component: Component) -> None:
        name = component.name
        attrs = component.attributes
        x, y = component.point
        if name == "Pin":
            width = _width(attrs)
            role = "driver" if not _pin_output(attrs) else "sink"
            component.ports = [Port("port", component.point, width, role)]
        elif name in {"Power", "Ground"}:
            component.ports = [Port("out", component.point, 1, "driver", False)]
        elif name == "Constant":
            component.ports = [Port("out", component.point, _width(attrs), "driver", False)]
        elif name == "Clock":
            component.ports = [Port("out", component.point, 1, "driver", False)]
        elif name in GATES:
            inputs, output = gate_ports({
                "name": name,
                "x": x,
                "y": y,
                "attributes": attrs,
            })
            width = _width(attrs)
            component.ports = [
                *[
                    Port(f"in{index}", pin, width, "sink")
                    for index, pin in enumerate(inputs)
                ],
                Port("out", output, width, "driver", False),
            ]
        elif name == "Splitter":
            incoming, branches, points = splitter_definition(attrs)
            component.splitter_mapping = [
                end
                for bit in range(incoming)
                for end, branch in enumerate(branches, 1)
                if bit in branch
            ]
            component.ports = [Port("bus", component.point, incoming, "io")]
            for index, branch in enumerate(branches):
                component.ports.append(Port(
                    f"out{index}", (x + points[index][0], y + points[index][1]),
                    len(branch), "io", False,
                ))
        elif name == "D Flip-Flop":
            component.ports = [
                Port("d", (x - 40, y + 20), 1, "sink"),
                Port("clock", (x - 40, y), 1, "sink"),
                Port("q", (x, y), 1, "driver", False),
                Port("notq", (x, y + 20), 1, "driver", False),
                Port("reset", (x - 10, y + 30), 1, "sink", False),
                Port("preset", (x - 30, y + 30), 1, "sink", False),
                Port("enable", (x - 20, y + 30), 1, "sink", False),
            ]
        elif name == "Adder":
            width = _width(attrs, 8)
            component.ports = [
                Port("in0", (x - 40, y - 10), width, "sink"),
                Port("in1", (x - 40, y + 10), width, "sink"),
                Port("cin", (x - 20, y - 20), 1, "sink", False),
                Port("out", (x, y), width, "driver", False),
                Port("cout", (x - 20, y + 20), 1, "driver", False),
            ]
        elif name == "Comparator":
            width = _width(attrs, 8)
            component.ports = [
                Port("in0", (x - 40, y - 10), width, "sink"),
                Port("in1", (x - 40, y + 10), width, "sink"),
                Port("gt", (x, y - 10), 1, "driver", False),
                Port("eq", (x, y), 1, "driver", False),
                Port("lt", (x, y + 10), 1, "driver", False),
            ]
        elif name == "Multiplexer":
            width = _width(attrs)
            select_width = int(attrs.get("select", "1"))
            count = 1 << select_width
            enable = attrs.get("enable", "true") != "false"
            select_location = attrs.get("selectloc", "bottom_left")
            component.ports = []
            if count == 2:
                component.ports.extend([
                    Port("in0", (x - 30, y - 10), width, "sink"),
                    Port("in1", (x - 30, y + 10), width, "sink"),
                ])
                select_point = (x - 20, y + (20 if select_location == "bottom_left" else -20))
            else:
                start_y = y - (count // 2) * 10
                component.ports.extend([
                    Port(f"in{index}", (x - 40, start_y + index * 10), width, "sink")
                    for index in range(count)
                ])
                select_point = (
                    x - 20,
                    y + (20 if select_location == "bottom_left" else (start_y + count * 10 - y)),
                )
            component.ports.append(Port("select", select_point, select_width, "sink"))
            if enable:
                component.ports.append(Port(
                    "enable",
                    (select_point[0] + 10, select_point[1]),
                    1, "sink", False,
                ))
            component.ports.append(Port("out", (x, y), width, "driver", False))
        elif name == "Decoder":
            select_width = int(attrs.get("select", "1"))
            count = 1 << select_width
            enable = attrs.get("enable", "true") != "false"
            select_location = attrs.get("selectloc", "bottom_left")
            if count == 2:
                ys = (-30, -10) if select_location == "bottom_left" else (10, 30)
                component.ports = [
                    Port(f"out{index}", (x + 10, y + ys[index]), 1, "driver", False)
                    for index in range(2)
                ]
            else:
                start = y - 10 * count if select_location == "bottom_left" else y
                component.ports = [
                    Port(f"out{index}", (x + 20, start + index * 10), 1, "driver", False)
                    for index in range(count)
                ]
            component.ports.append(Port("select", (x, y), select_width, "sink"))
            if enable:
                component.ports.append(Port("enable", (x - 10, y), 1, "sink", False))
        elif name in {"Register", "Counter"}:
            width = _width(attrs, 8)
            component.ports = [
                Port("d", (x - 30, y), width, "sink"),
                Port("clock", (x - 20, y + 20), 1, "sink"),
                Port("clear", (x - 10, y + 20), 1, "sink", False),
                Port("q", (x, y), width, "driver", False),
            ]
            if name == "Register":
                component.ports.append(Port("enable", (x - 30, y + 10), 1, "sink", False))
            else:
                component.ports[0].required = False
                component.ports.extend([
                    Port("load", (x - 30, y - 10), 1, "sink", False),
                    Port("count", (x - 30, y + 10), 1, "sink", False),
                    Port("carry", (x, y + 10), 1, "driver", False),
                ])
        elif name in self.circuits:
            for relative, (label, output, width) in self.appearances[name]:
                component.ports.append(Port(
                    f"{'out' if output else 'in'}:{label}",
                    (x + relative[0], y + relative[1]),
                    width,
                    "driver" if output else "sink",
                    not output,
                ))

    def model(self, name: str) -> CircuitModel:
        if name in self.models:
            return self.models[name]
        circuit = self.circuits[name]
        findings = []
        components = []
        for index, element in enumerate(circuit.findall("comp")):
            if not element.get("loc"):
                continue
            x, y = point(element.get("loc"))
            attrs = {
                item.get("name"): item.get("val", "")
                for item in element.findall("a")
            }
            comp_name = element.get("name", "")
            if comp_name == "Text":
                continue
            if comp_name == "Tunnel":
                components.append(Component(
                    index, comp_name, element.get("lib"), (x, y), attrs
                ))
                continue
            component = Component(
                index, comp_name, element.get("lib"), (x, y), attrs
            )
            self._component_ports(component)
            if not component.ports:
                findings.append(f"unsupported component {comp_name} at ({x},{y})")
            components.append(component)

        wires = [
            (point(element.get("from")), point(element.get("to")))
            for element in circuit.findall("wire")
        ]
        for component in components:
            if component.point[0] % 10 or component.point[1] % 10:
                findings.append(
                    f"off-grid component {component.name}[{component.index}] "
                    f"at {component.point}"
                )
        for endpoint in sorted({
            endpoint for wire in wires for endpoint in wire
            if endpoint[0] % 10 or endpoint[1] % 10
        }):
            findings.append(f"off-grid wire endpoint {endpoint}")
        for endpoint, containing, branch in implicit_t_junctions(wires):
            findings.append(
                f"implicit T junction at {endpoint}: {branch} ends inside "
                f"{containing}; split the containing wire"
            )
        for index, (start, end) in enumerate(wires):
            for other_start, other_end in wires[index + 1:]:
                if start[1] == end[1] == other_start[1] == other_end[1]:
                    overlap = min(max(start[0], end[0]), max(other_start[0], other_end[0])) - max(
                        min(start[0], end[0]), min(other_start[0], other_end[0])
                    )
                    if overlap > 0:
                        findings.append(
                            f"overlapping collinear wires: {start}->{end} and "
                            f"{other_start}->{other_end}"
                        )
                elif start[0] == end[0] == other_start[0] == other_end[0]:
                    overlap = min(max(start[1], end[1]), max(other_start[1], other_end[1])) - max(
                        min(start[1], end[1]), min(other_start[1], other_end[1])
                    )
                    if overlap > 0:
                        findings.append(
                            f"overlapping collinear wires: {start}->{end} and "
                            f"{other_start}->{other_end}"
                        )
        terminal_points = {
            port.point for component in components for port in component.ports
        }
        terminal_points.update(
            component.point for component in components if component.name == "Tunnel"
        )
        endpoint_counts = defaultdict(int)
        for start, end in wires:
            endpoint_counts[start] += 1
            endpoint_counts[end] += 1
        for wire_index, (start, end) in enumerate(wires):
            for endpoint in (start, end):
                if endpoint in terminal_points or endpoint_counts[endpoint] > 1:
                    continue
                if any(
                    other_index != wire_index
                    and on_wire_segment(endpoint, other_start, other_end)
                    for other_index, (other_start, other_end) in enumerate(wires)
                ):
                    continue
                findings.append(
                    f"dangling wire endpoint {endpoint} on {start}->{end}"
                )
        terminals = {
            port.point for component in components for port in component.ports
        }
        tunnels = [
            component for component in components if component.name == "Tunnel"
        ]
        terminals.update(component.point for component in tunnels)
        nets = Nets(wires, terminals)
        tunnel_groups = defaultdict(list)
        for tunnel in tunnels:
            label = tunnel.attributes.get("label", "")
            if label:
                tunnel_groups[label].append(tunnel.point)
        for locations in tunnel_groups.values():
            for location in locations[1:]:
                nets.union(locations[0], location)

        width_by_root: dict[tuple[int, int], set[int]] = defaultdict(set)
        for component in components:
            for port in component.ports:
                width_by_root[nets.find(port.point)].add(port.width)
        for root, widths in width_by_root.items():
            if len(widths) > 1:
                findings.append(
                    f"net at {root} has conflicting widths {sorted(widths)}"
                )

        roots = sorted({nets.find(port.point) for component in components for port in component.ports})
        root_width = {
            root: min(width_by_root.get(root, {1}))
            for root in roots
        }
        bit_parent = BitUF()

        def bit_node(root, index):
            return (root, index)

        for component in components:
            if component.name == "Splitter":
                incoming = component.ports[0].width
                bus_root = nets.find(component.ports[0].point)
                mapping = self._splitter_mapping(component)
                for bit, end in enumerate(mapping):
                    if end <= 0:
                        continue
                    branch_port = component.ports[end]
                    branch_bits = [
                        index for index, value in enumerate(mapping) if value == end
                    ]
                    thread = branch_bits.index(bit)
                    bit_parent.union(
                        bit_node(bus_root, bit),
                        bit_node(nets.find(branch_port.point), thread),
                    )

        for component in components:
            for port in component.ports:
                root = nets.find(port.point)
                component.port_bits[port.name] = [
                    bit_parent.find(bit_node(root, bit))
                    for bit in range(port.width)
                ]

        drivers = defaultdict(list)
        input_pins = {}
        output_pins = {}
        for component in components:
            if component.name == "Pin":
                label = component.attributes.get("label", "")
                if _pin_output(component.attributes):
                    output_pins[label] = component
                else:
                    input_pins[label] = component
            for port in component.ports:
                if port.role != "driver":
                    continue
                for bit in component.port_bits.get(port.name, []):
                    drivers[bit].append(
                        f"{component.name}[{component.index}].{port.name}"
                    )
        for root, names in drivers.items():
            if len(names) > 1:
                findings.append(
                    f"multiple drivers on bit {root}: {', '.join(names)}"
                )
        if name == self.main:
            for label, component in input_pins.items():
                attrs = component.attributes
                tristate = attrs.get("tristate", "true").lower() != "false"
                pull = attrs.get("pull", "none").lower()
                if tristate and pull == "none":
                    findings.append(
                        f"input Pin {label} is tristate; set tristate=false "
                        "for a manually operated top-level input"
                    )

        model = CircuitModel(
            name, components, wires, findings, nets.wire_covered,
            input_pins, output_pins, drivers,
        )
        self.models[name] = model
        return model

    def _splitter_mapping(self, component: Component) -> list[int]:
        attrs = component.attributes
        fanout = int(attrs.get("fanout", "2"))
        incoming = component.ports[0].width
        if any(f"bit{index}" in attrs for index in range(incoming)):
            mapping = []
            for index in range(incoming):
                value = attrs.get(f"bit{index}", "none").lower()
                mapping.append(0 if value in {"none", ""} else int(value))
            return mapping
        from logisim_geometry import splitter_distribution
        return splitter_distribution(fanout, incoming)

    @staticmethod
    def _read_bits(model: CircuitModel, component: Component, port: str,
                   values: dict[tuple[Any, int], int | None]) -> int | None:
        bits = component.port_bits.get(port, [])
        result = 0
        for index, bit in enumerate(bits):
            value = values.get(bit)
            if value is None:
                return None
            result |= (value & 1) << index
        return result

    @staticmethod
    def _write_bits(model: CircuitModel, component: Component, port: str,
                    value: int, values: dict[tuple[Any, int], int | None]) -> None:
        for index, bit in enumerate(component.port_bits.get(port, [])):
            new_value = (value >> index) & 1
            old_value = values.get(bit)
            if old_value is not None and old_value != new_value:
                raise ValueError(
                    f"value conflict on {model.name} {component.name}[{component.index}].{port}"
                )
            values[bit] = new_value

    def _seq_key(self, path, component: Component, field: str = "state"):
        return (path, component.index, field)

    def evaluate(self, circuit_name: str | None = None,
                 forced: dict[str, int] | None = None,
                 path: tuple[int, ...] = ()):
        name = circuit_name or self.main
        forced = forced or {}
        model = self.model(name)
        values: dict[tuple[Any, int], int | None] = {}
        for label, component in model.input_pins.items():
            self._write_bits(model, component, "port", forced.get(label, 0), values)
        for component in model.components:
            if component.name == "Power":
                self._write_bits(model, component, "out", 1, values)
            elif component.name == "Ground":
                self._write_bits(model, component, "out", 0, values)
            elif component.name == "Constant":
                self._write_bits(
                    model, component, "out",
                    int(component.attributes.get("value", "1"), 16), values
                )
            elif component.name == "Clock":
                self._write_bits(
                    model, component, "out",
                    self.clock_state.get(self._seq_key(path, component, "clock"), 0),
                    values,
                )
            elif component.name == "Adder":
                a = self._read_bits(model, component, "in0", values)
                b = self._read_bits(model, component, "in1", values)
                cin = self._read_bits(model, component, "cin", values)
                if a is not None and b is not None:
                    width = _width(component.attributes, 8)
                    total = a + b + (0 if cin is None else cin)
                    self._write_bits(model, component, "out", total & ((1 << width) - 1), values)
                    self._write_bits(model, component, "cout", (total >> width) & 1, values)
            elif component.name == "Comparator":
                a = self._read_bits(model, component, "in0", values)
                b = self._read_bits(model, component, "in1", values)
                if a is not None and b is not None:
                    width = _width(component.attributes, 8)
                    if component.attributes.get("mode", "signed") == "signed":
                        sign = 1 << (width - 1)
                        a = a - (1 << width) if a & sign else a
                        b = b - (1 << width) if b & sign else b
                    self._write_bits(model, component, "gt", int(a > b), values)
                    self._write_bits(model, component, "eq", int(a == b), values)
                    self._write_bits(model, component, "lt", int(a < b), values)
            elif component.name == "Multiplexer":
                select = self._read_bits(model, component, "select", values)
                enable = (
                    self._read_bits(model, component, "enable", values)
                    if any(port.name == "enable" for port in component.ports)
                    else 1
                )
                if select is not None and enable != 0:
                    chosen = self._read_bits(model, component, f"in{select}", values)
                    if chosen is not None:
                        self._write_bits(model, component, "out", chosen, values)
            elif component.name == "Decoder":
                select = self._read_bits(model, component, "select", values)
                enable = (
                    self._read_bits(model, component, "enable", values)
                    if any(port.name == "enable" for port in component.ports)
                    else 1
                )
                if select is not None:
                    selected = select if enable != 0 else -1
                    for port in component.ports:
                        if port.name.startswith("out"):
                            index = int(port.name[3:])
                            self._write_bits(
                                model, component, port.name,
                                1 if index == selected else 0, values,
                            )
            elif component.name in {"D Flip-Flop", "Register", "Counter"}:
                state = self.state.get(self._seq_key(path, component), 0)
                self._write_bits(model, component, "q", state, values)
                if component.name == "D Flip-Flop":
                    self._write_bits(model, component, "notq", 0 if state else 1, values)
                elif component.name == "Counter":
                    self._write_bits(model, component, "carry", 0, values)

        instances = [
            component for component in model.components
            if component.name in self.circuits
        ]

        for _ in range(max(2, len(model.components) * 2)):
            changed = False
            for component in model.components:
                if component.name in GATES:
                    input_values = [
                        self._read_bits(model, component, port.name, values)
                        for port in component.ports if port.name.startswith("in")
                    ]
                    if any(value is None for value in input_values):
                        continue
                    if component.name == "NOT Gate":
                        result = ~input_values[0]
                    elif component.name in {"AND Gate", "NAND Gate"}:
                        result = input_values[0]
                        for value in input_values[1:]:
                            result &= value
                        if component.name == "NAND Gate":
                            result = ~result
                    elif component.name in {"OR Gate", "NOR Gate"}:
                        result = 0
                        for value in input_values:
                            result |= value
                        if component.name == "NOR Gate":
                            result = ~result
                    else:
                        result = 0
                        for value in input_values:
                            result ^= value
                        if component.name == "XNOR Gate":
                            result = ~result
                    width = _width(component.attributes)
                    result &= (1 << width) - 1
                    before = self._read_bits(model, component, "out", values)
                    if before != result:
                        self._write_bits(model, component, "out", result, values)
                        changed = True
            for instance in instances:
                child_inputs = {}
                ready = True
                for port in instance.ports:
                    if port.role != "sink":
                        continue
                    value = self._read_bits(model, instance, port.name, values)
                    if value is None:
                        ready = False
                        break
                    child_inputs[port.name.split(":", 1)[1]] = value
                if not ready:
                    continue
                child_outputs, _ = self.evaluate(
                    instance.name, child_inputs, path + (instance.index,)
                )
                for port in instance.ports:
                    if port.role != "driver":
                        continue
                    result = child_outputs.get(port.name.split(":", 1)[1])
                    if result is None:
                        continue
                    before = self._read_bits(model, instance, port.name, values)
                    if before != result:
                        self._write_bits(model, instance, port.name, result, values)
                        changed = True
            if not changed:
                break

        outputs = {}
        details = {
            "inputs": {label: comp.ports[0].width for label, comp in model.input_pins.items()},
            "outputs": {label: comp.ports[0].width for label, comp in model.output_pins.items()},
            "values": values,
        }
        for label, component in model.output_pins.items():
            outputs[label] = self._read_bits(model, component, "port", values)
        return outputs, details

    def step(self, forced: dict[str, int] | None = None,
             circuit_name: str | None = None, path: tuple[int, ...] = ()):
        """Settle current inputs, then update sequential components on clock edges."""
        name = circuit_name or self.main
        forced = forced or {}
        outputs, details = self.evaluate(name, forced, path)
        model = self.model(name)
        values = details["values"]

        for component in model.components:
            if component.name == "D Flip-Flop":
                clock = self._read_bits(model, component, "clock", values)
                previous = self.clock_state.get(
                    self._seq_key(path, component, "prev_clock"), 0
                )
                trigger = component.attributes.get("trigger", "rising")
                enable = self._read_bits(model, component, "enable", values)
                reset = self._read_bits(model, component, "reset", values)
                preset = self._read_bits(model, component, "preset", values)
                d = self._read_bits(model, component, "d", values)
                state = self.state.get(self._seq_key(path, component), 0)
                if reset == 1:
                    state = 0
                elif preset == 1:
                    state = 1
                elif _triggered(previous, clock, trigger) and enable != 0 and d is not None:
                    state = d & 1
                self.state[self._seq_key(path, component)] = state
                self.clock_state[self._seq_key(path, component, "prev_clock")] = (
                    0 if clock is None else clock
                )
            elif component.name in {"Register", "Counter"}:
                clock = self._read_bits(model, component, "clock", values)
                previous = self.clock_state.get(
                    self._seq_key(path, component, "prev_clock"), 0
                )
                trigger = component.attributes.get("trigger", "rising")
                clear = self._read_bits(model, component, "clear", values)
                d = self._read_bits(model, component, "d", values)
                state = self.state.get(self._seq_key(path, component), 0)
                width = _width(component.attributes, 8)
                mask = (1 << width) - 1
                if clear == 1:
                    state = 0
                elif _triggered(previous, clock, trigger):
                    if component.name == "Register":
                        enable = self._read_bits(model, component, "enable", values)
                        if enable != 0 and d is not None:
                            state = d & mask
                    else:
                        load = self._read_bits(model, component, "load", values)
                        count_enable = self._read_bits(model, component, "count", values)
                        if load == 1 and d is not None:
                            state = d & mask
                        elif count_enable != 0:
                            updown = component.attributes.get("updown", "up")
                            state = (state + (-1 if updown == "down" else 1)) & mask
                self.state[self._seq_key(path, component)] = state
                self.clock_state[self._seq_key(path, component, "prev_clock")] = (
                    0 if clock is None else clock
                )

        # Update child circuits with their current input values.
        for instance in [
            component for component in model.components
            if component.name in self.circuits
        ]:
            child_inputs = {
                port.name.split(":", 1)[1]: self._read_bits(model, instance, port.name, values)
                for port in instance.ports if port.role == "sink"
            }
            self.step(child_inputs, instance.name, path + (instance.index,))

        return self.evaluate(name, forced, path)[0]

    def collect_findings(self) -> dict[str, list[str]]:
        findings = {}
        for name in self.circuits:
            model = self.model(name)
            result = list(model.findings)
            for label, component in model.input_pins.items():
                if component.ports[0].point not in model.wire_covered:
                    result.append(f"input Pin {label} is floating")
            for label, component in model.output_pins.items():
                if component.ports[0].point not in model.wire_covered:
                    result.append(f"output Pin {label} is floating")
            for component in model.components:
                for port in component.ports:
                    if port.required and port.point not in model.wire_covered:
                        result.append(
                            f"{component.name}[{component.index}].{port.name} is floating"
                        )
            findings[name] = result
        return findings
