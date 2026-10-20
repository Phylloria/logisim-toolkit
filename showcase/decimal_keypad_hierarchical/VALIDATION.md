# Validation Record

Date: 2026-10-20

## Runtime

- Logisim: 2.7.1
- Executable: `C:\Logisim\logisim-win-2.7.1.exe`
- Java: `C:\Program Files\Java\jre1.8.0_503\bin\java.exe`

## Hierarchy And Inventory

| Circuit | Components | Gates | Wires | Tunnels |
| --- | ---: | ---: | ---: | ---: |
| `PriorityStage` | 45 | 17 | 160 | 0 |
| `TermStage` | 34 | 8 | 25 | 0 |
| `BCDStage` | 17 | 4 | 43 | 0 |
| `main` | 20 | 0 | 43 | 0 |
| Total | 116 | 29 | 271 | 0 |

`main` contains exactly three subcircuit instances. Wires from `K0..K9` to
`PriorityStage`, from `PriorityStage` to `TermStage`, from `TermStage` to
`BCDStage`, and from `BCDStage` to the output Pins are direct orthogonal wires.

## Hierarchical Exhaustive Check

An independent hierarchy checker resolves the custom appearance ports of every
child circuit and simulates all `2^10 = 1024` key combinations:

```text
Main: main
Main inputs: 10; outputs: 5; instances: 3
Reference rows: 1024; mismatches: 0
```

Structural checks reported:

- No floating terminals.
- No multiple-driver nets.
- No missing appearance ports.
- No duplicate component locations.
- No wires entering gate bodies.
- No Tunnel components.

## Real Logisim Simulation

The clean hierarchical project was converted to temporary Power/Ground halt
harnesses for the runtime vectors:

```text
Logisim: C:\Logisim\logisim-win-2.7.1.exe
Java: C:\Program Files\Java\jre1.8.0_503\bin\java.exe
Vectors: 19
PASS: 19 vector(s) matched in Logisim 2.7.1
```

The vectors cover no key, every single key, multi-key priority combinations,
and all keys pressed together.

## Skill Regression

```text
Ran 10 tests in 53.733s
OK
```

The hierarchy test also asserts that all four expected circuits exist, that
`main` has exactly three instances, and that no Tunnel component appears in any
circuit.
