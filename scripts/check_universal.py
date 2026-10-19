#!/usr/bin/env python3
"""Bus/sequential-aware checker for Logisim 2.7.1 circuits.

Examples:
  python check_universal.py probe_bus.circ --table bus_vectors.tsv
  python check_universal.py register.circ --table sequence.tsv --sequential
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from circ_model import UniversalProject
from validate_logisim import parse_value


def read_table(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def pack_output(value, label):
    if value is None:
        return f"<undefined:{label}>"
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path)
    parser.add_argument("--circuit-name")
    parser.add_argument("--table", type=Path)
    parser.add_argument("--sequential", action="store_true")
    parser.add_argument("--require-exhaustive", action="store_true")
    args = parser.parse_args()
    try:
        project = UniversalProject(args.circuit)
        name = args.circuit_name or project.main
        outputs, details = project.evaluate(name)
        input_widths = details["inputs"]
        output_widths = details["outputs"]
        print(f"Circuit: {name}")
        print("Inputs:", ", ".join(f"{k}[{v}]" for k, v in input_widths.items()))
        print("Outputs:", ", ".join(f"{k}[{v}]" for k, v in output_widths.items()))

        findings = project.collect_findings()
        total_findings = 0
        for circuit_name, items in findings.items():
            if not items:
                continue
            total_findings += len(items)
            print(f"{circuit_name}: {len(items)} structural finding(s)")
            for item in items[:12]:
                print("  ", item)

        failed = total_findings > 0
        if args.table:
            rows = read_table(args.table)
            missing = [
                label for label in list(input_widths) + list(output_widths)
                if label not in rows[0]
            ]
            if missing:
                raise ValueError(f"table is missing columns: {missing}")
            mismatches = []
            for line, row in enumerate(rows, 2):
                forced = {
                    label: parse_value(row[label], width)
                    for label, width in input_widths.items()
                }
                if args.sequential:
                    got = project.step(forced, name)
                else:
                    got = project.evaluate(name, forced)[0]
                bad = {}
                for label, width in output_widths.items():
                    expected = parse_value(row[label], width)
                    actual = got.get(label)
                    if actual != expected:
                        bad[label] = (expected, pack_output(actual, label))
                if bad:
                    mismatches.append((line, bad))
            print(f"Reference rows: {len(rows)}; mismatches: {len(mismatches)}")
            for item in mismatches[:20]:
                print("  ", item)
            if args.require_exhaustive:
                if args.sequential:
                    raise ValueError("exhaustive mode is only valid for combinational tables")
                expected_rows = 1 << sum(input_widths.values())
                if len(rows) != expected_rows:
                    print(f"ERROR: expected {expected_rows} rows, found {len(rows)}")
                    return 2
            failed = failed or bool(mismatches)
        else:
            print("Outputs:", {key: pack_output(value, key) for key, value in outputs.items()})
        return int(failed)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
