# Logisim 2.7.1 Circuit Authoring

## Project Header

Use Logisim 2.7.1 compatible XML. Include the libraries actually used. For Text notes, the Base library must be present.

```xml
<project source="2.7.1" version="1.0">
  <lib desc="#Wiring" name="0"/>
  <lib desc="#Gates" name="1"/>
  <lib desc="#Plexers" name="2"/>
  <lib desc="#Arithmetic" name="3"/>
  <lib desc="#Memory" name="4"/>
  <lib desc="#I/O" name="5"/>
  <lib desc="#Base" name="6">
    <tool name="Text Tool">
      <a name="text" val=""/>
      <a name="font" val="SansSerif plain 12"/>
      <a name="halign" val="center"/>
      <a name="valign" val="base"/>
    </tool>
  </lib>
  <main name="main"/>
  <circuit name="main">
```

## Common XML Snippets

Input Pin:

```xml
<comp lib="0" loc="(120,180)" name="Pin">
  <a name="facing" val="east"/>
  <a name="tristate" val="false"/>
  <a name="width" val="4"/>
  <a name="label" val="input_name"/>
  <a name="labelloc" val="west"/>
</comp>
```

Output Pin:

```xml
<comp lib="0" loc="(520,180)" name="Pin">
  <a name="facing" val="west"/>
  <a name="output" val="true"/>
  <a name="width" val="4"/>
  <a name="label" val="output_name"/>
  <a name="labelloc" val="east"/>
</comp>
```

Facing convention:

- Module inputs normally sit to the left of the logic and face right: `facing="east"`.
- Module outputs normally sit to the right of the logic and face left: `facing="west"`.
- Apply this per sub-block, not only for the whole page. A left-side input for an ALU section faces east even if the whole page has other blocks around it.

On-canvas Text:

```xml
<comp lib="6" loc="(260,70)" name="Text">
  <a name="text" val="Explain the signal or datapath here."/>
  <a name="font" val="SansSerif plain 12"/>
  <a name="halign" val="left"/>
  <a name="valign" val="base"/>
</comp>
```

Wire:

```xml
<wire from="(120,180)" to="(220,180)"/>
```

Subcircuit instance:

```xml
<comp loc="(520,220)" name="ALU_CORE"/>
```

Custom appearance outline:

```xml
<appear>
  <rect fill="none" height="120" stroke="#000000" stroke-width="2" width="80" x="50" y="50"/>
  <circ-port height="8" pin="80,120" width="8" x="46" y="66"/>
  <circ-port height="10" pin="850,240" width="10" x="125" y="85"/>
  <circ-anchor facing="east" height="6" width="6" x="127" y="87"/>
</appear>
```

The `circ-port pin` coordinate must match the actual Pin location inside that subcircuit.

## Port Anchors

Use `data/logisim27-components.json` or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\component-port.ps1 RAM 500 220
```

Important offsets:

- ROM/RAM `loc` is DATA. ADDR is `(-140,0)`, CS is `(-90,+40)`.
- Register `loc` is Q. D is `(-30,0)`, CLK is `(-20,+20)`, CLR is `(-10,+20)`, EN is `(-30,+10)`.
- Counter `loc` is Q. D is `(-30,0)`, CLK is `(-20,+20)`, LOAD is `(-30,-10)`, COUNT is `(-30,+10)`.
- Adder `loc` is OUT. IN0 is `(-40,-10)`, IN1 is `(-40,+10)`, C_IN is `(-20,-20)`.
- Comparator `loc` is EQ. IN0 is `(-40,-10)`, IN1 is `(-40,+10)`, GT/EQ/LT are `(0,-10)/(0,0)/(0,+10)`.
- 2-input Multiplexer `loc` is OUT. IN0 is `(-30,-10)`, IN1 is `(-30,+10)`, SELECT is `(-20,+20)`, ENABLE is `(-10,+20)`.

Default east-facing basic gates use `loc` as the output terminal and
`size=50`. Their input-terminal x offsets are source-verified as:

| Gate | Input x offset | 2-input y offsets |
| --- | ---: | --- |
| AND | -50 | -20, +20 |
| OR | -50 | -20, +20 |
| XOR | -60 | -20, +20 |
| NAND | -60 | -20, +20 |
| NOR | -60 | -20, +20 |
| XNOR | -70 | -20, +20 |
| NOT | -30 | 0 |

The XOR symbol adds 10 units of width. NAND, NOR, and XNOR also reserve 10
units for output negation; XNOR reserves both 10-unit increments. Do not draw
an XOR input wire to `x-50`: it terminates 10 units inside the symbol and can
look connected while being visually over-extended.

## Layout Heuristics

- Treat Pins, Tunnels, Probes, and Text as visible boxes. Do not layout by port coordinate alone.
- A visible input/output Pin generally consumes at least two grid positions. Multi-bit Pins with value boxes consume more horizontal width and need extra vertical clearance.
- Never stack visible Pins, Tunnels, or labels at one-grid pitch. Use at least two grid positions for tiny 1-bit items and three to four grid positions for multi-bit Pins or labels such as `RESULT`, `ADD_CARRY`, `expected`, or mux input names.
- For dense component ports such as mux inputs or RAM controls, put visible labels/Pins in a breakout area away from the component with wider spacing, then connect to the dense component ports with short stubs.
- Put user inputs on the left or below, outputs on the right or separated lanes, with facing set toward the local logic.
- Leave open space around wide data buses and multi-bit Pin value boxes.
- Move outputs to a different lane instead of letting labels overlap a RAM/ROM data display.
- Route control feedback above or below the datapath and drop into ports with short vertical stubs.
- Cross wires only in open space.
- For complex deliverables, keep `main` sparse and move repeated gates, bit-slices, and bus
  splitting into subcircuits with custom appearances.

## Constants And Manual Inputs

Be strict about constants:

- Do not replace user-operable functional inputs with constants just to make a demo run.
- For adders and ALUs, `A`, `B`, `cin`, `bin`, operation select, result select, carry-chain inputs, borrow-chain inputs, and compare inputs should be input Pins or driven by earlier logic.
- Carry-out and borrow-out are outputs, not labels for hidden fixed input values.
- Constants are appropriate for fixed design facts, such as increment-by-1, a ROM-programmed value, an address base required by the specification, or validation harness stimuli.
- If a control pin is default-enabled in Logisim and the circuit should always be enabled, leave it unconnected rather than adding a constant `1`.
- If the user needs to operate a control signal, expose it as a Pin even if a test harness later fixes it.

For a 2.7.1 `Constant` component, write the value as a hexadecimal string with
an explicit prefix:

```xml
<comp lib="0" loc="(100,100)" name="Constant">
  <a name="facing" val="east"/>
  <a name="width" val="8"/>
  <a name="value" val="0xa5"/>
</comp>
```

Using `val="0"` for the value can leave Logisim waiting in a hidden load-error
dialog instead of starting TTY simulation.

## Splitter Geometry

For an east-facing 2.7.1 Splitter, `loc` is the combined bus terminal. Branch
ends are at `x+20` with 10-unit vertical spacing. The default `appear` mode is
`left`; `right` and `legacy` place the fanout differently.

The incoming bus width is stored as `incoming`. `bitN` attributes map each bus
bit to a one-based branch end; `none` or `0` leaves that bit unconnected.
Default distribution is contiguous from branch 1 upward. Splitter ends are
bidirectional, so the same component supports decode and combine.

## TTY Table Ordering

Logisim 2.7.1 prints output Pins in canonical graphical order:

1. Increasing `y`.
2. Increasing `x` for equal `y`.

The order is not XML component order. Bus values may be rendered as groups of
four binary digits separated by spaces. Harness parsers must reconstruct values
using each output Pin's declared width.
