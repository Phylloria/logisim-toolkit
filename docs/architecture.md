# Architecture

The toolkit separates generated circuit data, independent simulation, and real
Logisim execution so each layer can fail independently.

## Layers

### 1. Geometry

`scripts/logisim_geometry.py` records source-verified 2.7.1 port geometry and
splitter placement rules. Generators and checkers consume the same definitions
instead of duplicating offsets.

### 2. Native Project Generation

Generators emit native `.circ` XML with:

- Pins and component attributes,
- direct wires or intentional Tunnels,
- optional nested circuits and custom appearances,
- reference vector tables.

Generators are starting points. The XML and final artifact remain the primary
deliverables.

### 3. Bit-Level Model

`scripts/circ_model.py` resolves:

1. Component terminals and wire nets.
2. Tunnel label groups.
3. Net widths and splitter mappings.
4. Bit-level connectivity across buses and hierarchy.
5. Combinational values, splitter decode/combine, and stateful components.

This model is independent from Logisim's simulator.

### 4. Structural Checks

The checkers reject:

- overlapping collinear wires,
- free wire endpoints,
- wires entering gate bodies,
- width conflicts,
- multiple drivers,
- duplicate locations,
- unresolved text/tunnel labels where labels are required.

### 5. Real Logisim Harnesses

`validate_logisim.py` creates a temporary project copy:

- input Pins become scalar or bus Constants,
- a `halt` output stops TTY simulation,
- output values are read in Logisim's canonical top-down/left-right order.

`validate_logisim_clocked.py` additionally adds:

- a Clock source,
- a cycle Counter,
- a Comparator,
- a CYCLE output,
- a halt condition.

Clean user projects never receive these harness components.

### 6. CLI

`scripts/cli.py` exposes the stable command surface:

```text
logisim-toolkit <command> [arguments]
```

Commands forward to the same scripts used by tests and automation.

## Failure Policy

An XML parse is syntax evidence only. A model pass is independent functional
evidence. A real Logisim pass is runtime evidence. The completion report should
state which layers were actually executed.
