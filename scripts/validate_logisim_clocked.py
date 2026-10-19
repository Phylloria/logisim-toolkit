#!/usr/bin/env python3
"""Validate a clocked circuit with fixed data inputs in real Logisim 2.7.1.

The harness replaces the named clock Pin with a Clock source, fixes every
other input Pin with a Constant, adds a cycle Counter/Comparator, and halts
after the requested number of rising edges. The expected sequence is produced
by the independent UniversalProject sequential model.
"""
from __future__ import annotations

import argparse
import copy
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from circ_model import UniversalProject
from validate_logisim import (
    format_actual,
    locate_java,
    locate_logisim,
    normalize_outputs,
    parse_value,
    pin_rows,
    point,
    select_circuit,
)


def ensure_library(root, desc, name):
    if not any(lib.get("name") == name for lib in root.findall("lib")):
        ET.SubElement(root, "lib", {"desc": desc, "name": name})


def add_constant(circuit, location, width, value, facing="east"):
    node = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({location[0]},{location[1]})", "name": "Constant",
    })
    for key, item in (
        ("facing", facing),
        ("width", str(width)),
        ("value", "0x" + format(value, "x")),
    ):
        ET.SubElement(node, "a", {"name": key, "val": item})


def add_power(circuit, location, name="Power"):
    node = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({location[0]},{location[1]})", "name": name,
    })
    ET.SubElement(node, "a", {"name": "facing", "val": "east"})


def add_wire(circuit, start, end):
    ET.SubElement(circuit, "wire", {
        "from": f"({start[0]},{start[1]})",
        "to": f"({end[0]},{end[1]})",
    })


def build_harness(source: Path, destination: Path, clock_label: str,
                  inputs: dict[str, int], cycles: int, circuit_name=None):
    root = ET.parse(source).getroot()
    circuit = select_circuit(root, circuit_name)
    ensure_library(root, "#Arithmetic", "3")
    ensure_library(root, "#Memory", "4")
    inputs_rows, outputs_rows = pin_rows(circuit)
    if not any(label == clock_label for label, _ in inputs_rows):
        raise ValueError(f"clock input {clock_label!r} not found")

    clock_location = None
    for component in list(circuit.findall("comp")):
        if component.get("name") != "Pin":
            continue
        attrs = {
            item.get("name"): item.get("val", "")
            for item in component.findall("a")
        }
        if attrs.get("output") == "true" or attrs.get("type") == "output":
            continue
        label = attrs.get("label", "")
        width = int(attrs.get("width", "1"))
        location = point(component.get("loc"))
        if label == clock_label:
            clock_location = location
            component.set("name", "Clock")
            for child in list(component):
                component.remove(child)
            for key, value in (("facing", "east"), ("highDuration", 1), ("lowDuration", 1)):
                ET.SubElement(component, "a", {"name": key, "val": str(value)})
        else:
            value = inputs.get(label, 0)
            if value < 0 or value >= (1 << width):
                raise ValueError(f"input {label}={value} does not fit width {width}")
            component.set("name", "Constant")
            for child in list(component):
                component.remove(child)
            for key, item in (
                ("facing", "east"),
                ("width", str(width)),
                ("value", "0x" + format(value, "x")),
            ):
                ET.SubElement(component, "a", {"name": key, "val": item})
    if clock_location is None:
        raise ValueError("clock Pin replacement failed")

    locations = [
        point(component.get("loc"))
        for component in circuit.findall("comp") if component.get("loc")
    ]
    for wire in circuit.findall("wire"):
        locations.extend((point(wire.get("from")), point(wire.get("to"))))
    max_x = max(x for x, _ in locations)
    max_y = max(y for _, y in locations)
    cx, cy = max_x + 320, max_y + 220
    counter = ET.SubElement(circuit, "comp", {
        "lib": "4", "loc": f"({cx},{cy})", "name": "Counter",
    })
    for key, value in (("width", "8"), ("trigger", "rising")):
        ET.SubElement(counter, "a", {"name": key, "val": value})
    comparator = ET.SubElement(circuit, "comp", {
        "lib": "3", "loc": f"({cx + 260},{cy})", "name": "Comparator",
    })
    ET.SubElement(comparator, "a", {"name": "width", "val": "8"})
    add_constant(circuit, (cx + 180, cy + 10), 8, cycles)
    add_power(circuit, (cx - 100, cy + 10), "Power")
    add_power(circuit, (cx - 100, cy + 80), "Ground")
    cycle_pin = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({cx + 80},{cy - 100})", "name": "Pin",
    })
    for key, value in (
        ("facing", "west"), ("width", "8"), ("label", "CYCLE"),
        ("output", "true"), ("labelloc", "east"),
    ):
        ET.SubElement(cycle_pin, "a", {"name": key, "val": value})
    halt = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({cx + 360},{cy})", "name": "Pin",
    })
    for key, value in (
        ("facing", "west"), ("label", "halt"),
        ("output", "true"), ("labelloc", "east"),
    ):
        ET.SubElement(halt, "a", {"name": key, "val": value})

    # Counter Q fans out to CYCLE and Comparator IN0.
    add_wire(circuit, (cx, cy), (cx + 80, cy))
    add_wire(circuit, (cx + 80, cy), (cx + 80, cy - 100))
    add_wire(circuit, (cx + 80, cy), (cx + 180, cy))
    add_wire(circuit, (cx + 180, cy), (cx + 180, cy - 10))
    add_wire(circuit, (cx + 180, cy - 10), (cx + 220, cy - 10))
    add_wire(circuit, (cx + 180, cy + 10), (cx + 220, cy + 10))
    add_wire(circuit, (cx + 260, cy), (cx + 360, cy))
    add_wire(circuit, (cx - 100, cy + 10), (cx - 30, cy + 10))
    add_wire(circuit, (cx - 100, cy + 80), (cx - 10, cy + 80))
    add_wire(circuit, (cx - 10, cy + 80), (cx - 10, cy + 20))

    # Clock trunk to the harness Counter, routed below the DUT.
    lane_y = max_y + 100
    clock_lane_x = clock_location[0] + 120
    add_wire(circuit, clock_location, (clock_lane_x, clock_location[1]))
    add_wire(circuit, (clock_lane_x, clock_location[1]), (clock_lane_x, lane_y))
    add_wire(circuit, (clock_lane_x, lane_y), (cx - 20, lane_y))
    add_wire(circuit, (cx - 20, lane_y), (cx - 20, cy + 20))

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return outputs_rows


def expected_sequence(source: Path, clock_label: str, inputs: dict[str, int],
                      cycles: int, circuit_name=None):
    project = UniversalProject(source)
    name = circuit_name or project.main
    outputs, details = project.evaluate(name, inputs)
    result = []
    for _ in range(cycles):
        high = dict(inputs)
        high[clock_label] = 1
        after_high = project.step(high, name)
        low = dict(inputs)
        low[clock_label] = 0
        project.step(low, name)
        result.append(after_high)
    return result, details["outputs"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path)
    parser.add_argument("--clock", default="CLK")
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--input", action="append", default=[],
                        help="fixed input NAME=VALUE")
    parser.add_argument("--circuit-name")
    parser.add_argument("--logisim")
    parser.add_argument("--java")
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()
    try:
        fixed = {}
        for item in args.input:
            label, separator, value = item.partition("=")
            if not separator:
                raise ValueError(f"invalid --input {item!r}")
            fixed[label] = int(value, 0)
        logisim = locate_logisim(args.logisim)
        java = locate_java(args.java)
        expected, output_widths = expected_sequence(
            args.circuit, args.clock, fixed, args.cycles, args.circuit_name
        )
        with tempfile.TemporaryDirectory(prefix="logisim-clocked-") as temporary:
            harness = Path(temporary) / "harness.circ"
            outputs = build_harness(
                args.circuit, harness, args.clock, fixed, args.cycles,
                args.circuit_name,
            )
            command = [
                str(java), "-jar", str(logisim), "-locale", "en",
                "-tty", "table", str(harness),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=args.timeout, stdin=subprocess.DEVNULL,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if not lines:
                raise RuntimeError(
                    f"no Logisim output (exit {result.returncode}): "
                    f"{result.stderr.strip()}"
                )
            rows = []
            widths = [(label, width) for label, width in outputs] + [("CYCLE", 8)]
            for line in lines:
                tokens = normalize_outputs(line.split(), widths)
                if len(tokens) != len(widths):
                    continue
                values = {}
                for (label, width), token in zip(widths, tokens):
                    values[label] = format_actual(token, width)
                rows.append(values)
            observed = [row for row in rows if 1 <= row["CYCLE"] <= args.cycles]
            if len(observed) != args.cycles:
                raise RuntimeError(
                    f"expected {args.cycles} clock rows, got {len(observed)}"
                )
            mismatches = []
            for index, (row, wanted) in enumerate(zip(observed, expected), 1):
                bad = {
                    label: (wanted[label], row[label])
                    for label in output_widths
                    if row.get(label) != wanted[label]
                }
                if bad:
                    mismatches.append((index, bad))
            print(f"Logisim: {logisim}")
            print(f"Java: {java}")
            print(f"Clock cycles checked: {args.cycles}")
            if mismatches:
                print(f"FAIL: {len(mismatches)} cycle(s)")
                for item in mismatches[:20]:
                    print("  ", item)
                return 1
            print(f"PASS: {args.cycles} clocked cycle(s) matched the static model")
            return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
