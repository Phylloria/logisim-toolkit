# Agent Instructions

This repository is a standalone Logisim 2.7.1 toolkit. Agents do not need a
Codex-specific runtime.

## Preferred Workflow

1. Use `logisim-toolkit check` or `scripts/check_universal.py` as the
   independent reference model.
2. Use `logisim-toolkit validate` for real combinational/bus Logisim runs.
3. Use `logisim-toolkit validate-clocked` for fixed-input clocked sequences.
4. Use generators only as starting points; inspect and adapt generated XML.
5. Report structural evidence, independent simulation evidence, and real
   Logisim evidence separately.

## Source-Tree Invocation

When the package is not installed:

```powershell
python -m scripts.cli list-tools
python -m scripts.cli check design.circ --table vectors.tsv
python -m scripts.cli generate encoder-8to3 --out encoder.circ
```

The individual scripts under `scripts/` remain callable for automation.

## Non-Negotiable Checks

- Do not place Tunnels and call them direct wiring.
- Reject overlapping collinear wires and dangling wire endpoints.
- Reject wires entering gate bodies.
- Verify bus widths and splitter bit mappings.
- Do not treat static XML parsing as proof of Logisim compatibility.
- Keep validation-only clocks, counters, halt Pins, and stimuli out of final
  user projects.

## Evidence Boundaries

Read `references/capability-matrix.md` before claiming support for RAM, ROM,
external libraries, variable-input clocked replay, or Logisim Evolution 4.x.
