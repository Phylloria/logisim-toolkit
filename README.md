# Phylloria Logisim Toolkit

A standalone Python toolkit for designing, checking, generating, and validating
native Logisim 2.7.1 projects. It works from a normal terminal, CI, or any
AI coding agent. Codex is an optional integration, not a requirement.

The toolkit includes an independent bit-level circuit model, structural checks,
real Logisim harnesses, clocked validation, and generators for flat,
direct-wire, and hierarchical layouts.

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

## Install

```powershell
pipx install "git+https://github.com/Phylloria/Phylloria_Logisim.git"
```

For preview rendering:

```powershell
pipx install "phylloria-logisim[render] @ git+https://github.com/Phylloria/Phylloria_Logisim.git"
```

Or install from a clone:

```powershell
git clone https://github.com/Phylloria/Phylloria_Logisim.git
cd Phylloria_Logisim
python -m pip install .
```

The installed command is `logisim-toolkit`.

## Repository Layout

```text
pyproject.toml           Installable Python package
scripts/cli.py           Standalone CLI
SKILL.md                 Optional Codex adapter
AGENTS.md                Agent-neutral operating instructions
scripts/                 Generators, checkers, runtime validators
references/              Logisim 2.7.1 notes and capability matrix
reference/               Small component probes and circuit examples
examples/                Basic worked circuits
tests/                   End-to-end regression suite
showcase/                Full-size completed circuits
```

## Quick Validation

```powershell
logisim-toolkit check design.circ --table vectors.tsv
logisim-toolkit validate design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

Sequential circuits:

```powershell
logisim-toolkit check state.circ --table sequence.tsv --sequential
logisim-toolkit validate-clocked state.circ `
  --clock CLK --cycles 8 --input D=5 --input EN=1
```

Generate a complete circuit:

```powershell
logisim-toolkit generate encoder-8to3 --out encoder_8to3.circ
logisim-toolkit check encoder_8to3.circ `
  --table encoder_8to3_vectors.tsv --require-exhaustive
```

List commands:

```powershell
logisim-toolkit list-tools
```

## Included Showcase

- [8-to-3 priority encoder](showcase/encoder_8to3/)
- [Decimal keypad encoder - flat direct wiring](showcase/decimal_keypad_flat/)
- [Decimal keypad encoder - hierarchy](showcase/decimal_keypad_hierarchical/)
- [16-bit gate-level ALU](showcase/alu16/)

All showcases include the native `.circ`, reference vectors, previews, and
verification notes.

## Agents And Editors

- Codex: copy or link this repository to the Codex skills directory; `SKILL.md`
  remains a thin adapter over the same CLI and scripts.
- Claude Code, Cursor, and other agents: point them to `AGENTS.md`.
- Human terminal/CI use: call `logisim-toolkit` directly.

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

See `docs/usage.md` for command reference and automation patterns. The
capability matrix is in `references/capability-matrix.md`.
