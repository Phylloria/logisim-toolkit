# Validation Record

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Structure

- Circuits: 1.
- Basic gates: 31.
- Input Pins: 9.
- Output Pins: 4.
- Direct wires: 191.
- Tunnels: 0.
- Subcircuits: 0.
- Floating terminals: 0.
- Multiple-driver nets: 0.
- Off-grid components or endpoints: 0.
- Implicit T junctions: 0.
- Combinational gate cycles: 0.

## Exhaustive Check

All `2^9 = 512` input masks pass:

```text
Reference rows: 512; mismatches: 0
```

## Real Logisim

Eight vectors covering no key, one-hot keys, priorities, and mixed masks pass:

```text
Vectors: 8
PASS: 8 vector(s) matched in Logisim 2.7.1
```
