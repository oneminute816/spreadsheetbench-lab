#!/usr/bin/env python3
"""Count the countries from Table-1 in which each company has >0 employees.

Usage: python solution.py <input.xlsx> <output.xlsx>

Table-1 is a list of countries (column A). Table-2 has companies in column A
and country names across the header row, with employee counts in the cells.
For every company an Excel SUMPRODUCT formula is written in the "No of
countries" column.  The workbook is then recalculated by LibreOffice so the
saved result also contains the computed values.
"""

import os
import shutil
import subprocess
import sys
import tempfile

import openpyxl


def find_first_blank(values, start):
    """Return the index of the first empty value at or after start."""
    for i in range(start, len(values)):
        if values[i] in (None, ""):
            return i
    return len(values)


def main(input_path: str, output_path: str) -> None:
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    wb = openpyxl.load_workbook(input_path)
    ws = wb.active

    max_row = ws.max_row
    max_col = ws.max_column

    # Table-1: the header "Country" followed by the country names below it.
    country_header_row = None
    for row in range(1, max_row + 1):
        if str(ws.cell(row, 1).value).strip().lower() == "country":
            country_header_row = row
            break
    if country_header_row is None:
        raise ValueError("Could not find the Table-1 'Country' header")

    country_first = country_header_row + 1
    col_a_values = [ws.cell(r, 1).value for r in range(1, max_row + 1)]
    country_last = find_first_blank(col_a_values, country_first - 1)  # 0-based index
    # find_first_blank returns a 0-based index in the list, which equals the
    # 1-based row number of the first blank row.
    if country_last < country_first:
        raise ValueError("Table-1 contains no countries")

    # Table-2: find the row containing the 'Company' header.
    company_header_row = None
    for row in range(1, max_row + 1):
        if str(ws.cell(row, 1).value).strip().lower() == "company":
            company_header_row = row
            break
    if company_header_row is None:
        raise ValueError("Could not find the Table-2 'Company' header")

    # Find the result column ("No of countries" / similar) in Table-2's header.
    result_col = None
    for c in range(1, max_col + 1):
        text = str(ws.cell(company_header_row, c).value).strip().lower()
        if "no of countr" in text or text in {"countries", "country count"}:
            result_col = c
            break

    # Country columns are B through the column just before the result column
    # (or through the last non-empty header if there is no result column yet).
    first_country_col = 2
    if result_col is None:
        header_values = [
            ws.cell(company_header_row, c).value for c in range(2, max_col + 1)
        ]
        country_col_count = find_first_blank(header_values, 0)
        if country_col_count == 0:
            raise ValueError("Table-2 contains no country columns")
        last_country_col = first_country_col + country_col_count - 1
        result_col = last_country_col + 1
        ws.cell(company_header_row, result_col, "No of countries")
    else:
        last_country_col = result_col - 1
    if last_country_col < first_country_col:
        raise ValueError("Table-2 contains no country columns")

    # Company rows continue until the first blank company name.
    company_first = company_header_row + 1
    first_col_values = [ws.cell(r, 1).value for r in range(1, max_row + 1)]
    company_last = find_first_blank(first_col_values, company_first - 1)
    if company_last < company_first:
        raise ValueError("Table-2 contains no companies")

    country_range = f"$A${country_first}:$A${country_last}"
    header_range = (
        f"${openpyxl.utils.get_column_letter(first_country_col)}${company_header_row}:"
        f"${openpyxl.utils.get_column_letter(last_country_col)}${company_header_row}"
    )

    for row in range(company_first, company_last + 1):
        data_range = (
            f"{openpyxl.utils.get_column_letter(first_country_col)}{row}:"
            f"{openpyxl.utils.get_column_letter(last_country_col)}{row}"
        )
        # Count headers from Table-1 whose employee count is greater than zero.
        formula = f"=SUMPRODUCT((COUNTIF({country_range},{header_range})>0)*({data_range}>0))"
        ws.cell(row, result_col, formula)

    # Save once with openpyxl, then let LibreOffice calculate and cache the
    # formula results. If LibreOffice is unavailable, the formula-only file is
    # still valid and Excel will calculate it when opened.
    tmp_dir = tempfile.mkdtemp(prefix="xlsx_calc_")
    try:
        formula_file = os.path.join(tmp_dir, "formula.xlsx")
        wb.save(formula_file)

        converted_dir = os.path.join(tmp_dir, "converted")
        os.makedirs(converted_dir, exist_ok=True)
        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--calc",
                    "--convert-to",
                    "xlsx",
                    "--outdir",
                    converted_dir,
                    formula_file,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            converted_file = os.path.join(converted_dir, "formula.xlsx")
            if os.path.exists(converted_file):
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                shutil.move(converted_file, output_path)
            else:
                raise RuntimeError("LibreOffice did not produce an output file")
        except Exception:
            # Keep a usable formula workbook even if recalculation fails.
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            shutil.copyfile(formula_file, output_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.xlsx> <output.xlsx>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
