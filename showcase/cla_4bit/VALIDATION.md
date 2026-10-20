# Validation Record

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Structure

- Circuits: 1.
- Basic gates: 32.
  - AND: 16.
  - XOR: 8.
  - OR: 8.
- Input Pins: 9.
- Output Pins: 5.
- Direct wires: 334.
- Wire corner-or-junction points: 211.
- Tunnels: 0.
- Subcircuits: 0.
- High-level arithmetic components: 0.
- Floating terminals: 0.
- Multiple-driver nets: 0.
- Overlapping collinear wire pairs: 0.
- Dangling wire endpoints: 0.
- Wires entering gate bodies: 0.

## Exhaustive Check

All `16 x 16 x 2 = 512` combinations of `A`, `B`, and `CIN` were checked
against the independent arithmetic model:

```text
Reference rows: 512; mismatches: 0
```

The table supplies scalar columns `A0..A3`, `B0..B3`, `CIN`, `S0..S3`, and
`COUT`.

## Real Logisim

Sixteen runtime vectors cover zero, incoming carry, both one-bit operands,
low and high carry boundaries, `15+15`, and representative mixed-bit values:

```text
Vectors: 16
PASS: 16 vector(s) matched in Logisim 2.7.1
```

The runtime harness fixes the input Pins with Constant components and adds a
validation-only `halt` Pin. Those harness components are not present in the
clean deliverable.

## Regression

`tests/test_cla.py` generates the circuit in a temporary directory and checks:

- one flat circuit,
- zero Tunnels,
- the exact 16/8/8 gate inventory,
- scalar and exhaustive vector-table columns,
- all 512 input combinations in the independent model,
- real Logisim simulation when a local runtime is available.
