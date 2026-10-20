# Direct-Wire Routing

Read this reference when Tunnels or encapsulation are forbidden, or when a
gate-level circuit must remain readable as one flat diagram.

## Required Invariants

- Use orthogonal wires on the 10-unit grid.
- Keep every component anchor and gate terminal on the grid before routing.
- One logical net has one source and one routed tree.
- Split a long wire at every same-net T junction. Do not leave an endpoint on
  the interior of a long segment.
- Separate collinear wires from different nets. Perpendicular crossings are
  allowed only when neither wire turns or ends at the crossing.
- Keep all functional top-level input Pins non-tristate.
- Create escape stubs only for terminals that occur in a routed net.

`route_stage` runs these checks before and after routing. `check_circ.py` and
the universal model also report off-grid coordinates and implicit T junctions.

## Choose A Routing Mode

### Maze Routing

Use `route_stage` when the circuit has no obvious column structure.

- Prefer `WireNet(name, terminals)` over anonymous point lists.
- Set `preferred_bend_cost` according to layout density:
  - `16–20` for open, column-oriented logic.
  - `6–8` for dense fanout grids.
- The router retries failed nets with multiple sink orders, lowers bend cost,
  and performs one bounded low-fanout rip-up/reroute.
- Enable `corridor_mode` only when measured wire and bend counts improve. It
  biases vertical runs toward gaps between gate columns but does not allocate
  dedicated signal lanes.

Diagnostics:

- `1 state` usually means the target escape is blocked, reserved, or non-grid.
- Hundreds of thousands of states usually means channel congestion or a sink
  ordering problem.
- A failure names the logical net when `WireNet` is used.

### Layout-Time Corridors

Use this mode for priority encoders, staged datapaths, and other logic that can
be divided into narrow dependency columns.

Build the layout in two tiers:

1. **Local lane groups:** one group immediately before each target gate column.
   Add every signal entering that layer, whether it came from a top-level Pin
   or from an earlier gate output.
2. **Bypass tracks:** signals that skip one or more layers take one top or
   bottom track and drop only at their target layers.

Do not carry a skipped signal through every intermediate lane group. Do not
widen all channels merely because a long-lived signal crosses them.

`corridor_planner.assign_interval_tracks()` can pack tracks:

- Local lanes may share an x-coordinate when their vertical intervals do not
  touch.
- Bypass tracks may share a y-coordinate when their horizontal spans do not
  overlap.
- Touching intervals must not share because the shared point can become an
  accidental junction.

For a compact layout, size each inter-column gap from the number of lanes that
actually enter the next layer, plus a small margin. Do not leave uniform large
gaps between every pair of columns.

## Layout Recipe

1. Partition gates into dependency columns.
2. Place each column in a regular vertical order.
3. Identify signals entering each target column.
4. Assign local lanes in the gap immediately before the column.
5. Assign bypass tracks only to signals that skip layers.
6. Route Pin-to-first-layer and gate-to-next-layer connections with short local
   paths; use bypass only for skips.
7. Route any remaining irregular nets with `route_stage`.
8. Run XML parsing, structural checks, exhaustive or representative vectors,
   and real Logisim.

## Worked Measurements

- 9-key staged corridor encoder: 31 gates, 191 wires, 1490 x 910 footprint.
  The single-column reference uses 213 wires and 1360 x 4840.
- 4-bit CLA with corridor-aware maze routing: 326 wires, 196 bend/junction
  points.
- 256-gate stress netlist with corridor mode: 2581 wires, 1752 bend/junction
  points.

Use these as regression targets, not mandatory layouts. If a corridor change
increases both wire count and bend count, keep the simpler existing route.

## Related Tools

- `scripts/direct_router.py` - orthogonal maze router and rip-up/reroute.
- `scripts/corridor_planner.py` - interval-colored corridor tracks.
- `scripts/generate_hierarchical_keypad.py` - `route_stage` implementation and
  grid validation.
- `scripts/generate_corridor_priority9.py` - complete staged-corridor example.
- `scripts/generate_stress_256.py` - large direct-wire regression.
