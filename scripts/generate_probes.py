#!/usr/bin/env python3
"""Generate bus, splitter, and register probes for the universal checker."""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from direct_router import split_segments_at_endpoints


def comp(parent, library, point, name, attributes=()):
    node = ET.SubElement(parent, "comp", {
        "lib": library,
        "loc": f"({point[0]},{point[1]})",
        "name": name,
    })
    for key, value in attributes:
        ET.SubElement(node, "a", {"name": key, "val": str(value)})


def wire(parent, start, end):
    ET.SubElement(parent, "wire", {
        "from": f"({start[0]},{start[1]})",
        "to": f"({end[0]},{end[1]})",
    })


def project():
    root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
    ET.SubElement(root, "lib", {"desc": "#Wiring", "name": "0"})
    ET.SubElement(root, "lib", {"desc": "#Gates", "name": "1"})
    ET.SubElement(root, "lib", {"desc": "#Plexers", "name": "2"})
    ET.SubElement(root, "lib", {"desc": "#Arithmetic", "name": "3"})
    ET.SubElement(root, "lib", {"desc": "#Memory", "name": "4"})
    options = ET.SubElement(root, "options")
    for key, value in (("gateUndefined", "ignore"), ("simlimit", "1000"), ("simrand", "0")):
        ET.SubElement(options, "a", {"name": key, "val": value})
    return root


def circuit(root, name):
    node = ET.SubElement(root, "circuit", {"name": name})
    ET.SubElement(node, "a", {"name": "circuit", "val": name})
    return node


def write_table(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def make_bus_gate(path):
    root = project()
    ET.SubElement(root, "main", {"name": "main"})
    node = circuit(root, "main")
    comp(node, "0", (100, 100), "Pin", (
        ("facing", "east"), ("width", 8), ("label", "A"), ("tristate", "false"),
    ))
    comp(node, "0", (100, 200), "Pin", (
        ("facing", "east"), ("width", 8), ("label", "B"), ("tristate", "false"),
    ))
    comp(node, "1", (450, 150), "XOR Gate", (
        ("facing", "east"), ("width", 8), ("inputs", 2),
    ))
    comp(node, "0", (650, 150), "Pin", (
        ("facing", "west"), ("width", 8), ("label", "Y"),
        ("output", "true"), ("labelloc", "east"),
    ))
    wire(node, (100, 100), (300, 100))
    wire(node, (300, 100), (300, 130))
    wire(node, (300, 130), (390, 130))
    wire(node, (100, 200), (250, 200))
    wire(node, (250, 200), (250, 170))
    wire(node, (250, 170), (390, 170))
    wire(node, (450, 150), (650, 150))
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    write_table(
        path.with_name(path.stem + "_vectors.tsv"),
        ["A", "B", "Y"],
        [["0x00", "0x00", "0x00"], ["0x55", "0xff", "0xaa"],
         ["0x12", "0x34", "0x26"], ["0xf0", "0x0f", "0xff"]],
    )


def make_splitter(path):
    root = project()
    ET.SubElement(root, "main", {"name": "main"})
    node = circuit(root, "main")
    comp(node, "0", (100, 200), "Pin", (
        ("facing", "east"), ("width", 8), ("label", "A"), ("tristate", "false"),
    ))
    split_attrs = [
        ("facing", "east"), ("fanout", 2), ("incoming", 8), ("appear", "right"),
    ] + [(f"bit{bit}", 1 if bit < 4 else 2) for bit in range(8)]
    comp(node, "0", (250, 200), "Splitter", split_attrs)
    comp(node, "0", (500, 200), "Splitter", split_attrs)
    comp(node, "0", (800, 200), "Pin", (
        ("facing", "west"), ("width", 8), ("label", "Y"),
        ("output", "true"), ("labelloc", "east"),
    ))
    wire(node, (100, 200), (250, 200))
    wire(node, (270, 210), (520, 210))
    wire(node, (270, 220), (520, 220))
    wire(node, (500, 200), (800, 200))
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    write_table(
        path.with_name(path.stem + "_vectors.tsv"),
        ["A", "Y"],
        [["0x00", "0x00"], ["0x0f", "0x0f"], ["0xf0", "0xf0"], ["0xa5", "0xa5"]],
    )


def make_register(path):
    root = project()
    ET.SubElement(root, "main", {"name": "main"})
    node = circuit(root, "main")
    for label, y in (("D", 100), ("CLK", 220), ("CLR", 300), ("EN", 380)):
        comp(node, "0", (100, y), "Pin", (
            ("facing", "east"), ("width", 4 if label == "D" else 1),
            ("label", label), ("tristate", "false"),
        ))
    comp(node, "4", (450, 160), "Register", (
        ("facing", "east"), ("width", 4), ("trigger", "rising"),
    ))
    comp(node, "0", (700, 160), "Pin", (
        ("facing", "west"), ("width", 4), ("label", "Q"),
        ("output", "true"), ("labelloc", "east"),
    ))
    wire(node, (100, 100), (350, 100))
    wire(node, (350, 100), (350, 160))
    wire(node, (350, 160), (420, 160))
    wire(node, (100, 220), (250, 220))
    wire(node, (250, 220), (250, 200))
    wire(node, (250, 200), (430, 200))
    wire(node, (430, 200), (430, 180))
    wire(node, (100, 300), (300, 300))
    wire(node, (300, 300), (300, 190))
    wire(node, (300, 190), (440, 190))
    wire(node, (440, 190), (440, 180))
    wire(node, (100, 380), (320, 380))
    wire(node, (320, 380), (320, 170))
    wire(node, (320, 170), (420, 170))
    wire(node, (450, 160), (700, 160))
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    write_table(
        path.with_name(path.stem + "_sequence.tsv"),
        ["D", "CLK", "CLR", "EN", "Q"],
        [
            ["0x5", 0, 1, 1, "0x0"],
            ["0x5", 1, 0, 1, "0x5"],
            ["0x9", 0, 0, 0, "0x5"],
            ["0x9", 1, 0, 0, "0x5"],
            ["0x9", 0, 0, 1, "0x5"],
            ["0x9", 1, 0, 1, "0x9"],
        ],
    )


def make_wide_components(path):
    root = project()
    ET.SubElement(root, "main", {"name": "main"})
    node = circuit(root, "main")
    for label, y, width in (("A", 100, 4), ("B", 200, 4), ("SEL", 300, 1), ("CIN", 400, 1)):
        comp(node, "0", (100, y), "Pin", (
            ("facing", "east"), ("width", width), ("label", label), ("tristate", "false"),
        ))
    comp(node, "3", (500, 150), "Adder", (("width", 4),))
    comp(node, "3", (500, 400), "Comparator", (("width", 4), ("mode", "unsigned")))
    comp(node, "2", (800, 200), "Multiplexer", (
        ("facing", "east"), ("width", 4), ("select", 1),
    ))
    for label, y, width in (
        ("Y", 200, 4), ("COUT", 170, 1), ("GT", 390, 1), ("EQ", 400, 1), ("LT", 410, 1),
    ):
        comp(node, "0", (1000, y), "Pin", (
            ("facing", "west"), ("width", width), ("label", label),
            ("output", "true"), ("labelloc", "east"),
        ))
    wires = [
        ((100, 100), (350, 100)),
        ((350, 100), (350, 390)),
        ((350, 140), (460, 140)),
        ((350, 390), (460, 390)),
        ((350, 100), (740, 100)),
        ((740, 100), (740, 190)),
        ((740, 190), (770, 190)),
        ((100, 200), (400, 200)),
        ((400, 200), (400, 160)),
        ((400, 160), (460, 160)),
        ((400, 200), (400, 410)),
        ((400, 410), (460, 410)),
        ((100, 300), (780, 300)),
        ((780, 300), (780, 220)),
        ((100, 400), (300, 400)),
        ((300, 400), (300, 130)),
        ((300, 130), (480, 130)),
        ((500, 150), (550, 150)),
        ((550, 150), (550, 210)),
        ((550, 210), (770, 210)),
        ((800, 200), (1000, 200)),
        ((480, 170), (1000, 170)),
        ((500, 390), (1000, 390)),
        ((500, 400), (1000, 400)),
        ((500, 410), (1000, 410)),
    ]
    for start, end in split_segments_at_endpoints(wires):
        wire(node, start, end)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    rows = []
    for a, b, sel, cin in (
        (0, 0, 0, 0), (5, 3, 0, 0), (5, 3, 1, 0),
        (15, 1, 1, 1), (8, 9, 0, 1),
    ):
        total = a + b + cin
        rows.append([
            f"0x{a:x}", f"0x{b:x}", sel, cin,
            f"0x{(total & 0xf) if sel else a:x}", (total >> 4) & 1,
            int(a > b), int(a == b), int(a < b),
        ])
    write_table(
        path.with_name(path.stem + "_vectors.tsv"),
        ["A", "B", "SEL", "CIN", "Y", "COUT", "GT", "EQ", "LT"],
        rows,
    )


def make_decoder(path):
    root = project()
    ET.SubElement(root, "main", {"name": "main"})
    node = circuit(root, "main")
    comp(node, "0", (100, 300), "Pin", (
        ("facing", "east"), ("width", 2), ("label", "SEL"), ("tristate", "false"),
    ))
    comp(node, "2", (500, 300), "Decoder", (
        ("facing", "east"), ("select", 2),
    ))
    comp(node, "0", (400, 200), "Power", (("facing", "east"),))
    for index in range(4):
        comp(node, "0", (800, 260 + index * 10), "Pin", (
            ("facing", "west"), ("label", f"O{index}"),
            ("output", "true"), ("labelloc", "east"),
        ))
        wire(node, (520, 260 + index * 10), (800, 260 + index * 10))
    wire(node, (100, 300), (100, 360))
    wire(node, (100, 360), (500, 360))
    wire(node, (500, 360), (500, 300))
    wire(node, (400, 200), (490, 200))
    wire(node, (490, 200), (490, 300))
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    rows = []
    for select in range(4):
        rows.append([f"0b{select:02b}"] + [
            int(select == index) for index in range(4)
        ])
    write_table(
        path.with_name(path.stem + "_vectors.tsv"),
        ["SEL", "O0", "O1", "O2", "O3"],
        rows,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    make_bus_gate(args.out_dir / "probe_bus_gate.circ")
    make_splitter(args.out_dir / "probe_splitter.circ")
    make_register(args.out_dir / "probe_register.circ")
    make_wide_components(args.out_dir / "probe_wide_components.circ")
    make_decoder(args.out_dir / "probe_decoder.circ")
    print(f"Probes written to {args.out_dir}")


if __name__ == "__main__":
    main()
