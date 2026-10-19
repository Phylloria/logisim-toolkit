# Logisim Validation

## Bundled Validation Path

Use the bundled scripts for scalar gate-level projects:

```powershell
python scripts\check_circ.py path\to\design.circ --table path\to\vectors.tsv
python scripts\validate_logisim.py path\to\design.circ `
  --table path\to\vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe
```

`check_circ.py` is an independent XML/netlist simulator. It joins duplicate
Tunnel labels, checks floating terminals, multiple drivers, duplicate component
locations, gate-body overlap, and compares reference vectors.

For buses, splitters, hierarchy, stateful components, and high-level
arithmetic/plexers, use `check_universal.py`; `check_circ.py` remains the
smaller scalar-gate diagnostic.

`validate_logisim.py` performs the actual runtime check. For each vector it
creates a temporary project copy, replaces input Pins with scalar or bus
Constant components, adds a `halt` output, and invokes Logisim in TTY mode. The
clean source project is not modified.

## Clean Circuit And Harness Pattern

Keep two artifacts when possible:

- Clean circuit: intended for the user to open and operate. It should not contain validation-only counters, `halt` outputs, or hidden fixed stimuli unless they are part of the actual design.
- Harness circuit: generated copy used for CLI validation. It may include a clock source, stimulus constants, comparators, counters, and a `halt` pin so Logisim exits.

The generated harness pattern is:

```powershell
java -jar C:\Logisim\logisim-win-2.7.1.exe -locale en -tty table path\to\harness.circ
```

The `halt` output Pin must be driven high after the combinational values have
propagated. A successful scalar run prints one whitespace-separated output row.
If a 2.7.1 table run has no `halt`, it can keep the TTY simulation loop alive
after printing the first row.

Use a console `java.exe`. Do not launch the Windows GUI wrapper through
`javaw.exe` and expect redirected stdout; the wrapper can detach from the
capturing process.

For sequential circuits, `validate_logisim_clocked.py` replaces the named clock
Pin with a Clock, adds a cycle Counter/Comparator and halt Pin, and compares
the runtime cycle sequence with the independent model.

## Java And JAR Setup

Confirm the runtime:

```powershell
java -version
java -jar C:\Logisim\logisim-win-2.7.1.exe -version
```

The repository may also contain a plain JAR:

```powershell
java -jar tools\logisim-generic-2.7.1.jar -version
```

If `java` is not on PATH on Windows, pass an explicit path:

```powershell
python scripts\validate_logisim.py design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe `
  --java "C:\Program Files\Java\jre1.8.0_503\bin\java.exe"
```

Do not download or replace the user's runtime unless they explicitly authorize
it.

## Timeouts

If a CLI run hangs:

1. Check whether the circuit has a reachable `halt` condition.
2. Check whether a manual input Pin accidentally touches the clock or another control net.
3. Check whether Text components use `lib="6"` rather than Wiring library ids.
4. Stop only Java processes related to the active workspace, not arbitrary system Java processes.

Example cleanup pattern:

```powershell
Get-CimInstance Win32_Process -Filter "Name='java.exe' OR Name='javaw.exe'" |
  Where-Object { $_.CommandLine -like '*logisim*' -and $_.CommandLine -like '*\examples\*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```
