#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook


FORMULA = (
    '=SUMIFS($I$2:$I$22,$F$2:$F$22,$B$2,'
    '$G$2:$G$22,"<="&$B$1,$H$2:$H$22,">="&$B$1)'
)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: solution.py <input.xlsx> <output.xlsx>")

    input_path, output_path = map(Path, sys.argv[1:3])
    wb = load_workbook(input_path)
    ws = wb.active
    ws["B3"] = FORMULA
    wb.save(output_path)

    recalc = Path("/skills/xlsx/recalc.py")
    if recalc.exists():
        subprocess.run(
            [sys.executable, str(recalc), str(output_path)],
            check=False,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    main()
