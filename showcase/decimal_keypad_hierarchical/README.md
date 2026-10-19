# Hierarchical Decimal Keypad Priority Encoder

This Logisim 2.7.1 project uses four circuits and only direct orthogonal
wires. It contains zero Tunnel components and zero high-level encoder,
multiplexer, or arithmetic components.

## Hierarchy

`main` contains only:

- Ten top-level input Pins: `K0..K9`.
- One `PriorityStage` instance.
- One `TermStage` instance.
- One `BCDStage` instance.
- Five top-level output Pins: `B0..B3` and `VALID`.
- 43 direct orthogonal wires.

The data path is:

```text
K0..K9 -> PriorityStage -> TermStage -> BCDStage -> B0..B3
                    \-----------------------------> VALID
```

Connections between every pair of hierarchy levels are direct wires attached
to custom subcircuit ports.

## Where Are The Gates?

`main` intentionally contains no gates. It is the top-level interface and
hierarchy sheet, so it shows three subcircuit symbols connected by wires.

To inspect the implementation in Logisim:

1. Open `keypad_priority_encoder_hierarchical.circ`.
2. Double-click `PriorityStage`, `TermStage`, or `BCDStage` on the `main`
   canvas.
3. Alternatively, double-click the same circuit name in Logisim's circuit
   list/explorer.

The gate locations are:

- `PriorityStage`: 17 OR/NOT gates for the suffix priority scan.
- `TermStage`: 8 AND gates for per-digit term selection.
- `BCDStage`: 4 OR gates for BCD output combination.

## Internal Circuits

`PriorityStage`

- Builds the suffix priority chain `S0..S8`.
- Produces the higher-key suppression signals `H1..H8`.
- Forwards `K1..K9` to the next stage.
- Produces `VALID`.

`TermStage`

- Selects one BCD-relevant digit at a time:

```text
T1 = K1 AND H1
...
T8 = K8 AND H8
T9 = K9
```

`BCDStage`

- Combines the selected terms into `B0..B3`.
- Uses four multi-input OR gates with direct input routing.

## Interface

- `K0..K9`: active-high keys. `K9` has the highest priority.
- `B0..B3`: active-high BCD result, with `B0` as the least significant bit.
- `VALID`: high when at least one key is pressed.

If several keys are pressed, the highest-numbered pressed key wins. When no key
is pressed, `VALID=0` and the BCD value is `0000`.

## Inventory

- Circuits: 4.
- Basic gates: 29.
- Total components: 116.
- Total wires: 263.
- Main-level components: 20.
- Tunnel components: 0.

## Files

- `keypad_priority_encoder_hierarchical.circ` - the complete project.
- `keypad_priority_encoder_hierarchical_exhaustive.tsv` - all 1024 vectors.
- `keypad_priority_encoder_hierarchical_smoke.tsv` - 19 runtime vectors.
- `hierarchical_main_preview.png` - top-level hierarchy and direct wiring.
- `priority_stage_preview.png` - priority-stage internals.
- `term_stage_preview.png` - term-selection internals.
- `bcd_stage_preview.png` - BCD-combination internals.
- `VALIDATION.md` - verification record.
