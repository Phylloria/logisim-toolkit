# Flat Direct-Wire Decimal Keypad Priority Encoder

This version uses one flat Logisim circuit. All 29 gates are visible at the
same level. There are no subcircuits and no Tunnel components.

## Interface

- `K0..K9`: active-high key inputs. `K9` has the highest priority.
- `B0..B3`: active-high BCD output, with `B0` as the least significant bit.
- `VALID`: high when at least one key is pressed.

If several keys are pressed, the highest-numbered pressed key wins. When no key
is pressed, `VALID=0` and the BCD value is `0000`.

## Visual Organization

The flat drawing is divided into five columns:

1. `K0..K9` input Pins.
2. Suffix priority ladder `S8..S0`.
3. Higher-key suppression inverters `H8..H1`.
4. One-hot term gates `T8..T1`.
5. BCD output gates `B3..B0`.

Direct-wire techniques used to keep the drawing readable:

- Each priority-stage fanout has its own vertical lane.
- The K1..K8 lower-input branches run through a separate local channel below
  the gate bodies.
- BCD fanout terms use eight distinct vertical lanes between the term column
  and the BCD output column.
- K9 has one dedicated long vertical lane for its B0 and B3 terms.
- Crossings are orthogonal and occur between wire interiors; they do not create
  junctions. No wire passes through a gate body.
- The hierarchy is expressed visually by regular columns and signal-flow
  direction, without hiding any logic inside a subcircuit.

## Inventory

- Circuits: 1.
- Top-level components: 50.
- Basic gates: 29.
  - AND: 8.
  - OR: 13.
  - NOT: 8.
- Input Pins: 10.
- Output Pins: 5.
- Direct wires: 176.
- Tunnel components: 0.
- Subcircuit instances: 0.

## Files

- `keypad_priority_encoder_flat_direct.circ` - complete flat project.
- `keypad_priority_encoder_flat_exhaustive.tsv` - all 1024 vectors.
- `keypad_priority_encoder_flat_smoke.tsv` - 19 runtime vectors.
- `keypad_priority_encoder_flat_preview.png` - full flat-layout preview.
- `VALIDATION.md` - verification record.
