# Reference Circuit Index

Use these projects to inspect a specific Logisim pattern. They are examples, not templates to print or copy wholesale. Check the project header to confirm version, and verify uncertain component geometry in the target application before generating a circuit that depends on it.

## Component placement and terminals

| Files | Intended inspection |
|---|---|
| `and2.circ` through `and7.circ` | AND gate input-count placement and terminal spacing, as described by the original author. |
| `facing_south.circ` | Three-input gate facing south. |
| `facing_ew_pin.circ` | East/west gate orientations and Pin endpoints. |
| `xor_xnor.circ` | XOR/XNOR gate placement comparison. |
| `mux.circ` | Multiplexer component and terminal sample; source notes say coordinates are not fully confirmed. |
| `splitter.circ` | Splitter attributes, appearance, and fanout. |

## Circuit patterns

- `../examples/full_adder_gate_level.circ` is a verified one-bit full adder built only from XOR, AND, and OR gates. `outputs/full_adder_truth.tsv` records its exhaustive 8-row truth table.

| Files | Intended inspection |
|---|---|
| `mux_4to1.circ` | Gate-level 4-to-1 multiplexer and orthogonal wire routing. |
| `adder.circ` | Gate-built adder. Use as a logic example, not as an Adder component reference. |
| `button.circ` | Button and north-facing NOT example; original notes warn that its routing and terminal offset are not settled. |
| `references/hust_adder_reference.circ` | Additional adder project; inspect its own header and structure before reuse. |

## User-supplied archive

`supplied_archive/` preserves the contents of the separate `logisim.zip` archive. It includes alternate AND, mux, adder, splitter, button, power/ground, and XOR/XNOR examples plus `draft.circ`. Use the closest small example for the specific component or pattern under study. Do not treat an unverified sample as a universal coordinate specification.

## Versioned component data

For Logisim 2.7.1 component library IDs and documented anchors, see `../references/upstream/logisim27-components.json`. For project syntax and layout notes, see `../references/upstream/logisim27-circ.md`.
