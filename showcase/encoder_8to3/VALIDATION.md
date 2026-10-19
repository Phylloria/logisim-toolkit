# Validation Record

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Structure

- Circuits: 1.
- Basic gates: 22.
- OR gates: 10.
- NOT gates: 6.
- AND gates: 6.
- Direct wires: 130.
- Tunnels: 0.
- Subcircuits: 0.
- High-level encoder/arithmetic components: 0.
- Overlapping collinear wire pairs: 0.
- Dangling wire endpoints: 0.

## Exhaustive Check

All `2^8 = 256` input combinations were checked against the independent
priority-encoder model:

```text
Reference rows: 256; mismatches: 0
```

No floating terminals or multiple-driver nets were reported.

## Real Logisim

Fourteen runtime vectors cover no input, each single input, and representative
multi-input priority cases:

```text
Vectors: 14
PASS: 14 vector(s) matched in Logisim 2.7.1
```
