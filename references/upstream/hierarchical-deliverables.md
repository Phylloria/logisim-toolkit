# Complex Circuit Packaging / Hierarchical Deliverables

Use this reference when a circuit would become large, repetitive, or hard to operate if every
gate, Tunnel, bit wire, and validation signal were placed on `main`.

## Default Packaging

- Prefer a clean `main` circuit plus internal subcircuits for nontrivial datapaths, repeated
  bit-slices, ALUs, register files, controllers, RAM/ROM systems, buses, decoders, and CPUs.
- `main` is the user's operating surface. It should contain the top-level input Pins, output
  Pins, one or a few compact subcircuit instances, and only the Text notes needed to understand
  the interface.
- Subcircuits carry implementation detail. Use names such as `ALU_CORE`, `BitSlice`,
  `RegisterCell`, `Controller`, or `Datapath` so the hierarchy explains itself.
- Keep validation-only items out of the final artifact. `halt`, fixed stimuli, expected-value
  comparators, and counters belong in a harness circuit or separate generated test copy.

## N-bit Bus Policy

- When the user asks for an N-bit input or output, expose it as one native Logisim Pin with
  `width="N"` on the top level.
- Do not default to top-level `A0..A7`, `B0..B7`, or `R0..R7` Pins for an 8-bit interface.
  Split and join the bus inside a core subcircuit unless the user explicitly asks for bit Pins.
- Use Splitters/Joiners inside the implementation subcircuit to connect native buses to repeated
  one-bit cells.
- Give multi-bit Pins extra layout clearance. Their visible value boxes occupy more than one grid
  point and can overlap nearby labels or wires if placed at one-grid pitch.

## Custom Appearance

- Any reusable subcircuit placed in a parent circuit should have an `<appear>` block.
- Map each functional Pin with `<circ-port pin="x,y" .../>`; the `pin` value must match the Pin
  coordinate inside that subcircuit.
- Add one `<circ-anchor .../>` so Logisim places the instance predictably.
- Keep appearances compact but not cramped. Leave enough vertical spacing for ports whose labels
  are visible in the parent circuit.
- Inputs normally appear on the left edge of the block and outputs on the right edge. The actual
  Pin components inside the subcircuit should still face toward their local logic.

## Basic-gates 8-bit ALU Pattern

For an 8-bit ALU with `A`, `B`, `OP`, `F_IN`, `RESULT`, and `F_OUT`:

- `main`: only `A[7:0]`, `B[7:0]`, `OP[1:0]`, `F_IN`, `RESULT[7:0]`, `F_OUT`, a compact
  `ALU_CORE` instance, and a few short Text notes.
- `ALU_CORE`: split `A`, `B`, and `OP`; instantiate eight `BitSlice` cells; join the eight result
  bits into `RESULT`; route the carry/borrow chain.
- `BitSlice`: implement one-bit ADD, SUB, AND, and OR using only permitted primitives such as
  XOR, AND, OR, and NOT when the user forbids Logisim Arithmetic components.
- `F_IN` and `F_OUT`: share the carry/borrow role. Use them for ADD carry and SUB borrow; force
  `F_OUT=0` for logic operations when specified.
- Do not use constants for operands, operation select, carry-in, borrow-in, carry chain, borrow
  chain, or result selection unless the user explicitly asks for a fixed demonstration.

Recommended `main` Text notes for this ALU pattern:

```text
OP[1:0]: 00=ADD, 01=SUB, 10=AND, 11=OR
F_IN/F_OUT: carry for ADD, borrow for SUB; logic ops force F_OUT=0
Adder/subtractor is built from XOR/AND/OR/NOT gates inside ALU_CORE/BitSlice
```

## Structural Validation Targets

Use structural checks in addition to Logisim loading and harness runs:

- `main` top-level component count stays small for packaged designs.
- Required top-level Pins have the expected labels, directions, and bus widths.
- Forbidden libraries and components are absent, such as `desc="#Arithmetic"`, `lib="3"`,
  `name="Adder"`, and `name="Subtractor"` for a basic-gates ALU.
- Direct component locations are not duplicated inside any circuit.
- Final deliverables do not contain `halt` Pins; harnesses may contain them.
