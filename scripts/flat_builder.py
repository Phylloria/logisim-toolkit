"""Shared helpers for flat, scalar, direct-wire Logisim projects."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from direct_router import WireNet
from generate_hierarchical_keypad import (
    Stage,
    comp,
    gate_inputs,
    validate_stage_grid,
    wire,
)


def build_wire_nets(
    stage: Stage,
    output_signals: dict[str, str],
    *,
    require_all_drivers: bool = True,
) -> list[WireNet]:
    sinks: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for gate in stage.gates:
        for wanted, terminal in zip(gate.inputs, gate_inputs(gate)):
            sinks[wanted].append(terminal)

    output_pins = {pin.name: pin for pin in stage.outputs}
    if set(output_signals) != set(output_pins):
        raise ValueError(
            "output signal map does not match output Pins: "
            f"{sorted(output_signals)} != {sorted(output_pins)}"
        )
    for output_name, signal in output_signals.items():
        sinks[signal].append(output_pins[output_name].point)

    sources = {pin.name: pin.point for pin in stage.inputs}
    sources.update({gate.signal: gate.point for gate in stage.gates})
    nets = []
    for signal, terminals in sinks.items():
        try:
            source = sources[signal]
        except KeyError as error:
            raise ValueError(f"signal {signal!r} has no driver") from error
        nets.append(WireNet(signal, tuple([source, *terminals])))

    if require_all_drivers:
        unused = set(sources) - set(sinks)
        if unused:
            raise ValueError(f"unused signal(s): {sorted(unused)}")
    return nets


def write_flat_project(
    stage: Stage,
    path: Path,
    texts: list[tuple[str, int, int]],
) -> None:
    validate_stage_grid(stage)
    for text, x, y in texts:
        if x % 10 or y % 10:
            raise ValueError(
                f"off-grid Text {text!r} at ({x},{y})"
            )
    root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
    ET.SubElement(root, "lib", {"desc": "#Wiring", "name": "0"})
    ET.SubElement(root, "lib", {"desc": "#Gates", "name": "1"})
    ET.SubElement(root, "lib", {"desc": "#Base", "name": "6"})
    ET.SubElement(root, "main", {"name": "main"})
    options = ET.SubElement(root, "options")
    for key, value in (
        ("gateUndefined", "ignore"),
        ("simlimit", "1000"),
        ("simrand", "0"),
    ):
        ET.SubElement(options, "a", {"name": key, "val": value})
    circuit = ET.SubElement(root, "circuit", {"name": "main"})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": "main"})

    for text, x, y in texts:
        comp(circuit, "6", (x, y), "Text", (
            ("font", "SansSerif plain 14"),
            ("halign", "left"),
            ("text", text),
            ("valign", "base"),
        ))
    for pin in stage.inputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", "east"),
            ("label", pin.name),
            ("labelloc", "west"),
            ("tristate", "false"),
        ))
    for gate in stage.gates:
        attrs = [("facing", "east")]
        if gate.kind != "NOT":
            attrs.append(("inputs", len(gate.inputs)))
        comp(circuit, "1", gate.point, {
            "AND": "AND Gate",
            "OR": "OR Gate",
            "XOR": "XOR Gate",
            "NOT": "NOT Gate",
        }[gate.kind], attrs)
    for pin in stage.outputs:
        comp(circuit, "0", pin.point, "Pin", (
            ("facing", "west"),
            ("label", pin.name),
            ("labelloc", "east"),
            ("output", "true"),
        ))
    for start, end in stage.wires:
        wire(circuit, start, end)

    ET.indent(root, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
