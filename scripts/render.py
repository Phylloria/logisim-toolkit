#!/usr/bin/env python3
"""Render a diagnostic wiring/layout preview from a Logisim .circ file.

Usage: python render.py input.circ output.png [width=1600] [circuit=main]

This is a coordinate preview, not a Logisim renderer or connectivity validator.
Tunnel labels and their connection points are shown so large tunnel-routed
circuits can be inspected without opening the graphical editor.
"""
import argparse
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from logisim_geometry import gate_body_half_height, gate_input_axis

GATES = {"AND Gate": "&", "OR Gate": "|", "NOT Gate": "!", "NAND Gate": "&N", "NOR Gate": "|N",
         "XOR Gate": "=1", "XNOR Gate": "=1N"}


def point(text):
    x, y = (int(v.strip()) for v in text[1:-1].split(",", 1))
    return x, y


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("width", nargs="?", type=int, default=1600)
    parser.add_argument("circuit", nargs="?", default="main")
    args = parser.parse_args()
    root = ET.parse(args.source).getroot()
    circuits = {element.get("name"): element for element in root.findall("circuit")}
    circuit = next((e for e in root.findall("circuit") if e.get("name") == args.circuit), None)
    if circuit is None:
        parser.error(f"circuit {args.circuit!r} not found")

    comps = []
    for e in circuit.findall("comp"):
        if not e.get("loc"):
            continue
        x, y = point(e.get("loc"))
        comps.append({"x": x, "y": y, "name": e.get("name", ""),
                      "a": {a.get("name"): a.get("val", "") for a in e.findall("a")}})
    wires = [(point(e.get("from")), point(e.get("to"))) for e in circuit.findall("wire")]
    if not comps and not wires:
        parser.error("selected circuit contains no drawable components or wires")

    xs = [c["x"] for c in comps if c["name"] != "Text"]
    ys = [c["y"] for c in comps if c["name"] != "Text"]
    xs += [p[0] for wire in wires for p in wire]
    ys += [p[1] for wire in wires for p in wire]
    x0, y0 = min(xs) - 60, min(ys) - 60
    all_width, all_height = max(xs) - x0 + 120, max(ys) - y0 + 120
    scale = min(args.width / all_width, 1.0)
    height = max(int(all_height * scale), 200)
    image = Image.new("RGB", (args.width, height), "white")
    draw = ImageDraw.Draw(image)
    font_path = "C:/Windows/Fonts/consola.ttf"
    try:
        font = ImageFont.truetype(font_path, max(6, int(13 * scale)))
        title_font = ImageFont.truetype(font_path, max(10, int(22 * scale)))
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    def transform(x, y):
        return ((x - x0) * scale + 12, (y - y0) * scale + 42)

    for (x1, y1), (x2, y2) in wires:
        draw.line([transform(x1, y1), transform(x2, y2)], fill=(15, 115, 55),
                  width=max(1, int(scale * 2)))
    for comp in comps:
        x, y = comp["x"], comp["y"]
        name = comp["name"]
        attributes = comp["a"]
        if name == "Text":
            text = attributes.get("text", "")
            draw.text(transform(x, y), text, fill=(45, 70, 120), font=title_font)
        elif name == "Pin":
            radius = max(2, int(5 * scale))
            px, py = transform(x, y)
            color = (25, 80, 160) if attributes.get("output") == "true" else (35, 35, 35)
            draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=color)
            label_x = px + radius + 3
            if attributes.get("facing") == "west":
                label_x = px + radius + 3
            draw.text((label_x, py - 6 * scale), attributes.get("label", ""),
                      fill=color, font=font)
        elif name == "Tunnel":
            px, py = transform(x, y)
            half = max(2, int(4 * scale))
            draw.rectangle([px - half, py - half, px + half, py + half],
                           fill=(235, 244, 255), outline=(30, 100, 170))
            draw.text((px + half + 2, py - 6 * scale),
                      attributes.get("label", ""), fill=(30, 80, 150), font=font)
        elif name in {"Power", "Ground"}:
            px, py = transform(x, y)
            half = max(2, int(4 * scale))
            color = (190, 40, 40) if name == "Power" else (60, 60, 60)
            draw.rectangle([px - half, py - half, px + half, py + half], fill=color)
        elif name in circuits and name != args.circuit:
            child = circuits[name]
            appear = child.find("appear")
            if appear is None:
                continue
            anchor_node = appear.find("circ-anchor")
            rect_node = appear.find("rect")
            if anchor_node is None or rect_node is None:
                continue
            anchor_x = int(anchor_node.get("x")) + 3
            anchor_y = int(anchor_node.get("y")) + 3
            block_x = x + int(rect_node.get("x")) - anchor_x
            block_y = y + int(rect_node.get("y")) - anchor_y
            block_w = int(rect_node.get("width"))
            block_h = int(rect_node.get("height"))
            left, top = transform(block_x, block_y)
            right = transform(block_x + block_w, block_y)[0]
            bottom = transform(block_x, block_y + block_h)[1]
            draw.rectangle([left, top, right, bottom], fill=(241, 247, 255),
                           outline=(25, 85, 155), width=max(2, int(scale * 2)))
            draw.rectangle([left, top, right, top + 24 * scale], fill=(214, 230, 249),
                           outline=(25, 85, 155), width=max(1, int(scale)))
            draw.text((left + 6 * scale, top + 5 * scale), name,
                      fill=(20, 60, 120), font=title_font)
        else:
            count = 1 if name == "NOT Gate" else int(attributes.get("inputs", "2"))
            half_w = gate_input_axis(name)
            half_h = gate_body_half_height(name, count)
            left, top = transform(x - half_w, y - half_h)
            right, bottom = transform(x, y + half_h)
            draw.rectangle([left, top, right, bottom], fill=(255, 249, 232),
                           outline=(165, 85, 20), width=max(1, int(scale)))
            label = GATES.get(name, "?")
            if name != "NOT Gate":
                label += attributes.get("inputs", "2")
            draw.text((left + 2, top + 1), label, fill=(130, 60, 15), font=font)
    draw.text((14, 10), f"{args.circuit}: {len(comps)} components, {len(wires)} wires",
              fill=(20, 20, 20), font=title_font)
    image.save(args.destination)
    print(f"Preview saved: {args.destination} ({args.width}x{height}, circuit={args.circuit})")


if __name__ == "__main__":
    main()
