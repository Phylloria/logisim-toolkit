# Toolkit Usage

## Commands

```text
logisim-toolkit check              Universal bus/sequential model
logisim-toolkit check-scalar       Scalar basic-gate diagnostic
logisim-toolkit check-hierarchy    Legacy hierarchy-only checker
logisim-toolkit validate           Real Logisim combinational/bus vectors
logisim-toolkit validate-clocked   Real Logisim fixed-input clock sequence
logisim-toolkit stats              Runtime component statistics
logisim-toolkit render             Diagnostic layout PNG
logisim-toolkit generate alu
logisim-toolkit generate cla-4bit
logisim-toolkit generate keypad
logisim-toolkit generate keypad-flat
logisim-toolkit generate keypad-hierarchy
logisim-toolkit generate encoder-8to3
logisim-toolkit generate encoder-9-corridor
logisim-toolkit generate multiplier-4x4
logisim-toolkit generate stress-256
logisim-toolkit generate probes
logisim-toolkit list-tools
```

Every command forwards its remaining arguments to the corresponding script:

```powershell
logisim-toolkit check design.circ --table vectors.tsv --require-exhaustive
logisim-toolkit generate alu --bits 16 --out alu.circ
logisim-toolkit render alu.circ alu.png 3200
```

## Runtime Discovery

Real Logisim commands accept explicit paths:

```powershell
logisim-toolkit validate design.circ --table vectors.tsv `
  --logisim C:\Logisim\logisim-win-2.7.1.exe `
  --java "C:\Program Files\Java\jre1.8.0_503\bin\java.exe"
```

Environment alternatives:

- `LOGISIM_JAR` or `LOGISIM_EXE`
- `JAVA_EXE`

## Table Values

Tables are UTF-8 TSV files. Inputs and outputs use Pin labels as headers.

Accepted values:

- `0` and `1`
- Plain binary with exactly the Pin width, such as `0101`
- `0b0101`
- `0x1f`
- Decimal

## CI Pattern

```powershell
python -m pip install .
logisim-toolkit check design.circ --table vectors.tsv --require-exhaustive
```

Keep real-Logisim tests conditional in public CI unless the runner provides a
licensed/local Logisim runtime.
