#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def find_country_range(ws):
    start = 2
    end = start
    while ws.cell(end + 1, 1).value not in (None, ""):
        end += 1
    return start, end


def find_employee_table(ws):
    header_row = None
    for row in range(1, ws.max_row + 1):
        if ws.cell(row, 1).value == "Company":
            header_row = row
            break
    if header_row is None:
        raise ValueError("Could not find the company employee table")

    first_country_col = 2
    last_country_col = first_country_col
    while ws.cell(header_row, last_country_col + 1).value not in (None, ""):
        last_country_col += 1
    while ws.cell(header_row, last_country_col).value == "No of countries":
        last_country_col -= 1
    return header_row, first_country_col, last_country_col


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: solution.py <input.xlsx> <output.xlsx>")

    src, dst = sys.argv[1], sys.argv[2]
    wb = load_workbook(src)
    ws = wb.active

    country_start, country_end = find_country_range(ws)
    header_row, first_col, last_col = find_employee_table(ws)
    first_letter = get_column_letter(first_col)
    last_letter = get_column_letter(last_col)

    for row in range(header_row + 1, ws.max_row + 1):
        if ws.cell(row, 1).value in (None, ""):
            continue
        ws.cell(row, 9).value = (
            f"=SUMPRODUCT(--({first_letter}{row}:{last_letter}{row}>0),"
            f"--(COUNTIF($A${country_start}:$A${country_end},"
            f"${first_letter}${header_row}:${last_letter}${header_row})>0))"
        )

    wb.save(dst)

    recalc = Path("/skills/xlsx/recalc.py")
    if recalc.exists():
        subprocess.run([sys.executable, str(recalc), dst], check=False)


if __name__ == "__main__":
    main()
