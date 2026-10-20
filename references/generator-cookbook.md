# Generator Cookbook

All commands can also be run as `python -m scripts.cli ...` from a checkout.

## Gate-Level And Direct-Wire Designs

### 8-to-3 Priority Encoder

```powershell
logisim-toolkit generate encoder-8to3 --out encoder8.circ
logisim-toolkit check encoder8.circ `
  --table encoder8_vectors.tsv --require-exhaustive
```

Interface: `I0..I7`, `Y0..Y2`, `VALID`.

### Compact 9-Key Corridor Encoder

```powershell
logisim-toolkit generate encoder-9-corridor --out priority9.circ
logisim-toolkit check priority9.circ `
  --table priority9_vectors.tsv --require-exhaustive
```

Interface: active-high `I1..I9`, active-low `nD3..nD0`. Use this as the
worked example for staged local lanes and bypass tracks.

### Decimal Keypad, Hierarchical

```powershell
logisim-toolkit generate keypad-hierarchy --out keypad_hier.circ
logisim-toolkit check-hierarchy keypad_hier.circ `
  --table keypad_hier_exhaustive.tsv --require-exhaustive
```

Circuits: `main`, `PriorityStage`, `TermStage`, `BCDStage`.

### Decimal Keypad, Flat Direct-Wire

```powershell
logisim-toolkit generate keypad-flat --out keypad_flat.circ
logisim-toolkit check-scalar keypad_flat.circ `
  --table keypad_flat_exhaustive.tsv --require-exhaustive
```

Use when both Tunnels and encapsulation are forbidden.

### 4x4 Array Multiplier

```powershell
logisim-toolkit generate multiplier-4x4 --out multiplier4.circ
logisim-toolkit check multiplier4.circ `
  --table multiplier4_vectors.tsv --require-exhaustive
```

Interface: `A0..A3`, `B0..B3`, `P0..P7`. Sixty-four basic gates, no Tunnels.

### 4-bit Carry-Lookahead Adder

```powershell
logisim-toolkit generate cla-4bit --out cla4.circ
logisim-toolkit check cla4.circ `
  --table cla4_vectors.tsv --require-exhaustive
```

Interface: `A0..A3`, `B0..B3`, `CIN`, `S0..S3`, `COUT`. All 512 input
combinations are generated.

### 256-Gate Stress Netlist

```powershell
logisim-toolkit generate stress-256 --out stress256.circ
logisim-toolkit check stress256.circ --table stress256_vectors.tsv
logisim-toolkit validate stress256.circ --table stress256_vectors.tsv `
  --limit 2 --logisim C:\Logisim\logisim-win-2.7.1.exe
```

This is a routing regression, not a functional showcase.

## Larger Or Tunnel-Based Designs

### Gate-Level ALU

```powershell
logisim-toolkit generate alu --bits 16 --out alu16.circ
```

Use the generated vectors or `--exhaustive-table` for a smaller bit width.
This generator uses Tunnels for long-distance nets.

### Component Probes

```powershell
logisim-toolkit generate probes --out-dir probes
```

Creates bus, splitter, register, adder, comparator, multiplexer, and decoder
regressions.

## Validation Ladder

Run the strongest applicable checks in this order:

1. `check-scalar` for flat scalar gate circuits.
2. `check-hierarchy` for custom subcircuit appearances.
3. `check` for buses, splitters, high-level arithmetic, and sequential logic.
4. `validate` or `validate-clocked` against a real Logisim runtime.
5. `render` for visual inspection only, never as proof of connectivity.

All check commands accept TSV tables. Values may be `0`, `1`, exact-width
binary, `0b...`, `0x...`, or decimal.
