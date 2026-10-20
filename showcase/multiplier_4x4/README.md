# 4x4 Gate-Level Array Multiplier

This is a single flat Logisim 2.7.1 circuit for unsigned 4-bit
multiplication. It contains only scalar Pins, Text, basic gates, and direct
orthogonal wires. There are no subcircuits, Tunnels, or high-level arithmetic
components.

## Interface

Inputs:

- `A0..A3` and `B0..B3`, active high.
- Bit 0 is the least significant bit.

Outputs:

- `P0..P7`, the eight-bit unsigned product.
- `P0` is the least significant bit.

The supported range is `0..15 x 0..15 = 0..225`.

## Implementation

The multiplier uses the standard carry-save array organization:

- 16 AND gates form `PPij = Ai AND Bj`.
- The first partial-product row initializes the accumulator.
- Three accumulation rows add the remaining shifted partial products.
- The rows contain 4 expanded half adders and 8 expanded full adders.
- Every half or full adder is built from basic AND, XOR, and OR gates.

Gate inventory:

| Gate | Count |
| --- | ---: |
| AND | 36 |
| XOR | 20 |
| OR | 8 |
| Total | 64 |

The drawing is organized from top-left to bottom-right: operand Pins,
the 4x4 partial-product grid, three visible accumulation rows, and the final
product Pins. All 64 gates are visible at the same level.

## Direct Wiring

- 898 direct orthogonal wire segments.
- 0 Tunnel components.
- 0 subcircuit instances.
- Explicitly split same-net T junctions to avoid Logisim `E` values on dense
  direct-wire trees.
- No overlapping collinear wires, dangling endpoints, gate-body crossings, or
  multiple-driver nets in the independent structural check.

## Files

- `4x4_array_multiplier_gate_level.circ` - clean Logisim project.
- `4x4_array_multiplier_exhaustive.tsv` - all 256 operand pairs.
- `4x4_array_multiplier_smoke.tsv` - 16 runtime vectors.
- `4x4_array_multiplier_preview.png` - diagnostic layout preview.
- `VALIDATION.md` - verification record.
