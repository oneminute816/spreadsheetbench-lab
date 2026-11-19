import sys
import re
from collections import OrderedDict
from copy import copy
from datetime import date, datetime

from openpyxl import load_workbook


def norm_text(value):
    return re.sub(r"\s+", " ", str(value).strip()).upper() if value is not None else ""


def date_key(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                pass
        return s.upper()
    return str(value)


def find_sections(ws, names):
    """Return title -> (title_row, header_row, next_title_row) for titled tables."""
    wanted = {norm_text(n) for n in names}
    rows = []
    for r in range(1, ws.max_row):
        title = ws.cell(r, 3).value
        if norm_text(title) not in wanted:
            continue
        header = {norm_text(ws.cell(r + 1, c).value) for c in range(1, ws.max_column + 1)}
        if "DATE" in header and "REF" in header and ("AMOUNT" in header or "AMOUNTS" in header):
            rows.append((r, title))
    result = {}
    for i, (r, title) in enumerate(rows):
        nxt = rows[i + 1][0] if i + 1 < len(rows) else ws.max_row + 1
        result[norm_text(title)] = (r, r + 1, nxt)
    return result


def source_groups(ws, title_row, next_title_row):
    header_row = title_row + 1
    headers = {norm_text(ws.cell(header_row, c).value): c for c in range(1, ws.max_column + 1)}
    date_col = headers.get("DATE", 2)
    ref_col = headers.get("REF", 4)
    amt_col = headers.get("AMOUNTS", headers.get("AMOUNT", 5))

    groups = OrderedDict()
    for r in range(header_row + 1, next_title_row):
        d = ws.cell(r, date_col).value
        ref = ws.cell(r, ref_col).value
        amt = ws.cell(r, amt_col).value
        if d is None or ref is None or amt is None or isinstance(amt, str):
            continue
        key = (date_key(d), norm_text(ref))
        if key not in groups:
            groups[key] = {"date": d, "ref": ref, "amount": 0}
        groups[key]["amount"] += amt
    for item in groups.values():
        if isinstance(item["amount"], float) and item["amount"].is_integer():
            item["amount"] = int(item["amount"])
    return list(groups.values())


def copy_style(src_style, dst):
    dst._style = copy(src_style)


def main(in_path, out_path):
    wb = load_workbook(in_path)
    src = wb["RANGES"]
    dst = wb["LISTS"]
    names = ["STAGE", "DATA", "OPERATION"]

    src_sections = find_sections(src, names)
    dst_sections = find_sections(dst, names)

    # Capture the completed STAGE table's data and TOTAL formatting as the template.
    stage_header = dst_sections["STAGE"][1]
    data_styles = [copy(dst.cell(stage_header + 1, c)._style) for c in range(1, 5)]
    total_styles = [copy(dst.cell(stage_header + 8, c)._style) for c in range(1, 5)]

    # Delete all prior table content in each LISTS section, leaving titles/headers intact.
    for name in names:
        if name not in dst_sections:
            continue
        _, header_row, next_title_row = dst_sections[name]
        for r in range(header_row + 1, next_title_row):
            for c in range(1, 5):
                dst.cell(r, c).value = None

    # Populate each list from its corresponding range table.
    for name in names:
        if name not in src_sections or name not in dst_sections:
            continue
        title_row, header_row, next_title_row = dst_sections[name]
        _, _, src_next = src_sections[name]
        items = source_groups(src, src_sections[name][0], src_next)

        first_data_row = header_row + 1
        for i, item in enumerate(items):
            r = first_data_row + i
            values = [i + 1, item["date"], item["ref"], item["amount"]]
            for c, value in enumerate(values, 1):
                cell = dst.cell(r, c)
                cell.value = value
                copy_style(data_styles[c - 1], cell)

        total_row = first_data_row + len(items)
        dst.cell(total_row, 1).value = "TOTAL"
        dst.cell(total_row, 2).value = None
        dst.cell(total_row, 3).value = None
        if items:
            dst.cell(total_row, 4).value = f"=SUM(D{first_data_row}:D{total_row - 1})"
        else:
            dst.cell(total_row, 4).value = 0
        for c in range(1, 5):
            copy_style(total_styles[c - 1], dst.cell(total_row, c))

    wb.save(out_path)



if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python solution.py <input_workbook> <output_workbook>")
    main(sys.argv[1], sys.argv[2])
