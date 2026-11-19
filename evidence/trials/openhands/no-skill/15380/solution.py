#!/usr/bin/env python3
"""Fill column B from a token in column A matched against the 'codes2'/'month' ranges."""
import re
import sys

import openpyxl
from openpyxl.utils import range_boundaries


def norm(value):
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def resolve_range(wb, name, default_col_letter, sheet):
    """Return (first_row, last_row, column) for a named range, with a column fallback."""
    if name in wb.defined_names:
        try:
            for sheet_name, ref in wb.defined_names[name].destinations:
                if not ref or '#' in ref:
                    continue
                target = wb[sheet_name]
                min_col, min_row, max_col, max_row = range_boundaries(ref.replace('$', ''))
                return min_row, max_row, min_col, target
        except Exception:
            pass
    # fallback: use the rows of the sheet that hold data, column given by default_col_letter
    col = openpyxl.utils.column_index_from_string(default_col_letter)
    rows = [r for r in range(sheet.max_row, 1, -1)
            if any(sheet.cell(row=r, column=c).value is not None
                   for c in range(1, sheet.max_column + 1))]
    if not rows:
        return 3, 3, col, sheet
    return min(rows), max(rows), col, sheet


def find_in_text(text, codes):
    """Return the code contained in text, preferring whole underscore/digit-delimited tokens."""
    if text is None:
        return None
    tokens = [t for t in re.split(r'[^0-9A-Za-z]+', str(text)) if t]
    for token in tokens:
        for code in codes:
            if token.upper() == code.upper():
                return code
    # no exact token: fall back to a delimited substring search
    for token in tokens:
        for code in codes:
            if code and re.fullmatch(r'\d+', code) and re.search(rf'(?<!\d){re.escape(code)}(?!\d)', token):
                return code
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit('usage: solution.py <input.xlsx> <output.xlsx>')
    in_path, out_path = sys.argv[1], sys.argv[2]

    wb = openpyxl.load_workbook(in_path)
    ws = wb[wb.sheetnames[0]]

    _, _, codes_col, codes_sheet = resolve_range(wb, 'codes2', 'D', ws)
    m_first, m_last, month_col, months_sheet = resolve_range(wb, 'month', 'E', ws)

    codes, months = [], {}
    for row in range(m_first, m_last + 1):
        code = norm(codes_sheet.cell(row=row, column=codes_col).value)
        month = months_sheet.cell(row=row, column=month_col).value
        if code is None or month is None:
            continue
        codes.append(code)
        months.setdefault(code, month)
    if not codes:
        sys.exit("could not read any values from the 'codes2' range")

    for row in range(m_first, m_last + 1):
        source = ws.cell(row=row, column=1).value
        code = find_in_text(source, codes)
        ws.cell(row=row, column=2).value = months.get(code) if code is not None else None

    wb.save(out_path)


if __name__ == '__main__':
    main()
