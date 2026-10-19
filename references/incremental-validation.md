# Incremental Logisim Validation

This procedure is the default for large or hierarchical projects.

## Checkpoints

Keep these checkpoints as separate files while developing:

1. `probe-hierarchy.circ`: parent plus one child and matching Pins.
2. `probe-bus.circ`: one multi-bit Pin, Splitter/Joiner, and explicitly checked bit mapping.
3. `probe-block.circ`: one verified functional block with a small reference table.
4. `design.circ`: the clean user-facing project.
5. `harness.circ`: optional validation copy with fixed stimuli, expected values, and halt logic.

Each checkpoint must load in the target Logisim version before the next checkpoint is built.

For the bundled flat gate-level regression:

```powershell
python scripts\generate_alu.py --bits 2 --exhaustive-table --out work\alu2.circ
python scripts\check_circ.py work\alu2.circ --table work\alu2_vectors.tsv --require-exhaustive
python scripts\validate_logisim.py work\alu2.circ --table work\alu2_vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe --limit 8
```

Use 2 to 3 bits for exhaustive regression and the default 16-bit design for
loading, layout, carry-chain, selector, flag, and representative-vector
coverage.

## Universal Bus And Sequential Probes

```powershell
python scripts\generate_probes.py --out-dir work\probes
python scripts\check_universal.py work\probes\probe_bus_gate.circ `
  --table work\probes\probe_bus_gate_vectors.tsv
python scripts\check_universal.py work\probes\probe_splitter.circ `
  --table work\probes\probe_splitter_vectors.tsv
python scripts\check_universal.py work\probes\probe_register.circ `
  --table work\probes\probe_register_sequence.tsv --sequential
python scripts\validate_logisim_clocked.py work\probes\probe_register.circ `
  --clock CLK --cycles 4 --input D=5 --input CLR=0 --input EN=1
```

The probes cover bus-width gates, splitter decode/combine, wide
adder/comparator/multiplexer components, and register state with reset, enable,
and rising-edge updates.

## Failure Isolation

If loading or `-tty stats` hangs, compare against the previous checkpoint and remove one class of content at a time: harness-only components, child instances, component attributes, functional components, and wires. Save the smallest reproducer. A successful XML parse does not imply that Logisim accepts the project.

For Logisim 2.7.1 Splitter probes, start with only `<a name="fanout" val="N"/>`. Do not invent `incoming`, `bit0`, or `bit1` attributes. Confirm splitter orientation and branch coordinates from a loaded probe before adding bus routing.

## Evidence Levels

- XML parse: syntax only.
- Structural checker: component, port, wire, and driver evidence for the supported subset.
- Runtime load: Logisim recognized the project.
- Vector or truth-table run: behavior evidence for the exercised inputs.
- Exhaustive/reference-model comparison: strong combinational evidence for the tested interface.

Report these levels separately. Never promote a lower level to a functional claim.
