# 16-bit Gate-Level ALU

This project is a native Logisim 2.7.1 circuit built only from scalar Pins,
Tunnels, Text, and basic AND/OR/XOR/NOT gates. It does not use Logisim's
Arithmetic, Multiplexer, ROM, or other high-level functional components.

## Files

- `16bit_alu_gate_level.circ` - clean, operable Logisim project.
- `16bit_alu_gate_level_vectors.tsv` - 22 representative reference vectors.
- `16bit_alu_preview.png` - diagnostic layout preview with tunnel labels.
- `VALIDATION.md` - detailed verification evidence.

## Interface

Inputs:

- `A0..A15`, `B0..B15`
- `CIN`
- `OP2`, `OP1`, `OP0`

Outputs:

- `Y0..Y15`
- `COUT`
- `BORROW`
- `ZERO`
- `NEG`
- `OVF`

All values are scalar pins. Bit 0 is the least significant bit.

## Operations

| OP2..0 | Operation | Result |
| --- | --- | --- |
| 000 | ADD | `A + B + CIN` |
| 001 | SUB | `A - B - (1 - CIN)` |
| 010 | AND | `A & B` |
| 011 | OR | `A | B` |
| 100 | XOR | `A ^ B` |
| 101 | NOT A | `~A` |
| 110 | SHL | `(A << 1) | CIN` |
| 111 | SHR | `(A >> 1) | (CIN << 15)` |

For subtraction, `CIN=1` means no incoming borrow. `BORROW` is asserted when
the 16-bit unsigned subtraction borrows.

Flags:

- `COUT`: unsigned add carry; zero for other operations.
- `BORROW`: unsigned subtract borrow; zero for other operations.
- `ZERO`: high when all 16 result bits are zero.
- `NEG`: the result sign bit, `Y15`.
- `OVF`: signed two's-complement overflow for ADD/SUB only.

## Structure

- 433 basic gates.
- 1343 labeled Tunnel components for the large netlist.
- 1343 short orthogonal wire stubs.
- One 16-stage ripple carry chain.
- One-hot operation decoding.
- Eight-way result selection implemented as four OR-pair stages, two OR stages,
  and one final OR per result bit.
- Gate-built zero, carry, borrow, negative, and overflow logic.

The circuit is laid out as one horizontal gate pipeline per result bit. Named
Tunnels carry the long-distance nets so that the diagram remains scrollable and
inspectable without a dense web of crossing wires.

## Open

Open `16bit_alu_gate_level.circ` in Logisim 2.7.1, select the `main` circuit,
and use the Poke tool to set input pins. The clean project contains no `halt`
pin or validation-only stimuli.

## Verification Summary

- A 2-bit generated variant passed all 256 scalar input combinations in the
  independent static checker.
- The 16-bit project passed all 22 representative vectors in the independent
  static checker.
- The same 16-bit vectors passed in real Logisim 2.7.1 through generated
  Power/Ground halt harnesses.
- The circuit contains no arithmetic, multiplexer, ROM, or hidden halt
  components.

An exhaustive 16-bit test would require `2^36` input combinations, so the
large circuit uses representative arithmetic, carry, borrow, overflow, logic,
shift, zero, and sign vectors rather than an exhaustive table.
