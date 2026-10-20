from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_circ import parse
from circ_model import UniversalProject


def write_project(
    path: Path,
    wires: list[tuple[tuple[int, int], tuple[int, int]]],
    components: list[tuple[str, tuple[int, int], dict[str, str]]] = (),
) -> None:
    root = ET.Element("project", {"source": "2.7.1", "version": "1.0"})
    for desc, name in (("#Wiring", "0"), ("#Gates", "1"), ("#Base", "6")):
        ET.SubElement(root, "lib", {"desc": desc, "name": name})
    ET.SubElement(root, "main", {"name": "main"})
    circuit = ET.SubElement(root, "circuit", {"name": "main"})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": "main"})
    for name, location, attributes in components:
        component = ET.SubElement(circuit, "comp", {
            "lib": "0",
            "loc": f"({location[0]},{location[1]})",
            "name": name,
        })
        for key, value in attributes.items():
            ET.SubElement(component, "a", {"name": key, "val": value})
    for start, end in wires:
        ET.SubElement(circuit, "wire", {
            "from": f"({start[0]},{start[1]})",
            "to": f"({end[0]},{end[1]})",
        })
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


class SemanticGeometryTest(unittest.TestCase):
    def test_implicit_t_junction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="implicit-t-test-") as temporary:
            path = Path(temporary) / "implicit_t.circ"
            write_project(path, [
                ((0, 0), (30, 0)),
                ((10, 0), (10, 20)),
            ])
            _, components, _ = parse(path)
            self.assertTrue(any(
                component["name"] == "Implicit T junction"
                for component in components
            ))
            findings = UniversalProject(path).collect_findings()["main"]
            self.assertTrue(any("implicit T junction" in item for item in findings))

    def test_explicitly_split_t_junction_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="explicit-t-test-") as temporary:
            path = Path(temporary) / "explicit_t.circ"
            write_project(path, [
                ((0, 0), (10, 0)),
                ((10, 0), (30, 0)),
                ((10, 0), (10, 20)),
            ])
            _, components, _ = parse(path)
            self.assertFalse(any(
                component["name"] == "Implicit T junction"
                for component in components
            ))
            findings = UniversalProject(path).collect_findings()["main"]
            self.assertFalse(any("implicit T junction" in item for item in findings))

    def test_off_grid_pin_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="off-grid-test-") as temporary:
            path = Path(temporary) / "off_grid.circ"
            write_project(
                path,
                [((105, 100), (200, 100))],
                [("Pin", (105, 100), {
                    "facing": "east",
                    "label": "A",
                    "tristate": "false",
                })],
            )
            _, components, _ = parse(path)
            self.assertTrue(any(
                component["name"] == "Off-grid component"
                and "Pin" in component["attributes"]["detail"]
                for component in components
            ))
            findings = UniversalProject(path).collect_findings()["main"]
            self.assertTrue(any("off-grid component" in item for item in findings))

    def test_collinear_overlap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="overlap-test-") as temporary:
            path = Path(temporary) / "overlap.circ"
            write_project(path, [
                ((0, 0), (30, 0)),
                ((10, 0), (20, 0)),
            ])
            _, components, _ = parse(path)
            self.assertTrue(any(
                component["name"] == "Overlapping wire"
                for component in components
            ))
            findings = UniversalProject(path).collect_findings()["main"]
            self.assertTrue(any("overlapping collinear wires" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
