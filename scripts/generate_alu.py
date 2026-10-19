#!/usr/bin/env python3
"""Generate a flat gate-level N-bit ALU as a native Logisim 2.7.1 project.

The layout uses short orthogonal gate stubs and labeled Tunnels for the
long-distance nets. The circuit contains only Pins, Tunnels, Text, and basic
gates; no arithmetic, multiplexer, or truth-table components are used.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from logisim_geometry import GATE_NAMES, gate_input_axis, port_offsets


@dataclass(frozen=True)
class Gate:
    name: str
    kind: str
    inputs: tuple[str, ...]
    x: int
    y: int


@dataclass(frozen=True)
class PinSpec:
    name: str
    x: int
    y: int


@dataclass(frozen=True)
class OutputSpec:
    name: str
    signal: str
    x: int
    y: int


class CircuitBuilder:
    def __init__(self) -> None:
        self.inputs: list[PinSpec] = []
        self.outputs: list[OutputSpec] = []
        self.gates: list[Gate] = []
        self.texts: list[tuple[str, int, int]] = []
        self._input_names: set[str] = set()
        self._gate_names: set[str] = set()

    def add_input(self, name: str, x: int, y: int) -> None:
        if name in self._input_names or name in self._gate_names:
            raise ValueError(f"duplicate signal {name!r}")
        self.inputs.append(PinSpec(name, x, y))
        self._input_names.add(name)

    def add_output(self, name: str, signal: str, x: int, y: int) -> None:
        self.outputs.append(OutputSpec(name, signal, x, y))

    def add_gate(self, name: str, kind: str, inputs: Iterable[str], x: int, y: int) -> None:
        if kind not in GATE_NAMES:
            raise ValueError(f"unsupported gate kind {kind!r}")
        if name in self._input_names or name in self._gate_names:
            raise ValueError(f"duplicate signal {name!r}")
        values = tuple(inputs)
        if (kind == "NOT" and len(values) != 1) or (kind != "NOT" and len(values) < 2):
            raise ValueError(f"invalid input count for {name}: {len(values)}")
        self.gates.append(Gate(name, kind, values, x, y))
        self._gate_names.add(name)

    def add_text(self, text: str, x: int, y: int) -> None:
        self.texts.append((text, x, y))

    def ordered_gates(self) -> list[Gate]:
        available = set(self._input_names)
        remaining = list(self.gates)
        ordered: list[Gate] = []
        while remaining:
            progressed = False
            for gate in list(remaining):
                missing = [signal for signal in gate.inputs if signal not in available]
                if missing:
                    continue
                ordered.append(gate)
                available.add(gate.name)
                remaining.remove(gate)
                progressed = True
            if not progressed:
                names = ", ".join(gate.name for gate in remaining)
                raise ValueError(f"cycle or undefined input in gates: {names}")
        missing_outputs = sorted(
            {output.signal for output in self.outputs if output.signal not in available}
        )
        if missing_outputs:
            raise ValueError(f"undefined output signals: {missing_outputs}")
        return ordered

    @staticmethod
    def _comp(parent: ET.Element, library: str, x: int, y: int, name: str,
              attributes: Iterable[tuple[str, str | int]] = ()) -> None:
        node = ET.SubElement(parent, "comp", {
            "lib": library,
            "loc": f"({x},{y})",
            "name": name,
        })
        for key, value in sorted(attributes):
            ET.SubElement(node, "a", {"name": key, "val": str(value)})

    @staticmethod
    def _wire(parent: ET.Element, a: tuple[int, int], b: tuple[int, int]) -> None:
        if a == b:
            return
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError(f"diagonal wire {a} -> {b}")
        ET.SubElement(parent, "wire", {
            "from": f"({a[0]},{a[1]})",
            "to": f"({b[0]},{b[1]})",
        })

    def emit(self, path: Path, main_name: str = "main") -> None:
        ordered = self.ordered_gates()
        root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
        ET.SubElement(root, "lib", {"desc": "#Wiring", "name": "0"})
        ET.SubElement(root, "lib", {"desc": "#Gates", "name": "1"})
        ET.SubElement(root, "lib", {"desc": "#Base", "name": "6"})
        ET.SubElement(root, "main", {"name": main_name})
        options = ET.SubElement(root, "options")
        for key, value in (
            ("gateUndefined", "ignore"),
            ("simlimit", "1000"),
            ("simrand", "0"),
        ):
            ET.SubElement(options, "a", {"name": key, "val": value})

        circuit = ET.SubElement(root, "circuit", {"name": main_name})
        ET.SubElement(circuit, "a", {"name": "circuit", "val": main_name})

        for text, x, y in self.texts:
            self._comp(circuit, "6", x, y, "Text", (
                ("font", "SansSerif plain 14"),
                ("halign", "left"),
                ("text", text),
                ("valign", "base"),
            ))

        for pin in self.inputs:
            self._comp(circuit, "0", pin.x, pin.y, "Pin", (
                ("facing", "east"),
                ("label", pin.name),
                ("labelloc", "west"),
                ("tristate", "false"),
            ))
            source = (pin.x + 250, pin.y)
            self._comp(circuit, "0", source[0], source[1], "Tunnel", (
                ("facing", "west"),
                ("label", pin.name),
            ))
            self._wire(circuit, (pin.x, pin.y), source)

        for gate in ordered:
            self._comp(circuit, "1", gate.x, gate.y, GATE_NAMES[gate.kind],
                       (("facing", "east"), ("inputs", len(gate.inputs)))
                       if gate.kind != "NOT" else (("facing", "east"),))
            for signal, offset in zip(gate.inputs, port_offsets(len(gate.inputs))):
                port_y = gate.y + offset
                tunnel_x = gate.x - 90
                self._comp(circuit, "0", tunnel_x, port_y, "Tunnel", (
                    ("facing", "east"),
                    ("label", signal),
                ))
                self._wire(circuit, (tunnel_x, port_y),
                           (gate.x - gate_input_axis(GATE_NAMES[gate.kind]), port_y))
            output_tunnel = (gate.x + 70, gate.y)
            self._comp(circuit, "0", output_tunnel[0], output_tunnel[1], "Tunnel", (
                ("facing", "west"),
                ("label", gate.name),
            ))
            self._wire(circuit, (gate.x, gate.y), output_tunnel)

        for output in self.outputs:
            sink_x = output.x - 100
            self._comp(circuit, "0", sink_x, output.y, "Tunnel", (
                ("facing", "east"),
                ("label", output.signal),
            ))
            self._wire(circuit, (sink_x, output.y), (output.x, output.y))
            self._comp(circuit, "0", output.x, output.y, "Pin", (
                ("facing", "west"),
                ("label", output.name),
                ("labelloc", "east"),
                ("output", "true"),
            ))

        ET.indent(root, space="  ")
        path.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def alu_reference(a: int, b: int, cin: int, op: int, bits: int) -> dict[str, int]:
    mask = (1 << bits) - 1
    sign = 1 << (bits - 1)
    if op == 0:
        raw = a + b + cin
        y = raw & mask
        cout = (raw >> bits) & 1
        borrow = 0
    elif op == 1:
        raw = a + ((~b) & mask) + cin
        y = raw & mask
        cout = 0
        borrow = 1 - ((raw >> bits) & 1)
    elif op == 2:
        y = a & b
        cout = borrow = 0
    elif op == 3:
        y = a | b
        cout = borrow = 0
    elif op == 4:
        y = a ^ b
        cout = borrow = 0
    elif op == 5:
        y = (~a) & mask
        cout = borrow = 0
    elif op == 6:
        y = ((a << 1) | cin) & mask
        cout = borrow = 0
    elif op == 7:
        y = (a >> 1) | (cin << (bits - 1))
        cout = borrow = 0
    else:
        raise ValueError(f"invalid operation {op}")

    overflow = 0
    if op in (0, 1):
        a_negative = bool(a & sign)
        b_negative = bool(b & sign)
        y_negative = bool(y & sign)
        overflow = int(
            (a_negative == b_negative) and (y_negative != a_negative)
            if op == 0
            else (a_negative != b_negative) and (y_negative != a_negative)
        )

    result = {
        "COUT": cout,
        "BORROW": borrow,
        "ZERO": int(y == 0),
        "NEG": (y >> (bits - 1)) & 1,
        "OVF": overflow,
    }
    for index in range(bits):
        result[f"Y{index}"] = (y >> index) & 1
    return result


def build_alu(bits: int) -> CircuitBuilder:
    if bits < 2 or bits > 24:
        raise ValueError("bits must be between 2 and 24")
    builder = CircuitBuilder()

    builder.add_text(
        "OP2..0: 000 ADD  001 SUB  010 AND  011 OR  "
        "100 XOR  101 NOT-A  110 SHL  111 SHR",
        470, 45,
    )
    builder.add_text(
        "CIN: ADD carry input; SUB borrow input is active low (1 = no incoming borrow).",
        470, 85,
    )
    builder.add_text("ARITHMETIC", 820, 240)
    builder.add_text("ONE-HOT RESULT MUX", 3520, 240)
    builder.add_text("OUTPUTS", 7200, 240)
    builder.add_text("FLAGS", 820, bits * 240 + 620)

    for index in range(bits):
        row_y = 420 + index * 240
        builder.add_input(f"A{index}", 180, row_y - 70)
        builder.add_input(f"B{index}", 180, row_y + 70)
    builder.add_input("CIN", 180, 190)
    builder.add_input("OP2", 180, 70)
    builder.add_input("OP1", 180, 110)
    builder.add_input("OP0", 180, 150)

    control_y = 160
    builder.add_gate("NOP0", "NOT", ["OP0"], 820, control_y)
    builder.add_gate("NOP1", "NOT", ["OP1"], 1040, control_y)
    builder.add_gate("NOP2", "NOT", ["OP2"], 1260, control_y)
    selects = [
        ("SEL0", ["NOP2", "NOP1", "NOP0"]),
        ("SEL1", ["NOP2", "NOP1", "OP0"]),
        ("SEL2", ["NOP2", "OP1", "NOP0"]),
        ("SEL3", ["NOP2", "OP1", "OP0"]),
        ("SEL4", ["OP2", "NOP1", "NOP0"]),
        ("SEL5", ["OP2", "NOP1", "OP0"]),
        ("SEL6", ["OP2", "OP1", "NOP0"]),
        ("SEL7", ["OP2", "OP1", "OP0"]),
    ]
    for index, (name, inputs) in enumerate(selects):
        builder.add_gate(name, "AND", inputs, 1480 + index * 260, control_y)
    builder.add_gate("ADD_OR_SUB", "OR", ["SEL0", "SEL1"], 3560, control_y)

    columns = {
        "bx": 820,
        "p": 1100,
        "g": 1380,
        "cprop": 1660,
        "carry": 1940,
        "sum": 2220,
        "orl": 2500,
        "xorl": 2780,
        "nota": 3060,
    }
    mux_start = 3340
    mux_step = 280
    or_start = mux_start + 8 * mux_step
    output_x = or_start + 7 * mux_step + 260
    carry = "CIN"

    for index in range(bits):
        row_y = 420 + index * 240
        builder.add_gate(f"BX{index}", "XOR", [f"B{index}", "SEL1"],
                         columns["bx"], row_y)
        builder.add_gate(f"P{index}", "XOR", [f"A{index}", f"BX{index}"],
                         columns["p"], row_y)
        builder.add_gate(f"G{index}", "AND", [f"A{index}", f"BX{index}"],
                         columns["g"], row_y)
        builder.add_gate(f"CPROP{index}", "AND", [f"P{index}", carry],
                         columns["cprop"], row_y)
        builder.add_gate(f"CARRY{index + 1}", "OR",
                         [f"G{index}", f"CPROP{index}"], columns["carry"], row_y)
        builder.add_gate(f"SUM{index}", "XOR", [f"P{index}", carry],
                         columns["sum"], row_y)
        builder.add_gate(f"ORLOGIC{index}", "OR",
                         [f"A{index}", f"B{index}"], columns["orl"], row_y)
        builder.add_gate(f"XORLOGIC{index}", "XOR",
                         [f"A{index}", f"B{index}"], columns["xorl"], row_y)
        builder.add_gate(f"NOTA{index}", "NOT", [f"A{index}"],
                         columns["nota"], row_y)
        carry = f"CARRY{index + 1}"

    for index in range(bits):
        row_y = 420 + index * 240
        shift_left = "CIN" if index == 0 else f"A{index - 1}"
        shift_right = "CIN" if index == bits - 1 else f"A{index + 1}"
        operation_inputs = [
            ("SEL0", f"SUM{index}"),
            ("SEL1", f"SUM{index}"),
            ("SEL2", f"ANDLOGIC{index}"),
            ("SEL3", f"ORLOGIC{index}"),
            ("SEL4", f"XORLOGIC{index}"),
            ("SEL5", f"NOTA{index}"),
            ("SEL6", shift_left),
            ("SEL7", shift_right),
        ]

        products: list[str] = []
        for operation, signal in operation_inputs:
            name = f"OP{operation[-1]}_{index}"
            builder.add_gate(name, "AND", [operation, signal],
                             mux_start + int(operation[-1]) * mux_step, row_y)
            products.append(name)

        level_one: list[str] = []
        for pair in range(4):
            name = f"M1_{index}_{pair}"
            builder.add_gate(name, "OR", products[2 * pair:2 * pair + 2],
                             or_start + pair * mux_step, row_y)
            level_one.append(name)
        level_two: list[str] = []
        for pair in range(2):
            name = f"M2_{index}_{pair}"
            builder.add_gate(name, "OR", level_one[2 * pair:2 * pair + 2],
                             or_start + (4 + pair) * mux_step, row_y)
            level_two.append(name)
        builder.add_gate(f"Y{index}", "OR", level_two,
                         or_start + 6 * mux_step, row_y)
        builder.add_output(f"Y{index}", f"Y{index}", output_x, row_y)

    for index in range(bits):
        row_y = 420 + index * 240
        builder.add_gate(f"ANDLOGIC{index}", "AND",
                         [f"A{index}", f"B{index}"],
                         columns["bx"], row_y + 90)

    top_carry = f"CARRY{bits}"
    builder.add_gate("N_CARRY_TOP", "NOT", [top_carry], 820, bits * 240 + 680)
    builder.add_gate("COUT", "AND", ["SEL0", top_carry], 1100, bits * 240 + 680)
    builder.add_gate("BORROW", "AND", ["SEL1", "N_CARRY_TOP"],
                     1380, bits * 240 + 680)
    builder.add_gate("OVF_RAW", "XOR", [f"CARRY{bits - 1}", top_carry],
                     1660, bits * 240 + 680)
    builder.add_gate("OVF", "AND", ["OVF_RAW", "ADD_OR_SUB"],
                     1940, bits * 240 + 680)

    zero_level = [f"Y{index}" for index in range(bits)]
    zero_x = 2220
    zero_round = 0
    while len(zero_level) > 1:
        next_level: list[str] = []
        for pair in range(0, len(zero_level) - 1, 2):
            name = f"ZOR{zero_round}_{pair // 2}"
            builder.add_gate(name, "OR", zero_level[pair:pair + 2],
                             zero_x, bits * 240 + 680)
            next_level.append(name)
            zero_x += 260
        if len(zero_level) % 2:
            next_level.append(zero_level[-1])
        zero_level = next_level
        zero_round += 1
    builder.add_gate("ZERO", "NOT", zero_level, zero_x, bits * 240 + 680)

    flag_y = bits * 240 + 680
    builder.add_output("COUT", "COUT", output_x, flag_y)
    builder.add_output("BORROW", "BORROW", output_x, flag_y + 60)
    builder.add_output("ZERO", "ZERO", output_x, flag_y + 120)
    builder.add_output("NEG", f"Y{bits - 1}", output_x, flag_y + 180)
    builder.add_output("OVF", "OVF", output_x, flag_y + 240)
    return builder


INPUT_COLUMNS = ["CIN", "OP2", "OP1", "OP0"]
OUTPUT_COLUMNS = ["COUT", "BORROW", "ZERO", "NEG", "OVF"]


def vector_row(bits: int, a: int, b: int, cin: int, op: int) -> dict[str, int]:
    row: dict[str, int] = {}
    for index in range(bits):
        row[f"A{index}"] = (a >> index) & 1
    for index in range(bits):
        row[f"B{index}"] = (b >> index) & 1
    row.update({
        "CIN": cin,
        "OP2": (op >> 2) & 1,
        "OP1": (op >> 1) & 1,
        "OP0": op & 1,
    })
    row.update(alu_reference(a, b, cin, op, bits))
    return row


def representative_vectors(bits: int) -> list[dict[str, int]]:
    mask = (1 << bits) - 1
    sign = 1 << (bits - 1)
    samples = [
        (0, 0, 0, 0),
        (1, 1, 0, 0),
        (0x1234 & mask, 0x0FED & mask, 0, 0),
        (mask, 1, 0, 0),
        (sign - 1, 1, 0, 0),
        (sign, mask, 0, 0),
        (0x1234 & mask, 0x00FF & mask, 1, 1),
        (1, 2, 1, 1),
        (5, 2, 0, 1),
        (sign, 1, 1, 1),
        (0x55AA & mask, 0x00FF & mask, 0, 2),
        (0x1234 & mask, 0x00F0 & mask, 0, 3),
        (0x5555 & mask, 0xAAAA & mask, 0, 4),
        (0x55AA & mask, 0, 0, 5),
        (mask, 0, 0, 5),
        (0x8001 & mask, 0, 0, 6),
        (0x8001 & mask, 0, 1, 6),
        (0x8001 & mask, 0, 0, 7),
        (0x8001 & mask, 0, 1, 7),
        (0, 0, 1, 2),
        (0, mask, 1, 3),
        (sign, sign, 0, 0),
    ]
    return [vector_row(bits, a, b, cin, op)
            for a, b, cin, op in samples if a <= mask and b <= mask]


def exhaustive_vectors(bits: int) -> Iterable[dict[str, int]]:
    input_names = (
        [f"A{index}" for index in range(bits)]
        + [f"B{index}" for index in range(bits)]
        + INPUT_COLUMNS
    )
    for values in itertools.product((0, 1), repeat=len(input_names)):
        state = dict(zip(input_names, values))
        a = sum(state[f"A{index}"] << index for index in range(bits))
        b = sum(state[f"B{index}"] << index for index in range(bits))
        op = state["OP2"] * 4 + state["OP1"] * 2 + state["OP0"]
        cin = state["CIN"]
        yield vector_row(bits, a, b, cin, op)


def write_table(path: Path, bits: int, rows: Iterable[dict[str, int]]) -> None:
    input_names = (
        [f"A{index}" for index in range(bits)]
        + [f"B{index}" for index in range(bits)]
        + INPUT_COLUMNS
    )
    output_names = [f"Y{index}" for index in range(bits)] + OUTPUT_COLUMNS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=input_names + output_names,
                                delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in input_names + output_names})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bits", type=int, default=16)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table-out", type=Path,
                        help="Defaults to <out stem>_vectors.tsv")
    parser.add_argument("--exhaustive-table", action="store_true",
                        help="Enumerate all scalar input combinations (small widths only)")
    parser.add_argument("--main-name", default="main")
    args = parser.parse_args()
    table_path = args.table_out or args.out.with_name(args.out.stem + "_vectors.tsv")
    builder = build_alu(args.bits)
    builder.emit(args.out, args.main_name)
    rows = (exhaustive_vectors(args.bits) if args.exhaustive_table
            else representative_vectors(args.bits))
    write_table(table_path, args.bits, rows)
    print(f"Circuit: {args.out}")
    print(f"Vectors: {table_path}")
    print(f"Inputs: {len(builder.inputs)}; outputs: {len(builder.outputs)}; "
          f"gates: {len(builder.gates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
