# 4-bit Block Carry-Lookahead Adder

This is a flat gate-level Logisim 2.7.1 carry-lookahead adder. It uses only
scalar Pins, Text, two-input basic gates, and direct orthogonal wires. There
are no subcircuits, Tunnels, or high-level arithmetic components.

## Interface

Inputs:

- `A0..A3`, `B0..B3`, active high.
- `CIN`, the incoming carry.
- Bit 0 is the least significant bit.

Outputs:

- `S0..S3`, the four sum bits.
- `COUT`, the carry beyond bit 3.

The arithmetic result is `A + B + CIN`, represented as the five-bit value
`COUT S3 S2 S1 S0`.

## Lookahead Structure

The first stage generates:

```text
Pi = Ai XOR Bi
Gi = Ai AND Bi
```

The 2-bit groups generate:

```text
P10 = P1 AND P0
G10 = G1 OR (P1 AND G0)
P32 = P3 AND P2
G32 = G3 OR (P3 AND G2)
```

The complete 4-bit group generates:

```text
P30 = P32 AND P10
G30 = G32 OR (P32 AND G10)
```

The carries are selected in parallel:

```text
C1 = G0  OR (P0  AND CIN)
C2 = G10 OR (P10 AND CIN)
C3 = G21 OR (P21 AND CIN)
C4 = G30 OR (P30 AND CIN)

G21 = G2  OR (P2 AND G10)
P21 = P2  AND P10
Si  = Pi  XOR Ci
```

There is no serial ripple chain from `C1` to `C4`.

## Inventory

| Component | Count |
| --- | ---: |
| AND gates | 16 |
| XOR gates | 8 |
| OR gates | 8 |
| Total basic gates | 32 |
| Direct wires | 334 |
| Tunnels | 0 |
| Subcircuits | 0 |

The measured component-and-wire footprint is 2750 by 770 circuit units.
Every gate is a two-input basic gate, which keeps the direct-wire fanout
channels readable while preserving the lookahead structure. The router uses
a high bend cost of 20 because this column-oriented layout can be routed with
markedly fewer doglegs.

## Files

- `4bit_carry_lookahead_adder_gate_level.circ` - clean Logisim project.
- `4bit_carry_lookahead_adder_exhaustive.tsv` - all 512 input combinations.
- `4bit_carry_lookahead_adder_smoke.tsv` - 16 runtime vectors.
- `4bit_carry_lookahead_adder_preview.png` - diagnostic layout preview.
- `VALIDATION.md` - verification record.
