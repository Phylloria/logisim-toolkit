# Contributing

## Development Setup

```powershell
python -m pip install -e ".[render]"
python -m unittest discover -s tests -v
```

Use Python 3.10 or later.

## Component Support

Before adding a component to `scripts/circ_model.py`:

1. Inspect the Logisim 2.7.1 source or a tiny loaded probe.
2. Verify port anchors, width rules, facing, and optional controls.
3. Implement simulation behavior.
4. Add the component to `scripts/generate_probes.py` when practical.
5. Add a static test and a real-runtime test when Logisim is available.
6. Update `references/capability-matrix.md`.

Do not infer geometry from a visually similar component.

## Layout Changes

Generated direct-wire projects must pass all of these:

- no overlapping collinear wires,
- no dangling wire endpoints,
- no wires entering gate bodies,
- no duplicate locations,
- no unintended multiple drivers,
- no accidental endpoint-on-wire junctions.

## Validation Expectations

Keep independent-model and real-Logisim evidence separate. A static pass does
not prove Logisim compatibility, and a Logisim load does not prove behavior.

## Pull Requests

Include:

- the problem being solved,
- affected component or command,
- tests run,
- real Logisim version if runtime tests were executed,
- known boundaries or unverified cases.
