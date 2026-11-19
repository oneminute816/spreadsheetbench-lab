#!/usr/bin/env python3
"""Aggregate the ranges in RANGES into the matching tables in LISTS."""
import sys
from collections import OrderedDict
from datetime import date, datetime

import openpyxl
import re
import zipfile
from xml.etree import ElementTree as ET


def date_key(value):
    """Return a comparison key for a date cell.

    The source sheet can contain real Excel dates and date strings.  Treat the
    same calendar date as equal regardless of how it is stored in the cell.
    """
    if isinstance(value, datetime):
        return ("date", value.date().isoformat())
    if isinstance(value, date):
        return ("date", value.isoformat())
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return ("date", datetime.strptime(text, fmt).date().isoformat())
            except ValueError:
                pass
        return ("text", text)
    return ("value", value)


def find_list_tables(ws):
    """Locate the title/header/data blocks in the LISTS sheet."""
    titles = []
    for row in range(1, ws.max_row + 1):
        value = ws.cell(row, 3).value
        if isinstance(value, str) and value.strip():
            # A block header is followed by the SN/DATE/REF/AMOUNTS header.
            for header_row in range(row + 1, min(row + 5, ws.max_row + 1)):
                if (str(ws.cell(header_row, 1).value).strip().upper() in {"SN", "S.N"}
                        and str(ws.cell(header_row, 2).value).strip().upper() == "DATE"
                        and str(ws.cell(header_row, 3).value).strip().upper() == "REF"):
                    titles.append((row, value.strip(), header_row))
                    break

    tables = []
    for i, (title_row, title, header_row) in enumerate(titles):
        next_title_row = titles[i + 1][0] if i + 1 < len(titles) else ws.max_row + 1
        total_row = None
        for row in range(header_row + 1, next_title_row):
            if str(ws.cell(row, 1).value).strip().upper() == "TOTAL":
                total_row = row
                break
        if total_row is None:
            total_row = header_row + 1
        tables.append({
            "title_row": title_row,
            "title": title,
            "header_row": header_row,
            "data_start": header_row + 1,
            "old_total_row": total_row,
            "next_title_row": next_title_row,
        })
    return tables


def read_range_sections(ws, wanted_titles):
    """Read source data for every title in wanted_titles from RANGES."""
    # First find title rows.  In RANGES the title occupies column C, the next
    # row contains the column headers, and the records follow.
    title_rows = OrderedDict((title, []) for title in wanted_titles)
    all_title_rows = []
    for row in range(1, ws.max_row + 1):
        value = ws.cell(row, 3).value
        if isinstance(value, str):
            clean = value.strip().upper()
            for title in wanted_titles:
                if clean == title.upper():
                    title_rows[title].append(row)
                    all_title_rows.append(row)
                    break

    result = OrderedDict()
    for title, rows in title_rows.items():
        records = []
        for title_row in rows:
            header_row = None
            for row in range(title_row + 1, min(title_row + 5, ws.max_row + 1)):
                if (str(ws.cell(row, 1).value).strip().upper() in {"SN", "S.N"}
                        and str(ws.cell(row, 2).value).strip().upper() == "DATE"
                        and str(ws.cell(row, 4).value).strip().upper() == "REF"
                        and str(ws.cell(row, 5).value).strip().upper() == "AMOUNTS"):
                    header_row = row
                    break
            if header_row is None:
                continue

            # End this block at the next title row (or the end of the sheet).
            later_title_rows = [r for r in all_title_rows if r > title_row]
            end_row = min(later_title_rows) - 1 if later_title_rows else ws.max_row
            for row in range(header_row + 1, end_row + 1):
                dt = ws.cell(row, 2).value
                ref = ws.cell(row, 4).value
                amount = ws.cell(row, 5).value
                if dt is None or ref is None or amount is None:
                    continue
                if isinstance(amount, str):
                    try:
                        amount = float(amount.replace(",", "").strip())
                    except ValueError:
                        continue
                records.append((dt, ref, amount))
        result[title] = records
    return result


def aggregate(records):
    """Combine records having the same DATE and REF, preserving source order."""
    groups = OrderedDict()
    for dt, ref, amount in records:
        key = (date_key(dt), ref)
        if key not in groups:
            groups[key] = [dt, ref, 0]
        groups[key][2] += amount
    return list(groups.values())


def copy_row_style(ws, source_row, target_row):
    """Copy basic row styling when a rebuilt table needs more rows."""
    if source_row == target_row:
        return
    for col in range(1, 5):
        src = ws.cell(source_row, col)
        dst = ws.cell(target_row, col)
        if src.has_style:
            dst._style = src._style


def rebuild_tables(ws, tables, source_sections):
    totals = []
    for table in tables:
        title = table["title"]
        records = aggregate(source_sections.get(title, []))
        start = table["data_start"]
        old_total = table["old_total_row"]
        boundary = table["next_title_row"]

        # Keep a copy of the old table's styles before clearing its contents.
        template_data_style_row = start
        template_total_style_row = old_total

        # Delete all old range data and the old TOTAL row contents, but leave
        # the table title/header rows and untouched spacer rows intact.
        for row in range(start, boundary):
            for col in range(1, 5):
                ws.cell(row, col).value = None

        for i, (dt, ref, amount) in enumerate(records):
            row = start + i
            if row != start:
                copy_row_style(ws, template_data_style_row, row)
            ws.cell(row, 1).value = i + 1
            ws.cell(row, 2).value = dt
            ws.cell(row, 3).value = ref
            ws.cell(row, 4).value = amount

        total_row = start + len(records)
        copy_row_style(ws, template_total_style_row, total_row)
        ws.cell(total_row, 1).value = "TOTAL"
        ws.cell(total_row, 2).value = None
        ws.cell(total_row, 3).value = None
        if records:
            total_value = sum(item[2] for item in records)
            ws.cell(total_row, 4).value = f"=SUM(D{start}:D{total_row - 1})"
            totals.append((total_row, total_value))
        else:
            ws.cell(total_row, 4).value = None
    return totals


def add_formula_cache(path, sheet_name, cached_totals):
    """Keep the formulas while also storing their computed values in the XLSX.

    This makes the result readable both by formula-aware and data-only readers.
    """
    if not cached_totals:
        return
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    sheet_key = f"{{{main_ns}}}sheet"
    rid_key = f"{{{rel_ns}}}id"

    with zipfile.ZipFile(path, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    workbook_root = ET.fromstring(files["xl/workbook.xml"])
    sheet_el = next(el for el in workbook_root.iter(sheet_key)
                    if el.get("name") == sheet_name)
    rid = sheet_el.get(rid_key)
    rels_root = ET.fromstring(files["xl/_rels/workbook.xml.rels"])
    rel_el = next(el for el in rels_root.iter(f"{{{pkg_rel_ns}}}Relationship")
                  if el.get("Id") == rid)
    sheet_path = rel_el.get("Target").lstrip("/")
    if not sheet_path.startswith("xl/"):
        sheet_path = "xl/" + sheet_path

    xml = files[sheet_path].decode("utf-8")
    for row, cached_value in cached_totals:
        ref = f"D{row}"
        pattern = (r'(<c\b[^>]*\br="' + re.escape(ref) +
                   r'"[^>]*>\s*<f[^>]*>[^<]*</f>)\s*<v\s*/>')
        replacement = r'\1<v>' + str(cached_value) + r'</v>'
        xml, count = re.subn(pattern, replacement, xml, count=1)
        if count == 0:
            # Some writers omit the empty value element entirely.
            pattern2 = (r'(<c\b[^>]*\br="' + re.escape(ref) +
                        r'"[^>]*>\s*<f[^>]*>[^<]*</f>)(\s*</c>)')
            xml = re.sub(pattern2, r'\1<v>' + str(cached_value) + r'</v>\2',
                         xml, count=1)
    files[sheet_path] = xml.encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py INPUT.xlsx OUTPUT.xlsx")
    input_path, output_path = sys.argv[1], sys.argv[2]

    wb = openpyxl.load_workbook(input_path)
    ranges_ws = wb["RANGES"]
    lists_ws = wb["LISTS"]

    tables = find_list_tables(lists_ws)
    titles = [table["title"] for table in tables]
    sections = read_range_sections(ranges_ws, titles)
    totals = rebuild_tables(lists_ws, tables, sections)
    wb.save(output_path)
    add_formula_cache(output_path, "LISTS", totals)


if __name__ == "__main__":
    main()
