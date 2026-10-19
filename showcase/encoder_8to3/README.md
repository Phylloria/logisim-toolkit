# 8-to-3 Priority Encoder

This is a single flat Logisim 2.7.1 circuit built only from basic AND, OR, and
NOT gates. It has no subcircuits and no Tunnel components.

## Interface

Inputs:

- `I0..I7`, active high.
- `I7` has the highest priority and `I0` the lowest.

Outputs:

- `Y2`, `Y1`, `Y0`: three-bit binary digit.
- `VALID`: high when any input is high.

When no input is active, `Y2..Y0=000` and `VALID=0`. This distinguishes no
input from `I0`, which also produces code `000`.

## Priority Table

| Active input | Y2 Y1 Y0 | VALID |
| --- | --- | --- |
| none | 000 | 0 |
| I0 | 000 | 1 |
| I1 | 001 | 1 |
| I2 | 010 | 1 |
| I3 | 011 | 1 |
| I4 | 100 | 1 |
| I5 | 101 | 1 |
| I6 | 110 | 1 |
| I7 | 111 | 1 |

If multiple inputs are active, the highest-numbered input determines the code.

## Implementation

- 7 OR gates build the suffix priority chain.
- 6 NOT gates create the higher-priority suppression signals.
- 6 AND gates create selected terms `T6..T1`.
- 3 OR gates combine each output bit.
- 22 basic gates total.
- 130 direct orthogonal wires.

The layout is organized by signal flow: inputs, priority ladder, suppression,
one-hot terms, and binary output.

## Files

- `encoder_8to3_gate_level.circ`
- `encoder_8to3_exhaustive.tsv` - all 256 input combinations.
- `encoder_8to3_smoke.tsv` - 14 runtime vectors.
- `encoder_8to3_preview.png`
- `VALIDATION.md`
