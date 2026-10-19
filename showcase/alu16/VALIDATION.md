# Validation Record

Date: 2026-10-20

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`
- Runtime version command returned `2.7.1`.

## Project Inventory

- Main circuit: `main`
- Total components: 1839
- Basic gates: 433
  - AND: 187
  - OR: 160
  - XOR: 65
  - NOT: 21
- Tunnels: 1343
- Wires: 1343
- Input Pins: 36
- Output Pins: 21
- Text notes: 6
- Forbidden arithmetic/multiplexer/halt search: no matches
- XOR input wires terminate on the source-verified `x-60` terminals.

## Static Checks

Independent checker command:

```text
python scripts\check_circ.py 16bit_alu_gate_level.circ \
  --table 16bit_alu_gate_level_vectors.tsv
```

Result:

```text
Floating terminals: 0
Multiple-driver nets: 0
Missing labels: 0
Unsupported or duplicate components: 0
Reference rows: 22; mismatches: 0
```

The checker validates tunnel connectivity, drivers, floating terminals,
duplicate locations, gate-body overlap, and scalar basic-gate behavior.

## Exhaustive Small Regression

A 2-bit generated circuit has 8 scalar inputs and 256 combinations. It passed
all rows with:

```text
Reference rows: 256; mismatches: 0
```

## Real Logisim Simulation

Each vector was converted into a temporary harness with input Pins replaced by
Power/Ground sources and an output Pin named `halt`. The clean project was not
modified.

```text
Logisim: C:\Logisim\logisim-win-2.7.1.exe
Java: C:\Program Files\Java\jre1.8.0_503\bin\java.exe
Vectors: 22
PASS: 22 vector(s) matched in Logisim 2.7.1
```

## Skill Regression

```text
Ran 4 tests in 15.067s
OK
```

The tests cover circuit/table generation, 256-row static exhaustive simulation,
source-verified XOR terminal placement, and a real Logisim harness round trip.

## Evidence Boundary

The checked behavior covers ADD, SUB, AND, OR, XOR, NOT, SHL, SHR, carry,
borrow, signed overflow, zero, and negative outputs, including boundary values.
The 16-bit input space was not exhaustively enumerated in Logisim.
