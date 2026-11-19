#!/usr/bin/env python3
"""Filter rows by the inclusive date range in I2:J2 and extract them to I6:M295."""
from __future__ import annotations

import copy
import datetime as dt
import html
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils import get_column_letter


DATA_FIRST_ROW = 6
DATA_LAST_ROW = 315
OUT_FIRST_ROW = 6
OUT_LAST_ROW = 295


def to_date(value: Any) -> dt.datetime | None:
    """Return a datetime for an Excel date, Excel serial, or common date string."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        # Excel's 1900 date-system conversion.  The workbook uses ordinary dates.
        try:
            return openpyxl.utils.datetime.from_excel(float(value))
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return dt.datetime.strptime(text, fmt)
            except ValueError:
                pass
    return None


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py INPUT.xlsx OUTPUT.xlsx")

    input_path, output_path = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active

    start = to_date(ws["I2"].value)
    end = to_date(ws["J2"].value)
    if start is None or end is None:
        raise ValueError("Cells I2 and J2 must contain valid start and end dates")
    if end < start:
        start, end = end, start

    # Collect matching rows from the source data range A6:E315.
    matches = []
    for row in range(DATA_FIRST_ROW, DATA_LAST_ROW + 1):
        row_date = to_date(ws.cell(row=row, column=1).value)
        if row_date is not None and start <= row_date <= end:
            matches.append(row)

    # Clear all destination cells in the requested output area so no stale data
    # remains if the script is rerun with different criteria.
    for row in ws.iter_rows(
        min_row=OUT_FIRST_ROW, max_row=OUT_LAST_ROW, min_col=9, max_col=13
    ):
        for cell in row:
            cell.value = None

    # Write the filtered records, preserving the source values and number formats.
    for out_row, src_row in enumerate(
        matches[: OUT_LAST_ROW - OUT_FIRST_ROW + 1], start=OUT_FIRST_ROW
    ):
        for out_col, src_col in zip(range(9, 14), range(1, 6)):
            src = ws.cell(row=src_row, column=src_col)
            dst = ws.cell(row=out_row, column=out_col)
            dst.value = src.value
            dst.number_format = src.number_format
            dst.font = copy.copy(src.font)
            dst.fill = copy.copy(src.fill)
            dst.border = copy.copy(src.border)
            dst.alignment = copy.copy(src.alignment)
            dst.protection = copy.copy(src.protection)

    # Make the start/end criteria and the extracted date column unambiguous and
    # readable.  The helper criteria in M2:N2 must use TEXT; otherwise Excel
    # concatenates the underlying date serial (e.g. >=45007) rather than a date.
    for coord in ("I2", "J2"):
        ws[coord].number_format = "dd/mm/yyyy"
    for row in range(OUT_FIRST_ROW, OUT_FIRST_ROW + len(matches)):
        ws.cell(row=row, column=9).number_format = "dd/mm/yyyy"

    ws["M2"] = '=">="&TEXT(I2,"dd/mm/yyyy")'
    ws["N2"] = '="<="&TEXT(J2,"dd/mm/yyyy")'

    # Keep the saved print/calculation state sensible for Excel.
    wb.calculation.fullCalcOnLoad = True
    wb.save(output_path)

    # openpyxl stores formulas without a cached result.  Store the two helper
    # formula results as cached strings too, so readers that use data_only=True
    # see the same readable criteria that Excel displays after recalculation.
    readable_start = start.strftime("%d/%m/%Y")
    readable_end = end.strftime("%d/%m/%Y")
    _set_cached_formula_results(
        output_path,
        {
            "M2": f">={readable_start}",
            "N2": f"<={readable_end}",
        },
    )


def _set_cached_formula_results(workbook_path: str, results: dict[str, str]) -> None:
    """Insert cached string results for formula cells in the first worksheet.

    This is deliberately a small XML patch rather than a second workbook
    round-trip: openpyxl has no public API for writing a formula and its cached
    value at the same time.
    """
    import os
    import tempfile

    with zipfile.ZipFile(workbook_path, "r") as zin:
        names = zin.namelist()
        sheet_name = next(
            (n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            None,
        )
        if sheet_name is None:
            return
        sheet_xml = zin.read(sheet_name).decode("utf-8")

        for coord, result in results.items():
            pattern = re.compile(
                rf'(<c r="{re.escape(coord)}"(?P<attrs>[^>]*)>)(?P<body>.*?)(</c>)',
                re.DOTALL,
            )
            match = pattern.search(sheet_xml)
            if not match:
                continue
            attrs = match.group("attrs")
            if " t=" not in attrs:
                attrs += ' t="str"'
            escaped = html.escape(result, quote=False)
            body = re.sub(r"<v\s*/>|<v>.*?</v>", f"<v>{escaped}</v>",
                          match.group("body"), flags=re.DOTALL)
            replacement = f'<c r="{coord}"{attrs}>{body}</c>'
            sheet_xml = sheet_xml[:match.start()] + replacement + sheet_xml[match.end():]

        fd, tmp_name = tempfile.mkstemp(
            prefix=".cached-results-", suffix=".xlsx",
            dir=os.path.dirname(os.path.abspath(workbook_path)) or None,
        )
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp_name, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = (
                        sheet_xml.encode("utf-8")
                        if item.filename == sheet_name
                        else zin.read(item.filename)
                    )
                    zout.writestr(item, data)
            os.replace(tmp_name, workbook_path)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)


if __name__ == "__main__":
    main()
