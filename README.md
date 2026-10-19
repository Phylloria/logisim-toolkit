# Logisim Toolkit

[![Tests](https://github.com/Phylloria/logisim-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/Phylloria/logisim-toolkit/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)](pyproject.toml)

`logisim-toolkit` is a standalone toolkit for creating, inspecting, checking,
generating, and validating native Logisim 2.7.1 projects.

It is designed to work from a normal terminal, CI, or any AI coding agent. The
repository also contains optional adapters for Codex, Claude Code, and
agent-neutral workflows, but none of them is required.

## Why This Exists

Logisim files are XML, but valid XML does not mean a usable circuit. Ports can
be misaligned, buses can have the wrong width, wires can overrun a bend,
tunnels can hide accidental shorts, and a project can still fail to behave in
Logisim.

This toolkit adds an independent layer around Logisim:

1. Generate readable native `.circ` projects.
2. Resolve geometry and wiring into a bit-level circuit model.
3. Check buses, splitter mappings, hierarchy, sequential state, and layout.
4. Run the same vectors in real Logisim 2.7.1.
5. Keep clean deliverables separate from temporary validation harnesses.

## Capabilities

- Scalar and multi-bit Pins with width conflict detection.
- Basic gates at scalar or bus width.
- Tunnels, Constants, Clocks, Power, Ground, and direct orthogonal wiring.
- Splitter decode and combine.
- Adders, Comparators, Multiplexers, and Decoders.
- D Flip-Flops, Registers, and Counters.
- Nested subcircuits with custom appearance ports.
- Combinational vector tables and clocked state tables.
- Real Logisim bus, vector, and clocked runtime validation.
- Layout checks for:
  - overlapping collinear wires,
  - dangling wire endpoints,
  - wires entering gate bodies,
  - duplicate locations,
  - multiple drivers.

Detailed support and boundaries are documented in
[references/capability-matrix.md](references/capability-matrix.md).

## Install

```powershell
pipx install "git+https://github.com/Phylloria/logisim-toolkit.git"
```

With PNG layout previews:

```powershell
pipx install "logisim-toolkit[render] @ git+https://github.com/Phylloria/logisim-toolkit.git"
```

From a clone:

```powershell
git clone https://github.com/Phylloria/logisim-toolkit.git
cd logisim-toolkit
python -m pip install .
```

The installed command is:

```text
logisim-toolkit
```

## Quick Start

List commands:

```powershell
logisim-toolkit list-tools
```

Check a circuit against a TSV truth table:

```powershell
logisim-toolkit check design.circ --table vectors.tsv
```

Check and then run the same vectors in real Logisim:

```powershell
logisim-toolkit check design.circ --table vectors.tsv
logisim-toolkit validate design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

Sequential circuit:

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

## Command Map

| Command | Purpose |
| --- | --- |
| `check` | Universal bus and sequential model |
| `check-scalar` | Scalar basic-gate diagnostic |
| `check-hierarchy` | Legacy hierarchy-only checker |
| `validate` | Real Logisim combinational and bus vectors |
| `validate-clocked` | Real Logisim fixed-input clock sequence |
| `stats` | Logisim component statistics |
| `render` | Diagnostic layout PNG |
| `generate alu` | Gate-level N-bit ALU |
| `generate encoder-8to3` | 8-to-3 priority encoder |
| `generate keypad-flat` | Flat decimal keypad encoder |
| `generate keypad-hierarchy` | Hierarchical decimal keypad encoder |
| `generate probes` | Bus, splitter, state, and plexer probes |

Full command reference: [docs/usage.md](docs/usage.md).

## Showcase

| Circuit | Design |
| --- | --- |
| [8-to-3 priority encoder](showcase/encoder_8to3/) | Single flat gate-level circuit |
| [Decimal keypad encoder](showcase/decimal_keypad_flat/) | Large flat direct-wire circuit |
| [Hierarchical keypad encoder](showcase/decimal_keypad_hierarchical/) | Three direct-wire subcircuits |
| [16-bit ALU](showcase/alu16/) | 433 basic gates, eight operations, status flags |

Each showcase includes the `.circ`, vectors, preview, and validation record.

## Agent Integrations

- Codex: `SKILL.md` is a thin adapter over the CLI and scripts.
- Claude Code: `CLAUDE.md` points to the agent-neutral workflow.
- Cursor and other agents: use `AGENTS.md`.
- Non-agent automation: call `logisim-toolkit` or `python -m scripts.cli`.

## Repository Layout

```text
scripts/                 CLI, generators, model, checkers, validators
references/              Logisim 2.7.1 notes and capability matrix
reference/               Small component probes
examples/                Basic worked circuits
tests/                   End-to-end regression suite
showcase/                Completed large circuits
docs/usage.md            Command reference
docs/architecture.md     Model and validation architecture
AGENTS.md                Agent-neutral instructions
```

## Verification

```powershell
python -m unittest discover -s tests -v
```

The local regression includes independent simulation and real Logisim 2.7.1
checks. Public CI runs the model and CLI tests; runtime tests skip automatically
when Logisim is not available.

## Scope

The primary target is Logisim 2.7.1. RAM, ROM, arbitrary plugins, variable-input
clocked replay, and Logisim Evolution 4.x formatting remain documented
boundaries rather than implicit claims.

Bundled circuit examples may retain separate original provenance; see
[NOTICE.md](NOTICE.md).
