# Validation Record

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Structure

- Circuits: 1.
- Basic gates: 256.
- Input Pins: 16.
- Output Pins: 4.
- Direct wires: 2705.
- Tunnels: 0.
- Subcircuits: 0.
- Off-grid components or wire endpoints: 0.
- Floating terminals: 0.
- Multiple-driver nets: 0.
- Overlapping collinear wires: 0.
- Implicit T junctions: 0.

## Independent Model

Sixty-eight deterministic vectors cover zero, all ones, every one-hot input,
alternating masks, nibble masks, and a seeded pseudo-random sequence:

```text
Reference rows: 68; mismatches: 0
```

## Real Logisim

The first eight vectors were loaded as real Logisim 2.7.1 harnesses:

```text
Vectors: 8
PASS: 8 vector(s) matched in Logisim 2.7.1
```

The clean deliverable contains no Constant or halt harness components.
