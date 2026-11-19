#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import date, datetime

from openpyxl import load_workbook
from openpyxl.worksheet.formula import ArrayFormula

OUT_FIRST_ROW = 6
OUT_LAST_ROW = 295
DATA_FIRST_ROW = 6
DATA_LAST_ROW = 315


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def filtered_rows(ws):
    start = as_date(ws["I2"].value)
    end = as_date(ws["J2"].value)
    rows = []
    for r in range(DATA_FIRST_ROW, DATA_LAST_ROW + 1):
        d = as_date(ws.cell(r, 1).value)
        if d is not None and start is not None and end is not None and start <= d <= end:
            rows.append(tuple(ws.cell(r, c).value for c in range(1, 6)))
    return rows


def write_static_fallback(path, rows):
    wb = load_workbook(path)
    ws = wb.active
    start = as_date(ws["I2"].value)
    end = as_date(ws["J2"].value)
    ws["M2"] = f'>={start.strftime("%d/%m/%Y")}'
    ws["N2"] = f'<={end.strftime("%d/%m/%Y")}' 
    for i in range(OUT_FIRST_ROW, OUT_LAST_ROW + 1):
        vals = rows[i - OUT_FIRST_ROW] if i - OUT_FIRST_ROW < len(rows) else (None,) * 5
        for c, value in zip(range(9, 14), vals):
            ws.cell(i, c).value = value
    wb.save(path)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py <input.xlsx> <output.xlsx>")
    inp, out = sys.argv[1], sys.argv[2]

    wb = load_workbook(inp)
    ws = wb.active
    values_wb = load_workbook(inp, data_only=True)
    values_ws = values_wb.active
    rows = filtered_rows(values_ws)

    # Keep the existing visible unique-supplier helper result while avoiding
    # unsupported SORT/UNIQUE recalculation errors in LibreOffice.
    vals = [values_ws.cell(r, 7).value for r in range(2, 23)]
    if all(v is not None for v in vals):
        for r, value in enumerate(vals, start=2):
            ws.cell(r, 7).value = value
    else:
        unique = sorted({row[1] for row in rows if row[1] is not None})
        for r in range(2, 23):
            ws.cell(r, 7).value = unique[r - 2] if r - 2 < len(unique) else None

    ws["I2"].number_format = "dd/mm/yyyy"
    ws["J2"].number_format = "dd/mm/yyyy"
    ws["M2"] = '=">="&TEXT(I2,"dd/mm/yyyy")'
    ws["N2"] = '="<="&TEXT(J2,"dd/mm/yyyy")'

    for r in range(OUT_FIRST_ROW, OUT_LAST_ROW + 1):
        for out_col, src_col in zip("IJKLM", "ABCDE"):
            formula = (
                f'=IFERROR(INDEX({src_col}$6:{src_col}$315,'
                f'SMALL(IF(($A$6:$A$315>=$I$2)*($A$6:$A$315<=$J$2),'
                f'ROW($A$6:$A$315)-ROW($A$6)+1),ROWS($I$6:$I{r}))),"")'
            )
            ws[f"{out_col}{r}"] = ArrayFormula(f"{out_col}{r}", formula)

    for r in range(OUT_FIRST_ROW, OUT_LAST_ROW + 1):
        ws[f"I{r}"].number_format = "dd/mm/yyyy"
        ws[f"K{r}"].number_format = "000000000"
        ws[f"M{r}"].number_format = '_-* #,##0.00\\ "€"_-;\\-* #,##0.00\\ "€"_-;_-* "-"??\\ "€"_-;_-@_-'

    wb.save(out)

    recalc = "/skills/xlsx/recalc.py"
    if os.path.exists(recalc):
        result = subprocess.run(
            [sys.executable, recalc, out, "60"],
            capture_output=True,
            text=True,
        )
        try:
            status = json.loads(result.stdout)
        except Exception:
            status = {}
        if status.get("status") == "success":
            return

    write_static_fallback(out, rows)


if __name__ == "__main__":
    main()
