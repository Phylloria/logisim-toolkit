from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parents[2] / "gate_level_8bit_ripple_adder.circ"

def comp(lib, x, y, name, attrs=()):
    node = ET.Element("comp", {"lib": str(lib), "loc": f"({x},{y})", "name": name})
    for key, value in attrs:
        ET.SubElement(node, "a", {"name": key, "val": str(value)})
    return ET.tostring(node, encoding="unicode", short_empty_elements=True)

def wire(a, b):
    if a[0] != b[0] and a[1] != b[1]:
        raise ValueError(f"diagonal wire: {a} -> {b}")
    return f'<wire from="({a[0]},{a[1]})" to="({b[0]},{b[1]})"/>'

def path(*points):
    return "".join(wire(a, b) for a, b in zip(points, points[1:]) if a != b)

parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<project source="2.7.1" version="1.0">',
    '<lib desc="#Wiring" name="0"/><lib desc="#Gates" name="1"/>',
    '<main name="main"/><options><a name="gateUndefined" val="ignore"/><a name="simlimit" val="1000"/><a name="simrand" val="0"/></options>',
    '<circuit name="main"><a name="circuit" val="main"/>',
]

# Pin positions and per-bit slices use 160-unit vertical pitch. All gate
# terminals match the verified east-facing 2-input gate geometry.
for bit in range(8):
    y = 100 + bit * 160
    parts.extend([
        comp(0, 100, y, "Pin", (("facing", "east"), ("tristate", "false"), ("label", f"A{bit}"))),
        comp(0, 100, y + 40, "Pin", (("facing", "east"), ("tristate", "false"), ("label", f"B{bit}"))),
        comp(1, 350, y + 20, "XOR Gate", (("inputs", 2), ("facing", "east"))),
        comp(1, 550, y + 20, "XOR Gate", (("inputs", 2), ("facing", "east"))),
        comp(1, 350, y + 100, "AND Gate", (("inputs", 2), ("facing", "east"))),
        comp(1, 550, y + 100, "AND Gate", (("inputs", 2), ("facing", "east"))),
        comp(1, 750, y + 100, "OR Gate", (("inputs", 2), ("facing", "east"))),
        comp(0, 850, y + 20, "Pin", (("facing", "west"), ("output", "true"), ("label", f"SUM{bit}"), ("labelloc", "east"))),
    ])
    if bit == 0:
        parts.append(comp(0, 100, y + 80, "Pin", (("facing", "east"), ("tristate", "false"), ("label", "CIN"))))
    elif bit == 7:
        parts.append(comp(0, 850, y + 100, "Pin", (("facing", "west"), ("output", "true"), ("label", "COUT"), ("labelloc", "east"))))

for bit in range(8):
    y = 100 + bit * 160
    # A xor B and A and B.
    parts.extend([
        path((100, y), (220, y), (220, y), (300, y)),
        path((100, y), (180, y), (180, y + 80), (300, y + 80)),
        path((100, y + 40), (240, y + 40), (240, y + 40), (300, y + 40)),
        path((100, y + 40), (200, y + 40), (200, y + 120), (300, y + 120)),
        # Propagate and generate feed the sum and carry gates.
        path((350, y + 20), (430, y + 20), (430, y), (500, y)),
        path((350, y + 20), (450, y + 20), (450, y + 80), (500, y + 80)),
        path((550, y + 20), (850, y + 20)),
        path((350, y + 100), (650, y + 100), (650, y + 80), (700, y + 80)),
        path((550, y + 100), (670, y + 100), (670, y + 120), (700, y + 120)),
    ])
    if bit == 0:
        # CIN fans out locally to the two carry-in consumers.
        parts.extend([
            path((100, y + 80), (120, y + 80), (120, y + 40), (500, y + 40)),
            path((120, y + 80), (140, y + 80), (140, y + 120), (500, y + 120)),
        ])
    else:
        prev_y = 100 + (bit - 1) * 160
        # Previous OR output fans out to both consumers with separate routes.
        parts.extend([
            path((750, prev_y + 100), (780, prev_y + 100), (780, y + 40), (500, y + 40)),
            path((780, y + 40), (800, y + 40), (800, y + 120), (500, y + 120)),
        ])
    if bit == 7:
        parts.append(path((750, y + 100), (850, y + 100)))

parts.append('</circuit></project>')
xml = "\n".join(parts)
ET.fromstring(xml)
OUT.write_text(xml, encoding="utf-8")
print(OUT)
