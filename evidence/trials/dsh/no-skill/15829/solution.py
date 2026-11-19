#!/usr/bin/env python3
"""Fill the monthly-fee lookup formula in cell B3 and save the workbook.

Usage:
    python solution.py <input workbook> <output workbook>

The formula uses SUMIFS so that it:
  * selects rows whose Tariff Code matches the tariff in B2;
  * checks that the usage in B1 is between the row's minimum and maximum; and
  * adds the matching Additional Monthly Fee.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def normalized(value: object) -> str:
    """Normalize a header for tolerant matching."""
    if value is None:
        return ""
    return " ".join(str(value).replace("_", " ").split()).lower()


def find_column(ws, header_names: tuple[str, ...], fallback: int) -> int:
    """Find a column from its header in the first row, or use a fallback."""
    headers: dict[str, int] = {}
    for cell in ws[1]:
        # Keep the first occurrence: some worksheets contain a duplicate
        # validation list later in the same header row.
        headers.setdefault(normalized(cell.value), cell.column)
    for name in header_names:
        col = headers.get(normalized(name))
        if col is not None:
            return col
    return fallback


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {Path(sys.argv[0]).name} INPUT.xlsx OUTPUT.xlsx")

    input_path = Path(sys.argv[1]).expanduser().resolve()
    output_path = Path(sys.argv[2]).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(input_path)
    ws = wb.active

    # Locate the lookup table's columns. The source workbook has the table in
    # columns F:I, but looking them up by header keeps the formula adaptable.
    tariff_col = find_column(ws, ("Tariff Code",), 6)
    min_col = find_column(ws, ("Usage Range min.", "Usage Range min"), 7)
    max_col = find_column(ws, ("Usage Range max.", "Usage Range max"), 8)
    fee_col = find_column(ws, ("Additional Monthly Fee",), 9)

    # Include all populated data rows in the lookup table.
    last_data_row = max(ws.max_row, 2)
    while last_data_row > 2 and all(
        ws.cell(row=last_data_row, column=col).value is None
        for col in (tariff_col, min_col, max_col, fee_col)
    ):
        last_data_row -= 1

    tariff_rng = f"${get_column_letter(tariff_col)}$2:${get_column_letter(tariff_col)}${last_data_row}"
    min_rng = f"${get_column_letter(min_col)}$2:${get_column_letter(min_col)}${last_data_row}"
    max_rng = f"${get_column_letter(max_col)}$2:${get_column_letter(max_col)}${last_data_row}"
    fee_rng = f"${get_column_letter(fee_col)}$2:${get_column_letter(fee_col)}${last_data_row}"

    # B2 is the selected tariff and B1 is the usage. SUMIFS cross-references
    # both criteria against the tariff table and returns the matching fee.
    ws["B3"] = (
        f'=SUMIFS({fee_rng},{tariff_rng},$B$2,'
        f'{min_rng},"<="&$B$1,{max_rng},">="&$B$1)'
    )

    # Save first, then let LibreOffice recalculate so the workbook also stores
    # the formula's cached result (e.g. 500) for readers that do not calculate.
    with tempfile.TemporaryDirectory(prefix="tariff_calc_") as tmp:
        tmp = Path(tmp)
        temp_input = tmp / "workbook.xlsx"
        recalc_dir = tmp / "recalculated"
        recalc_dir.mkdir()
        wb.save(temp_input)

        libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
        if libreoffice:
            subprocess.run(
                [
                    libreoffice,
                    "--headless",
                    "--calc",
                    "--convert-to",
                    "xlsx",
                    "--outdir",
                    str(recalc_dir),
                    str(temp_input),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            recalculated = recalc_dir / temp_input.name
            if recalculated.exists():
                shutil.copyfile(recalculated, output_path)
                return

        # Fallback: save the formula even if LibreOffice is unavailable.
        wb.save(output_path)


if __name__ == "__main__":
    main()
