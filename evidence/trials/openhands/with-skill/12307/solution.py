#!/usr/bin/env python3
"""Fill "No of countries" for each company: count of countries listed in Table-1
where the company employs more than 0 people."""

import os
import platform
import subprocess
import sys

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def find_layout(ws):
    """Locate Table-2 header row and Table-1 country range."""
    header_row = None
    for row in ws.iter_rows(min_row=1, max_col=ws.max_column):
        if any(isinstance(c.value, str) and c.value.strip().lower() == "company" for c in row):
            header_row = row[0].row
            break
    if header_row is None:
        raise ValueError("Could not find the 'Company' header row")

    headers = {}
    for col in range(1, ws.max_column + 1):
        v = ws.cell(row=header_row, column=col).value
        if isinstance(v, str):
            headers[v.strip()] = col

    company_col = headers["Company"]
    target_col = headers.get("No of countries")
    if target_col is None:
        target_col = max(headers.values())
    company_cols = [c for name, c in headers.items() if c not in (company_col, target_col)]
    first_data_col = min(company_cols)
    last_data_col = max(company_cols)

    country_col = company_col
    last_country_row = header_row - 1
    while last_country_row > 1 and ws.cell(row=last_country_row, column=country_col).value in (None, ""):
        last_country_row -= 1

    return header_row, target_col, country_col, last_country_row, first_data_col, last_data_col


def build_formula(header_row, first_data_col, last_col, country_col, last_country_row, row):
    hdr = f"${get_column_letter(first_data_col)}${header_row}:${get_column_letter(last_col)}${header_row}"
    countries = f"${get_column_letter(country_col)}$2:${get_column_letter(country_col)}${last_country_row}"
    data = f"{get_column_letter(first_data_col)}{row}:{get_column_letter(last_col)}{row}"
    return (
        f"=SUMPRODUCT((COUNTIF({countries},{hdr})>0)*({hdr}<>\"\")"
        f"*ISNUMBER({data})*({data}>0))"
    )


def setup_libreoffice_macro():
    base = ("~/Library/Application Support/LibreOffice/4/user/basic/Standard"
            if platform.system() == "Darwin"
            else "~/.config/libreoffice/4/user/basic/Standard")
    macro_dir = os.path.expanduser(base)
    macro_file = os.path.join(macro_dir, "Module1.xba")
    if os.path.exists(macro_file):
        with open(macro_file) as f:
            if "RecalculateAndSave" in f.read():
                return True
    os.makedirs(macro_dir, exist_ok=True)
    macro = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">\n'
             '<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" '
             'script:language="StarBasic">\n'
             '    Sub RecalculateAndSave()\n'
             '      ThisComponent.calculateAll()\n'
             '      ThisComponent.store()\n'
             '      ThisComponent.close(True)\n'
             '    End Sub\n'
             '</script:module>')
    with open(macro_file, "w") as f:
        f.write(macro)
    return True


def recalc(path):
    """Recalculate formulas so cached values are stored in the file."""
    try:
        setup_libreoffice_macro()
        cmd = ["soffice", "--headless", "--norestore",
               "vnd.sun.star.script:Standard.Module1.RecalculateAndSave"
               "?language=Basic&location=application",
               os.path.abspath(path)]
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as exc:  # keep formulas even if LibreOffice is missing
        print(f"Warning: recalculation skipped ({exc})", file=sys.stderr)


def main():
    if len(sys.argv) != 3:
        print("Usage: solution.py <input_workbook> <output_workbook>", file=sys.stderr)
        return 1

    wb = load_workbook(sys.argv[1])
    for ws in wb.worksheets:
        header_row, target_col, country_col, last_country_row, first_data_col, last_data_col = find_layout(ws)
        for row in range(header_row + 1, ws.max_row + 1):
            name = ws.cell(row=row, column=country_col).value
            if name in (None, ""):
                continue
            ws.cell(row=row, column=target_col).value = build_formula(
                header_row, first_data_col, last_data_col, country_col, last_country_row, row
            )

    wb.save(sys.argv[2])
    recalc(sys.argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
