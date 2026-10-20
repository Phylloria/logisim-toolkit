---
name: logisim
description: Create, edit, inspect, and validate native Logisim 2.7.1 .circ projects, including gate-level direct-wire circuits, buses, sequential logic, hierarchy, and layout repair. Do not use for PCB schematics or unrelated simulators.
---

# Logisim Circuit Designer

Deliver a native `.circ` project that opens in Logisim, behaves as requested,
and remains readable in the editor. A diagram or truth table is not a
substitute for the project when the user asks for a Logisim circuit.

This repository is the reusable implementation. The CLI works without Codex:

```powershell
logisim-toolkit list-tools
logisim-toolkit check design.circ --table vectors.tsv
logisim-toolkit generate encoder-8to3 --out encoder.circ
```

From a checkout, use `python -m scripts.cli ...`.

## Establish The Contract

Before drawing, determine:

- Input/output labels, widths, bit order, active-high or active-low convention.
- Required equations, truth table, state behavior, clock/reset rules, or timing.
- Allowed components: gates only, Tunnels, hierarchy, buses, arithmetic blocks.
- Target Logisim version and whether the result is a new file or an edit.
- Required deliverables: `.circ`, vectors, preview, validation record.

Make a reasonable assumption when a missing detail does not change the
architecture. State that assumption in the final delivery.

## Choose The Architecture

1. Write the behavior before assigning geometry. Use equations or a truth table
   for combinational logic; identify state, clock edge, reset, and enables for
   sequential logic.
2. Prefer native Logisim components unless the request requires gate-level
   implementation. Do not quietly replace requested logic with a ROM,
   arithmetic component, or opaque subcircuit.
3. Keep `main` as the operating surface. Use hierarchy when it reduces repeated
   wiring and does not violate the assignment.
4. Pick a wiring policy from the request:
   - Tunnels allowed: short terminal stubs and labeled nets.
   - Tunnels forbidden: flat direct-wire layout.
   - Encapsulation forbidden: all gates visible in the selected circuit.
5. Fix signal flow before coordinates: inputs left, outputs right, controls in
   separate lanes, repeated bit slices at regular spacing.

For large designs, read
[references/incremental-validation.md](references/incremental-validation.md).

## Build The Circuit

- Read an existing `.circ` completely before editing. Preserve unrelated
  circuits, labels, options, and user-authored structure. Write a copy unless
  an in-place edit was requested.
- Use `xml.etree.ElementTree`; never parse or transform Logisim XML with regex.
- Component `loc` is an anchor, not a universal top-left corner. Resolve
  terminals for the exact component, facing, input count, and version.
- Reuse [scripts/logisim_geometry.py](scripts/logisim_geometry.py) for default
  2.7.1 gate geometry. East-facing input x-offsets are AND/OR `-50`,
  XOR/NAND/NOR `-60`, XNOR `-70`, and NOT `-30`.
- Top-level manually operated input Pins must explicitly contain
  `<a name="tristate" val="false"/>`. Do not hide functional controls as
  Constants.
- For buses, set Pin and Splitter widths, fanout, bit mapping, facing, and
  appearance explicitly. Verify branch-to-bit correspondence.
- For hierarchy, expose exact child Pins and map custom-appearance ports to
  those Pin coordinates.

Project and component references:

- [references/upstream/logisim27-circ.md](references/upstream/logisim27-circ.md)
- [references/upstream/logisim27-components.json](references/upstream/logisim27-components.json)
- [reference/INDEX.md](reference/INDEX.md)

## Routing And Layout

Use a readable structure rather than minimizing canvas area blindly.

- Keep all components, terminals, and wire endpoints on the 10-unit grid.
- Keep gate bodies, labels, and Pin displays clear of wires.
- Separate collinear wires from different nets. Perpendicular crossings are
  allowed only when neither wire ends or turns at the crossing.
- Split a long wire at every same-net T junction. Endpoint-on-interior wiring
  can produce `E` in Logisim even when a simple static model passes.
- Do not add escape stubs for unused or already routed terminals.
- Keep inputs, stages, and outputs visually grouped.

Choose the routing strategy:

- Use `route_stage` with `WireNet` names for irregular direct-wire circuits.
- Use staged corridors when logic has clear dependency columns.
- Use Tunnels only when allowed and genuinely easier to inspect.

Detailed rules, diagnostics, corridor allocation, lane packing, bypass tracks,
and measured examples are in
[references/direct-wire-routing.md](references/direct-wire-routing.md).

## Validate

Run the strongest applicable checks in order:

1. Structural and XML checks before simulation.
2. Independent behavior model against a TSV table.
3. Real Logisim through a generated harness.
4. Visual render for layout inspection only.

Scalar flat gates:

```powershell
logisim-toolkit check-scalar design.circ --table vectors.tsv
```

Hierarchy:

```powershell
logisim-toolkit check-hierarchy design.circ --table vectors.tsv
```

Buses, splitters, arithmetic, and sequential logic:

```powershell
logisim-toolkit check design.circ --table vectors.tsv
logisim-toolkit check state.circ --table sequence.tsv --sequential
```

Real Logisim:

```powershell
logisim-toolkit validate design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
logisim-toolkit validate-clocked state.circ `
  --clock CLK --cycles 8 --input D=5 --input EN=1
```

Exhaustively test small combinational interfaces. Use representative boundary,
carry/borrow, priority, control-code, and state-transition vectors for larger
circuits. The static checker proves structure and the independent model; only
real Logisim proves the project loads and evaluates as expected in the target
runtime.

Common explicit failures now include:

- off-grid component or wire coordinates,
- implicit T junctions,
- dangling terminals,
- multiple drivers,
- combinational gate loops,
- `None` outputs caused by an unresolved loop or floating source.

The renderer does not prove connectivity. A visual render and XML parse are not
real-Logisim validation.

## Generated Regressions

Use the cookbook for exact interfaces and commands:
[references/generator-cookbook.md](references/generator-cookbook.md).

| Generator | Use |
| --- | --- |
| `encoder-8to3` | Simple flat priority encoder |
| `encoder-9-corridor` | Staged corridor encoder |
| `keypad-flat` | Flat decimal keypad, no Tunnels |
| `keypad-hierarchy` | Hierarchical decimal keypad |
| `multiplier-4x4` | 64-gate array multiplier |
| `cla-4bit` | 32-gate carry-lookahead adder |
| `stress-256` | Large direct-wire routing regression |
| `alu` | Larger tunnel-based datapath |
| `probes` | Bus, splitter, state, and arithmetic probes |

## Deliver

Include:

- The clean `.circ` project.
- The exact interface and active-level conventions.
- The reference table or smoke vectors used.
- Structural and behavioral results actually run.
- Real Logisim version if tested, or an explicit statement that it was not.

Validation-only Constants, halt Pins, counters, and comparators must not remain
in the user-facing circuit.

Avoid extra explanatory documents when the circuit, vectors, and a short
README/VALIDATION record already communicate the result.
