# Phylloria_Logisim

A reusable Codex skill and example collection for designing, checking, and
validating native Logisim 2.7.1 projects.

The skill moves beyond hand-drawn XML: it includes an independent bit-level
circuit model, structural checks, real Logisim harnesses, clocked validation,
and generators for flat, direct-wire, and hierarchical layouts.

## Highlights

- Scalar and multi-bit buses with bit-level width checking.
- Basic gates, Tunnels, Splitters, Constants, and Clocks.
- Splitter decode and combine.
- Adder, Comparator, Multiplexer, and Decoder.
- D Flip-Flop, Register, and Counter state simulation.
- Nested subcircuits with custom appearances.
- Direct-wire layout checks for:
  - overlapping collinear wires,
  - dangling wire endpoints,
  - wires entering gate bodies,
  - duplicate component locations,
  - multiple drivers.
- Real Logisim bus, vector, and clocked runtime validation.

## Repository Layout

```text
SKILL.md                 Codex skill instructions
README.md                Repository overview
scripts/                 Generators, checkers, runtime validators
references/              Logisim 2.7.1 notes and capability matrix
reference/               Small component probes and circuit examples
examples/                Basic worked circuits
tests/                   End-to-end regression suite
showcase/                Full-size completed circuits
```

## Install As A Codex Skill

Clone the repository, then place it under the Codex skills directory with a
stable name:

```powershell
git clone https://github.com/Phylloria/Phylloria_Logisim.git
Copy-Item -Recurse Phylloria_Logisim "$env:USERPROFILE\.codex\skills\logisim"
```

Read `SKILL.md` for the full authoring workflow. The capability matrix is in
`references/capability-matrix.md`.

## Quick Validation

```powershell
python scripts/check_universal.py design.circ --table vectors.tsv
python scripts/validate_logisim.py design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

Sequential circuits:

```powershell
python scripts/check_universal.py state.circ --table sequence.tsv --sequential
python scripts/validate_logisim_clocked.py state.circ `
  --clock CLK --cycles 8 --input D=5 --input EN=1
```

## Included Showcase

- [8-to-3 priority encoder](showcase/encoder_8to3/)
- [Decimal keypad encoder - flat direct wiring](showcase/decimal_keypad_flat/)
- [Decimal keypad encoder - hierarchy](showcase/decimal_keypad_hierarchical/)
- [16-bit gate-level ALU](showcase/alu16/)

All showcases include the native `.circ`, reference vectors, previews, and
verification notes.

## Run The Regression

```powershell
python -m unittest discover -s tests -v
```

The suite covers gate geometry, bus gates, Splitters, hierarchy, wide
arithmetic/plexers, sequential state, direct-wire layout rules, and real
Logisim 2.7.1 execution.

## Runtime Notes

- Primary target: Logisim 2.7.1.
- Python 3.10 or later is recommended.
- A console `java.exe` is required for real runtime checks.
- Bus Constants must use the 2.7.1 `0x...` hexadecimal form.
- Unsupported components and format boundaries are documented instead of being
  silently treated as validated.
