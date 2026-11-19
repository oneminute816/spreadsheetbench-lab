"""Populate month abbreviations in column B by matching a code token from column A
against the `codes2` lookup range and returning the value from the `month` range."""
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

LOOKUP_CODES = "codes2"
LOOKUP_MONTH = "month"
SOURCE_LIST = "campaigns"


def named_range(wb, name):
    """Return (sheet_title, bounds) for a workbook-scoped defined name, or None."""
    try:
        dn = wb.defined_names[name]
        destinations = list(dn.destinations)
    except (KeyError, AttributeError, ValueError):
        return None
    if not destinations:
        return None
    sheet_title, ref = destinations[0]
    if sheet_title not in wb.sheetnames or "#REF" in ref:
        return None
    return sheet_title, range_boundaries(ref)


def guess_code_table(wb):
    """Fallback: find an adjacent pair of columns looking like a code/month table."""
    months = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"}
    for ws in wb.worksheets:
        for codes_col in range(1, ws.max_column):
            codes, labels = [], []
            for row in range(1, ws.max_row + 1):
                code = ws.cell(row=row, column=codes_col).value
                label = ws.cell(row=row, column=codes_col + 1).value
                if isinstance(code, str) and code.strip().isdigit() and len(code.strip()) <= 3:
                    codes.append(row)
                    labels.append(str(label).strip().upper() if label is not None else "")
            if len(codes) >= 2 and all(lbl in months for lbl in labels):
                return (ws.title, (codes_col, codes[0], codes_col, codes[-1]),
                        ws.title, (codes_col + 1, codes[0], codes_col + 1, codes[-1]))
    return None


def main(src, dst):
    wb = openpyxl.load_workbook(src)

    codes = named_range(wb, LOOKUP_CODES)
    months = named_range(wb, LOOKUP_MONTH)
    if codes is None or months is None:
        found = guess_code_table(wb)
        if found is None:
            raise SystemExit("Could not locate the code/month lookup table")
        codes = (found[0], found[1])
        months = (found[2], found[3])

    codes_ref = f"{codes[0]}!${get_column_letter(codes[1][0])}${codes[1][1]}:" \
                f"${get_column_letter(codes[1][2])}${codes[1][3]}"
    months_ref = f"{months[0]}!${get_column_letter(months[1][0])}${months[1][1]}:" \
                 f"${get_column_letter(months[1][2])}${months[1][3]}"

    source = named_range(wb, SOURCE_LIST)
    if source is not None:
        src_sheet, bounds = source
    else:
        src_sheet = codes[0]
        sheet_col = codes[1][0] - 3 if codes[1][0] > 3 else 1
        bounds = (sheet_col, codes[1][1], sheet_col, codes[1][3])

    ws = wb[src_sheet]
    first_row, last_row = bounds[1], bounds[3]
    src_col = bounds[0]

    # A code only counts when it is a whole delimiter-separated token of the text,
    # so the "01" inside "2014_09_D2_Reminder_EN" is not mistaken for January.
    for row in range(first_row, last_row + 1):
        if ws.cell(row=row, column=src_col).value in (None, ""):
            continue
        needle = f'"_"&{codes_ref}&"_"'
        haystack = f'"_"&${get_column_letter(src_col)}{row}&"_"'
        ws.cell(row=row, column=src_col + 1).value = (
            f'=IFERROR(LOOKUP(2,1/ISNUMBER(SEARCH({needle},{haystack})),{months_ref}),"")'
        )

    wb.save(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py <input.xlsx> <output.xlsx>")
    main(sys.argv[1], sys.argv[2])
