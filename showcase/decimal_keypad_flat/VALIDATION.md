# Validation Record

Date: 2026-10-20

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Flat Project Inventory

```text
Circuits: 1
Components: 50
AND gates: 8
OR gates: 13
NOT gates: 8
Input Pins: 10
Output Pins: 5
Text notes: 6
Wires: 176
Tunnels: 0
Subcircuit instances: 0
```

The single circuit contains every gate directly on the canvas.

## Structural Check

```text
Input pins: 10; output pins: 5
Floating terminals: 0
Multiple-driver nets: 0
Missing labels: 0
Unsupported or duplicate components: 0
```

The checker also rejects wires that enter gate bodies. It reported none.

## Exhaustive Functional Check

All `2^10 = 1024` key combinations were compared with the independent reference
model:

```text
Reference rows: 1024; mismatches: 0
```

## Real Logisim Simulation

Nineteen vectors covering no key, every single key, mixed-priority cases, and
all keys pressed were checked in Logisim 2.7.1:

```text
Logisim: C:\Logisim\logisim-win-2.7.1.exe
Java: C:\Program Files\Java\jre1.8.0_503\bin\java.exe
Vectors: 19
PASS: 19 vector(s) matched in Logisim 2.7.1
```

## Skill Regression

The flat regression asserts:

- Exactly one circuit.
- Zero Tunnel components.
- Exactly 29 basic gates.
- 1024/1024 exhaustive static matches.
- A real Logisim harness round trip.

Full skill regression result:

```text
Ran 13 tests in 74.909s
OK
```
