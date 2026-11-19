#!/usr/bin/env python3
"""Count, for each company, how many of the countries listed in Table-1 it operates in
(i.e. has more than 0 employees in that country).

Usage: solution.py <input.xlsx> <output.xlsx>
"""
import re
import sys
import zipfile

import openpyxl
from openpyxl.utils import get_column_letter

def find_label(ws, label):
    """Return (row, column) of the first cell whose stripped text equals `label`."""
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.strip().lower() == label.lower():
                return cell.row, cell.column
    raise ValueError(f"label {label!r} not found in sheet {ws.title!r}")


def sheet_xml_path(zf, sheet_name):
    """Resolve the worksheet XML part for a given sheet name."""
    wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
    rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    rid = re.search(r'<sheet[^>]*name="%s"[^>]*r:id="([^"]+)"' % re.escape(sheet_name), wb_xml)
    if not rid:
        rid = re.search(r'<sheet[^>]*r:id="([^"]+)"[^>]*name="%s"' % re.escape(sheet_name), wb_xml)
    target = re.search(r'Id="%s"[^>]*Target="([^"]+)"' % re.escape(rid.group(1)), rels) \
        or re.search(r'Target="([^"]+)"[^>]*Id="%s"' % re.escape(rid.group(1)), rels)
    path = target.group(1).lstrip("/")
    return path if path.startswith("xl/") else "xl/" + path


def inject_cached_values(path, sheet_name, values):
    """Store results as cached values next to the formulas.

    openpyxl writes formulas without results, so value-only readers (pandas,
    data_only=True) would see empty cells. Injecting <v> keeps the formula live
    in Excel while making the workbook readable without recalculation.
    """
    with zipfile.ZipFile(path) as zf:
        part = sheet_xml_path(zf, sheet_name)
        xml = zf.read(part).decode("utf-8")
        entries = [(i, zf.read(i.filename)) for i in zf.infolist()]

    for coord, val in values.items():
        # openpyxl leaves an empty <v/> placeholder; swap in the computed result.
        pattern = re.compile(
            r'(<c r="%s"[^>]*>\s*<f>.*?</f>)\s*(?:<v\s*/>|<v>[^<]*</v>)?\s*(</c>)' % coord,
            re.S)
        if not pattern.search(xml):
            raise ValueError(f"formula cell {coord} not found while caching result")
        xml = pattern.sub(lambda m: f"{m.group(1)}<v>{val}</v>{m.group(2)}", xml, count=1)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for info, data in entries:
            zf.writestr(info, xml.encode("utf-8") if info.filename == part else data)


def main(src, dst):
    wb = openpyxl.load_workbook(src)
    ws = wb.active

    # --- Table-1: list of countries of interest -------------------------------
    ctry_hdr_row, ctry_col = find_label(ws, "Country")
    comp_hdr_row, comp_col = find_label(ws, "Company")
    res_col = find_label(ws, "No of countries")[1]

    countries = []
    for r in range(ctry_hdr_row + 1, comp_hdr_row):  # Table-1 sits above Table-2
        v = ws.cell(row=r, column=ctry_col).value
        if isinstance(v, str) and v.strip():
            countries.append(v.strip())
    if not countries:
        raise ValueError("no countries found in Table-1")

    ctry_first = ctry_hdr_row + 1
    ctry_last = ctry_first + len(countries) - 1
    ctry_letter = get_column_letter(ctry_col)
    ctry_range = f"${ctry_letter}${ctry_first}:${ctry_letter}${ctry_last}"

    # --- Table-2: company rows x country columns -----------------------------
    ctry_cols = [c for c in range(comp_col + 1, res_col)
                 if isinstance(ws.cell(row=comp_hdr_row, column=c).value, str)
                 and ws.cell(row=comp_hdr_row, column=c).value.strip()]
    if not ctry_cols:
        raise ValueError("no country columns found in the company table")
    first_cc, last_cc = ctry_cols[0], ctry_cols[-1]
    hdr_range = (f"${get_column_letter(first_cc)}${comp_hdr_row}:"
                 f"${get_column_letter(last_cc)}${comp_hdr_row}")

    wanted = {c.strip().lower() for c in countries}
    cached = {}
    row = comp_hdr_row + 1
    while isinstance(ws.cell(row=row, column=comp_col).value, str) \
            and ws.cell(row=row, column=comp_col).value.strip():
        company = ws.cell(row=row, column=comp_col).value.strip()

        total = 0
        for c in ctry_cols:
            if str(ws.cell(row=comp_hdr_row, column=c).value).strip().lower() not in wanted:
                continue
            v = ws.cell(row=row, column=c).value
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                total += 1

        ws.cell(row=row, column=res_col).value = (
            f"=SUMPRODUCT(({get_column_letter(first_cc)}{row}:"
            f"{get_column_letter(last_cc)}{row}>0)"
            f"*ISNUMBER(MATCH({hdr_range},{ctry_range},0)))"
        )
        cached[f"{get_column_letter(res_col)}{row}"] = total
        print(f"{get_column_letter(res_col)}{row} = {total} ({company})")
        row += 1

    if not cached:
        raise ValueError("no company rows found in Table-2")

    wb.calculation.fullCalcOnLoad = True
    wb.save(dst)
    inject_cached_values(dst, ws.title, cached)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: solution.py <input.xlsx> <output.xlsx>")
    main(sys.argv[1], sys.argv[2])
