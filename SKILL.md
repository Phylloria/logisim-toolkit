---
name: logisim
description: Design and draw digital logic circuits in Logisim by creating or editing native .circ projects. Use for gate-level circuits, combinational logic, truth tables, multiplexers, decoders, adders, sequential circuits, buses, and Logisim project repair.
---

# Logisim Circuit Designer

Create a circuit the user can open, inspect, and operate in Logisim. The primary output is a native `.circ` project with the requested behavior and readable layout. A diagram or truth table alone is not a substitute when the user asked for a Logisim circuit.

This file is the optional Codex adapter for the standalone
`logisim-toolkit` project. The same functionality is available without
Codex:

```powershell
logisim-toolkit list-tools
logisim-toolkit check design.circ --table vectors.tsv
logisim-toolkit generate encoder-8to3 --out encoder.circ
```

From a source checkout, use `python -m scripts.cli ...`. The stable reusable
interface is the CLI and scripts; no Codex-specific environment is required.

## Work From The Request

Before drawing, identify:

- Required inputs and outputs, including labels, widths, and active-low conventions.
- The required behavior: Boolean equations, truth table, state diagram, timing behavior, or a written specification.
- Constraints on allowed components, hierarchy, appearance, and application version.
- Whether the user wants a new project, an edit to an existing project, or an explanation.

If behavior is underspecified, resolve only details that materially affect the circuit. Otherwise make a reasonable assumption and state it with the deliverable. Preserve the user's requested bit ordering; write down whether buses are indexed MSB-first or LSB-first before wiring them.

## Design Before Drawing

1. Convert the request to an explicit design model. For combinational logic, write equations or a complete truth table. For sequential logic, identify state bits, reset behavior, clock edge, enable behavior, and transition/output rules.
2. Choose components that satisfy the user's constraints. Prefer native Logisim components for a normal functional circuit. Use only gates when the request is specifically gate-level or forbids higher-level components. Do not silently replace a requested circuit with a truth-table ROM or opaque subcircuit.
3. Decompose large or repeated designs into named subcircuits. Keep `main` as the operating surface, with visible top-level Pins and a small number of meaningful blocks. Follow `references/upstream/hierarchical-deliverables.md` for reusable blocks and buses.
4. Choose a consistent signal flow and bus policy before assigning coordinates. Usually inputs enter from the left, outputs leave to the right, control signals use separate lanes, and repeated bit slices use regular spacing.

## Create The Native Project

- Read the full existing `.circ` before editing. Preserve its project header, libraries, options, unrelated circuits, labels, and user-authored structure. Make a separate output copy unless an in-place edit was requested.
- Use a version-compatible project header and include the library declarations needed by the chosen components. The Logisim 2.7.1 snippets and component notes are in `references/upstream/logisim27-circ.md` and `references/upstream/logisim27-components.json`.
- Prefer `xml.etree.ElementTree` for inspecting or transforming existing XML. Avoid regex-based XML parsing. If generating XML, escape labels and text correctly and emit all required component attributes.
- Component `loc` values are anchors, not universal top-left coordinates. Resolve port coordinates for the exact component, input count, facing, and Logisim version from a matching example, the bundled component reference, or a tiny project opened in Logisim. Never extrapolate an AND gate's geometry to an OR gate, a rotated gate, or a different application version without evidence.
- For default-size east-facing Logisim 2.7.1 gates, do not use one shared input offset: AND/OR inputs are at `x-50`, XOR/NAND/NOR at `x-60`, XNOR at `x-70`, and NOT at `x-30`. Reuse `scripts/logisim_geometry.py`; a wire that stops at `x-50` on an XOR gate extends into the symbol even if Logisim can still repair or simulate the connection.
- Pin `loc` is the connection point in the supplied 2.7.1 examples. Put input Pins where a user can reach them and orient them toward the local logic; orient output Pins toward the outside of the circuit.
- In Logisim 2.7.1, Pin `tristate` defaults to `true`. Always emit
  `<a name="tristate" val="false"/>` for manually operated top-level input
  Pins. Otherwise the Pin floats in the GUI and the error value can make
  downstream wires appear red, even when constant-driven tests pass.
- Preserve user-operated controls as Pins. Use constants only for values fixed by the specification. Do not hide functional inputs as constants to make a demo appear to work.

## Place And Route

- Lay out by signal flow and functional groups. Place inputs, major stages, and outputs in separate regions. Put related control logic near the block it controls and use labels or Text sparingly to clarify interfaces.
- Leave room for the component's visible body, labels, value display, and every terminal. Multi-bit Pins, splitters, multiplexers, and memory controls need more room than their connection point suggests.
- Use orthogonal wires on the project grid. Route from verified terminal coordinates to verified terminal coordinates. Keep long runs in distinct lanes; cross only where the target application treats the crossing as unconnected. An endpoint touching a segment is a junction and may join nets.
- Avoid wire overlaps, ambiguous T-junctions, duplicate labels on tunnels, overlapping Pins, and routes that pass through component bodies. Use tunnels when a named net improves readability or reduces a genuinely unwieldy route; duplicate tunnel labels intentionally join those nets.
- For a dense gate-level datapath, prefer short gate stubs plus labeled Tunnels over thousands of long point-to-point wires. Give every internal net one driver and use the same label at every sink. Keep a visible source tunnel next to each top-level Pin so the Pin-to-net connection is explicit.
- For bus circuits, use native multi-bit Pins and Splitters/Joiners. Set bit width, fanout, bit mapping, and facing explicitly; verify that each splitter branch corresponds to the intended bit.
- For hierarchy, keep the implementation inside subcircuits and expose clear input/output Pins. Add custom appearance and correctly mapped circuit ports when the block is intended to be placed or operated in a parent circuit.

## Validate And Deliver

- Parse generated XML and check that the project contains the intended main circuit, required components, Pins, and libraries.
- Check that every wire is orthogonal and on-grid, coordinates are valid for the chosen components, required ports are connected, labels are unique where required, and no unintended multiple drivers or dangling inputs remain.
- Open the project in the target Logisim version whenever available. Confirm that it loads without warnings and that the diagram is legible at normal zoom. A PNG render and XML parse do not prove that Logisim recognizes the circuit as intended.
- Test behavior in Logisim using the truth table, simulation, or a harness. Exhaustively test small combinational circuits. For sequential circuits, test reset, clock transitions, enables, and representative state sequences. Keep validation-only stimuli and halt logic out of the clean user-facing circuit.
- Deliver the `.circ` file. Include a truth table, screenshot/render, or concise operating note only when it helps the user. State which simulator/version checks were actually performed and call out anything unverified.

## Universal 2.7.1 Validation

Use `scripts/check_universal.py` as the primary model for circuits containing
buses, splitters, registers, or nested subcircuits:

```powershell
python scripts/check_universal.py design.circ --table vectors.tsv
python scripts/check_universal.py register.circ --table sequence.tsv --sequential
```

Table values accept `0b0101`, plain binary matching the Pin width, `0x1f`, or
decimal.

Supported component families in the universal model:

- Wiring: Pin, Tunnel, Power, Ground, Constant, Clock, Splitter.
- Gates: AND/OR/NAND/NOR/XOR/XNOR/NOT with scalar or bus width.
- Arithmetic: Adder, Comparator.
- Plexers: Multiplexer.
- Memory/state: D Flip-Flop, Register, Counter.
- Hierarchy: nested subcircuits through custom appearance ports.

The model resolves wires and splitter mappings to bit-level nets. It checks
width conflicts and multiple drivers per bit, then evaluates the full network.
For sequential logic, `--sequential` treats each table row as one clocked step.

Use the real Logisim validators after the independent model passes:

```powershell
python scripts/validate_logisim.py design.circ --table vectors.tsv
python scripts/validate_logisim_clocked.py register.circ `
  --clock CLK --cycles 6 --input D=5 --input CLR=0 --input EN=1
```

`validate_logisim.py` replaces scalar/bus inputs with `Constant` components.
Bus constants must use a `0x...` value in 2.7.1. Logisim TTY prints wide values
as 4-bit groups, so the validator normalizes grouped binary output back to the
declared Pin widths.

`validate_logisim_clocked.py` replaces the named clock Pin with a Clock, fixes
the remaining inputs, adds a cycle Counter/Comparator and halt Pin, then checks
the runtime sequence against the independent sequential model.

## Incremental Construction For Large Designs

Use this workflow for any design that has hierarchy, buses, repeated blocks, or more than one functional stage. It applies to ALUs, datapaths, registers, counters, FSMs, memories, and CPU-sized projects.

1. Build a minimal probe first: one parent circuit, one child circuit, and only the intended ports. Load it with the target Logisim version before adding functional logic.
2. Add one component family or one signal path at a time. After each addition, run XML parsing, structural checks, and the target runtime's load command. Keep the last loadable checkpoint.
3. Maintain separate interface, implementation, and harness circuits. Do not use a harness's constants, clocks, halt pins, or expected-value comparators in the clean deliverable.
4. Treat every component's attributes and terminal coordinates as version-specific. Confirm unfamiliar settings in a tiny probe or an existing 2.7.1 example; do not infer a multi-input or multi-bit layout from a visually similar component.
5. When a runtime hangs, bisect from the last loadable checkpoint. First remove harness logic, then child instances, then component families, then wires. Record the smallest reproducer and do not call the larger artifact validated.
6. Validate behavior independently of the XML generator. Use a reference model for boundary vectors, control-code coverage, carry/borrow or state transitions, and representative bus bit order. A static checker that does not understand a child circuit is structural evidence only.

For reusable projects, keep a regression directory containing the smallest hierarchy probe, one bus probe, one representative functional block, and a known-good full-project load command. This makes future skill changes testable without relying on a single large example.

## Bundled Gate-Level Regression

Use the bundled 16-bit ALU generator as a large-design smoke test and as a
worked example of tunnel-based layout:

```powershell
python scripts/generate_alu.py --bits 16 --out outputs/alu16.circ
python scripts/check_circ.py outputs/alu16.circ --table outputs/alu16_vectors.tsv
python scripts/render.py outputs/alu16.circ outputs/alu16_preview.png 3200
python scripts/validate_logisim.py outputs/alu16.circ --table outputs/alu16_vectors.tsv --logisim C:\Logisim\logisim-win-2.7.1.exe
```

`generate_alu.py` emits a flat, gate-only datapath. The implementation uses
XOR/AND/OR/NOT gates, a ripple adder/subtractor, one-hot operation decode,
balanced result muxes, and gate-built flag logic. It deliberately exposes
scalar pins so the static checker and per-vector Logisim harness can verify
each bit without depending on splitter behavior.

`check_circ.py` is an independent netlist simulator for scalar Pin, Tunnel,
Power, Ground, and basic-gate circuits. It joins duplicate tunnel labels,
checks drivers and floating terminals, and compares a TSV table. It is still
not a substitute for opening the project in Logisim.

`validate_logisim.py` creates a temporary harness for each vector by replacing
input Pins with Power/Ground sources and adding a `halt` output. This avoids
Logisim 2.7.1's interactive table stream behavior. Invoke a JAR-compatible
Logisim with a console Java process (`java -jar ... -tty table ...`); launching
the Windows GUI wrapper through `javaw` can detach before output is collected.

## Decimal Keypad Priority Encoder

For a conventional active-high decimal keypad with `K9` highest priority:

```powershell
python scripts/generate_keypad_encoder.py --out outputs/keypad.circ
python scripts/check_circ.py outputs/keypad.circ `
  --table outputs/keypad_exhaustive.tsv --require-exhaustive
python scripts/validate_logisim.py outputs/keypad.circ `
  --table outputs/keypad_smoke.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

The generated interface is `K0..K9`, BCD `B0..B3`, and `VALID`. It uses nine
AND gates, nine NOT gates, and thirteen multi-input OR gates. `VALID`
distinguishes "no key" from key `0`. For an active-low keypad, invert all ten
keys at the interface and document that convention; do not silently change the
priority order.

For the hierarchical direct-wire variant required by some courses:

```powershell
python scripts/generate_hierarchical_keypad.py --out outputs/keypad_hier.circ
python scripts/check_hierarchical.py outputs/keypad_hier.circ `
  --table outputs/keypad_hier_exhaustive.tsv --require-exhaustive
python scripts/validate_logisim.py outputs/keypad_hier.circ `
  --table outputs/keypad_hier_smoke.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

This project has `main`, `PriorityStage`, `TermStage`, and `BCDStage`.
Inter-stage and intra-stage connections are direct orthogonal wires. It emits
zero Tunnel components. `check_hierarchical.py` expands custom-appearance ports
and simulates the hierarchy independently from Logisim.

When the assignment forbids encapsulation as well as Tunnels, use the flat
direct-wire variant:

```powershell
python scripts/generate_flat_keypad.py --out outputs/keypad_flat.circ
python scripts/check_circ.py outputs/keypad_flat.circ `
  --table outputs/keypad_flat_exhaustive.tsv --require-exhaustive
```

The flat layout is organized in five visible bands: input column, suffix
priority ladder, higher-key suppression column, one-hot term column, and BCD
output column. It uses unique vertical fanout lanes between columns and local
source-row channels below gate bodies. Do not let two nets share a vertical
lane or use a source-row junction where another lane turns; those are the two
common sources of accidental shorts in large direct-wire diagrams.

## Bundled Resources

- Start at `reference/INDEX.md` to choose a sample. Treat user-supplied files under `reference/supplied_archive/` as examples to inspect, not authoritative documentation.
- `examples/mux2_gate_level.circ` is a compact worked gate-level 2:1 multiplexer. Use it to inspect a complete small project with three inputs, one output, basic gates, and orthogonal wires.
- `references/upstream/logisim27-circ.md` contains 2.7.1 project snippets and layout conventions. `logisim27-components.json` records library IDs, anchors, assumptions, and terminal offsets derived from 2.7.1 component sources. Respect each component's stated facing and configuration assumptions.
- `scripts/layout.py` is a narrowly scoped 9-input priority-encoder layout experiment, not a general-purpose circuit generator. Reuse its ideas only after checking its assumptions against the current task and Logisim version.
- `scripts/render.py` makes a rough image for layout inspection. It does not render Logisim's actual symbols or prove connectivity.
- `scripts/check_circ.py` parses and simulates scalar basic-gate circuits, including Tunnel nets and Power/Ground constants. It reports floating terminals and multiple drivers and can compare a reference TSV table.
- `scripts/circ_model.py` is the bit-level bus/sequential model used by the universal checker.
- `scripts/check_universal.py` checks buses, splitters, hierarchy, high-level arithmetic/plexers, and sequential tables.
- `scripts/generate_alu.py` builds the bundled 16-bit gate-level ALU regression, its reference vectors, and its optional exhaustive table.
- `scripts/generate_keypad_encoder.py` builds the gate-only decimal keypad priority encoder, a 1024-row exhaustive table, and a smaller Logisim smoke table.
- `scripts/generate_hierarchical_keypad.py` builds the four-circuit direct-wire hierarchy without Tunnels.
- `scripts/generate_flat_keypad.py` builds the single-circuit, direct-wire layout with no encapsulation and no Tunnels.
- `scripts/generate_encoder_8to3.py` builds a flat gate-level 8-to-3 priority encoder with a 256-row exhaustive table.
- `scripts/direct_router.py` provides deterministic orthogonal routing for direct-wire subcircuits.
- `scripts/check_hierarchical.py` resolves custom subcircuit appearances and simulates nested circuits.
- `scripts/validate_logisim.py` runs real Logisim 2.7.1 CLI simulations with generated halt harnesses.
- `scripts/validate_logisim_clocked.py` runs real clocked sequences and compares them with the independent state model.
- `scripts/generate_probes.py` creates bus, splitter, and register regression probes.
- `references/capability-matrix.md` lists the supported component and validation matrix plus current boundaries.
- `references/upstream/validation.md` describes CLI/harness validation. Do not fetch or install a runtime unless the user has authorized that action.
