# Logisim 2.7.1 Capability Matrix

## Design And Generation

Supported:

- Native 2.7.1 `.circ` XML.
- Scalar and multi-bit Pins.
- Basic gates with scalar or bus widths.
- Labeled Tunnels and fully direct orthogonal wiring.
- Splitter decoding and combining with explicit bit mappings.
- Hierarchical subcircuits and custom appearance ports.
- Text notes and custom recursive gate-netlist generators.
- Structured flat layouts using functional columns and dedicated fanout lanes.

## Independent Simulation

`scripts/circ_model.py` and `scripts/check_universal.py` support:

- Pin, Tunnel, Power, Ground, Constant, Clock.
- Splitter.
- AND/OR/NAND/NOR/XOR/XNOR/NOT.
- Adder, Comparator.
- Multiplexer, Decoder.
- D Flip-Flop, Register, Counter.
- Nested subcircuits.
- Bit-level width checking and multiple-driver detection.
- Combinational vector tables.
- Sequential tables using `--sequential`.

The model treats splitter ends as bidirectional bit collections. It correctly
handles both splitting a bus into branches and combining branches back into a
bus.

## Real Logisim Validation

Supported:

- Scalar and bus combinational harnesses using Constant inputs and a halt Pin.
- 2.7.1 TTY grouped-binary output normalization.
- Canonical output order: top-to-bottom, then left-to-right Pin position.
- Fixed-input clocked harnesses using Clock, Counter, Comparator, CYCLE output,
  and a halt Pin.
- Sequential runtime comparison against the independent state model.

## Current Boundaries

- The universal model does not yet simulate RAM, ROM, LEDs, probes, transistors,
  transmission gates, or arbitrary plugin libraries.
- Clocked runtime validation currently fixes data inputs for the whole run.
  Changing input vectors over time should be checked with `--sequential` in the
  independent model and a project-specific harness.
- Bus TTY values are normalized from Logisim 2.7.1 grouped binary output.
  Logisim Evolution 4.x output formatting is not covered by the same parser.
- Rendering is a diagnostic layout preview, not the real Logisim painter.
- Unsupported component libraries should be inspected with a tiny probe before
  extending `circ_model.py`.
