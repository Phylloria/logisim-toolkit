"""Verified Logisim 2.7.1 basic-gate geometry used by bundled tools.

Default gate size is 50. XOR adds 10 units to the symbol width. Output
negation adds another 10 units and is present by default on NAND, NOR, and
XNOR. Therefore east-facing input terminals are:

    AND/OR        x - 50
    XOR/NAND/NOR  x - 60
    XNOR          x - 70
    NOT           x - 30

The vertical offsets follow AbstractGate.getInputOffset. Do not replace these
values with one shared non-NOT offset.
"""
from __future__ import annotations

from collections import defaultdict


GATE_NAMES = {
    "AND": "AND Gate",
    "OR": "OR Gate",
    "XOR": "XOR Gate",
    "NOT": "NOT Gate",
    "NAND": "NAND Gate",
    "NOR": "NOR Gate",
    "XNOR": "XNOR Gate",
}

INPUT_AXIS = {
    "AND Gate": 50,
    "OR Gate": 50,
    "XOR Gate": 60,
    "NAND Gate": 60,
    "NOR Gate": 60,
    "XNOR Gate": 70,
    "NOT Gate": 30,
}


def on_wire_segment(target, start, end) -> bool:
    x, y = target
    x1, y1 = start
    x2, y2 = end
    if x1 == x2 == x:
        return min(y1, y2) <= y <= max(y1, y2)
    if y1 == y2 == y:
        return min(x1, x2) <= x <= max(x1, x2)
    return False


def strictly_on_wire_segment(target, start, end) -> bool:
    return (
        target != start
        and target != end
        and on_wire_segment(target, start, end)
    )


def implicit_t_junctions(wires) -> list[tuple[tuple[int, int], tuple, tuple]]:
    findings = set()
    horizontal = defaultdict(list)
    vertical = defaultdict(list)
    for index, (start, end) in enumerate(wires):
        if start[1] == end[1]:
            horizontal[start[1]].append((index, start, end))
        elif start[0] == end[0]:
            vertical[start[0]].append((index, start, end))

    for index, (start, end) in enumerate(wires):
        if start[1] == end[1]:
            candidates_at = {start[0]: vertical.get(start[0], []), end[0]: vertical.get(end[0], [])}
            for endpoint in (start, end):
                for other_index, other_start, other_end in candidates_at[endpoint[0]]:
                    if index != other_index and strictly_on_wire_segment(
                        endpoint, other_start, other_end
                    ):
                        findings.add((
                            endpoint,
                            (start, end),
                            (other_start, other_end),
                        ))
        elif start[0] == end[0]:
            candidates_at = {
                start[1]: horizontal.get(start[1], []),
                end[1]: horizontal.get(end[1], []),
            }
            for endpoint in (start, end):
                for other_index, other_start, other_end in candidates_at[endpoint[1]]:
                    if index != other_index and strictly_on_wire_segment(
                        endpoint, other_start, other_end
                    ):
                        findings.add((
                            endpoint,
                            (start, end),
                            (other_start, other_end),
                        ))
    return sorted(findings)


def gate_input_axis(name: str) -> int:
    try:
        return INPUT_AXIS[name]
    except KeyError as error:
        raise ValueError(f"no verified input geometry for {name!r}") from error


def port_offsets(count: int) -> list[int]:
    """Return y offsets for a default-size east-facing multi-input gate."""
    if count == 1:
        return [0]
    if count < 1:
        raise ValueError("gates require at least one input")
    spacing = 20 if count <= 3 else 10
    if count % 2:
        half = (count - 1) // 2
        return [index * spacing for index in range(-half, half + 1)]
    half = count // 2
    return [index * spacing for index in range(-half, half + 1) if index]


def gate_body_half_height(name: str, count: int) -> int:
    if name == "NOT Gate":
        return 22
    effective_inputs = count + (1 if count % 2 == 0 else 0)
    return max(10 * effective_inputs, 50) // 2


def splitter_distribution(fanout: int, bits: int) -> list[int]:
    """Reproduce SplitterAttributes.computeDistribution(fanout, bits, 1)."""
    result = [0] * bits
    if fanout >= bits:
        return [index + 1 for index in range(bits)]
    threads_per_end = bits // fanout
    ends_with_extra = bits % fanout
    current_end = 0
    left_in_end = 0
    for index in range(bits):
        if left_in_end == 0:
            current_end += 1
            left_in_end = threads_per_end
            if ends_with_extra > 0:
                left_in_end += 1
                ends_with_extra -= 1
        result[index] = current_end
        left_in_end -= 1
    return result


def splitter_definition(attributes: dict[str, str]):
    """Return (incoming width, end->bus-bit lists, branch points)."""
    fanout = int(attributes.get("fanout", "2"))
    incoming = int(attributes.get("incoming", "2"))
    mapping = []
    explicit = any(f"bit{index}" in attributes for index in range(incoming))
    default = splitter_distribution(fanout, incoming)
    for index in range(incoming):
        if explicit and f"bit{index}" in attributes:
            value = attributes[f"bit{index}"].strip().lower()
            if value in {"none", ""}:
                mapping.append(0)
            else:
                mapping.append(int(value))
        else:
            mapping.append(default[index])
    branches = [[] for _ in range(fanout)]
    for bit, end in enumerate(mapping):
        if end > 0:
            branches[end - 1].append(bit)

    facing = attributes.get("facing", "east")
    appear = attributes.get("appear", "left").lower()
    justify = 0 if appear in {"center", "legacy"} else 1 if appear == "right" else -1
    points = []
    if facing in {"north", "south"}:
        m = 1 if facing == "north" else -1
        x = 10 * ((fanout + 1) // 2 - 1) if justify == 0 else (-10 if m * justify < 0 else 10 * fanout)
        y = -m * 20
        dx, dy = -10, 0
        points = [(x + index * dx, y + index * dy) for index in range(fanout)]
    else:
        m = -1 if facing == "west" else 1
        x = m * 20
        y = -10 * (fanout // 2) if justify == 0 else (10 if m * justify > 0 else -10 * fanout)
        dx, dy = 0, 10
        points = [(x + index * dx, y + index * dy) for index in range(fanout)]
    return incoming, branches, points
