# Staged-Corridor 9-Key Priority Encoder

This is a compact corridor-routed alternative to the single-column `prio9`
layout. It preserves the active-low BCD interface and adds no Tunnels or
subcircuits.

## Interface

- Inputs: `I1..I9`, active high. `I9` has the highest priority.
- Outputs: `nD3..nD0`, active-low BCD digit.
- When no input is active, all four outputs are high.

## Corridor Organization

The logic is split into five narrow columns:

1. `HIGH` OR gates suppress all higher-priority keys.
2. `N` NOT gates create the per-key select conditions.
3. `T` AND gates create one term per key.
4. `D` OR gates generate the four BCD bits.
5. `ND` NOT gates produce the active-low output pins.

Input signals use a top distribution corridor and drop into a dedicated lane
immediately before the target gate column. Lanes are local to one column rather
than running through the complete circuit. The `T` terms use a second short
lane group before the BCD gates.

Signals that cross multiple layers keep one bypass track and drop only at their
target layers. Lane and track positions use interval packing, so non-touching
vertical spans may share an x-coordinate and non-overlapping bypass spans may
share a y-coordinate.

## Size Comparison

| Layout | Gates | Wires | Footprint |
| --- | ---: | ---: | --- |
| Single-column reference | 29 | 213 | 1360 x 4840 |
| Staged corridors | 31 | 191 | 1490 x 910 |

The staged layout uses two extra gates but reduces wire count and circuit area
by about 79% compared with the single-column reference.

## Files

- `priority9_staged_corridor.circ`
- `priority9_staged_corridor_vectors.tsv` - all 512 input masks.
- `priority9_staged_corridor_preview.png`
- `VALIDATION.md`
