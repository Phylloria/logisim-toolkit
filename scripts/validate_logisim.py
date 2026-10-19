#!/usr/bin/env python3
"""Run real Logisim 2.7.1 simulations for a tab-separated vector table.

Each vector becomes a temporary harness copy. Functional input Pins are
replaced with Power/Ground sources, and an output Pin named 'halt' makes the
2.7.1 TTY loop finish after propagation. The clean source project is never
modified.
"""
from __future__ import annotations

import argparse
import copy
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def point(text: str) -> tuple[int, int]:
    x, y = (int(value.strip()) for value in text[1:-1].split(",", 1))
    return x, y


def locate_logisim(explicit: str | None) -> Path:
    candidates = [
        explicit,
        os.environ.get("LOGISIM_JAR"),
        os.environ.get("LOGISIM_EXE"),
        r"C:\Logisim\logisim-win-2.7.1.exe",
        "tools/logisim-generic-2.7.1.jar",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve()
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Logisim runtime not found; pass --logisim or set LOGISIM_JAR/LOGISIM_EXE"
    )


def locate_java(explicit: str | None) -> Path:
    candidates = [
        explicit,
        os.environ.get("JAVA_EXE"),
        shutil.which("java"),
        r"C:\Program Files\Java\jre1.8.0_503\bin\java.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve()
        if path.is_file():
            return path
    raise FileNotFoundError("Java runtime not found; pass --java or set JAVA_EXE")


def select_circuit(root: ET.Element, name: str | None) -> ET.Element:
    main = root.find("main")
    selected = name or (main.get("name") if main is not None else "main")
    for circuit in root.findall("circuit"):
        if circuit.get("name") == selected:
            return circuit
    raise ValueError(f"circuit {selected!r} not found")


def pin_rows(circuit: ET.Element):
    inputs = []
    outputs = []
    for component in circuit.findall("comp"):
        if component.get("name") != "Pin":
            continue
        attributes = {
            item.get("name"): item.get("val", "")
            for item in component.findall("a")
        }
        label = attributes.get("label", "")
        width = int(attributes.get("width", "1"))
        x, y = point(component.get("loc"))
        is_output = attributes.get("output") == "true" or attributes.get("type") == "output"
        if is_output:
            outputs.append((label, width, x, y))
        else:
            inputs.append((label, width, x, y))
    inputs.sort(key=lambda item: (item[3], item[2]))
    outputs.sort(key=lambda item: (item[3], item[2]))
    return (
        [(label, width) for label, width, _, _ in inputs],
        [(label, width) for label, width, _, _ in outputs],
    )


def replace_input_pins(circuit: ET.Element, values: dict[str, int]) -> None:
    for component in list(circuit.findall("comp")):
        if component.get("name") != "Pin":
            continue
        attributes = {
            item.get("name"): item.get("val", "")
            for item in component.findall("a")
        }
        if attributes.get("output") == "true" or attributes.get("type") == "output":
            continue
        label = attributes.get("label", "")
        if label not in values:
            raise ValueError(f"vector is missing input {label!r}")
        width = int(attributes.get("width", "1"))
        component.set("name", "Constant")
        for child in list(component):
            component.remove(child)
        for key, value in (
            ("facing", "east"),
            ("width", str(width)),
            ("value", "0x" + format(values[label], "x")),
        ):
            ET.SubElement(component, "a", {"name": key, "val": value})


def add_halt(circuit: ET.Element) -> None:
    locations = [
        point(component.get("loc"))
        for component in circuit.findall("comp") if component.get("loc")
    ]
    for wire in circuit.findall("wire"):
        locations.extend((point(wire.get("from")), point(wire.get("to"))))
    max_x = max(x for x, _ in locations) + 300
    max_y = max(y for _, y in locations) + 220
    halt = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({max_x},{max_y})", "name": "Pin",
    })
    for key, value in (
        ("facing", "west"),
        ("label", "halt"),
        ("labelloc", "east"),
        ("output", "true"),
    ):
        ET.SubElement(halt, "a", {"name": key, "val": value})
    source = ET.SubElement(circuit, "comp", {
        "lib": "0", "loc": f"({max_x - 100},{max_y})", "name": "Power",
    })
    ET.SubElement(source, "a", {"name": "facing", "val": "east"})
    ET.SubElement(circuit, "wire", {
        "from": f"({max_x - 100},{max_y})",
        "to": f"({max_x},{max_y})",
    })


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise ValueError("vector table has no data rows")
    return rows


def parse_value(value: str, width: int) -> int:
    text = value.strip().lower()
    if text.startswith("0x"):
        number = int(text, 16)
    elif text.startswith("0b"):
        number = int(text[2:], 2)
    elif set(text) <= {"0", "1"} and len(text) == width:
        number = int(text, 2)
    else:
        number = int(text, 10)
    if number < 0 or number >= (1 << width):
        raise ValueError(f"value {value!r} does not fit width {width}")
    return number


def format_actual(value: str, width: int) -> int:
    text = value.strip().lower()
    if text in {"e", "x"}:
        raise ValueError(f"Logisim reported an undefined/error value {value!r}")
    if text.startswith("0x"):
        return int(text, 16)
    if set(text) <= {"0", "1"}:
        if len(text) == width:
            return int(text, 2)
        if width > 6 and re.fullmatch(r"[0-9a-f]+", text):
            return int(text, 16)
    return int(text, 10)


def make_harness(source: Path, row: dict[str, str], circuit_name: str | None,
                 destination: Path) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    root = ET.parse(source).getroot()
    circuit = select_circuit(root, circuit_name)
    inputs, outputs = pin_rows(circuit)
    values = {}
    for label, width in inputs:
        value = row[label].strip()
        values[label] = parse_value(value, width)
    replace_input_pins(circuit, values)
    add_halt(circuit)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return inputs, outputs


def run_logisim(java: Path, logisim: Path, harness: Path, timeout: float):
    command = [
        str(java), "-jar", str(logisim), "-locale", "en",
        "-tty", "table", str(harness),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    output_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not output_lines:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Logisim produced no output (exit {completed.returncode}): {detail}")
    values = output_lines[-1].split()
    return values, completed


def normalize_outputs(values: list[str], outputs: list[tuple[str, int]]) -> list[str]:
    joined = "".join(values)
    total_width = sum(width for _, width in outputs)
    if set(joined) <= {"0", "1"} and len(joined) == total_width:
        result = []
        offset = 0
        for _, width in outputs:
            result.append(joined[offset:offset + width])
            offset += width
        return result
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--logisim", help="Path to a JAR-compatible Logisim executable/JAR")
    parser.add_argument("--java", help="Path to java.exe")
    parser.add_argument("--circuit-name")
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--limit", type=int, help="Run only the first N vectors")
    parser.add_argument("--keep-harnesses", type=Path,
                        help="Write each generated harness here instead of a temp directory")
    args = parser.parse_args()
    try:
        source = args.circuit.resolve()
        logisim = locate_logisim(args.logisim)
        java = locate_java(args.java)
        rows = read_rows(args.table)
        if args.limit is not None:
            rows = rows[:args.limit]
        print(f"Logisim: {logisim}")
        print(f"Java: {java}")
        print(f"Vectors: {len(rows)}")
        failures = []
        keep_dir = args.keep_harnesses
        if keep_dir:
            keep_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="logisim-vectors-") as temporary:
            harness_dir = keep_dir or Path(temporary)
            expected_outputs = None
            for index, row in enumerate(rows, 1):
                harness = harness_dir / f"harness_{index:03d}.circ"
                inputs, outputs = make_harness(
                    source, row, args.circuit_name, harness
                )
                if expected_outputs is None:
                    expected_outputs = outputs
                elif [item[0] for item in outputs] != [item[0] for item in expected_outputs]:
                    raise ValueError("output Pin order changed between harnesses")
                actual, completed = run_logisim(java, logisim, harness, args.timeout)
                actual = normalize_outputs(actual, outputs)
                if len(actual) != len(outputs):
                    failures.append((
                        index,
                        f"expected {len(outputs)} output values, got {len(actual)}",
                    ))
                    continue
                mismatches = {}
                for (label, width), value in zip(outputs, actual):
                    expected = parse_value(row[label], width)
                    try:
                        got = format_actual(value, width)
                    except ValueError as error:
                        mismatches[label] = (row[label].strip(), str(error))
                        continue
                    if got != expected:
                        mismatches[label] = (expected, got)
                if mismatches:
                    failures.append((index, mismatches))
                if completed.returncode not in (0, None):
                    # Halt exits with status 0; preserve stderr for a useful report.
                    failures.append((
                        index,
                        f"Logisim exit {completed.returncode}: {completed.stderr.strip()}",
                    ))
                if index % 8 == 0 or index == len(rows):
                    print(f"  checked {index}/{len(rows)}")
        if failures:
            print(f"FAIL: {len(failures)} vector(s)")
            for item in failures[:20]:
                print("  ", item)
            return 1
        print(f"PASS: {len(rows)} vector(s) matched in Logisim 2.7.1")
        return 0
    except (OSError, ET.ParseError, ValueError, RuntimeError,
            subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
