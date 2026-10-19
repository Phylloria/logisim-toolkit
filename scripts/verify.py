"""Print Logisim 2.7.1 component statistics for one or more projects."""
from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

from validate_logisim import locate_java, locate_logisim

def run(f):
    try:
        r = subprocess.run(
            [
                str(JAVA), "-jar", str(LOGISIM), "-locale", "en",
                "-tty", "stats", str(f),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            stdin=subprocess.DEVNULL,
        )
        lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
        return f, lines
    except Exception as e:
        return f, ["ERR " + str(e)]

def main():
    global JAVA, LOGISIM
    JAVA = locate_java(os.environ.get("JAVA_EXE"))
    LOGISIM = locate_logisim(os.environ.get("LOGISIM_JAR") or os.environ.get("LOGISIM_EXE"))
    files = sys.argv[1:]
    if not files:
        files = sorted(x for x in os.listdir(".") if x.endswith(".circ"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for f, lines in ex.map(run, files):
            print(os.path.basename(f), "->", " ".join(lines)[:80])

if __name__ == "__main__":
    main()
