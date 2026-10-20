# Validation Record

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Structure

- Circuits: 1.
- Basic gates: 64.
  - AND: 36.
  - XOR: 20.
  - OR: 8.
- Input Pins: 8.
- Output Pins: 8.
- Direct wires: 882.
- Wire corner-or-junction points: 637.
- Tunnels: 0.
- Subcircuits: 0.
- High-level arithmetic components: 0.
- Floating terminals: 0.
- Multiple-driver nets: 0.
- Overlapping collinear wire pairs: 0.
- Dangling wire endpoints: 0.
- Wires entering gate bodies: 0.

## Exhaustive Check

All `2^8 = 256` operand pairs were checked against the independent arithmetic
model:

```text
Reference rows: 256; mismatches: 0
```

The table supplies scalar columns `A0..A3`, `B0..B3`, and `P0..P7`.

## Real Logisim

Sixteen runtime vectors cover zero, identity, maximum, overflow boundary,
large-by-small, symmetric factors, and representative mixed-bit cases:

```text
Vectors: 16
PASS: 16 vector(s) matched in Logisim 2.7.1
```

The runtime harness fixes the input Pins with Constant components and adds a
validation-only `halt` Pin. Those harness components are not present in the
clean deliverable.

## Regression

`tests/test_multiplier.py` generates the circuit in a temporary directory and
checks:

- one flat circuit,
- zero Tunnels,
- the exact 36/20/8 gate inventory,
- scalar and exhaustive vector-table columns,
- all 256 operand pairs in the independent model,
- real Logisim simulation when a local runtime is available.
