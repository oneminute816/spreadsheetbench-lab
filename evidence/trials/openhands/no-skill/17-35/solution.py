#!/usr/bin/env python3
"""Filter the invoice table A6:E315 by the start/end dates held in I2 / J2.

The filtered rows are written to I6:M295 with readable dd/mm/yyyy dates.
Cells M2 / N2 (the ">=" and "<=" criteria helpers that are linked to I2 / J2)
are rebuilt with TEXT(...) so they show e.g. ">=22/03/2023" instead of an
Excel serial number, which is what breaks native date filtering.

usage: solution.py <input.xlsx> <output.xlsx>
"""

import datetime as dt
import re
import sys

import openpyxl

SHEET = "FILTER 5b"
DATA_FIRST_ROW, DATA_LAST_ROW = 6, 315
OUT_FIRST_ROW, OUT_LAST_ROW = 6, 295
OUT_FIRST_COL, OUT_LAST_COL = 9, 13          # I..M
DATE_FMT = "dd/mm/yyyy"
MONEY_FMT = '_-* #,##0.00\\ "€"_-;\\-* #,##0.00\\ "€"_-;_-* "-"??\\ "€"_-;_-@_-'
OUT_COL_FORMATS = {9: DATE_FMT, 10: "General", 11: "000000000",
                   12: "General", 13: MONEY_FMT}
DATE_TEXT_FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
                     "%Y-%m-%d", "%d.%m.%Y", "%d %m %Y", "%m/%d/%Y")
CRITERION_OP = re.compile(r"^\s*(>=|<=|<>|>|<|=)?\s*(.*?)\s*$")


def to_date(value):
    """datetime / Excel serial / text -> date, or None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=float(value))).date()
    for fmt in DATE_TEXT_FORMATS:
        try:
            return dt.datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def split_criterion(value):
    """">=22/03/2023" -> (">=", date(2023, 3, 22))."""
    if value is None:
        return None, None
    if isinstance(value, (dt.date, dt.datetime, int, float)) and not isinstance(value, bool):
        return None, to_date(value)
    op, _, rest = CRITERION_OP.match(str(value)).groups()
    return op, to_date(rest)


def read_bounds(ws_formula, ws_cached):
    """Start/end from I2/J2, falling back to the M2/N2 helper text."""
    start = to_date(ws_cached["I2"].value) or to_date(ws_formula["I2"].value)
    end = to_date(ws_cached["J2"].value) or to_date(ws_formula["J2"].value)
    if start is None:
        start = split_criterion(ws_cached["M2"].value)[1]
    if end is None:
        end = split_criterion(ws_cached["N2"].value)[1]
    return start, end


def in_range(day, start, end):
    return (start is None or day >= start) and (end is None or day <= end)


def _cache_text_values(xlsx_path, cached):
    """openpyxl writes no cached results for formulas; add them for M2/N2 so
    value-only readers see ">=22/03/2023" instead of an empty cell."""
    import shutil
    import tempfile
    import zipfile
    from xml.sax.saxutils import escape

    with zipfile.ZipFile(xlsx_path) as src:
        names = src.namelist()
        sheets = [n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]
        data = {n: src.read(n) for n in names}

    for sheet in sheets:
        xml = data[sheet].decode("utf-8")
        changed = False
        for ref, text in cached.items():
            pattern = re.compile(
                r'<c r="%s"([^>]*)>(<f>.*?</f>)(<v\s*/>|<v></v>)' % ref, re.S)
            new, hits = pattern.subn(
                lambda m: '<c r="%s"%s t="str">%s<v>%s</v>'
                          % (ref, m.group(1), m.group(2), escape(text)), xml)
            if hits:
                xml, changed = new, True
        if changed:
            data[sheet] = xml.encode("utf-8")

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in names:
            dst.writestr(name, data[name])
    shutil.move(tmp, xlsx_path)


def main(in_path, out_path):
    wb = openpyxl.load_workbook(in_path)                       # formulas preserved
    ws = wb[SHEET] if SHEET in wb.sheetnames else wb.active
    cached = openpyxl.load_workbook(in_path, data_only=True)[ws.title]

    start, end = read_bounds(ws, cached)
    if start is None and end is None:
        raise SystemExit("No usable start/end date in I2/J2 (or M2/N2).")

    # criteria cells must be real dates displayed as dd/mm/yyyy
    for ref, value in (("I2", start), ("J2", end)):
        if value is not None:
            ws[ref] = dt.datetime.combine(value, dt.time())
        ws[ref].number_format = DATE_FMT
    # helper cells: text criteria that stay readable (no serial numbers)
    ws["M2"] = f'=">="&TEXT(I2,"{DATE_FMT}")'
    ws["N2"] = f'="<="&TEXT(J2,"{DATE_FMT}")'

    for row in ws.iter_rows(min_row=OUT_FIRST_ROW, max_row=OUT_LAST_ROW,
                            min_col=OUT_FIRST_COL, max_col=OUT_LAST_COL):
        for cell in row:
            cell.value = None

    out_row = OUT_FIRST_ROW
    for src_row in range(DATA_FIRST_ROW, DATA_LAST_ROW + 1):
        day = to_date(cached.cell(src_row, 1).value)
        if day is None or not in_range(day, start, end):
            continue
        if out_row > OUT_LAST_ROW:
            break
        for offset in range(5):
            value = cached.cell(src_row, 1 + offset).value
            if offset == 0:
                value = dt.datetime.combine(day, dt.time())
            target = ws.cell(out_row, OUT_FIRST_COL + offset)
            target.value = value
            target.number_format = OUT_COL_FORMATS[OUT_FIRST_COL + offset]
        out_row += 1


    wb.save(out_path)
    cached_text = {}
    if start is not None:
        cached_text["M2"] = ">=" + start.strftime("%d/%m/%Y")
    if end is not None:
        cached_text["N2"] = "<=" + end.strftime("%d/%m/%Y")
    _cache_text_values(out_path, cached_text)
    print(f"{out_row - OUT_FIRST_ROW} rows ({start} .. {end}) -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py <input.xlsx> <output.xlsx>")
    main(sys.argv[1], sys.argv[2])
