# 256-Gate Direct-Wire Stress Netlist

This project is a synthetic combinational scale regression for the direct-wire
router and validators. It is not intended as a computational showcase; its
purpose is to exercise 256 connected gates and more than 2700 wire segments
without hiding connectivity behind Tunnels or subcircuits.

## Structure

- 32 logic columns.
- 8 rows per column.
- 256 two-input basic gates total.
  - 96 AND gates.
  - 96 XOR gates.
  - 64 OR gates.
- 16 scalar input Pins.
- 4 scalar output Pins.
- 2705 direct orthogonal wire segments.
- 0 Tunnels.
- 0 subcircuits.
- No high-level components.

The first column draws from all 16 inputs. Each later column combines its
previous-column neighbors, creating repeated fanout and many local routing
channels. The measured component-and-wire footprint is 7560 by 950 circuit
units.

## Files

- `stress_256_gate_level.circ` - Logisim 2.7.1 project.
- `stress_256_vectors.tsv` - 68 deterministic reference vectors.
- `stress_256_preview.png` - diagnostic full-netlist preview.
- `VALIDATION.md` - verification record.

## Generate

```powershell
logisim-toolkit generate stress-256 --out stress256.circ
logisim-toolkit check stress256.circ --table stress256_vectors.tsv
```
